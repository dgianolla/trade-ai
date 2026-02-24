from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import verificar_api_key
from app.api.v1.plantas.schemas import ProcessarPlantaRequest, ProcessamentoPlantaV2Response
from app.api.v1.plantas.tasks import processar_planta_task
from app.models.processamento import Processamento, TipoProcessamento, StatusProcessamento
import uuid

router = APIRouter()

@router.post(
    "/processar",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Cadastrar Mapeamento de Planta"
)
async def processar_planta(
    request: ProcessarPlantaRequest,
    db: Session = Depends(get_db),
    api_key = Depends(verificar_api_key)
):
    """
    Processa uma planta de loja para verificar share e rupturas.
    O processamento é assíncrono. Use o processamento_id para consultar o resultado.
    """
    processamento_id = uuid.uuid4()
    
    meta = {
        "loja_id": request.loja_id,
        "modelo_llm": request.modelo_llm
    }
    
    processamento = Processamento(
        id=processamento_id,
        tipo=TipoProcessamento.PLANTAS,
        loja_id=request.loja_id,
        nome_arquivo=request.nome_arquivo,
        imagem_url="pendente", # Será preenchido assincronamente pelo celery
        status=StatusProcessamento.PROCESSANDO,
        meta_dados=meta
    )
    db.add(processamento)
    db.commit()

    # Enfileirar task
    processar_planta_task.apply_async(
        args=[str(processamento_id), request.imagem_base64, request.nome_arquivo, request.loja_id, request.modelo_llm],
        queue='plantas'
    )

    return {
        "sucesso": True,
        "processamento_id": str(processamento_id),
        "status": "processando",
        "mensagem": f"Cadastramento de Planta V2 iniciado. Consulte o resultado em /api/v1/plantas/processamentos/{processamento_id}",
        "tempo_estimado_segundos": 20
    }

@router.get(
    "/processamentos/{processamento_id}",
    summary="Consultar Resultado do Mapeamento de Planta"
)
async def obter_processamento_planta(
    processamento_id: str,
    db: Session = Depends(get_db),
    api_key = Depends(verificar_api_key)
):
    """Consulta o resultado de um processamento/mapeamento de planta."""
    processamento = db.query(Processamento).filter(
        Processamento.id == processamento_id,
        Processamento.tipo == TipoProcessamento.PLANTAS
    ).first()

    if not processamento:
        raise HTTPException(status_code=404, detail="Processamento não encontrado")

    resultado_obj = processamento.resultado.get("plantas") if processamento.resultado else None

    # Mapeamento de Status Interno x Externo
    status_map = {
        StatusProcessamento.PROCESSANDO: "PROCESSANDO",
        StatusProcessamento.CONCLUIDO: "SUCESSO",
        StatusProcessamento.ERRO: "ERRO"
    }

    status_final = status_map.get(processamento.status, "ERRO")
    loja_id = processamento.loja_id or ""
    alertas = []
    enderecos = []
    relatorio = None

    if status_final == "ERRO":
        alertas.append(processamento.erro_mensagem or "Erro desconhecido")

    if resultado_obj:
        enderecos = resultado_obj.get("enderecos", [])
        alertas.extend(resultado_obj.get("alertas", []))
        
        # O relatorio será mapeado caso o parser do serviço preencha
        rel = resultado_obj.get("relatorio", {})
        if rel:
            relatorio = {
                "quantidade_detectada": rel.get("quantidade_detectada", 0),
                "quantidade_cadastravel": rel.get("quantidade_cadastravel", 0),
                "quantidade_descartada": rel.get("quantidade_descartada", 0)
            }

    # Mantendo o encapsulamento padrão de coleções desejado ou apenas o Objeto V2 (Vamos retornar o Objeto conforme PMC)
    return ProcessamentoPlantaV2Response(
        loja_id=loja_id,
        planta_id=str(processamento.id),
        status=status_final,
        alertas=alertas,
        enderecos=enderecos,
        relatorio=relatorio
    )


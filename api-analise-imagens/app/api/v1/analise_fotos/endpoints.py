from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import verificar_api_key
from app.api.v1.analise_fotos.schemas import (
    AuditarPDVRequest,
    AuditarPDVResponse,
    ProcessamentoAuditoriaPDVResponse
)
from app.api.v1.analise_fotos.tasks import processar_auditoria_pdv_task
from app.models.processamento import Processamento, TipoProcessamento, StatusProcessamento
import uuid

router = APIRouter()

    # Removed the /processar endpoint to only keep /auditar-pdv


@router.post(
    "/auditar-pdv",
    response_model=AuditarPDVResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Auditar Material Promocional de PDV",
    description="""
    Analisa uma foto de material promocional (ativo de PDV) e retorna auditoria completa
    avaliando posicionamento, visibilidade, integridade e conteúdo.

    O processamento é assíncrono. Use o processamento_id retornado para consultar o resultado.
    """
)
async def auditar_pdv(
    request: AuditarPDVRequest,
    db: Session = Depends(get_db),
    api_key = Depends(verificar_api_key)
):
    """
    Endpoint para auditoria de material promocional de PDV.

    Fluxo:
    1. Valida URL da imagem
    2. Cria registro no banco
    3. Enfileira task assíncrona
    4. Retorna processamento_id
    """

    # Criar registro no banco
    processamento_id = uuid.uuid4()
    # Safely building metadata
    meta = {
        "tipo_analise": "auditoria_pdv",
        "modelo_llm": "gpt-4o",
    }
        
    processamento = Processamento(
        id=processamento_id,
        tipo=TipoProcessamento.ANALISE_FOTOS,
        loja_id=None,
        nome_arquivo=str(request.imagem_url).split("/")[-1],
        imagem_url=str(request.imagem_url),
        status=StatusProcessamento.PROCESSANDO,
        meta_dados=meta
    )
    db.add(processamento)
    db.commit()

    # Enfileirar task
    processar_auditoria_pdv_task.apply_async(
        args=[
            str(processamento_id),
            str(request.imagem_url),
            "gpt-4o"
        ],
        queue='analise_fotos'
    )

    return AuditarPDVResponse(
        sucesso=True,
        processamento_id=str(processamento_id),
        status="processando",
        mensagem=f"Auditoria iniciada. Consulte o resultado em /api/v1/processamentos/{processamento_id}",
        tempo_estimado_segundos=15
    )

@router.get(
    "/auditorias/{processamento_id}",
    summary="Consultar Resultado de Auditoria"
)
async def obter_auditoria_pdv(
    processamento_id: str,
    db: Session = Depends(get_db),
    api_key = Depends(verificar_api_key)
):
    """Consulta o resultado de uma auditoria de PDV."""

    processamento = db.query(Processamento).filter(
        Processamento.id == processamento_id,
        Processamento.tipo == TipoProcessamento.ANALISE_FOTOS
    ).first()

    if not processamento:
        raise HTTPException(
            status_code=404,
            detail="Auditoria não encontrada"
        )

    # Expected output format matching n8n standard:
    # [ { "output": { ... fields ... } } ]
    
    resultado_obj = processamento.resultado.get("auditoria") if processamento.resultado else None
    
    # Se ainda estiver processando ou der erro, e não tiver resultado, retorne no padrão anterior ou informe
    if not resultado_obj:
        return ProcessamentoAuditoriaPDVResponse(
            processamento_id=str(processamento.id),
            status=processamento.status.value,
            imagem_url=processamento.imagem_url,
            resultado=None,
            erro_mensagem=processamento.erro_mensagem,
            tempo_processamento_ms=processamento.tempo_processamento_ms,
            metadata=processamento.meta_dados,
            created_at=processamento.created_at.isoformat(),
            updated_at=processamento.updated_at.isoformat()
        )
    
    # Custom format demanded by the user
    return [
        {
            "output": {
                "nota": resultado_obj.get("nota"),
                "status": resultado_obj.get("status"),
                "tipo_ativo": resultado_obj.get("tipo_ativo"),
                "marca": resultado_obj.get("marca"),
                "visualizacao_ok": resultado_obj.get("visualizacao_ok"),
                "parecer": resultado_obj.get("parecer"),
                "problemas": resultado_obj.get("problemas", []),
                "recomendacao": resultado_obj.get("recomendacao"),
                "preço": resultado_obj.get("preço") or resultado_obj.get("preco")
            }
        }
    ]

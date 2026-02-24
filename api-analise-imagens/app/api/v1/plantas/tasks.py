import time
import requests
from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.services.storage_service import StorageService
from app.api.v1.plantas.services import PlantasService
from app.models.processamento import Processamento, StatusProcessamento
from app.core.logging import logger

@celery_app.task(name='plantas.processar_imagem', bind=True, max_retries=3)
def processar_planta_task(
    self, 
    processamento_id: str, 
    imagem_base64: str, 
    nome_arquivo: str, 
    loja_id: str, 
    modelo_llm: str = "gpt-4o"
):
    """Task assíncrona para processar dados de planta a partir de imagem."""
    inicio = time.time()
    db = SessionLocal()

    import base64

    try:
        # 1. Transformar payload de Base64 para Bytes
        logger.info(f"[{processamento_id}] Decodificando imagem base64: {nome_arquivo}")
        imagem_bytes = base64.b64decode(imagem_base64)

        # 2. Salvar imagem no storage (MinIO)
        storage = StorageService()
        
        url_armazenada = storage.salvar_imagem(
            bucket="plantas",
            loja_id=loja_id,
            nome_arquivo=nome_arquivo,
            imagem_bytes=imagem_bytes
        )

        # 3. Executar o novo serviço de Plantas/Gôndola c/ OCR e LLM Híbrido
        plantas_service = PlantasService(db, modelo_llm=modelo_llm)
        resultado_auditoria = plantas_service.mapear_enderecos_planta(
            loja_id=loja_id,
            imagem_bytes=imagem_bytes
        )

        # 4. Atualizar banco
        tempo_ms = int((time.time() - inicio) * 1000)
        
        processamento = db.query(Processamento).filter_by(id=processamento_id).first()
        if processamento:
            processamento.imagem_url = url_armazenada
            processamento.resultado = {"plantas": resultado_auditoria}
            processamento.status = StatusProcessamento.CONCLUIDO
            processamento.tempo_processamento_ms = tempo_ms
            db.commit()

        return {"status": "success", "processamento_id": processamento_id}

    except Exception as e:
        logger.error(f"[{processamento_id}] Erro no processamento de plantas: {str(e)}")
        # Atualizar status para erro
        processamento = db.query(Processamento).filter_by(id=processamento_id).first()
        if processamento:
            processamento.status = StatusProcessamento.ERRO
            processamento.erro_mensagem = str(e)
            db.commit()

        # Retry com backoff exponencial
        raise self.retry(exc=e, countdown=2 ** self.request.retries)

    finally:
        db.close()

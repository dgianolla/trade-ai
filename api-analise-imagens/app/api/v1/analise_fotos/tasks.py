from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.processamento import Processamento, StatusProcessamento
from app.api.v1.analise_fotos.services import AnalisePDVService
from app.services.storage_service import StorageService
import time
import requests

@celery_app.task(name='analise_fotos.processar_imagem', bind=True, max_retries=3)
def processar_analise_task(self, processamento_id: str, imagem_base64: str, nome_arquivo: str, tipo_analise: str, opcoes: dict):
    """Task assíncrona para processar análise de fotos."""
    db = SessionLocal()
    inicio = time.time()
    try:
        # Mocking the AI logic
        time.sleep(1) # Simulated delay
        tempo_ms = int((time.time() - inicio) * 1000)
        
        processamento = db.query(Processamento).filter_by(id=processamento_id).first()
        processamento.status = StatusProcessamento.CONCLUIDO
        processamento.tempo_processamento_ms = tempo_ms
        processamento.resultado = {
            "classificacao": {
                "categoria": "Mock Category",
                "subcategoria": "Mock Subcategory",
                "confidence": 0.99,
                "tags": ["mock"]
            }
        }
        db.commit()

        return {"status": "success", "processamento_id": processamento_id}
    except Exception as e:
        processamento = db.query(Processamento).filter_by(id=processamento_id).first()
        processamento.status = StatusProcessamento.ERRO
        processamento.erro_mensagem = str(e)
        db.commit()
        raise self.retry(exc=e, countdown=2 ** self.request.retries)
    finally:
        db.close()

@celery_app.task(name='analise_fotos.processar_auditoria_pdv', bind=True, max_retries=3)
def processar_auditoria_pdv_task(
    self,
    processamento_id: str,
    imagem_url: str,
    modelo_llm: str = "gpt-4o"
):
    """
    Task assíncrona para processar auditoria de PDV.

    Args:
        processamento_id: UUID do processamento
        imagem_url: URL da imagem a ser analisada
        modelo_llm: Modelo de LLM a usar
    """
    inicio = time.time()
    db = SessionLocal()

    try:
        # 1. Baixar imagem da URL
        response = requests.get(imagem_url, timeout=30)
        response.raise_for_status()
        imagem_bytes = response.content

        # 2. Salvar imagem no MinIO (backup)
        storage = StorageService()
        nome_arquivo = imagem_url.split("/")[-1]
        imagem_storage_url = storage.salvar_imagem(
            bucket="auditorias-pdv",
            loja_id=None,
            nome_arquivo=nome_arquivo,
            imagem_bytes=imagem_bytes
        )

        # 3. Chamar serviço de análise de PDV
        analise_service = AnalisePDVService(modelo_llm=modelo_llm)
        resultado_auditoria = analise_service.auditar_ativo_pdv(imagem_bytes)

        # 4. Calcular tempo de processamento
        tempo_ms = int((time.time() - inicio) * 1000)

        # 5. Atualizar banco com resultado
        processamento = db.query(Processamento).filter_by(id=processamento_id).first()
        processamento.imagem_url = imagem_storage_url
        processamento.resultado = {
            "auditoria": resultado_auditoria,
            "modelo_llm_usado": modelo_llm
        }
        processamento.status = StatusProcessamento.CONCLUIDO
        processamento.tempo_processamento_ms = tempo_ms
        db.commit()

        return {
            "status": "success",
            "processamento_id": processamento_id,
            "nota": resultado_auditoria["nota"]
        }

    except requests.exceptions.RequestException as e:
        # Erro ao baixar imagem
        processamento = db.query(Processamento).filter_by(id=processamento_id).first()
        processamento.status = StatusProcessamento.ERRO
        processamento.erro_mensagem = f"Erro ao baixar imagem: {str(e)}"
        db.commit()
        raise

    except Exception as e:
        # Erro genérico
        processamento = db.query(Processamento).filter_by(id=processamento_id).first()
        processamento.status = StatusProcessamento.ERRO
        processamento.erro_mensagem = str(e)
        db.commit()

        # Retry com backoff exponencial
        raise self.retry(exc=e, countdown=2 ** self.request.retries)

    finally:
        db.close()

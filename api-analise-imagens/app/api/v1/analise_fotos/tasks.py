import time
import requests
from app.core.celery_app import celery_app
from app.core.database import get_db_session
from app.models.processamento import Processamento, StatusProcessamento
from app.api.v1.analise_fotos.services import AnalisePDVService
from app.services.storage_service import StorageService


def _marcar_erro(processamento_id: str, mensagem: str) -> None:
    """Atualiza status para ERRO em uma sessão própria, sem depender de sessão anterior."""
    with get_db_session() as db:
        processamento = db.query(Processamento).filter_by(id=processamento_id).first()
        if processamento:
            processamento.status = StatusProcessamento.ERRO
            processamento.erro_mensagem = mensagem
            db.commit()


@celery_app.task(name='analise_fotos.processar_imagem', bind=True, max_retries=3)
def processar_analise_task(self, processamento_id: str, imagem_base64: str, nome_arquivo: str, tipo_analise: str, opcoes: dict):
    """Task assíncrona para processar análise de fotos."""
    inicio = time.time()
    try:
        time.sleep(1)  # Simulated delay
        tempo_ms = int((time.time() - inicio) * 1000)

        with get_db_session() as db:
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
        _marcar_erro(processamento_id, str(e))
        raise self.retry(exc=e, countdown=2 ** self.request.retries)


@celery_app.task(name='analise_fotos.processar_auditoria_pdv', bind=True, max_retries=3)
def processar_auditoria_pdv_task(
    self,
    processamento_id: str,
    imagem_url: str,
    modelo_llm: str = "gpt-4o-mini",
    nome_ativo: str = None
):
    """
    Task assíncrona para processar auditoria de PDV.

    Args:
        processamento_id: UUID do processamento
        imagem_url: URL da imagem a ser analisada
        modelo_llm: Modelo de LLM a usar
    """
    inicio = time.time()

    try:
        # 1. Baixar imagem da URL  (sem DB aberto)
        response = requests.get(imagem_url, timeout=30)
        response.raise_for_status()
        imagem_bytes = response.content

        # 2. Salvar imagem no MinIO  (sem DB aberto)
        storage = StorageService()
        nome_arquivo = imagem_url.split("/")[-1]
        imagem_storage_url = storage.salvar_imagem(
            bucket="auditorias-pdv",
            loja_id=None,
            nome_arquivo=nome_arquivo,
            imagem_bytes=imagem_bytes
        )

        # 3. Chamar LLM  (sem DB aberto — chamada mais longa da task)
        analise_service = AnalisePDVService(modelo_llm=modelo_llm)
        resultado_auditoria = analise_service.auditar_ativo_pdv(imagem_bytes, nome_ativo=nome_ativo)

        tempo_ms = int((time.time() - inicio) * 1000)

        # 4. Persistir resultado — DB aberto apenas aqui, operação rápida
        with get_db_session() as db:
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
        _marcar_erro(processamento_id, f"Erro ao baixar imagem: {str(e)}")
        raise

    except Exception as e:
        _marcar_erro(processamento_id, str(e))
        raise self.retry(exc=e, countdown=2 ** self.request.retries)

from datetime import datetime, timedelta
from app.core.celery_app import celery_app
from app.core.database import get_db_session
from app.core.logging import logger
from app.models.processamento import Processamento, StatusProcessamento

ZOMBIE_TIMEOUT_HORAS = 2


@celery_app.task(name='shared.cleanup_zumbis')
def cleanup_processamentos_zumbis():
    """
    Sweeper agendado: move para ERRO registros presos em PROCESSANDO há mais de
    ZOMBIE_TIMEOUT_HORAS. Previne poluição do banco e facilita auditorias.

    Rodado via Celery Beat (ver celery_app.beat_schedule).
    """
    limite = datetime.utcnow() - timedelta(hours=ZOMBIE_TIMEOUT_HORAS)

    with get_db_session() as db:
        zumbis = (
            db.query(Processamento)
            .filter(
                Processamento.status == StatusProcessamento.PROCESSANDO,
                Processamento.created_at < limite,
            )
            .all()
        )

        if not zumbis:
            logger.info("[SweepZumbi] Nenhum processamento zumbi encontrado.")
            return {"corrigidos": 0}

        ids = [str(z.id) for z in zumbis]
        logger.warning(f"[SweepZumbi] {len(zumbis)} zumbi(s) encontrado(s): {ids}")

        for proc in zumbis:
            proc.status = StatusProcessamento.ERRO
            proc.erro_mensagem = (
                f"Timeout de processamento excedido após {ZOMBIE_TIMEOUT_HORAS}h "
                f"(Zumbi Cleanup — {datetime.utcnow().isoformat()})"
            )

        db.commit()
        logger.info(f"[SweepZumbi] {len(zumbis)} registro(s) movido(s) para ERRO.")

    return {"corrigidos": len(ids), "ids": ids}

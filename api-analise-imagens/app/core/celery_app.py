from celery import Celery
from app.config import settings

celery_app = Celery(
    'analise_imagens',
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

# Configuração de filas especializadas
celery_app.conf.update(
    task_routes={
        'plantas.*': {'queue': 'plantas'},
        'analise_fotos.*': {'queue': 'analise_fotos'},
    },
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutos
    task_soft_time_limit=240,  # 4 minutos
)

# Auto-discover tasks
celery_app.autodiscover_tasks([
    'app.api.v1.plantas',
    'app.api.v1.analise_fotos'
])

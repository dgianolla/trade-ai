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

    # Reconexão ao broker no startup
    broker_connection_retry_on_startup=True,

    # Keepalive para evitar conexão TCP stale com o Redis
    broker_transport_options={
        'socket_keepalive': True,
        'socket_keepalive_options': {
            'TCP_KEEPIDLE': 60,   # inicia keepalive após 60s idle
            'TCP_KEEPINTVL': 10,  # envia probe a cada 10s
            'TCP_KEEPCNT': 5,     # desiste após 5 falhas consecutivas
        },
        'socket_connect_timeout': 5,
        'socket_timeout': 5,
    },

    # Reconexão automática ilimitada em caso de perda de conexão
    broker_connection_max_retries=None,
)

# Auto-discover tasks
celery_app.autodiscover_tasks([
    'app.api.v1.plantas',
    'app.api.v1.analise_fotos'
])

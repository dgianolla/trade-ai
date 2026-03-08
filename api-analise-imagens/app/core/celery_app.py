import socket
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
    # Nota: socket_timeout NÃO deve ser definido — interfere com BRPOP do kombu
    broker_transport_options={
        'socket_keepalive': True,
        'socket_keepalive_options': {
            socket.TCP_KEEPIDLE: 60,   # inicia keepalive após 60s idle
            socket.TCP_KEEPINTVL: 10,  # envia probe a cada 10s
            socket.TCP_KEEPCNT: 5,     # desiste após 5 falhas consecutivas
        },
        'socket_connect_timeout': 10,
    },

    # Reconexão automática ilimitada em caso de perda de conexão
    broker_connection_max_retries=None,

    # Retry de publish no producer (API) — evita silent drop de conexão stale
    # Sem isso, apply_async retorna sem erro mas a mensagem é descartada após idle
    task_publish_retry=True,
    task_publish_retry_policy={
        'max_retries': 3,
        'interval_start': 0.2,
        'interval_step': 0.2,
        'interval_max': 1.0,
    },
)

# Auto-discover tasks
celery_app.autodiscover_tasks([
    'app.api.v1.plantas',
    'app.api.v1.analise_fotos',
    'app.api.v1.shared',
])

# Agendamento do sweeper de zumbis (requer celery beat rodando)
celery_app.conf.beat_schedule = {
    'cleanup-zumbis-a-cada-hora': {
        'task': 'shared.cleanup_zumbis',
        'schedule': 3600.0,  # a cada 1 hora
    },
}

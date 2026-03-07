from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,       # testa conexão antes de usar — elimina stale connections
    pool_recycle=1800,        # recicla após 30 min, antes do firewall/NAT matar a TCP
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    connect_args={
        "options": "-c idle_in_transaction_session_timeout=30000"  # mata sessões esquecidas em transação após 30s
    }
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Dependency para uso via FastAPI Depends (endpoints)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_session():
    """Context manager para uso em Celery tasks e código imperativo."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

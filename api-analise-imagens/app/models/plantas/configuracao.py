from sqlalchemy import Column, String, JSON, DateTime
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
from app.models.base import Base

class PlantaConfiguracao(Base):
    __tablename__ = "plantas_configuracoes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    loja_id = Column(String(100), unique=True, nullable=False, index=True)
    mapeamento_tipos = Column(JSON, nullable=False)  # {"C": 1, "PG": 2}
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

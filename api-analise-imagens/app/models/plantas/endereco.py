from sqlalchemy import Column, String, Integer, Float, JSON, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
from app.models.base import Base

class PlantaEndereco(Base):
    __tablename__ = "plantas_enderecos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    processamento_id = Column(UUID(as_uuid=True), ForeignKey('processamentos.id'), nullable=False)
    codigo = Column(String(50), nullable=False)
    tipo_endereco_id = Column(Integer, nullable=False)
    categoria_id = Column(Integer, nullable=True)
    nome = Column(String(200), nullable=False)
    x_pct = Column(Float, nullable=False)
    y_pct = Column(Float, nullable=False)
    confidence = Column(Float, nullable=False)
    alertas = Column(JSON, default=[])
    created_at = Column(DateTime, default=datetime.utcnow)

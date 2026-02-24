from sqlalchemy import Column, String, JSON, DateTime, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
from app.models.base import Base

class AnaliseFotoResultado(Base):
    __tablename__ = "analise_fotos_resultados"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    processamento_id = Column(UUID(as_uuid=True), ForeignKey('processamentos.id'), nullable=False)
    tipo_analise = Column(String(50), nullable=False)  # 'classificacao', 'ocr', 'objetos'
    resultado = Column(JSON, nullable=False)
    confidence = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

from sqlalchemy import Column, String, Integer, JSON, Boolean, DateTime
from datetime import datetime
from app.models.base import Base

class PlantaCategoria(Base):
    __tablename__ = "plantas_categorias"

    id = Column(Integer, primary_key=True)
    nome = Column(String(100), nullable=False)
    sinonimos = Column(JSON, nullable=False)  # ["bebida", "refrigerante"]
    ativo = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

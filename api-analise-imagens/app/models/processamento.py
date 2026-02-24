from sqlalchemy import Column, String, Integer, JSON, DateTime, Text, Enum
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
import enum
from app.models.base import Base

class TipoProcessamento(str, enum.Enum):
    PLANTAS = "plantas"
    ANALISE_FOTOS = "analise_fotos"

class StatusProcessamento(str, enum.Enum):
    PROCESSANDO = "processando"
    CONCLUIDO = "concluido"
    ERRO = "erro"

class Processamento(Base):
    __tablename__ = "processamentos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tipo = Column(Enum(TipoProcessamento), nullable=False, index=True)
    loja_id = Column(String(100), nullable=True, index=True)  # Apenas para plantas
    nome_arquivo = Column(String(255), nullable=False)
    imagem_url = Column(Text, nullable=False)
    status = Column(Enum(StatusProcessamento), default=StatusProcessamento.PROCESSANDO, index=True)
    resultado = Column(JSON, nullable=True)  # Resultado específico por tipo
    erro_mensagem = Column(Text, nullable=True)
    tempo_processamento_ms = Column(Integer, nullable=True)
    meta_dados = Column(JSON, nullable=True)  # Dados adicionais flexíveis
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

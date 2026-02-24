from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import verificar_api_key
from app.models.processamento import Processamento
from typing import Optional

router = APIRouter()

@router.get("/")
async def listar_processamentos(
    tipo: Optional[str] = None,
    loja_id: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    api_key = Depends(verificar_api_key)
):
    query = db.query(Processamento)
    if tipo:
        query = query.filter(Processamento.tipo == tipo)
    if loja_id:
        query = query.filter(Processamento.loja_id == loja_id)
    if status:
        query = query.filter(Processamento.status == status)
    
    processamentos = query.all()
    return processamentos

@router.get("/{id}")
async def obter_processamento(
    id: str,
    db: Session = Depends(get_db),
    api_key = Depends(verificar_api_key)
):
    processamento = db.query(Processamento).filter(Processamento.id == id).first()
    if not processamento:
        raise HTTPException(status_code=404, detail="Processamento não encontrado")
    return processamento

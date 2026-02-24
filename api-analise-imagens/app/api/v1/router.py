from fastapi import APIRouter
from app.api.v1.plantas.endpoints import router as plantas_router
from app.api.v1.analise_fotos.endpoints import router as analise_router
from app.api.v1.shared.health import router as health_router
from app.api.v1.shared.processamentos import router as processamentos_router

api_v1_router = APIRouter()

# Módulo Plantas
api_v1_router.include_router(
    plantas_router,
    prefix="/plantas",
    tags=["🌿 Plantas - OCR"]
)

# Módulo Análise de Fotos
api_v1_router.include_router(
    analise_router,
    prefix="/analise-fotos",
    tags=["📸 Análise de Fotos"]
)

# Endpoints Compartilhados
api_v1_router.include_router(
    processamentos_router,
    prefix="/processamentos",
    tags=["📊 Processamentos"]
)

api_v1_router.include_router(
    health_router,
    tags=["❤️ Health"]
)

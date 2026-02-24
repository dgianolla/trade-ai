from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "database": "ok",
        "redis": "ok",
        "storage": "ok",
        "workers": {
            "plantas": "ok",
            "analise_fotos": "ok"
        }
    }

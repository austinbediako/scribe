from fastapi import APIRouter

from app.core.config import settings

router = APIRouter()


@router.get("/health")
def health_check():
    return {"status": "ok"}


@router.get("/api/status")
def api_status():
    return {
        "hasApiKey": True,
        "demo_mode": settings.should_use_demo_data,
    }
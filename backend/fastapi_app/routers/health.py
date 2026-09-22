from __future__ import annotations

from fastapi import APIRouter

from ..config import get_settings


router = APIRouter(tags=["health"])


@router.get("/")
async def root() -> dict[str, str]:
    settings = get_settings()
    return {"message": settings.app_name, "version": settings.app_version}


@router.get("/health")
async def health() -> dict[str, str | bool]:
    settings = get_settings()
    return {
        "status": "healthy",
        "ai_configured": bool((settings.gemini_api_key or "").strip()),
        "ai_model": settings.gemini_model,
    }

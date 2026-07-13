from __future__ import annotations

from fastapi import APIRouter

from ..config import get_settings


router = APIRouter(tags=["health"])


@router.get("/")
async def root() -> dict[str, str]:
    settings = get_settings()
    return {"message": settings.app_name, "version": settings.app_version}


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy"}

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..dependencies import get_db
from ..schemas import AnalysisResponse, CodePayload, MetricsPayload
from ..services.optimization_service import OptimizationService


router = APIRouter(tags=["analysis"])


@router.post("/analysis", response_model=AnalysisResponse)
async def analysis(payload: CodePayload, db: Session = Depends(get_db)) -> dict:
    service = OptimizationService(db)
    try:
        return service.analyze(payload.code)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/metrics")
async def metrics(payload: MetricsPayload, db: Session = Depends(get_db)) -> dict:
    service = OptimizationService(db)
    try:
        return service.metrics(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

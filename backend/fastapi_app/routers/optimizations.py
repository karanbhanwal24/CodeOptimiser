from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from ..dependencies import get_db
from ..exceptions import AppError
from ..schemas import (
    CodePayload,
    OptimizationRecordListResponse,
    OptimizationRecordResponse,
    OptimizationRecordUpdate,
    OptimizationResponse,
)
from ..services.optimization_service import OptimizationService


router = APIRouter(tags=["optimizations"])


async def _run_optimization(payload: CodePayload, db: Session) -> dict:
    service = OptimizationService(db)
    try:
        return service.optimize_and_store(payload)
    except AppError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/optimize", response_model=OptimizationResponse)
async def optimize(payload: CodePayload, db: Session = Depends(get_db)) -> dict:
    return await _run_optimization(payload, db)


@router.post("/optimise", response_model=OptimizationResponse)
async def optimise(payload: CodePayload, db: Session = Depends(get_db)) -> dict:
    return await _run_optimization(payload, db)


@router.post("/optmise", response_model=OptimizationResponse)
async def optmise(payload: CodePayload, db: Session = Depends(get_db)) -> dict:
    return await _run_optimization(payload, db)


@router.get("/optimizations", response_model=OptimizationRecordListResponse)
async def list_optimizations(db: Session = Depends(get_db)) -> OptimizationRecordListResponse:
    service = OptimizationService(db)
    return OptimizationRecordListResponse(items=service.list_records())


@router.get("/optimizations/{record_id}", response_model=OptimizationRecordResponse)
async def get_optimization(record_id: int, db: Session = Depends(get_db)) -> OptimizationRecordResponse:
    service = OptimizationService(db)
    return service.get_record(record_id)


@router.put("/optimizations/{record_id}", response_model=OptimizationRecordResponse)
async def update_optimization(
    record_id: int,
    payload: OptimizationRecordUpdate,
    db: Session = Depends(get_db),
) -> OptimizationRecordResponse:
    service = OptimizationService(db)
    try:
        return service.update_record(record_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/optimizations/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_optimization(record_id: int, db: Session = Depends(get_db)) -> Response:
    service = OptimizationService(db)
    service.delete_record(record_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

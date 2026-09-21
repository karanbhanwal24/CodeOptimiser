from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..config import get_settings
from ..schemas import AIInsightsRequest, AIInsightsResponse, AIQuestionRequest, AIQuestionResponse
from ..services.ai_insights_service import AIInsightsService, AIInsightsUnavailableError


router = APIRouter(prefix="/ai", tags=["ai"])


def get_ai_insights_service() -> AIInsightsService:
    return AIInsightsService(get_settings())


@router.post("/insights", response_model=AIInsightsResponse)
async def insights(
    payload: AIInsightsRequest,
    service: AIInsightsService = Depends(get_ai_insights_service),
) -> AIInsightsResponse:
    try:
        return await service.get_insights(payload)
    except AIInsightsUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/questions", response_model=AIQuestionResponse)
async def questions(
    payload: AIQuestionRequest,
    service: AIInsightsService = Depends(get_ai_insights_service),
) -> AIQuestionResponse:
    try:
        return await service.answer_question(payload)
    except AIInsightsUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

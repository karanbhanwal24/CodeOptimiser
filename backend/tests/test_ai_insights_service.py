from __future__ import annotations

import asyncio

from fastapi_app.config import Settings
from fastapi_app.schemas import (
    AIInsightsRequest,
    AIInsightsResponse,
    AIQuestionRequest,
    AIQuestionResponse,
)
from fastapi_app.services.ai_insights_service import AIInsightsService


def test_ai_insights_service_returns_structured_advisory_response(
    monkeypatch,
) -> None:
    service = AIInsightsService(
        Settings(gemini_api_key="test-key")
    )

    expected = AIInsightsResponse(
        summary="Simple assignment and output.",
        code_explanation="The code assigns x then prints it.",
        issues_explanation=[],
        suggestions=["Keep the code as-is for this simple case."],
    )

    monkeypatch.setattr(
        service,
        "_generate",
        lambda request: expected,
    )

    request = AIInsightsRequest(
        code="x = 1\nprint(x)\n",
        analysis={},
    )

    assert asyncio.run(service.get_insights(request)) == expected


def test_ai_question_service_preserves_follow_up_history(monkeypatch) -> None:
    service = AIInsightsService(Settings(gemini_api_key="test-key"))
    captured = {}

    def generate(request):
        captured["request"] = request
        return AIQuestionResponse(answer="The loop has one execution path.")

    monkeypatch.setattr(service, "_generate_question", generate)

    request = AIQuestionRequest(
        question="Can you explain that more?",
        code="x = 1\nprint(x)\n",
        analysis={},
        history=[
            {"role": "user", "content": "Why is this code simple?"},
            {"role": "assistant", "content": "It has no branching."},
        ],
    )

    result = asyncio.run(service.answer_question(request))

    assert result.answer == "The loop has one execution path."
    assert [message.content for message in captured["request"].history] == [
        "Why is this code simple?",
        "It has no branching.",
    ]
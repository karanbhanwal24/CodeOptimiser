from __future__ import annotations

import asyncio
import json
import logging

from ..config import Settings
from ..schemas import AIInsightsRequest, AIInsightsResponse, AIQuestionRequest, AIQuestionResponse


logger = logging.getLogger(__name__)


class AIInsightsUnavailableError(Exception):
    """Raised when the optional Gemini integration cannot respond."""


class AIInsightsService:
    """Gemini adapter that only explains supplied analyzer results."""

    def __init__(self, settings: Settings):
        self._api_key = (settings.gemini_api_key or "").strip() or None
        self._model = (settings.gemini_model or "gemini-2.5-flash").strip()

    async def get_insights(self, request: AIInsightsRequest) -> AIInsightsResponse:
        return await self._run_optional_request(self._generate, request)

    async def answer_question(self, request: AIQuestionRequest) -> AIQuestionResponse:
        return await self._run_optional_request(self._generate_question, request)

    async def _run_optional_request(self, generator, request):
        if not self._api_key:
            raise AIInsightsUnavailableError("AI Insights is unavailable because GEMINI_API_KEY is not configured.")
        try:
            return await asyncio.to_thread(generator, request)
        except AIInsightsUnavailableError:
            raise
        except Exception as exc:
            # Provider details may include sensitive configuration; keep them server-side.
            logger.exception("Gemini insights request failed: %s", type(exc).__name__)
            raise AIInsightsUnavailableError(
                "AI Insights is temporarily unavailable. Your CodeOptimise analysis is unchanged."
            ) from exc

    def _generate(self, request: AIInsightsRequest) -> AIInsightsResponse:
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:
            raise AIInsightsUnavailableError("AI Insights dependency is not installed on this server.") from exc

        prompt_data = {
            "source_code": request.code,
            "analyzer_results": request.analysis.model_dump(),
            "existing_optimized_code": request.optimized_code,
            "include_refactored_code": request.include_refactored_code,
        }
        prompt = (
            "You are CodeOptimise's advisory explanation layer. The provided analyzer results are "
            "authoritative: explain only those findings and do not invent detected issues, benchmark "
            "results, or complexity claims. Provide practical, language-appropriate suggestions. "
            "A refactored_code value is allowed only when include_refactored_code is true; otherwise set it "
            "to null. Refactored code is optional, must preserve intent, and is only a suggestion.\n\n"
            f"Input JSON:\n{json.dumps(prompt_data, ensure_ascii=False)}"
        )
        client = genai.Client(api_key=self._api_key)
        response = client.models.generate_content(
            model=self._model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=AIInsightsResponse,
                temperature=0.2,
                max_output_tokens=2048,
            ),
        )
        if isinstance(response.parsed, AIInsightsResponse):
            return response.parsed
        if response.parsed is not None:
            return AIInsightsResponse.model_validate(response.parsed)
        return AIInsightsResponse.model_validate_json(response.text)

    def _generate_question(self, request: AIQuestionRequest) -> AIQuestionResponse:
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:
            raise AIInsightsUnavailableError("AI Insights dependency is not installed on this server.") from exc

        prompt_data = {
            "question": request.question,
            "source_code": request.code,
            "analyzer_results": request.analysis.model_dump() if request.analysis else None,
            "conversation_history": [message.model_dump() for message in request.history],
        }
        prompt = (
            "You are CodeOptimise's advisory Q&A layer. Answer the user's question about the supplied "
            "code concisely and accurately. Treat analyzer_results as authoritative where present; do not "
            "invent analyzer findings, benchmark data, or complexity claims. Explain uncertainty when code "
            "alone is insufficient.\n\n"
            f"Input JSON:\n{json.dumps(prompt_data, ensure_ascii=False)}"
        )
        client = genai.Client(api_key=self._api_key)
        response = client.models.generate_content(
            model=self._model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=AIQuestionResponse,
                temperature=0.2,
                max_output_tokens=1024,
            ),
        )
        if isinstance(response.parsed, AIQuestionResponse):
            return response.parsed
        if response.parsed is not None:
            return AIQuestionResponse.model_validate(response.parsed)
        return AIQuestionResponse.model_validate_json(response.text)

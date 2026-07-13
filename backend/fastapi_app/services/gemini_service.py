from __future__ import annotations

import logging

import httpx
from google import genai
from google.genai import types
from pydantic import BaseModel, Field, ValidationError

from ..config import Settings
from ..exceptions import (
    AIProviderConfigurationError,
    AIProviderError,
    AIProviderRateLimitError,
    AIProviderTimeoutError,
)
from .ai_provider import AIOptimizationProvider, AIOptimizationResult


logger = logging.getLogger(__name__)


class GeminiOptimizationSchema(BaseModel):
    optimized_code: str = Field(description="Optimized code with the same behavior as the input.")
    explanation: str = Field(description="Explanation of the optimizations that were applied.")
    time_complexity_before: str = Field(description="Estimated Big-O time complexity before optimization.")
    time_complexity_after: str = Field(description="Estimated Big-O time complexity after optimization.")
    space_complexity_before: str = Field(description="Estimated Big-O space complexity before optimization.")
    space_complexity_after: str = Field(description="Estimated Big-O space complexity after optimization.")
    suggestions: list[str] = Field(default_factory=list, description="Actionable improvement suggestions.")
    performance_issues: list[str] = Field(default_factory=list, description="Detected performance issues in the input code.")
    better_practices: list[str] = Field(default_factory=list, description="Suggested coding best practices.")


SYSTEM_PROMPT = """
You are an expert software engineer and code optimizer.

Optimize the user's code without changing its behavior.
Preserve correctness, readability, and maintainability.
Reduce time and space complexity where it is safely possible.
Avoid unnecessary edits, stylistic churn, or speculative rewrites.
Point out performance issues and suggest better coding practices.
Return only valid JSON that exactly matches the required schema.
Do not wrap the JSON in markdown fences.
If a safe optimization is not possible, keep the code functionally equivalent and explain why.
""".strip()


class GeminiOptimizationProvider(AIOptimizationProvider):
    provider_name = "gemini"

    def __init__(self, settings: Settings) -> None:
        if not settings.gemini_api_key:
            raise AIProviderConfigurationError("GEMINI_API_KEY is not configured")

        self.model = settings.gemini_model
        self.max_retries = max(settings.gemini_max_retries, 0)
        self.client = genai.Client(
            api_key=settings.gemini_api_key,
            http_options=types.HttpOptions(
                client_args={"timeout": httpx.Timeout(settings.gemini_timeout_seconds)}
            ),
        )

    def optimize_code(self, *, language: str, code: str) -> AIOptimizationResult:
        prompt = self._build_prompt(language=language, code=code)
        preview = " | ".join(code.strip().splitlines()[:3])
        logger.info(
            "Submitting Gemini optimization request model=%s language=%s code_chars=%s code_preview=%s",
            self.model,
            language,
            len(code),
            preview,
        )

        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                interaction = self.client.interactions.create(
                    model=self.model,
                    system_instruction=SYSTEM_PROMPT,
                    input=prompt,
                    response_format={
                        "type": "text",
                        "mime_type": "application/json",
                        "schema": GeminiOptimizationSchema.model_json_schema(),
                    },
                    generation_config={
                        "temperature": 0.1,
                        "thinking_level": "low",
                    },
                )
                result = GeminiOptimizationSchema.model_validate_json(interaction.output_text)
                logger.info(
                    "Gemini optimization completed model=%s suggestion_count=%s performance_issue_count=%s",
                    self.model,
                    len(result.suggestions),
                    len(result.performance_issues),
                )
                return AIOptimizationResult(**result.model_dump())
            except ValidationError as exc:
                logger.exception("Gemini response validation failed on attempt=%s", attempt + 1)
                raise AIProviderError("Gemini returned an invalid structured response") from exc
            except Exception as exc:  # pragma: no cover - external SDK behavior
                last_error = exc
                message = str(exc).lower()
                logger.warning("Gemini request failed on attempt=%s error=%s", attempt + 1, exc)
                if isinstance(exc, httpx.TimeoutException) or "timed out" in message:
                    if attempt == self.max_retries:
                        raise AIProviderTimeoutError("Gemini request timed out") from exc
                    continue
                if "429" in message or "rate limit" in message or "resource exhausted" in message:
                    if attempt == self.max_retries:
                        raise AIProviderRateLimitError("Gemini rate limit exceeded") from exc
                    continue
                if attempt == self.max_retries:
                    raise AIProviderError("Gemini request failed") from exc

        raise AIProviderError("Gemini request failed") from last_error

    @staticmethod
    def _build_prompt(*, language: str, code: str) -> str:
        return f"""
Optimize this {language} code.

Requirements:
- Preserve the original functionality.
- Improve readability and maintainability.
- Reduce time and space complexity where safe.
- Identify common performance issues.
- Suggest better coding practices.
- Estimate time and space complexity before and after optimization.

Code:
{code}
""".strip()

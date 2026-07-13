from __future__ import annotations

from pathlib import Path
import sys
from unittest.mock import MagicMock, patch

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from backend.fastapi_app.config import Settings
from backend.fastapi_app.exceptions import AIProviderError, AIProviderRateLimitError
from backend.fastapi_app.services.gemini_service import GeminiOptimizationProvider


def build_settings() -> Settings:
    return Settings(
        gemini_api_key="test-key",
        allowed_origins=["http://localhost:5173"],
    )


def test_gemini_service_returns_structured_result() -> None:
    fake_interaction = MagicMock()
    fake_interaction.output_text = """
    {
      "optimized_code": "def sum_values(values):\\n    return sum(values)\\n",
      "explanation": "Use sum instead of a manual accumulator loop.",
      "time_complexity_before": "O(n)",
      "time_complexity_after": "O(n)",
      "space_complexity_before": "O(1)",
      "space_complexity_after": "O(1)",
      "suggestions": ["Prefer built-ins where behavior is unchanged."],
      "performance_issues": ["Manual accumulation loop detected."],
      "better_practices": ["Use clear standard-library helpers."]
    }
    """

    with patch("backend.fastapi_app.services.gemini_service.genai.Client") as client_cls:
        client_cls.return_value.interactions.create.return_value = fake_interaction
        provider = GeminiOptimizationProvider(build_settings())
        result = provider.optimize_code(language="python", code="print('hi')\n")

    assert "sum(values)" in result.optimized_code
    assert result.time_complexity_before == "O(n)"
    assert result.suggestions


def test_gemini_service_raises_on_invalid_json_schema() -> None:
    fake_interaction = MagicMock()
    fake_interaction.output_text = '{"optimized_code": "print(1)"}'

    with patch("backend.fastapi_app.services.gemini_service.genai.Client") as client_cls:
        client_cls.return_value.interactions.create.return_value = fake_interaction
        provider = GeminiOptimizationProvider(build_settings())

        with pytest.raises(AIProviderError):
            provider.optimize_code(language="python", code="print('hi')\n")


def test_gemini_service_maps_rate_limit_errors() -> None:
    with patch("backend.fastapi_app.services.gemini_service.genai.Client") as client_cls:
        client_cls.return_value.interactions.create.side_effect = RuntimeError("429 rate limit exceeded")
        provider = GeminiOptimizationProvider(build_settings())

        with pytest.raises(AIProviderRateLimitError):
            provider.optimize_code(language="python", code="print('hi')\n")

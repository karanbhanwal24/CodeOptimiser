from __future__ import annotations

from ..config import Settings, get_settings
from ..exceptions import AIProviderConfigurationError
from .ai_provider import AIOptimizationProvider
from .gemini_service import GeminiOptimizationProvider


def get_ai_provider(settings: Settings | None = None) -> AIOptimizationProvider:
    resolved_settings = settings or get_settings()

    if resolved_settings.ai_provider == "gemini":
        return GeminiOptimizationProvider(resolved_settings)

    raise AIProviderConfigurationError(f"Unsupported AI provider: {resolved_settings.ai_provider}")

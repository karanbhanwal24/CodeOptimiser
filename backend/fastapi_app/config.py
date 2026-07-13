from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent

load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(BACKEND_DIR / ".env", override=False)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", case_sensitive=False, enable_decoding=False)

    app_name: str = "CodeOptimise FastAPI Backend"
    app_version: str = "1.0.0"
    app_description: str = "Python optimizer backend for the React frontend"
    environment: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    database_url: str = "postgresql+psycopg://postgres:password@postgres:5432/codeoptimise"
    database_echo: bool = False
    auto_migrate: bool = True
    ai_provider: str = "gemini"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-3.5-flash"
    gemini_timeout_seconds: float = 20.0
    gemini_max_retries: int = 2
    allowed_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]
    )
    allowed_origin_regex: str | None = r"^https://.*\.vercel\.app$"

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_allowed_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, list):
            return value
        if not value:
            return []
        return [origin.strip() for origin in value.split(",") if origin.strip()]

    @field_validator("allowed_origin_regex", mode="before")
    @classmethod
    def parse_allowed_origin_regex(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


@lru_cache
def get_settings() -> Settings:
    return Settings()

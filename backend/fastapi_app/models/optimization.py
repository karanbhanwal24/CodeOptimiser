from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from ..database import Base


class OptimizationRecord(Base):
    __tablename__ = "optimization_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    language: Mapped[str] = mapped_column(String(32), default="python", nullable=False)
    provider: Mapped[str] = mapped_column(String(32), default="gemini", nullable=False)
    original_code: Mapped[str] = mapped_column(Text, nullable=False)
    optimized_code: Mapped[str] = mapped_column(Text, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    time_complexity_before: Mapped[str | None] = mapped_column(String(64), nullable=True)
    time_complexity_after: Mapped[str | None] = mapped_column(String(64), nullable=True)
    space_complexity_before: Mapped[str | None] = mapped_column(String(64), nullable=True)
    space_complexity_after: Mapped[str | None] = mapped_column(String(64), nullable=True)
    original_time_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    optimized_time_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    original_memory_mb: Mapped[float | None] = mapped_column(Float, nullable=True)
    optimized_memory_mb: Mapped[float | None] = mapped_column(Float, nullable=True)
    time_improvement_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    memory_improvement_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    lines_of_code_before: Mapped[int | None] = mapped_column(Integer, nullable=True)
    lines_of_code_after: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cyclomatic_complexity_before: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cyclomatic_complexity_after: Mapped[int | None] = mapped_column(Integer, nullable=True)
    improvements: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    suggestions: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    ai_response: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    variants: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    analysis: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

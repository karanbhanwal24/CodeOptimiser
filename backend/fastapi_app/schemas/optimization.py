from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CodePayload(BaseModel):
    code: str


class OptimizationVariant(BaseModel):
    name: str | None = None
    code: str
    description: str | None = None
    technique: str | None = None
    category: str | None = None
    time_ms: float | None = None
    memory_mb: float | None = None
    time_improvement_pct: float | None = None
    memory_improvement_pct: float | None = None
    confidence: str | None = None
    error: str | None = None


class MetricsPayload(BaseModel):
    original_code: str | None = None
    code: str | None = None
    variants: list[OptimizationVariant] | None = None


class AnalysisIssue(BaseModel):
    severity: str
    description: str
    line: int
    category: str
    fix_available: bool
    effort: str
    impact: str


class AIAnalysisContext(BaseModel):
    """Analyzer output supplied as context only; it remains the source of truth."""

    issues: list[AnalysisIssue] = Field(default_factory=list)
    issue_count: int = Field(default=0, ge=0)
    complexity_estimate: str = Field(default="Unknown", max_length=200)
    cyclomatic_complexity: int = Field(default=0, ge=0)


class AIInsightsRequest(BaseModel):
    code: str = Field(min_length=1, max_length=50_000)
    analysis: AIAnalysisContext
    optimized_code: str | None = Field(default=None, max_length=50_000)
    include_refactored_code: bool = False

    @field_validator("code")
    @classmethod
    def code_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Code must not be blank.")
        return value


class AIInsightsResponse(BaseModel):
    summary: str
    code_explanation: str
    issues_explanation: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    refactored_code: str | None = None
    disclaimer: str = "AI guidance is advisory. CodeOptimise analyzer results remain the source of truth."


class AIQuestionRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2_000)
    code: str = Field(min_length=1, max_length=50_000)
    analysis: AIAnalysisContext | None = None
    history: list["AIChatMessage"] = Field(default_factory=list, max_length=20)

    @field_validator("question", "code")
    @classmethod
    def values_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Question and code must not be blank.")
        return value


class AIChatMessage(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(min_length=1, max_length=2_000)

    @field_validator("content")
    @classmethod
    def content_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Chat messages must not be blank.")
        return value


class AIQuestionResponse(BaseModel):
    answer: str
    disclaimer: str = "AI guidance is advisory. CodeOptimise analyzer results remain the source of truth."


class AnalysisResponse(BaseModel):
    issues: list[AnalysisIssue]
    issue_count: int
    complexity_estimate: str
    cyclomatic_complexity: int


class OptimizationRecordBase(BaseModel):
    id: int
    language: str
    original_code: str
    optimized_code: str
    explanation: str
    original_time_ms: float | None = None
    optimized_time_ms: float | None = None
    original_memory_mb: float | None = None
    optimized_memory_mb: float | None = None
    time_improvement_pct: float | None = None
    memory_improvement_pct: float | None = None
    lines_of_code_before: int | None = None
    lines_of_code_after: int | None = None
    cyclomatic_complexity_before: int | None = None
    cyclomatic_complexity_after: int | None = None
    improvements: list[Any] = Field(default_factory=list)
    variants: list[dict[str, Any]] = Field(default_factory=list)
    analysis: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OptimizationResponse(BaseModel):
    record_id: int
    optimized_code: str
    original_time_ms: float | None = None
    optimized_time_ms: float | None = None
    original_memory_mb: float | None = None
    optimized_memory_mb: float | None = None
    time_improvement_pct: float | None = None
    memory_improvement_pct: float | None = None
    variants: list[dict[str, Any]] = Field(default_factory=list)
    explanation: str
    improvements: list[Any] = Field(default_factory=list)
    lines_of_code_before: int | None = None
    lines_of_code_after: int | None = None
    cyclomatic_complexity_before: int | None = None
    cyclomatic_complexity_after: int | None = None
    analysis: dict[str, Any] = Field(default_factory=dict)


class OptimizationRecordResponse(OptimizationRecordBase):
    pass


class OptimizationRecordListResponse(BaseModel):
    items: list[OptimizationRecordResponse]


class OptimizationRecordUpdate(BaseModel):
    original_code: str | None = None
    optimized_code: str | None = None
    language: str | None = None

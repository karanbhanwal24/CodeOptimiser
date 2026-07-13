from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CodePayload(BaseModel):
    language: str = "python"
    code: str


class OptimizationSuggestionResponse(BaseModel):
    optimized_code: str
    explanation: str
    time_complexity_before: str
    time_complexity_after: str
    space_complexity_before: str
    space_complexity_after: str
    suggestions: list[str] = Field(default_factory=list)
    performance_issues: list[str] = Field(default_factory=list)
    better_practices: list[str] = Field(default_factory=list)


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


class AnalysisResponse(BaseModel):
    issues: list[AnalysisIssue]
    issue_count: int
    complexity_estimate: str
    cyclomatic_complexity: int


class OptimizationRecordBase(BaseModel):
    id: int
    language: str
    provider: str
    original_code: str
    optimized_code: str
    explanation: str
    time_complexity_before: str | None = None
    time_complexity_after: str | None = None
    space_complexity_before: str | None = None
    space_complexity_after: str | None = None
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
    suggestions: list[str] = Field(default_factory=list)
    ai_response: dict[str, Any] = Field(default_factory=dict)
    variants: list[dict[str, Any]] = Field(default_factory=list)
    analysis: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OptimizationResponse(BaseModel):
    record_id: int
    language: str
    provider: str
    optimized_code: str
    explanation: str
    time_complexity_before: str
    time_complexity_after: str
    space_complexity_before: str
    space_complexity_after: str
    suggestions: list[str] = Field(default_factory=list)
    performance_issues: list[str] = Field(default_factory=list)
    better_practices: list[str] = Field(default_factory=list)
    original_time_ms: float | None = None
    optimized_time_ms: float | None = None
    original_memory_mb: float | None = None
    optimized_memory_mb: float | None = None
    time_improvement_pct: float | None = None
    memory_improvement_pct: float | None = None
    variants: list[dict[str, Any]] = Field(default_factory=list)
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
    provider: str | None = None
    original_code: str | None = None
    optimized_code: str | None = None
    language: str | None = None

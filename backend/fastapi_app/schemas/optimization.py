from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


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

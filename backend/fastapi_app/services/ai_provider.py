from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel, Field


class AIOptimizationResult(BaseModel):
    optimized_code: str
    explanation: str
    time_complexity_before: str
    time_complexity_after: str
    space_complexity_before: str
    space_complexity_after: str
    suggestions: list[str] = Field(default_factory=list)
    performance_issues: list[str] = Field(default_factory=list)
    better_practices: list[str] = Field(default_factory=list)


class AIOptimizationProvider(ABC):
    provider_name: str

    @abstractmethod
    def optimize_code(self, *, language: str, code: str) -> AIOptimizationResult:
        raise NotImplementedError

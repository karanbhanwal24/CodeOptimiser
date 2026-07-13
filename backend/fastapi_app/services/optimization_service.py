from __future__ import annotations

import ast
import logging
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..exceptions import DatabaseOperationError, ResourceNotFoundError
from ..repositories import OptimizationRecordRepository
from ..schemas import CodePayload, MetricsPayload, OptimizationRecordUpdate
from .analysis import analyze_code
from .engine import compare_variants
from .provider_factory import get_ai_provider


logger = logging.getLogger(__name__)


class OptimizationService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = OptimizationRecordRepository(db)

    @staticmethod
    def validate_code(code: str) -> str:
        if not code or not code.strip():
            raise ValueError("Code is required")
        try:
            ast.parse(code)
        except SyntaxError as exc:
            raise ValueError(f"Invalid Python code: {exc.msg}") from exc
        return code

    @staticmethod
    def validate_language(language: str) -> str:
        normalized = (language or "").strip().lower()
        if normalized != "python":
            raise ValueError("Only Python optimization is currently supported")
        return normalized

    def analyze(self, code: str) -> dict[str, Any]:
        validated_code = self.validate_code(code)
        return analyze_code(validated_code)

    def metrics(self, payload: MetricsPayload) -> dict[str, Any]:
        original_code = payload.original_code or payload.code
        if not original_code:
            raise ValueError("Original code is required")

        validated_original = self.validate_code(original_code)
        variants = None
        if payload.variants is not None:
            variants = []
            for variant in payload.variants:
                validated_variant_code = self.validate_code(variant.code)
                variant_dict = variant.model_dump()
                variant_dict["code"] = validated_variant_code
                variants.append(variant_dict)
        return compare_variants(validated_original, variants)

    def optimize_and_store(self, payload: CodePayload) -> dict[str, Any]:
        optimization_result, record_payload = self._build_optimization_result(payload)

        try:
            record = self.repository.create(record_payload)
            self.db.commit()
            self.db.refresh(record)
        except SQLAlchemyError as exc:
            self.db.rollback()
            logger.exception("Failed to persist optimization record")
            raise DatabaseOperationError("Failed to persist optimization result") from exc

        logger.info("Stored optimization record id=%s provider=%s", record.id, record.provider)
        return {
            **optimization_result,
            "record_id": record.id,
        }

    def list_records(self) -> list:
        return self.repository.list()

    def get_record(self, record_id: int):
        record = self.repository.get(record_id)
        if record is None:
            raise ResourceNotFoundError(f"Optimization record {record_id} not found")
        return record

    def update_record(self, record_id: int, payload: OptimizationRecordUpdate):
        record = self.get_record(record_id)
        try:
            if payload.original_code is not None:
                refreshed_payload = CodePayload(language=payload.language or record.language, code=payload.original_code)
                result, record_payload = self._build_optimization_result(refreshed_payload)
                record.original_code = record_payload["original_code"]
                record.optimized_code = record_payload["optimized_code"]
                record.explanation = record_payload["explanation"]
                record.provider = record_payload["provider"]
                record.time_complexity_before = record_payload["time_complexity_before"]
                record.time_complexity_after = record_payload["time_complexity_after"]
                record.space_complexity_before = record_payload["space_complexity_before"]
                record.space_complexity_after = record_payload["space_complexity_after"]
                record.original_time_ms = record_payload["original_time_ms"]
                record.optimized_time_ms = record_payload["optimized_time_ms"]
                record.original_memory_mb = record_payload["original_memory_mb"]
                record.optimized_memory_mb = record_payload["optimized_memory_mb"]
                record.time_improvement_pct = record_payload["time_improvement_pct"]
                record.memory_improvement_pct = record_payload["memory_improvement_pct"]
                record.lines_of_code_before = record_payload["lines_of_code_before"]
                record.lines_of_code_after = record_payload["lines_of_code_after"]
                record.cyclomatic_complexity_before = record_payload["cyclomatic_complexity_before"]
                record.cyclomatic_complexity_after = record_payload["cyclomatic_complexity_after"]
                record.improvements = record_payload["improvements"]
                record.suggestions = record_payload["suggestions"]
                record.ai_response = record_payload["ai_response"]
                record.variants = record_payload["variants"]
                record.analysis = record_payload["analysis"]
                if payload.language is None:
                    record.language = result["language"]

            if payload.optimized_code is not None:
                record.optimized_code = self.validate_code(payload.optimized_code)
            if payload.language is not None:
                record.language = self.validate_language(payload.language)
            if payload.provider is not None:
                record.provider = payload.provider

            self.db.commit()
            self.db.refresh(record)
        except ValueError:
            self.db.rollback()
            raise
        except SQLAlchemyError as exc:
            self.db.rollback()
            logger.exception("Failed to update optimization record id=%s", record_id)
            raise DatabaseOperationError(f"Failed to update optimization record {record_id}") from exc

        logger.info("Updated optimization record id=%s", record.id)
        return record

    def delete_record(self, record_id: int) -> None:
        record = self.get_record(record_id)
        try:
            self.repository.delete(record)
            self.db.commit()
        except SQLAlchemyError as exc:
            self.db.rollback()
            logger.exception("Failed to delete optimization record id=%s", record_id)
            raise DatabaseOperationError(f"Failed to delete optimization record {record_id}") from exc

        logger.info("Deleted optimization record id=%s", record_id)

    def _build_optimization_result(self, payload: CodePayload) -> tuple[dict[str, Any], dict[str, Any]]:
        language = self.validate_language(payload.language)
        validated_code = self.validate_code(payload.code)
        analysis_result = analyze_code(validated_code)
        provider = get_ai_provider()
        ai_result = provider.optimize_code(language=language, code=validated_code)
        validated_optimized_code = self.validate_code(ai_result.optimized_code)

        benchmark_result = compare_variants(
            validated_code,
            [
                {
                    "name": "ai-optimized",
                    "code": validated_optimized_code,
                    "description": "AI-generated optimization from Gemini.",
                    "technique": "LLM optimization",
                    "category": "performance",
                }
            ],
        )

        optimization_result = {
            "language": language,
            "provider": provider.provider_name,
            "optimized_code": validated_optimized_code,
            "explanation": ai_result.explanation,
            "time_complexity_before": ai_result.time_complexity_before,
            "time_complexity_after": ai_result.time_complexity_after,
            "space_complexity_before": ai_result.space_complexity_before,
            "space_complexity_after": ai_result.space_complexity_after,
            "suggestions": ai_result.suggestions,
            "performance_issues": ai_result.performance_issues,
            "better_practices": ai_result.better_practices,
            "original_time_ms": benchmark_result.get("original_time_ms"),
            "optimized_time_ms": benchmark_result.get("optimized_time_ms"),
            "original_memory_mb": benchmark_result.get("original_memory_mb"),
            "optimized_memory_mb": benchmark_result.get("optimized_memory_mb"),
            "time_improvement_pct": benchmark_result.get("time_improvement_pct"),
            "memory_improvement_pct": benchmark_result.get("memory_improvement_pct"),
            "variants": benchmark_result.get("variants", []),
            "improvements": ai_result.better_practices,
            "lines_of_code_before": benchmark_result.get("lines_of_code_before"),
            "lines_of_code_after": benchmark_result.get("lines_of_code_after"),
            "cyclomatic_complexity_before": benchmark_result.get("cyclomatic_complexity_before"),
            "cyclomatic_complexity_after": benchmark_result.get("cyclomatic_complexity_after"),
            "analysis": analysis_result,
        }

        record_payload = {
            "language": language,
            "provider": provider.provider_name,
            "original_code": validated_code,
            "optimized_code": validated_optimized_code,
            "explanation": ai_result.explanation,
            "time_complexity_before": ai_result.time_complexity_before,
            "time_complexity_after": ai_result.time_complexity_after,
            "space_complexity_before": ai_result.space_complexity_before,
            "space_complexity_after": ai_result.space_complexity_after,
            "original_time_ms": benchmark_result.get("original_time_ms"),
            "optimized_time_ms": benchmark_result.get("optimized_time_ms"),
            "original_memory_mb": benchmark_result.get("original_memory_mb"),
            "optimized_memory_mb": benchmark_result.get("optimized_memory_mb"),
            "time_improvement_pct": benchmark_result.get("time_improvement_pct"),
            "memory_improvement_pct": benchmark_result.get("memory_improvement_pct"),
            "lines_of_code_before": benchmark_result.get("lines_of_code_before"),
            "lines_of_code_after": benchmark_result.get("lines_of_code_after"),
            "cyclomatic_complexity_before": benchmark_result.get("cyclomatic_complexity_before"),
            "cyclomatic_complexity_after": benchmark_result.get("cyclomatic_complexity_after"),
            "improvements": ai_result.better_practices,
            "suggestions": ai_result.suggestions,
            "ai_response": ai_result.model_dump(),
            "variants": benchmark_result.get("variants", []),
            "analysis": analysis_result,
        }

        return optimization_result, record_payload

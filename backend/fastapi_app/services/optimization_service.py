from __future__ import annotations

import ast
import logging
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..exceptions import DatabaseOperationError, ResourceNotFoundError
from ..repositories import OptimizationRecordRepository
from ..schemas import MetricsPayload, OptimizationRecordUpdate
from .analysis import analyze_code
from .engine import compare_variants


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

    def optimize_and_store(self, code: str) -> dict[str, Any]:
        validated_code = self.validate_code(code)
        analysis_result = analyze_code(validated_code)
        optimization_result = compare_variants(validated_code)

        record_payload = {
            "language": "python",
            "original_code": validated_code,
            "optimized_code": optimization_result["optimized_code"],
            "explanation": optimization_result["explanation"],
            "original_time_ms": optimization_result.get("original_time_ms"),
            "optimized_time_ms": optimization_result.get("optimized_time_ms"),
            "original_memory_mb": optimization_result.get("original_memory_mb"),
            "optimized_memory_mb": optimization_result.get("optimized_memory_mb"),
            "time_improvement_pct": optimization_result.get("time_improvement_pct"),
            "memory_improvement_pct": optimization_result.get("memory_improvement_pct"),
            "lines_of_code_before": optimization_result.get("lines_of_code_before"),
            "lines_of_code_after": optimization_result.get("lines_of_code_after"),
            "cyclomatic_complexity_before": optimization_result.get("cyclomatic_complexity_before"),
            "cyclomatic_complexity_after": optimization_result.get("cyclomatic_complexity_after"),
            "improvements": optimization_result.get("improvements", []),
            "variants": optimization_result.get("variants", []),
            "analysis": analysis_result,
        }

        try:
            record = self.repository.create(record_payload)
            self.db.commit()
            self.db.refresh(record)
        except SQLAlchemyError as exc:
            self.db.rollback()
            logger.exception("Failed to persist optimization record")
            raise DatabaseOperationError("Failed to persist optimization result") from exc

        logger.info("Stored optimization record id=%s", record.id)
        return {
            **optimization_result,
            "analysis": analysis_result,
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
                validated_code = self.validate_code(payload.original_code)
                analysis_result = analyze_code(validated_code)
                optimization_result = compare_variants(validated_code)
                record.original_code = validated_code
                record.optimized_code = optimization_result["optimized_code"]
                record.explanation = optimization_result["explanation"]
                record.original_time_ms = optimization_result.get("original_time_ms")
                record.optimized_time_ms = optimization_result.get("optimized_time_ms")
                record.original_memory_mb = optimization_result.get("original_memory_mb")
                record.optimized_memory_mb = optimization_result.get("optimized_memory_mb")
                record.time_improvement_pct = optimization_result.get("time_improvement_pct")
                record.memory_improvement_pct = optimization_result.get("memory_improvement_pct")
                record.lines_of_code_before = optimization_result.get("lines_of_code_before")
                record.lines_of_code_after = optimization_result.get("lines_of_code_after")
                record.cyclomatic_complexity_before = optimization_result.get("cyclomatic_complexity_before")
                record.cyclomatic_complexity_after = optimization_result.get("cyclomatic_complexity_after")
                record.improvements = optimization_result.get("improvements", [])
                record.variants = optimization_result.get("variants", [])
                record.analysis = analysis_result

            if payload.optimized_code is not None:
                record.optimized_code = self.validate_code(payload.optimized_code)
            if payload.language is not None:
                record.language = payload.language

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

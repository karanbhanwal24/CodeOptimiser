from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import OptimizationRecord


class OptimizationRecordRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, payload: dict) -> OptimizationRecord:
        record = OptimizationRecord(**payload)
        self.db.add(record)
        return record

    def list(self) -> list[OptimizationRecord]:
        return list(self.db.scalars(select(OptimizationRecord).order_by(OptimizationRecord.created_at.desc())))

    def get(self, record_id: int) -> OptimizationRecord | None:
        return self.db.get(OptimizationRecord, record_id)

    def delete(self, record: OptimizationRecord) -> None:
        self.db.delete(record)

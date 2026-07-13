"""initial optimization records

Revision ID: 20260713_000001
Revises:
Create Date: 2026-07-13 00:00:01
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260713_000001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "optimization_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("language", sa.String(length=32), nullable=False),
        sa.Column("original_code", sa.Text(), nullable=False),
        sa.Column("optimized_code", sa.Text(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("original_time_ms", sa.Float(), nullable=True),
        sa.Column("optimized_time_ms", sa.Float(), nullable=True),
        sa.Column("original_memory_mb", sa.Float(), nullable=True),
        sa.Column("optimized_memory_mb", sa.Float(), nullable=True),
        sa.Column("time_improvement_pct", sa.Float(), nullable=True),
        sa.Column("memory_improvement_pct", sa.Float(), nullable=True),
        sa.Column("lines_of_code_before", sa.Integer(), nullable=True),
        sa.Column("lines_of_code_after", sa.Integer(), nullable=True),
        sa.Column("cyclomatic_complexity_before", sa.Integer(), nullable=True),
        sa.Column("cyclomatic_complexity_after", sa.Integer(), nullable=True),
        sa.Column("improvements", sa.JSON(), nullable=False),
        sa.Column("variants", sa.JSON(), nullable=False),
        sa.Column("analysis", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_optimization_records_id"), "optimization_records", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_optimization_records_id"), table_name="optimization_records")
    op.drop_table("optimization_records")

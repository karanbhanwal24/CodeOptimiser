"""add ai optimization fields

Revision ID: 20260713_000002
Revises: 20260713_000001
Create Date: 2026-07-13 00:00:02
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260713_000002"
down_revision = "20260713_000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("optimization_records", sa.Column("provider", sa.String(length=32), server_default="gemini", nullable=False))
    op.add_column("optimization_records", sa.Column("time_complexity_before", sa.String(length=64), nullable=True))
    op.add_column("optimization_records", sa.Column("time_complexity_after", sa.String(length=64), nullable=True))
    op.add_column("optimization_records", sa.Column("space_complexity_before", sa.String(length=64), nullable=True))
    op.add_column("optimization_records", sa.Column("space_complexity_after", sa.String(length=64), nullable=True))
    op.add_column("optimization_records", sa.Column("suggestions", sa.JSON(), server_default="[]", nullable=False))
    op.add_column("optimization_records", sa.Column("ai_response", sa.JSON(), server_default="{}", nullable=False))


def downgrade() -> None:
    op.drop_column("optimization_records", "ai_response")
    op.drop_column("optimization_records", "suggestions")
    op.drop_column("optimization_records", "space_complexity_after")
    op.drop_column("optimization_records", "space_complexity_before")
    op.drop_column("optimization_records", "time_complexity_after")
    op.drop_column("optimization_records", "time_complexity_before")
    op.drop_column("optimization_records", "provider")

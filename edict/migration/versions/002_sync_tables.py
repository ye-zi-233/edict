"""add sync-related tables: model_changes, officials_stats, morning_briefs

Revision ID: 002_sync_tables
Revises: 001_initial
Create Date: 2026-03-06 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "002_sync_tables"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── model_changes 表 — 模型变更日志 ──
    op.create_table(
        "model_changes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("agent_id", sa.String(50), nullable=False),
        sa.Column("old_model", sa.String(100), server_default=""),
        sa.Column("new_model", sa.String(100), nullable=False),
        sa.Column("status", sa.String(20), server_default="applied"),
        sa.Column("error", sa.Text(), server_default=""),
        sa.Column("applied_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_model_changes_agent_id", "model_changes", ["agent_id"])
    op.create_index("ix_model_changes_applied_at", "model_changes", ["applied_at"])

    # ── officials_stats 表 — 官员统计快照 ──
    op.create_table(
        "officials_stats",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("agent_id", sa.String(50), nullable=False),
        sa.Column("label", sa.String(50), server_default=""),
        sa.Column("input_tokens", sa.BigInteger(), server_default="0"),
        sa.Column("output_tokens", sa.BigInteger(), server_default="0"),
        sa.Column("cache_read", sa.BigInteger(), server_default="0"),
        sa.Column("cache_write", sa.BigInteger(), server_default="0"),
        sa.Column("total_cost_usd", sa.Float(), server_default="0"),
        sa.Column("total_cost_cny", sa.Float(), server_default="0"),
        sa.Column("sessions_count", sa.Integer(), server_default="0"),
        sa.Column("tasks_done", sa.Integer(), server_default="0"),
        sa.Column("tasks_active", sa.Integer(), server_default="0"),
        sa.Column("merit_score", sa.Float(), server_default="0"),
        sa.Column("model", sa.String(100), server_default=""),
        sa.Column("snapshot_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_officials_stats_agent_id", "officials_stats", ["agent_id"])
    op.create_index("ix_officials_stats_snapshot_at", "officials_stats", ["snapshot_at"])

    # ── morning_briefs 表 — 早报存档 ──
    op.create_table(
        "morning_briefs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("date", sa.String(10), nullable=False, unique=True),
        sa.Column("categories", postgresql.JSONB(), server_default="{}"),
        sa.Column("article_count", sa.Integer(), server_default="0"),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_morning_briefs_date", "morning_briefs", ["date"], unique=True)


def downgrade() -> None:
    op.drop_table("morning_briefs")
    op.drop_table("officials_stats")
    op.drop_table("model_changes")

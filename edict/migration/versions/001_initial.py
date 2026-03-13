"""initial schema — aligned with Task / Event / Thought / Todo ORM models

⚠️  如果你已在旧版本（task_id UUID 主键）的数据库上运行过本迁移，
    请先备份数据，然后 drop 并重建数据库后再次运行：
      docker compose down -v
      docker compose up -d

Revision ID: 001_initial
Revises:
Create Date: 2026-03-13 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# 与 task.py TaskState 枚举值保持完全一致
_TASK_STATES = (
    "Gongzhu", "Zhongshu", "Menxia", "Assigned", "Next",
    "Doing", "Review", "Done", "Blocked", "Cancelled", "Pending",
)


def upgrade() -> None:
    # ── 创建 task_state 枚举类型（PostgreSQL native enum）──
    task_state = postgresql.ENUM(*_TASK_STATES, name="task_state")
    task_state.create(op.get_bind(), checkfirst=True)

    # ── tasks 表 — 与 app/models/task.py Task 类完全对齐 ──
    op.create_table(
        "tasks",
        sa.Column("id", sa.String(32), nullable=False,
                  comment="任务ID, e.g. JJC-20260301-001"),
        sa.Column("title", sa.Text(), nullable=False,
                  comment="任务标题"),
        sa.Column("state",
                  sa.Enum(*_TASK_STATES, name="task_state"),
                  nullable=False, server_default="Gongzhu",
                  comment="当前状态"),
        sa.Column("org", sa.String(32), nullable=False, server_default="公主",
                  comment="当前执行部门"),
        sa.Column("official", sa.String(32), server_default="",
                  comment="责任官员"),
        sa.Column("now", sa.Text(), server_default="",
                  comment="当前进展描述"),
        sa.Column("eta", sa.String(64), server_default="-",
                  comment="预计完成时间"),
        sa.Column("block", sa.Text(), server_default="无",
                  comment="阻塞原因"),
        sa.Column("output", sa.Text(), server_default="",
                  comment="最终产出"),
        sa.Column("priority", sa.String(16), server_default="normal",
                  comment="优先级"),
        sa.Column("archived", sa.Boolean(), nullable=False,
                  server_default=sa.text("false"),
                  comment="是否已归档"),
        sa.Column("flow_log", postgresql.JSONB(), server_default="[]",
                  comment="流转日志 [{at, from, to, remark}]"),
        sa.Column("progress_log", postgresql.JSONB(), server_default="[]",
                  comment="进展日志"),
        sa.Column("todos", postgresql.JSONB(), server_default="[]",
                  comment="子任务"),
        sa.Column("scheduler", postgresql.JSONB(), server_default="{}",
                  comment="调度器元数据"),
        sa.Column("template_id", sa.String(64), server_default="",
                  comment="模板ID"),
        sa.Column("template_params", postgresql.JSONB(), server_default="{}",
                  comment="模板参数"),
        sa.Column("ac", sa.Text(), server_default="",
                  comment="验收标准"),
        sa.Column("target_dept", sa.String(64), server_default="",
                  comment="目标部门"),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )
    # 与 task.py __table_args__ 索引保持一致
    op.create_index("ix_tasks_state_archived", "tasks", ["state", "archived"])
    op.create_index("ix_tasks_updated_at", "tasks", ["updated_at"])

    # ── events 表 — 与 app/models/event.py Event 类完全对齐 ──
    op.create_table(
        "events",
        sa.Column("event_id", postgresql.UUID(), nullable=False,
                  server_default=sa.text("gen_random_uuid()"),
                  comment="事件唯一ID"),
        sa.Column("trace_id", sa.String(32), nullable=False,
                  comment="关联任务ID"),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("topic", sa.String(128), nullable=False,
                  comment="事件主题, e.g. task.created"),
        sa.Column("event_type", sa.String(128), nullable=False,
                  comment="事件类型"),
        sa.Column("producer", sa.String(128), nullable=False,
                  comment="事件生产者"),
        sa.Column("payload", postgresql.JSONB(), server_default="{}"),
        sa.Column("meta", postgresql.JSONB(), server_default="{}"),
        sa.PrimaryKeyConstraint("event_id"),
    )
    # 与 event.py __table_args__ 索引保持一致
    op.create_index("ix_events_trace_topic", "events", ["trace_id", "topic"])
    op.create_index("ix_events_timestamp", "events", ["timestamp"])

    # ── thoughts 表 — 与 app/models/thought.py Thought 类完全对齐 ──
    op.create_table(
        "thoughts",
        sa.Column("thought_id", postgresql.UUID(), nullable=False,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("trace_id", sa.String(32), nullable=False,
                  comment="关联任务ID"),
        sa.Column("agent", sa.String(32), nullable=False,
                  comment="Agent 标识"),
        sa.Column("step", sa.Integer(), nullable=False, server_default="0",
                  comment="思考步骤序号"),
        sa.Column("type", sa.String(32), nullable=False, server_default="reasoning",
                  comment="thinking类型"),
        sa.Column("source", sa.String(16), server_default="llm",
                  comment="来源: llm|tool|human"),
        sa.Column("content", sa.Text(), nullable=False, server_default="",
                  comment="思考内容"),
        sa.Column("tokens", sa.Integer(), server_default="0"),
        sa.Column("confidence", sa.Float(precision=4), server_default="0"),
        sa.Column("sensitive", sa.Boolean(), nullable=False,
                  server_default=sa.text("false")),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("thought_id"),
    )
    # 与 thought.py __table_args__ 索引保持一致
    op.create_index("ix_thoughts_trace_agent", "thoughts", ["trace_id", "agent"])
    op.create_index("ix_thoughts_timestamp", "thoughts", ["timestamp"])

    # ── todos 表 — 与 app/models/todo.py Todo 类完全对齐 ──
    # 注意：trace_id 是字符串型任务ID关联，不是 UUID FK，与 tasks.id 对应
    op.create_table(
        "todos",
        sa.Column("todo_id", postgresql.UUID(), nullable=False,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("trace_id", sa.String(32), nullable=False,
                  comment="关联任务ID (对应 tasks.id)"),
        sa.Column("parent_id", postgresql.UUID(), nullable=True,
                  comment="父级 todo_id（树状结构）"),
        sa.Column("title", sa.String(256), nullable=False,
                  comment="子任务标题"),
        sa.Column("description", sa.Text(), server_default="",
                  comment="详细描述"),
        sa.Column("owner", sa.String(64), server_default="",
                  comment="负责部门"),
        sa.Column("assignee_agent", sa.String(32), server_default="",
                  comment="执行 Agent"),
        sa.Column("status", sa.String(32), nullable=False, server_default="open",
                  comment="状态: open|in_progress|done|cancelled"),
        sa.Column("priority", sa.String(16), server_default="normal"),
        sa.Column("estimated_cost", sa.Float(), server_default="0",
                  comment="预估 token 耗费"),
        sa.Column("created_by", sa.String(64), server_default=""),
        sa.Column("checkpoints", postgresql.JSONB(), server_default="[]",
                  comment="检查点 [{name, status}]"),
        sa.Column("metadata", postgresql.JSONB(), server_default="{}",
                  comment="扩展元数据（Python 侧映射为 metadata_）"),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("todo_id"),
    )
    # 与 todo.py __table_args__ 索引保持一致
    op.create_index("ix_todos_trace_status", "todos", ["trace_id", "status"])


def downgrade() -> None:
    op.drop_table("todos")
    op.drop_table("thoughts")
    op.drop_table("events")
    op.drop_table("tasks")
    op.execute("DROP TYPE IF EXISTS task_state")

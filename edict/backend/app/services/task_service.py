"""任务服务层 — CRUD + 状态机逻辑。

所有业务规则集中在此：
- 创建任务 → 发布 task.created 事件
- 状态流转 → 校验合法性 + 发布状态事件
- 查询、过滤、聚合

注意：task_id 类型为 str（如 "JJC-20260301-001"），不是 UUID。
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.task import Task, TaskState, STATE_TRANSITIONS, TERMINAL_STATES
from .event_bus import (
    EventBus,
    TOPIC_TASK_CREATED,
    TOPIC_TASK_STATUS,
    TOPIC_TASK_COMPLETED,
    TOPIC_TASK_DISPATCH,
)

log = logging.getLogger("edict.task_service")


def _generate_task_id() -> str:
    """按 JJC-YYYYMMDD-NNN 格式生成任务 ID（序号部分用随机后缀避免并发冲突）。"""
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    short = uuid.uuid4().hex[:6]
    return f"JJC-{today}-{short}"


class TaskService:
    def __init__(self, db: AsyncSession, event_bus: EventBus):
        self.db = db
        self.bus = event_bus

    # ── 创建 ──

    async def create_task(
        self,
        title: str,
        task_id: str | None = None,
        org: str = "公主",
        priority: str = "normal",
        initial_state: TaskState = TaskState.Gongzhu,
        target_dept: str = "",
        ac: str = "",
        template_id: str = "",
        template_params: dict | None = None,
    ) -> Task:
        """创建任务并发布 task.created 事件。

        Args:
            title: 任务标题
            task_id: 可选，不传则自动生成 JJC-YYYYMMDD-xxx
            org: 当前执行部门，默认 "公主"
            priority: 优先级
            initial_state: 初始状态
            target_dept: 目标部门
            ac: 验收标准
            template_id: 模板 ID
            template_params: 模板参数
        """
        now = datetime.now(timezone.utc)
        task_id = task_id or _generate_task_id()
        # trace_id 仅用于事件总线追踪，不持久化到任务表
        trace_id = str(uuid.uuid4())

        task = Task(
            id=task_id,
            title=title,
            state=initial_state,
            org=org,
            priority=priority,
            target_dept=target_dept,
            ac=ac,
            template_id=template_id,
            template_params=template_params or {},
            flow_log=[
                {
                    "from": None,
                    "to": initial_state.value,
                    "agent": "system",
                    "reason": "任务创建",
                    "ts": now.isoformat(),
                }
            ],
            progress_log=[],
            todos=[],
        )
        self.db.add(task)
        await self.db.flush()

        await self.bus.publish(
            topic=TOPIC_TASK_CREATED,
            trace_id=trace_id,
            event_type="task.created",
            producer="task_service",
            payload={
                "task_id": task.id,
                "title": title,
                "state": initial_state.value,
                "priority": priority,
                "org": org,
            },
        )

        await self.db.commit()
        log.info(f"Created task {task.id}: {title} [{initial_state.value}]")
        return task

    # ── 状态流转 ──

    async def transition_state(
        self,
        task_id: str,
        new_state: TaskState,
        agent: str = "system",
        reason: str = "",
    ) -> Task:
        """执行状态流转，校验合法性。"""
        task = await self._get_task(task_id)
        old_state = task.state

        allowed = STATE_TRANSITIONS.get(old_state, set())
        if new_state not in allowed:
            raise ValueError(
                f"Invalid transition: {old_state.value} → {new_state.value}. "
                f"Allowed: {[s.value for s in allowed]}"
            )

        task.state = new_state
        task.updated_at = datetime.now(timezone.utc)

        flow_entry = {
            "from": old_state.value,
            "to": new_state.value,
            "agent": agent,
            "reason": reason,
            "ts": datetime.now(timezone.utc).isoformat(),
        }
        if task.flow_log is None:
            task.flow_log = []
        task.flow_log = [*task.flow_log, flow_entry]

        topic = TOPIC_TASK_COMPLETED if new_state in TERMINAL_STATES else TOPIC_TASK_STATUS
        trace_id = str(uuid.uuid4())
        await self.bus.publish(
            topic=topic,
            trace_id=trace_id,
            event_type=f"task.state.{new_state.value}",
            producer=agent,
            payload={
                "task_id": task.id,
                "from": old_state.value,
                "to": new_state.value,
                "reason": reason,
                "org": task.org,
            },
        )

        await self.db.commit()
        log.info(f"Task {task.id} state: {old_state.value} → {new_state.value} by {agent}")
        return task

    # ── 派发请求 ──

    async def request_dispatch(
        self,
        task_id: str,
        target_agent: str,
        message: str = "",
    ):
        """发布 task.dispatch 事件，由 DispatchWorker 消费执行。"""
        task = await self._get_task(task_id)
        trace_id = str(uuid.uuid4())
        await self.bus.publish(
            topic=TOPIC_TASK_DISPATCH,
            trace_id=trace_id,
            event_type="task.dispatch.request",
            producer="task_service",
            payload={
                "task_id": task.id,
                "agent": target_agent,
                "message": message,
                "state": task.state.value,
            },
        )
        log.info(f"Dispatch requested: task {task.id} → agent {target_agent}")

    # ── 进度/备注更新 ──

    async def add_progress(
        self,
        task_id: str,
        agent: str,
        content: str,
    ) -> Task:
        task = await self._get_task(task_id)
        entry = {
            "agent": agent,
            "content": content,
            "ts": datetime.now(timezone.utc).isoformat(),
        }
        if task.progress_log is None:
            task.progress_log = []
        task.progress_log = [*task.progress_log, entry]
        task.updated_at = datetime.now(timezone.utc)
        await self.db.commit()
        return task

    async def update_todos(
        self,
        task_id: str,
        todos: list[dict],
    ) -> Task:
        task = await self._get_task(task_id)
        task.todos = todos
        task.updated_at = datetime.now(timezone.utc)
        await self.db.commit()
        return task

    async def update_scheduler(
        self,
        task_id: str,
        scheduler: dict,
    ) -> Task:
        task = await self._get_task(task_id)
        task.scheduler = scheduler
        task.updated_at = datetime.now(timezone.utc)
        await self.db.commit()
        return task

    # ── 查询 ──

    async def get_task(self, task_id: str) -> Task:
        return await self._get_task(task_id)

    async def list_tasks(
        self,
        state: TaskState | None = None,
        org: str | None = None,
        priority: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Task]:
        stmt = select(Task)
        conditions = []
        if state is not None:
            conditions.append(Task.state == state)
        if org is not None:
            conditions.append(Task.org == org)
        if priority is not None:
            conditions.append(Task.priority == priority)
        if conditions:
            stmt = stmt.where(and_(*conditions))
        stmt = stmt.order_by(Task.created_at.desc()).limit(limit).offset(offset)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_live_status(self) -> dict[str, Any]:
        """生成兼容旧 live_status.json 格式的全局状态。"""
        tasks = await self.list_tasks(limit=200)
        active_tasks = {}
        completed_tasks = {}
        for t in tasks:
            d = t.to_dict()
            if t.state in TERMINAL_STATES:
                completed_tasks[t.id] = d
            else:
                active_tasks[t.id] = d
        return {
            "tasks": active_tasks,
            "completed_tasks": completed_tasks,
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }

    async def count_tasks(self, state: TaskState | None = None) -> int:
        stmt = select(func.count(Task.id))
        if state is not None:
            stmt = stmt.where(Task.state == state)
        result = await self.db.execute(stmt)
        return result.scalar_one()

    # ── 内部 ──

    async def _get_task(self, task_id: str) -> Task:
        """根据任务 ID（如 JJC-20260301-001）查找任务。"""
        task = await self.db.get(Task, task_id)
        if task is None:
            raise ValueError(f"Task not found: {task_id}")
        return task

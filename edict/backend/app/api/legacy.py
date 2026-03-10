"""Legacy 兼容路由 — 通过 JJC-xxx 格式 ID 操作任务。

Task 模型主键本身就是 JJC-YYYYMMDD-NNN 格式的 String，
因此直接用 Task.id 查询即可，无需绕道 tags/meta。
"""

import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..models.task import Task, TaskState
from ..services.event_bus import get_event_bus
from ..services.task_service import TaskService

log = logging.getLogger("edict.api.legacy")
router = APIRouter()


async def _find_by_legacy_id(db: AsyncSession, legacy_id: str) -> Task | None:
    """通过 JJC-xxx ID 查找任务（即 Task 主键）。"""
    return await db.get(Task, legacy_id)


class LegacyTransition(BaseModel):
    new_state: str
    agent: str = "system"
    reason: str = ""


class LegacyProgress(BaseModel):
    agent: str
    content: str


class LegacyTodoUpdate(BaseModel):
    todos: list[dict]


@router.post("/by-legacy/{legacy_id}/transition")
async def legacy_transition(
    legacy_id: str,
    body: LegacyTransition,
    db: AsyncSession = Depends(get_db),
):
    task = await _find_by_legacy_id(db, legacy_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Legacy task not found: {legacy_id}")

    bus = await get_event_bus()
    svc = TaskService(db, bus)
    try:
        new_state = TaskState(body.new_state)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid state: {body.new_state}")

    try:
        t = await svc.transition_state(task.id, new_state, body.agent, body.reason)
        return {"task_id": t.id, "state": t.state.value}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/by-legacy/{legacy_id}/progress")
async def legacy_progress(
    legacy_id: str,
    body: LegacyProgress,
    db: AsyncSession = Depends(get_db),
):
    task = await _find_by_legacy_id(db, legacy_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Legacy task not found: {legacy_id}")

    bus = await get_event_bus()
    svc = TaskService(db, bus)
    await svc.add_progress(task.id, body.agent, body.content)
    return {"message": "ok"}


@router.put("/by-legacy/{legacy_id}/todos")
async def legacy_todos(
    legacy_id: str,
    body: LegacyTodoUpdate,
    db: AsyncSession = Depends(get_db),
):
    task = await _find_by_legacy_id(db, legacy_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Legacy task not found: {legacy_id}")

    bus = await get_event_bus()
    svc = TaskService(db, bus)
    await svc.update_todos(task.id, body.todos)
    return {"message": "ok"}


@router.get("/by-legacy/{legacy_id}")
async def legacy_get(
    legacy_id: str,
    db: AsyncSession = Depends(get_db),
):
    task = await _find_by_legacy_id(db, legacy_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Legacy task not found: {legacy_id}")
    return task.to_dict()

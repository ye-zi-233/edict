"""任务操作 API — 叫停/取消/恢复、御批、推进、归档、创建、活动查询。

所有端点已迁移至 PostgreSQL（通过 TaskService），不再读写 JSON 文件。
路由通过 main.py 以 prefix="/api" 挂载，对外路径不变。
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..services.event_bus import EventBus, get_event_bus
from ..services.task_service import TaskService
from ..models.task import TaskState, STATE_AGENT_MAP, ORG_AGENT_MAP

log = logging.getLogger("edict.api.task_ops")
router = APIRouter()

# 状态值 → 显示标签（供 API 响应使用）
_STATE_LABELS: dict[str, str] = {
    "Pending": "待处理",
    "Taizi": "太子",
    "Zhongshu": "中书省",
    "Menxia": "门下省",
    "Assigned": "尚书省",
    "Next": "待执行",
    "Doing": "执行中",
    "Review": "审查",
    "Done": "完成",
    "Blocked": "已叫停",
    "Cancelled": "已取消",
}

# 手动推进：当前状态 → 默认下一状态（不含终态和 Blocked）
_ADVANCE_NEXT: dict[TaskState, TaskState] = {
    TaskState.Pending: TaskState.Zhongshu,
    TaskState.Taizi: TaskState.Zhongshu,
    TaskState.Zhongshu: TaskState.Menxia,
    TaskState.Menxia: TaskState.Assigned,
    TaskState.Assigned: TaskState.Doing,
    TaskState.Next: TaskState.Doing,
    TaskState.Doing: TaskState.Review,
    TaskState.Review: TaskState.Done,
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _svc(db: AsyncSession, bus: EventBus) -> TaskService:
    return TaskService(db, bus)


# ── POST /api/task-action — 叫停/取消/恢复 ──

@router.post("/task-action")
async def task_action(
    body: dict,
    db: AsyncSession = Depends(get_db),
    bus: EventBus = Depends(get_event_bus),
):
    task_id = body.get("taskId", "")
    action = body.get("action", "")
    reason = body.get("reason", "")
    if not task_id or action not in ("stop", "cancel", "resume"):
        return {"ok": False, "error": "taskId 和 action(stop/cancel/resume) 必填"}

    svc = _svc(db, bus)
    try:
        task = await svc.get_task(task_id)
    except ValueError as e:
        return {"ok": False, "error": str(e)}

    old_state = task.state
    try:
        if action == "stop":
            if old_state in (TaskState.Done, TaskState.Cancelled, TaskState.Blocked):
                return {"ok": False, "error": f"任务已处于 {old_state.value}，无法叫停"}
            await svc._force_transition(task, TaskState.Blocked, agent="operator", reason=reason or "手动叫停")
            task.block = reason or "手动叫停"
            task.now = f"🛑 手动叫停: {reason}" if reason else "🛑 手动叫停"
            await db.commit()

        elif action == "cancel":
            if old_state == TaskState.Cancelled:
                return {"ok": False, "error": "任务已取消"}
            await svc._force_transition(task, TaskState.Cancelled, agent="operator", reason=reason or "手动取消")
            task.now = f"❌ 已取消: {reason}" if reason else "❌ 已取消"
            await db.commit()

        elif action == "resume":
            if old_state not in (TaskState.Blocked, TaskState.Cancelled):
                return {"ok": False, "error": f"任务状态 {old_state.value} 无法恢复"}
            task = await svc.resume_task(task_id, agent="operator")

    except ValueError as e:
        return {"ok": False, "error": str(e)}

    return {"ok": True, "message": f"{task_id} {action} 成功"}


# ── POST /api/review-action — 门下省御批 ──

@router.post("/review-action")
async def review_action(
    body: dict,
    db: AsyncSession = Depends(get_db),
    bus: EventBus = Depends(get_event_bus),
):
    task_id = body.get("taskId", "")
    action = body.get("action", "")
    comment = body.get("comment", "")
    if not task_id or action not in ("approve", "reject"):
        return {"ok": False, "error": "taskId 和 action(approve/reject) 必填"}

    svc = _svc(db, bus)
    try:
        task = await svc.get_task(task_id)
    except ValueError as e:
        return {"ok": False, "error": str(e)}

    if task.state != TaskState.Menxia:
        verb = "准奏" if action == "approve" else "封驳"
        return {"ok": False, "error": f"只有门下省审议中的任务可以{verb}（当前: {task.state.value}）"}

    try:
        if action == "approve":
            await svc.transition_state(task_id, TaskState.Assigned, agent="menxia", reason=comment or "门下省准奏")
            task.now = f"✅ 门下省准奏{': ' + comment if comment else ''}"
            await db.commit()
        else:
            # 封驳：退回中书省，review_round + 1
            await svc.transition_state(task_id, TaskState.Zhongshu, agent="menxia", reason=comment or "门下省封驳")
            task = await svc.get_task(task_id)
            scheduler = dict(task.scheduler or {})
            scheduler["review_round"] = scheduler.get("review_round", 0) + 1
            task.scheduler = scheduler
            task.now = f"🚫 门下省封驳{': ' + comment if comment else ''}"
            await db.commit()
    except ValueError as e:
        return {"ok": False, "error": str(e)}

    return {"ok": True, "message": f"{task_id} {action} 成功"}


# ── POST /api/advance-state — 手动推进 ──

@router.post("/advance-state")
async def advance_state(
    body: dict,
    db: AsyncSession = Depends(get_db),
    bus: EventBus = Depends(get_event_bus),
):
    task_id = body.get("taskId", "")
    comment = body.get("comment", "")
    if not task_id:
        return {"ok": False, "error": "taskId 必填"}

    svc = _svc(db, bus)
    try:
        task = await svc.get_task(task_id)
    except ValueError as e:
        return {"ok": False, "error": str(e)}

    cur = task.state
    next_state = _ADVANCE_NEXT.get(cur)
    if next_state is None:
        return {"ok": False, "error": f"任务 {task_id} 状态为 {cur.value}，无法继续推进"}

    reason = comment or f"手动推进：{_STATE_LABELS.get(cur.value, cur.value)} → {_STATE_LABELS.get(next_state.value, next_state.value)}"
    try:
        await svc.transition_state(task_id, next_state, agent="operator", reason=reason)
    except ValueError as e:
        return {"ok": False, "error": str(e)}

    from_label = _STATE_LABELS.get(cur.value, cur.value)
    to_label = _STATE_LABELS.get(next_state.value, next_state.value)
    return {"ok": True, "message": f"{task_id} {from_label} → {to_label}（编排器将自动派发 Agent）"}


# ── POST /api/archive-task — 归档/取消归档 ──

@router.post("/archive-task")
async def archive_task(
    body: dict,
    db: AsyncSession = Depends(get_db),
    bus: EventBus = Depends(get_event_bus),
):
    task_id = body.get("taskId", "")
    archived = body.get("archived", True)
    archive_all_done = body.get("archiveAllDone", False)

    svc = _svc(db, bus)

    if archive_all_done:
        count = await svc.bulk_archive_terminal()
        return {"ok": True, "message": f"已归档 {count} 个已完成任务", "count": count}

    if not task_id:
        return {"ok": False, "error": "taskId 必填"}

    try:
        await svc.archive_task(task_id, archived=archived)
    except ValueError as e:
        return {"ok": False, "error": str(e)}

    action = "归档" if archived else "取消归档"
    return {"ok": True, "message": f"{task_id} {action}成功"}


# ── POST /api/create-task — 创建旨意 ──

@router.post("/create-task")
async def create_task(
    body: dict,
    db: AsyncSession = Depends(get_db),
    bus: EventBus = Depends(get_event_bus),
):
    title = body.get("title", "").strip()
    if not title:
        return {"ok": False, "error": "title 不能为空"}

    org = body.get("org", "太子")
    priority = body.get("priority", "normal")
    template_id = body.get("templateId", "")
    params = body.get("params", {})
    target_dept = body.get("targetDept", "")

    svc = _svc(db, bus)
    try:
        task = await svc.create_task(
            title=title,
            org=org,
            priority=priority,
            initial_state=TaskState.Pending,
            target_dept=target_dept,
            template_id=template_id,
            template_params=params,
        )
    except Exception as e:
        log.error(f"创建任务失败: {e}", exc_info=True)
        return {"ok": False, "error": str(e)}

    return {"ok": True, "taskId": task.id, "message": f"旨意 {task.id} 已下达"}


# ── POST /api/task-todos — 更新任务 todos ──

@router.post("/task-todos")
async def update_task_todos(
    body: dict,
    db: AsyncSession = Depends(get_db),
    bus: EventBus = Depends(get_event_bus),
):
    task_id = body.get("taskId", "")
    todos = body.get("todos", [])
    if not task_id:
        return {"ok": False, "error": "taskId 必填"}

    svc = _svc(db, bus)
    try:
        await svc.update_todos(task_id, todos)
    except ValueError as e:
        return {"ok": False, "error": str(e)}

    return {"ok": True, "message": f"{task_id} todos 已更新"}


# ── GET /api/task-activity/{task_id} — 任务实时进展 ──

@router.get("/task-activity/{task_id}")
async def get_task_activity(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    bus: EventBus = Depends(get_event_bus),
):
    svc = _svc(db, bus)
    try:
        task = await svc.get_task(task_id)
    except ValueError:
        return {"ok": False, "error": f"任务 {task_id} 不存在"}

    state = task.state.value if task.state else ""
    org = task.org or ""
    flow_log = task.flow_log or []
    progress_log = task.progress_log or []
    todos = task.todos or []
    scheduler = task.scheduler or {}

    task_meta = {
        "title": task.title,
        "state": state,
        "org": org,
        "output": task.output or "",
        "block": task.block or "",
        "priority": task.priority or "normal",
        "reviewRound": scheduler.get("review_round", 0),
        "archived": task.archived or False,
    }

    # 当前状态对应 Agent
    try:
        state_enum = TaskState(state)
        agent_id = STATE_AGENT_MAP.get(state_enum)
        if agent_id is None and state_enum in (TaskState.Doing, TaskState.Next):
            agent_id = ORG_AGENT_MAP.get(org)
    except ValueError:
        agent_id = None

    # 构建活动条目（兼容 DB 格式 ts/reason 和旧 JSON 格式 at/remark）
    activity = []
    related_agents: set[str] = set()
    total_tokens, total_cost, total_elapsed = 0, 0.0, 0
    has_resource_data = False

    for fl in flow_log:
        activity.append({
            "at": fl.get("ts") or fl.get("at", ""),
            "kind": "flow",
            "from": fl.get("from", ""),
            "to": fl.get("to", ""),
            "remark": fl.get("reason") or fl.get("remark", ""),
        })

    for pl in progress_log:
        p_agent = pl.get("agent", "")
        if p_agent:
            related_agents.add(p_agent)
        if pl.get("tokens"):
            total_tokens += pl["tokens"]
            has_resource_data = True
        if pl.get("cost"):
            total_cost += pl["cost"]
            has_resource_data = True
        if pl.get("elapsed"):
            total_elapsed += pl["elapsed"]
            has_resource_data = True
        text = pl.get("content") or pl.get("text", "")
        ts = pl.get("ts") or pl.get("at", "")
        if text:
            activity.append({
                "at": ts, "kind": "progress", "text": text,
                "agent": p_agent, "agentLabel": pl.get("agentLabel", ""),
                "state": pl.get("state", ""), "org": pl.get("org", ""),
            })
        if pl.get("todos"):
            activity.append({
                "at": ts, "kind": "todos", "items": pl["todos"],
                "agent": p_agent, "agentLabel": pl.get("agentLabel", ""),
            })

    # 无进展日志时用 now 字段兜底
    if not progress_log and task.now:
        updated_at = task.updated_at.isoformat() if task.updated_at else ""
        activity.append({"at": updated_at, "kind": "progress", "text": task.now, "agent": agent_id or ""})
        if todos:
            activity.append({"at": updated_at, "kind": "todos", "items": todos, "agent": agent_id or ""})

    activity.sort(key=lambda x: x.get("at", ""))
    if agent_id:
        related_agents.add(agent_id)

    phase_durations = _compute_phase_durations(flow_log)

    todos_summary = None
    if todos:
        total = len(todos)
        completed = sum(1 for t in todos if t.get("status") == "completed")
        in_prog = sum(1 for t in todos if t.get("status") == "in-progress")
        todos_summary = {
            "total": total, "completed": completed, "inProgress": in_prog,
            "notStarted": total - completed - in_prog,
            "percent": round(completed / total * 100) if total else 0,
        }

    result = {
        "ok": True, "taskId": task_id, "taskMeta": task_meta,
        "agentId": agent_id, "agentLabel": _STATE_LABELS.get(state, state),
        "activity": activity, "relatedAgents": sorted(list(related_agents)),
        "phaseDurations": phase_durations,
    }
    if todos_summary:
        result["todosSummary"] = todos_summary
    if has_resource_data:
        result["resourceSummary"] = {
            "totalTokens": total_tokens,
            "totalCost": round(total_cost, 4),
            "totalElapsedSec": total_elapsed,
        }
    return result


# ── GET /api/scheduler-state/{task_id} — 调度状态 ──

@router.get("/scheduler-state/{task_id}")
async def get_scheduler_state(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    bus: EventBus = Depends(get_event_bus),
):
    svc = _svc(db, bus)
    try:
        task = await svc.get_task(task_id)
    except ValueError:
        return {"ok": False, "error": f"任务 {task_id} 不存在"}

    scheduler = task.scheduler or {}
    state = task.state.value if task.state else ""
    org = task.org or ""

    stalled_sec = 0
    active_states = {"Doing", "Assigned", "Review", "Zhongshu", "Menxia", "Pending", "Taizi"}
    if state in active_states and task.updated_at:
        stalled_sec = max(0, int((datetime.now(timezone.utc) - task.updated_at).total_seconds()))

    return {
        "ok": True, "taskId": task_id,
        "state": state, "org": org,
        "scheduler": scheduler, "stalledSec": stalled_sec,
        "checkedAt": _now_iso(),
    }


def _compute_phase_durations(flow_log: list) -> list:
    """从 flow_log 计算每个阶段的停留时长（兼容 ts 和 at 两种时间字段名）。"""
    if not flow_log:
        return []
    phases = []
    for i, fl in enumerate(flow_log):
        start_at = fl.get("ts") or fl.get("at", "")
        to_dept = fl.get("to", "")
        remark = fl.get("reason") or fl.get("remark", "")
        if i + 1 < len(flow_log):
            end_at = flow_log[i + 1].get("ts") or flow_log[i + 1].get("at", "")
            ongoing = False
        else:
            end_at = _now_iso()
            ongoing = True
        dur_sec = 0
        try:
            from_dt = datetime.fromisoformat(start_at.replace("Z", "+00:00"))
            to_dt = datetime.fromisoformat(end_at.replace("Z", "+00:00"))
            dur_sec = max(0, int((to_dt - from_dt).total_seconds()))
        except Exception:
            pass
        if dur_sec < 60:
            dur_text = f"{dur_sec}秒"
        elif dur_sec < 3600:
            dur_text = f"{dur_sec // 60}分{dur_sec % 60}秒"
        elif dur_sec < 86400:
            h, rem = divmod(dur_sec, 3600)
            dur_text = f"{h}小时{rem // 60}分"
        else:
            d, rem = divmod(dur_sec, 86400)
            dur_text = f"{d}天{rem // 3600}小时"
        phases.append({
            "phase": to_dept, "from": start_at, "to": end_at,
            "durationSec": dur_sec, "durationText": dur_text,
            "ongoing": ongoing, "remark": remark,
        })
    return phases

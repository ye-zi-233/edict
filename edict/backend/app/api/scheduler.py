"""调度器 API — 停滞扫描、重试、升级、回滚。

对应前端调用的 /api/scheduler-* 端点。
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter

from ..services.openclaw_gateway import gateway_agent_request, check_gateway_alive

log = logging.getLogger("edict.api.scheduler")
router = APIRouter()

DATA = Path("/app/data")


def _read_json(path: Path, default=None):
    if not path.exists():
        return default if default is not None else {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, IOError):
        return default if default is not None else {}


def _write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _load_tasks() -> list:
    return _read_json(DATA / "tasks_source.json", [])


def _save_tasks(tasks: list):
    _write_json(DATA / "tasks_source.json", tasks)


# 状态 → Agent 映射
_STATE_AGENT_MAP = {
    "Gongzhu": "gongzhu", "Zhongshu": "zhongshu", "Menxia": "menxia",
    "Assigned": "shangshu", "Review": "shangshu", "Pending": "zhongshu",
}
_ORG_AGENT_MAP = {
    "礼部": "libu", "户部": "hubu", "兵部": "bingbu",
    "刑部": "xingbu", "工部": "gongbu", "吏部": "libu_hr",
}
_STATE_LABELS = {
    "Pending": "待处理", "Gongzhu": "公主", "Zhongshu": "中书省", "Menxia": "门下省",
    "Assigned": "尚书省", "Next": "待执行", "Doing": "执行中", "Review": "审查", "Done": "完成",
}


@router.post("/scheduler-scan")
async def scheduler_scan(body: dict | None = None):
    """扫描停滞任务并自动重试/升级/回滚。"""
    threshold = (body or {}).get("thresholdSec", 180)
    tasks = _load_tasks()
    actions = []
    active_states = {"Gongzhu", "Zhongshu", "Menxia", "Assigned", "Doing", "Review", "Next"}

    for task in tasks:
        state = task.get("state", "")
        if state not in active_states:
            continue

        updated = task.get("updatedAt", "")
        if not updated:
            continue

        try:
            upd_dt = datetime.fromisoformat(updated.replace("Z", "+00:00"))
        except Exception:
            continue

        stalled_sec = int((datetime.now(timezone.utc) - upd_dt).total_seconds())
        if stalled_sec < threshold:
            continue

        task_id = task.get("id", "")
        scheduler = task.get("_scheduler", {})
        retry_count = scheduler.get("retryCount", 0)
        max_retry = scheduler.get("maxRetry", 3)
        escalation = scheduler.get("escalationLevel", 0)

        action = None
        if retry_count < max_retry:
            scheduler["retryCount"] = retry_count + 1
            scheduler["stallSince"] = scheduler.get("stallSince") or _now_iso()
            task["_scheduler"] = scheduler
            action = {"taskId": task_id, "action": "retry", "stalledSec": stalled_sec, "retryCount": retry_count + 1}
        elif escalation < 2:
            scheduler["escalationLevel"] = escalation + 1
            task["_scheduler"] = scheduler
            action = {"taskId": task_id, "action": "escalate", "stalledSec": stalled_sec, "level": escalation + 1}
        elif scheduler.get("autoRollback") and scheduler.get("snapshot"):
            action = {"taskId": task_id, "action": "rollback", "stalledSec": stalled_sec}

        if action:
            actions.append(action)
            task["updatedAt"] = _now_iso()

    if actions:
        _save_tasks(tasks)

    return {
        "ok": True, "thresholdSec": threshold,
        "actions": actions, "count": len(actions),
        "checkedAt": _now_iso(),
    }


@router.post("/scheduler-retry")
async def scheduler_retry(body: dict):
    """手动重试任务派发。"""
    task_id = body.get("taskId", "")
    reason = body.get("reason", "手动重试")
    if not task_id:
        return {"ok": False, "error": "taskId 必填"}

    tasks = _load_tasks()
    task = next((t for t in tasks if t.get("id") == task_id), None)
    if not task:
        return {"ok": False, "error": f"任务 {task_id} 不存在"}

    state = task.get("state", "")
    scheduler = task.get("_scheduler", {})
    retry_count = scheduler.get("retryCount", 0) + 1
    scheduler["retryCount"] = retry_count
    scheduler["lastProgressAt"] = _now_iso()
    task["_scheduler"] = scheduler
    task["updatedAt"] = _now_iso()
    _save_tasks(tasks)

    # 触发派发（导入避免循环）
    from .task_ops import _dispatch_for_state_sync
    _dispatch_for_state_sync(task_id, task, state, trigger=f"manual-retry: {reason}")

    return {"ok": True, "message": f"{task_id} 已触发重试（第{retry_count}次）", "retryCount": retry_count}


@router.post("/scheduler-escalate")
async def scheduler_escalate(body: dict):
    """升级到门下省/尚书省协调。"""
    task_id = body.get("taskId", "")
    reason = body.get("reason", "手动升级")
    if not task_id:
        return {"ok": False, "error": "taskId 必填"}

    tasks = _load_tasks()
    task = next((t for t in tasks if t.get("id") == task_id), None)
    if not task:
        return {"ok": False, "error": f"任务 {task_id} 不存在"}

    scheduler = task.get("_scheduler", {})
    level = scheduler.get("escalationLevel", 0) + 1
    scheduler["escalationLevel"] = level
    task["_scheduler"] = scheduler
    task["updatedAt"] = _now_iso()
    _save_tasks(tasks)

    return {"ok": True, "message": f"{task_id} 已升级协调（级别{level}）", "escalationLevel": level}


@router.post("/scheduler-rollback")
async def scheduler_rollback(body: dict):
    """回滚到调度快照状态。"""
    task_id = body.get("taskId", "")
    reason = body.get("reason", "手动回滚")
    if not task_id:
        return {"ok": False, "error": "taskId 必填"}

    tasks = _load_tasks()
    task = next((t for t in tasks if t.get("id") == task_id), None)
    if not task:
        return {"ok": False, "error": f"任务 {task_id} 不存在"}

    scheduler = task.get("_scheduler", {})
    snapshot = scheduler.get("snapshot", {})
    if not snapshot:
        return {"ok": False, "error": f"{task_id} 无可用快照"}

    old_state = task.get("state", "")
    rollback_state = snapshot.get("state", old_state)
    task["state"] = rollback_state
    task["now"] = f"⏪ 已回滚至 {_STATE_LABELS.get(rollback_state, rollback_state)}: {reason}"
    scheduler["retryCount"] = 0
    scheduler["escalationLevel"] = 0
    scheduler.pop("stallSince", None)
    task["_scheduler"] = scheduler
    task.setdefault("flow_log", []).append({
        "at": _now_iso(), "from": old_state, "to": rollback_state,
        "remark": f"⏪ 回滚: {reason}",
    })
    task["updatedAt"] = _now_iso()
    _save_tasks(tasks)

    from .task_ops import _dispatch_for_state_sync
    _dispatch_for_state_sync(task_id, task, rollback_state, trigger=f"rollback: {reason}")

    return {"ok": True, "message": f"{task_id} 已回滚至 {_STATE_LABELS.get(rollback_state, rollback_state)}"}

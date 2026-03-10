"""任务操作 API — 叫停/取消/恢复、御批、推进、归档、创建、活动查询。

这些端点通过 compat.py 注册到旧路径（/api/task-action 等），
保持与前端 api.ts 完全兼容。
"""

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter

from ..config import get_settings
from ..services.openclaw_gateway import gateway_agent_request, check_gateway_alive

log = logging.getLogger("edict.api.task_ops")
router = APIRouter()

DATA = Path("/app/data")
_SAFE_NAME_RE = re.compile(r"^[a-zA-Z0-9_\-\u4e00-\u9fff]+$")


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
    # 触发 live data 刷新
    import subprocess
    try:
        subprocess.Popen(
            ["python3", "/app/scripts/refresh_live_data.py"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass


# 状态 → Agent 映射
_STATE_AGENT_MAP = {
    "Gongzhu": "gongzhu", "Zhongshu": "zhongshu", "Menxia": "menxia",
    "Assigned": "shangshu", "Review": "shangshu", "Pending": "zhongshu",
}
_ORG_AGENT_MAP = {
    "礼部": "libu", "户部": "hubu", "兵部": "bingbu",
    "刑部": "xingbu", "工部": "gongbu", "吏部": "libu_hr",
    "中书省": "zhongshu", "门下省": "menxia", "尚书省": "shangshu",
}
_STATE_FLOW = {
    "Pending":  ("Gongzhu", "主人", "公主", "待处理旨意转交公主分拣"),
    "Gongzhu": ("Zhongshu", "公主", "中书省", "公主分拣完毕，转中书省起草"),
    "Zhongshu": ("Menxia", "中书省", "门下省", "中书省方案提交门下省审议"),
    "Menxia":   ("Assigned", "门下省", "尚书省", "门下省准奏，转尚书省派发"),
    "Assigned": ("Doing", "尚书省", "六部", "尚书省开始派发执行"),
    "Next":     ("Doing", "尚书省", "六部", "待执行任务开始执行"),
    "Doing":    ("Review", "六部", "尚书省", "各部完成，进入汇总"),
    "Review":   ("Done", "尚书省", "公主", "全流程完成，回奏公主转报主人"),
}
_STATE_LABELS = {
    "Pending": "待处理", "Gongzhu": "公主", "Zhongshu": "中书省", "Menxia": "门下省",
    "Assigned": "尚书省", "Next": "待执行", "Doing": "执行中", "Review": "审查", "Done": "完成",
}


def _dispatch_for_state_sync(task_id, task, new_state, trigger="state-transition"):
    """推进后异步派发 Agent（后台线程，不阻塞响应）。"""
    import asyncio
    import threading

    agent_id = _STATE_AGENT_MAP.get(new_state)
    if agent_id is None and new_state in ("Doing", "Next"):
        agent_id = _ORG_AGENT_MAP.get(task.get("org", ""))
    if not agent_id:
        return

    title = task.get("title", "(无标题)")
    msg = f"📌 请处理任务\n任务ID: {task_id}\n旨意: {title}\n⚠️ 看板已有此任务，请勿重复创建。"

    def _do():
        try:
            loop = asyncio.new_event_loop()
            result = loop.run_until_complete(gateway_agent_request(agent_id, msg, timeout=310))
            if result["ok"]:
                log.info(f"✅ {task_id} 自动派发成功 → {agent_id}")
            else:
                log.warning(f"⚠️ {task_id} 派发失败: {result.get('error', '')[:200]}")
            loop.close()
        except Exception as e:
            log.warning(f"⚠️ {task_id} 派发异常: {e}")

    threading.Thread(target=_do, daemon=True).start()


def _ensure_scheduler(task):
    if not task.get("_scheduler"):
        task["_scheduler"] = {
            "enabled": True, "stallThresholdSec": 180, "maxRetry": 3,
            "retryCount": 0, "escalationLevel": 0,
        }


# ── POST /api/task-action — 叫停/取消/恢复 ──

@router.post("/task-action")
async def task_action(body: dict):
    task_id = body.get("taskId", "")
    action = body.get("action", "")
    reason = body.get("reason", "")
    if not task_id or action not in ("stop", "cancel", "resume"):
        return {"ok": False, "error": "taskId 和 action(stop/cancel/resume) 必填"}

    tasks = _load_tasks()
    task = next((t for t in tasks if t.get("id") == task_id), None)
    if not task:
        return {"ok": False, "error": f"任务 {task_id} 不存在"}

    old_state = task.get("state", "")
    if action == "stop":
        if old_state in ("Done", "Cancelled", "Blocked"):
            return {"ok": False, "error": f"任务已处于 {old_state}，无法叫停"}
        task["state"] = "Blocked"
        task["block"] = reason or "手动叫停"
        task["now"] = f"🛑 手动叫停: {reason}" if reason else "🛑 手动叫停"
    elif action == "cancel":
        if old_state == "Cancelled":
            return {"ok": False, "error": "任务已取消"}
        task["state"] = "Cancelled"
        task["now"] = f"❌ 已取消: {reason}" if reason else "❌ 已取消"
    elif action == "resume":
        if old_state not in ("Blocked", "Cancelled"):
            return {"ok": False, "error": f"任务状态 {old_state} 无法恢复"}
        _ensure_scheduler(task)
        prev_state = "Gongzhu"
        flow_log = task.get("flow_log", [])
        for fl in reversed(flow_log):
            s = fl.get("to", "")
            if s and s not in ("Blocked", "Cancelled"):
                prev_state = s
                break
        task["state"] = prev_state
        task["block"] = "无"
        task["now"] = f"♻️ 已恢复到 {_STATE_LABELS.get(prev_state, prev_state)}"
        _dispatch_for_state_sync(task_id, task, prev_state, trigger="resume")

    task.setdefault("flow_log", []).append({
        "at": _now_iso(), "from": old_state,
        "to": task["state"], "remark": f"{action}: {reason}" if reason else action,
    })
    task["updatedAt"] = _now_iso()
    _save_tasks(tasks)
    return {"ok": True, "message": f"{task_id} {action} 成功"}


# ── POST /api/review-action — 门下省御批 ──

@router.post("/review-action")
async def review_action(body: dict):
    task_id = body.get("taskId", "")
    action = body.get("action", "")
    comment = body.get("comment", "")
    if not task_id or action not in ("approve", "reject"):
        return {"ok": False, "error": "taskId 和 action(approve/reject) 必填"}

    tasks = _load_tasks()
    task = next((t for t in tasks if t.get("id") == task_id), None)
    if not task:
        return {"ok": False, "error": f"任务 {task_id} 不存在"}

    cur = task.get("state", "")
    if action == "approve":
        if cur != "Menxia":
            return {"ok": False, "error": f"只有门下省审议中的任务可以准奏（当前: {cur}）"}
        task["state"] = "Assigned"
        task["now"] = f"✅ 门下省准奏{': ' + comment if comment else ''}"
        task.setdefault("flow_log", []).append({
            "at": _now_iso(), "from": "门下省", "to": "尚书省",
            "remark": f"准奏{': ' + comment if comment else ''}",
        })
        _dispatch_for_state_sync(task_id, task, "Assigned", trigger="review-approve")
    else:
        if cur != "Menxia":
            return {"ok": False, "error": f"只有门下省审议中的任务可以封驳（当前: {cur}）"}
        task["state"] = "Zhongshu"
        task["now"] = f"🚫 门下省封驳{': ' + comment if comment else ''}"
        task["review_round"] = task.get("review_round", 0) + 1
        task.setdefault("flow_log", []).append({
            "at": _now_iso(), "from": "门下省", "to": "中书省",
            "remark": f"封驳{': ' + comment if comment else ''}",
        })
        _dispatch_for_state_sync(task_id, task, "Zhongshu", trigger="review-reject")

    task["updatedAt"] = _now_iso()
    _save_tasks(tasks)
    return {"ok": True, "message": f"{task_id} {action} 成功"}


# ── POST /api/advance-state — 手动推进 ──

@router.post("/advance-state")
async def advance_state(body: dict):
    task_id = body.get("taskId", "")
    comment = body.get("comment", "")
    if not task_id:
        return {"ok": False, "error": "taskId 必填"}

    tasks = _load_tasks()
    task = next((t for t in tasks if t.get("id") == task_id), None)
    if not task:
        return {"ok": False, "error": f"任务 {task_id} 不存在"}

    cur = task.get("state", "")
    if cur not in _STATE_FLOW:
        return {"ok": False, "error": f"任务 {task_id} 状态为 {cur}，无法推进"}

    next_state, from_dept, to_dept, default_remark = _STATE_FLOW[cur]
    remark = comment or default_remark
    task["state"] = next_state
    task["now"] = f"⬇️ 手动推进：{remark}"
    task.setdefault("flow_log", []).append({
        "at": _now_iso(), "from": from_dept, "to": to_dept,
        "remark": f"⬇️ 手动推进：{remark}",
    })
    task["updatedAt"] = _now_iso()
    _save_tasks(tasks)

    if next_state != "Done":
        _dispatch_for_state_sync(task_id, task, next_state)

    from_label = _STATE_LABELS.get(cur, cur)
    to_label = _STATE_LABELS.get(next_state, next_state)
    dispatched = " (已自动派发 Agent)" if next_state != "Done" else ""
    return {"ok": True, "message": f"{task_id} {from_label} → {to_label}{dispatched}"}


# ── POST /api/archive-task — 归档/取消归档 ──

@router.post("/archive-task")
async def archive_task(body: dict):
    task_id = body.get("taskId", "")
    archived = body.get("archived", True)
    archive_all_done = body.get("archiveAllDone", False)

    tasks = _load_tasks()

    if archive_all_done:
        count = 0
        for t in tasks:
            if t.get("state") in ("Done", "Cancelled") and not t.get("archived"):
                t["archived"] = True
                count += 1
        _save_tasks(tasks)
        return {"ok": True, "message": f"已归档 {count} 个已完成任务", "count": count}

    if not task_id:
        return {"ok": False, "error": "taskId 必填"}

    task = next((t for t in tasks if t.get("id") == task_id), None)
    if not task:
        return {"ok": False, "error": f"任务 {task_id} 不存在"}

    task["archived"] = archived
    _save_tasks(tasks)
    action = "归档" if archived else "取消归档"
    return {"ok": True, "message": f"{task_id} {action}成功"}


# ── POST /api/create-task — 创建旨意 ──

@router.post("/create-task")
async def create_task(body: dict):
    title = body.get("title", "").strip()
    if not title:
        return {"ok": False, "error": "title 不能为空"}

    org = body.get("org", "公主")
    priority = body.get("priority", "normal")
    template_id = body.get("templateId", "")
    params = body.get("params", {})
    target_dept = body.get("targetDept", "")

    tasks = _load_tasks()
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    existing_today = [t for t in tasks if t.get("id", "").startswith(f"JJC-{today}-")]
    seq = len(existing_today) + 1
    task_id = f"JJC-{today}-{seq:03d}"

    task = {
        "id": task_id,
        "title": title,
        "state": "Gongzhu",
        "org": org,
        "official": "",
        "now": "📜 新旨意已下达",
        "eta": "-",
        "block": "无",
        "output": "",
        "priority": priority,
        "archived": False,
        "flow_log": [{"at": _now_iso(), "from": "主人", "to": "公主", "remark": "旨意下达"}],
        "progress_log": [],
        "todos": [],
        "templateId": template_id,
        "templateParams": params,
        "targetDept": target_dept,
        "createdAt": _now_iso(),
        "updatedAt": _now_iso(),
        "_scheduler": {
            "enabled": True, "stallThresholdSec": 180, "maxRetry": 3,
            "retryCount": 0, "escalationLevel": 0,
        },
    }
    tasks.append(task)
    _save_tasks(tasks)

    _dispatch_for_state_sync(task_id, task, "Gongzhu", trigger="imperial-edict")
    return {"ok": True, "taskId": task_id, "message": f"旨意 {task_id} 已下达"}


# ── POST /api/task-todos — 更新任务 todos ──

@router.post("/task-todos")
async def update_task_todos(body: dict):
    task_id = body.get("taskId", "")
    todos = body.get("todos", [])
    if not task_id:
        return {"ok": False, "error": "taskId 必填"}

    tasks = _load_tasks()
    task = next((t for t in tasks if t.get("id") == task_id), None)
    if not task:
        return {"ok": False, "error": f"任务 {task_id} 不存在"}

    task["todos"] = todos
    task["updatedAt"] = _now_iso()
    _save_tasks(tasks)
    return {"ok": True, "message": f"{task_id} todos 已更新"}


# ── GET /api/task-activity/{task_id} — 任务实时进展 ──

@router.get("/task-activity/{task_id}")
async def get_task_activity(task_id: str):
    tasks = _load_tasks()
    task = next((t for t in tasks if t.get("id") == task_id), None)
    if not task:
        return {"ok": False, "error": f"任务 {task_id} 不存在"}

    state = task.get("state", "")
    org = task.get("org", "")
    flow_log = task.get("flow_log", [])
    progress_log = task.get("progress_log", [])
    todos = task.get("todos", [])

    task_meta = {
        "title": task.get("title", ""),
        "state": state,
        "org": org,
        "output": task.get("output", ""),
        "block": task.get("block", ""),
        "priority": task.get("priority", "normal"),
        "reviewRound": task.get("review_round", 0),
        "archived": task.get("archived", False),
    }

    agent_id = _STATE_AGENT_MAP.get(state)
    if agent_id is None and state in ("Doing", "Next"):
        agent_id = _ORG_AGENT_MAP.get(org)

    # 构建活动条目
    activity = []
    related_agents = set()
    total_tokens, total_cost, total_elapsed = 0, 0.0, 0
    has_resource_data = False

    for fl in flow_log:
        activity.append({
            "at": fl.get("at", ""), "kind": "flow",
            "from": fl.get("from", ""), "to": fl.get("to", ""),
            "remark": fl.get("remark", ""),
        })

    for pl in progress_log:
        p_agent = pl.get("agent", "")
        if p_agent:
            related_agents.add(p_agent)
        if pl.get("tokens"):
            total_tokens += pl["tokens"]; has_resource_data = True
        if pl.get("cost"):
            total_cost += pl["cost"]; has_resource_data = True
        if pl.get("elapsed"):
            total_elapsed += pl["elapsed"]; has_resource_data = True
        if pl.get("text"):
            activity.append({
                "at": pl.get("at", ""), "kind": "progress", "text": pl["text"],
                "agent": p_agent, "agentLabel": pl.get("agentLabel", ""),
                "state": pl.get("state", ""), "org": pl.get("org", ""),
            })
        if pl.get("todos"):
            activity.append({
                "at": pl.get("at", ""), "kind": "todos", "items": pl["todos"],
                "agent": p_agent, "agentLabel": pl.get("agentLabel", ""),
            })

    if not progress_log:
        now_text = task.get("now", "")
        updated_at = task.get("updatedAt", "")
        if now_text:
            activity.append({"at": updated_at, "kind": "progress", "text": now_text, "agent": agent_id or ""})
        if todos:
            activity.append({"at": updated_at, "kind": "todos", "items": todos, "agent": agent_id or ""})

    activity.sort(key=lambda x: x.get("at", ""))
    if agent_id:
        related_agents.add(agent_id)

    # 阶段耗时
    phase_durations = _compute_phase_durations(flow_log)

    # Todos 汇总
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
async def get_scheduler_state(task_id: str):
    tasks = _load_tasks()
    task = next((t for t in tasks if t.get("id") == task_id), None)
    if not task:
        return {"ok": False, "error": f"任务 {task_id} 不存在"}

    scheduler = task.get("_scheduler", {})
    state = task.get("state", "")
    org = task.get("org", "")

    stalled_sec = 0
    if state in ("Doing", "Assigned", "Review", "Zhongshu", "Menxia", "Gongzhu"):
        updated = task.get("updatedAt", "")
        if updated:
            try:
                upd_dt = datetime.fromisoformat(updated.replace("Z", "+00:00"))
                stalled_sec = max(0, int((datetime.now(timezone.utc) - upd_dt).total_seconds()))
            except Exception:
                pass

    return {
        "ok": True, "taskId": task_id,
        "state": state, "org": org,
        "scheduler": scheduler, "stalledSec": stalled_sec,
        "checkedAt": _now_iso(),
    }


def _compute_phase_durations(flow_log: list) -> list:
    """从 flow_log 计算每个阶段的停留时长。"""
    if not flow_log:
        return []
    phases = []
    for i, fl in enumerate(flow_log):
        start_at = fl.get("at", "")
        to_dept = fl.get("to", "")
        remark = fl.get("remark", "")
        if i + 1 < len(flow_log):
            end_at = flow_log[i + 1].get("at", "")
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

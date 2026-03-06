"""兼容层路由 — 映射旧 dashboard/server.py 的端点路径到新架构。

前端 api.ts 使用的端点路径与旧 server.py 一致，
这些路由提供无缝兼容，避免前端改动。
"""

import json
import logging
from pathlib import Path
from datetime import datetime, timezone

from fastapi import APIRouter

from ..services.openclaw_gateway import get_agents_status, wake_agent

log = logging.getLogger("edict.api.compat")
router = APIRouter()

DATA = Path("/app/data")


def _read_json(path: Path, default=None):
    """安全读取 JSON 文件。"""
    if not path.exists():
        return default if default is not None else {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, IOError):
        return default if default is not None else {}


# ── 旧路径兼容：直接读 data/ JSON 文件的端点 ──

@router.get("/api/live-status")
async def live_status():
    """兼容旧 /api/live-status — 读取 live_status.json。"""
    return _read_json(DATA / "live_status.json", {"tasks": [], "syncStatus": {}})


@router.get("/api/agent-config")
async def agent_config():
    """兼容旧 /api/agent-config — 读取 agent_config.json。"""
    return _read_json(DATA / "agent_config.json", {"agents": []})


@router.get("/api/agents-status")
async def agents_status_compat():
    """兼容旧 /api/agents-status — 代理到新 agents 服务。"""
    return await get_agents_status()


@router.post("/api/agent-wake")
async def agent_wake_compat(body: dict):
    """兼容旧 /api/agent-wake。"""
    agent_id = body.get("agentId", "")
    message = body.get("message", "")
    return await wake_agent(agent_id, message)


# ── 模型管理兼容路由 ──

@router.post("/api/set-model")
async def set_model_compat(body: dict):
    """兼容旧 /api/set-model。"""
    from .models import set_model
    return await set_model(body)


@router.get("/api/model-change-log")
async def model_change_log_compat():
    """兼容旧 /api/model-change-log。"""
    return _read_json(DATA / "model_change_log.json", [])


@router.get("/api/last-result")
async def last_result_compat():
    """兼容旧 /api/last-result。"""
    return _read_json(DATA / "last_model_change_result.json", {})


# ── 官员统计兼容路由 ──

@router.get("/api/officials-stats")
async def officials_stats_compat():
    """兼容旧 /api/officials-stats。"""
    return _read_json(DATA / "officials_stats.json", {"officials": [], "totals": {}})


# ── 早报系统兼容路由 ──

@router.get("/api/morning-brief")
async def morning_brief_compat():
    """兼容旧 /api/morning-brief。"""
    return _read_json(DATA / "morning_brief.json", {"categories": {}})


@router.get("/api/morning-config")
async def morning_config_get_compat():
    """兼容旧 GET /api/morning-config。"""
    return _read_json(DATA / "morning_brief_config.json", {
        "categories": [], "keywords": [], "custom_feeds": [], "feishu_webhook": "",
    })


@router.post("/api/morning-config")
async def morning_config_post_compat(body: dict):
    """兼容旧 POST /api/morning-config。"""
    from .morning import save_morning_config
    return await save_morning_config(body)


@router.post("/api/morning-brief/refresh")
async def morning_refresh_compat(body: dict | None = None):
    """兼容旧 /api/morning-brief/refresh。"""
    from .morning import refresh_morning_brief
    return await refresh_morning_brief(body or {})


# ── Skills 管理兼容路由 ──

@router.get("/api/skill-content/{agent_id}/{skill_name}")
async def skill_content_compat(agent_id: str, skill_name: str):
    """兼容旧 /api/skill-content/{agentId}/{skillName}。"""
    from .skills import read_skill_content
    return await read_skill_content(agent_id, skill_name)


@router.get("/api/remote-skills-list")
async def remote_skills_list_compat():
    """兼容旧 /api/remote-skills-list。"""
    from .skills import remote_skills_list
    return await remote_skills_list()


@router.post("/api/add-skill")
async def add_skill_compat(body: dict):
    """兼容旧 /api/add-skill。"""
    from .skills import add_skill
    return await add_skill(body)


@router.post("/api/add-remote-skill")
async def add_remote_skill_compat(body: dict):
    """兼容旧 /api/add-remote-skill。"""
    from .skills import add_remote_skill
    return await add_remote_skill(body)


@router.post("/api/update-remote-skill")
async def update_remote_skill_compat(body: dict):
    """兼容旧 /api/update-remote-skill。"""
    from .skills import update_remote_skill
    return await update_remote_skill(body)


@router.post("/api/remove-remote-skill")
async def remove_remote_skill_compat(body: dict):
    """兼容旧 /api/remove-remote-skill。"""
    from .skills import remove_remote_skill
    return await remove_remote_skill(body)


# ── 任务操作兼容路由 ──

@router.post("/api/task-action")
async def task_action_compat(body: dict):
    from .task_ops import task_action
    return await task_action(body)


@router.post("/api/review-action")
async def review_action_compat(body: dict):
    from .task_ops import review_action
    return await review_action(body)


@router.post("/api/advance-state")
async def advance_state_compat(body: dict):
    from .task_ops import advance_state
    return await advance_state(body)


@router.post("/api/archive-task")
async def archive_task_compat(body: dict):
    from .task_ops import archive_task
    return await archive_task(body)


@router.post("/api/create-task")
async def create_task_compat(body: dict):
    from .task_ops import create_task
    return await create_task(body)


@router.post("/api/task-todos")
async def task_todos_compat(body: dict):
    from .task_ops import update_task_todos
    return await update_task_todos(body)


@router.get("/api/task-activity/{task_id}")
async def task_activity_compat(task_id: str):
    from .task_ops import get_task_activity
    return await get_task_activity(task_id)


@router.get("/api/scheduler-state/{task_id}")
async def scheduler_state_compat(task_id: str):
    from .task_ops import get_scheduler_state
    return await get_scheduler_state(task_id)


# ── 调度器兼容路由 ──

@router.post("/api/scheduler-scan")
async def scheduler_scan_compat(body: dict | None = None):
    from .scheduler import scheduler_scan
    return await scheduler_scan(body)


@router.post("/api/scheduler-retry")
async def scheduler_retry_compat(body: dict):
    from .scheduler import scheduler_retry
    return await scheduler_retry(body)


@router.post("/api/scheduler-escalate")
async def scheduler_escalate_compat(body: dict):
    from .scheduler import scheduler_escalate
    return await scheduler_escalate(body)


@router.post("/api/scheduler-rollback")
async def scheduler_rollback_compat(body: dict):
    from .scheduler import scheduler_rollback
    return await scheduler_rollback(body)

"""Agents API — Agent 配置、状态查询、唤醒。

端点：
- GET  /api/agents              — 列出所有 Agent
- GET  /api/agents/status       — 所有 Agent 在线状态
- GET  /api/agents/{agent_id}   — Agent 详情（含 SOUL.md 预览）
- GET  /api/agents/{agent_id}/config — Agent 运行时配置
- POST /api/agents/{agent_id}/wake   — 唤醒 Agent
"""

import json
import logging
from pathlib import Path

from fastapi import APIRouter

from ..services.openclaw_gateway import (
    get_agents_status as _get_agents_status,
    wake_agent as _wake_agent,
    AGENT_DEPTS,
)

log = logging.getLogger("edict.api.agents")
router = APIRouter()


@router.get("")
async def list_agents():
    """列出所有可用 Agent。"""
    agents = [{"id": d["id"], "name": d["label"], "role": d["role"], "icon": d["emoji"]} for d in AGENT_DEPTS]
    return {"agents": agents}


@router.get("/status")
async def agents_status():
    """获取所有 Agent 的在线状态（兼容 /api/agents-status）。"""
    return await _get_agents_status()


@router.get("/{agent_id}")
async def get_agent(agent_id: str):
    """获取 Agent 详情。"""
    dept = next((d for d in AGENT_DEPTS if d["id"] == agent_id), None)
    if not dept:
        return {"error": f"Agent '{agent_id}' not found"}

    soul_path = Path("/app/agents") / agent_id / "SOUL.md"
    soul_content = ""
    if soul_path.exists():
        soul_content = soul_path.read_text(encoding="utf-8")[:2000]

    return {
        "id": agent_id,
        "name": dept["label"],
        "role": dept["role"],
        "icon": dept["emoji"],
        "soul_preview": soul_content,
    }


@router.get("/{agent_id}/config")
async def get_agent_config(agent_id: str):
    """获取 Agent 运行时配置。"""
    config_path = Path("/app/data/agent_config.json")
    if not config_path.exists():
        return {"agent_id": agent_id, "config": {}}
    try:
        configs = json.loads(config_path.read_text(encoding="utf-8"))
        if isinstance(configs, dict) and "agents" in configs:
            agent_config = next((a for a in configs["agents"] if a.get("id") == agent_id), {})
        else:
            agent_config = configs.get(agent_id, {})
        return {"agent_id": agent_id, "config": agent_config}
    except (json.JSONDecodeError, IOError):
        return {"agent_id": agent_id, "config": {}}


@router.post("/{agent_id}/wake")
async def wake_agent_endpoint(agent_id: str, body: dict | None = None):
    """唤醒指定 Agent。"""
    message = (body or {}).get("message", "")
    return await _wake_agent(agent_id, message)

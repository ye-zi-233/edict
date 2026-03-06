"""模型管理 API — 切换 Agent 模型、查看变更日志。

端点：
- POST /api/models/set       — 设置 Agent 模型（排队异步应用）
- GET  /api/models/change-log — 模型变更日志
- GET  /api/models/last-result — 最近一次变更结果
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter

log = logging.getLogger("edict.api.models")
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


@router.post("/set")
async def set_model(body: dict):
    """设置 Agent 模型 — 写入 pending 文件，由 sync worker 异步应用。"""
    agent_id = body.get("agentId", "")
    model = body.get("model", "")
    if not agent_id or not model:
        return {"ok": False, "error": "agentId 和 model 不能为空"}

    pending_path = DATA / "pending_model_changes.json"
    pending = _read_json(pending_path, [])
    if not isinstance(pending, list):
        pending = []

    # 去重：同 agent 只保留最新
    pending = [p for p in pending if p.get("agentId") != agent_id]
    pending.append({
        "agentId": agent_id,
        "model": model,
        "queuedAt": datetime.now(timezone.utc).isoformat(),
    })
    _write_json(pending_path, pending)

    return {"ok": True, "message": f"Queued: {agent_id} → {model}"}


@router.get("/change-log")
async def model_change_log():
    """模型变更日志。"""
    return _read_json(DATA / "model_change_log.json", [])


@router.get("/last-result")
async def last_model_result():
    """最近一次模型变更结果。"""
    return _read_json(DATA / "last_model_change_result.json", {})

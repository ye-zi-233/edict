"""早报系统 API — 新闻查看、订阅配置、手动刷新。

端点：
- GET  /api/morning/brief         — 获取最新早报
- GET  /api/morning/config        — 获取订阅配置
- POST /api/morning/config        — 保存订阅配置
- POST /api/morning/brief/refresh — 触发早报采集
"""

import json
import logging
import subprocess
from pathlib import Path

from fastapi import APIRouter

log = logging.getLogger("edict.api.morning")
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


@router.get("/brief")
async def get_morning_brief():
    return _read_json(DATA / "morning_brief.json", {"categories": {}})


@router.get("/config")
async def get_morning_config():
    return _read_json(DATA / "morning_brief_config.json", {
        "categories": [
            {"name": "政治", "enabled": True},
            {"name": "军事", "enabled": True},
            {"name": "经济", "enabled": True},
            {"name": "AI大模型", "enabled": True},
        ],
        "keywords": [], "custom_feeds": [], "feishu_webhook": "",
    })


async def save_morning_config(body: dict) -> dict:
    """保存订阅配置 — 供 compat 路由调用。"""
    _write_json(DATA / "morning_brief_config.json", body)
    return {"ok": True, "message": "订阅配置已保存"}


@router.post("/config")
async def post_morning_config(body: dict):
    return await save_morning_config(body)


async def refresh_morning_brief(body: dict) -> dict:
    """触发早报采集 — 供 compat 路由调用。"""
    try:
        cmd = ["python3", "/app/scripts/fetch_morning_news.py"]
        if body.get("force"):
            cmd.append("--force")
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return {"ok": True, "message": "采集已触发，约30-60秒后刷新"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/brief/refresh")
async def post_morning_refresh(body: dict | None = None):
    return await refresh_morning_brief(body or {})

"""官员统计 API — 官员 Token/成本/任务统计。

端点：
- GET /api/officials/stats — 官员统计数据
"""

import json
import logging
from pathlib import Path

from fastapi import APIRouter

log = logging.getLogger("edict.api.officials")
router = APIRouter()

DATA = Path("/app/data")


@router.get("/stats")
async def get_officials_stats():
    """读取官员统计数据。"""
    path = DATA / "officials_stats.json"
    if not path.exists():
        return {"officials": [], "totals": {}}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, IOError):
        return {"officials": [], "totals": {}}

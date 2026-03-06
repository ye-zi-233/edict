"""Edict Backend — FastAPI 应用入口。

Lifespan 管理：
- startup: 连接 Redis Event Bus, 初始化数据库
- shutdown: 关闭连接

路由：
- /api/tasks     — 任务 CRUD（新架构）
- /api/agents    — Agent 信息与状态
- /api/events    — 事件查询
- /api/admin     — 管理操作
- /api/models    — 模型管理
- /api/skills    — Skills 管理
- /api/morning   — 早报系统
- /api/officials — 官员统计
- /ws            — WebSocket 实时推送
- compat routes  — 旧路径兼容（/api/live-status 等）
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .services.event_bus import get_event_bus
from .api import tasks, agents, events, admin, websocket, legacy
from .api import compat, models, task_ops, scheduler, skills, morning, officials

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
log = logging.getLogger("edict")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理。"""
    settings = get_settings()
    log.info(f"🏛️ Edict Backend starting on port {settings.port}...")

    bus = await get_event_bus()
    log.info("✅ Event Bus connected")

    yield

    await bus.close()
    log.info("Edict Backend shutdown complete")


app = FastAPI(
    title="Edict 三省六部",
    description="事件驱动的 AI Agent 协作平台",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 新架构路由 ──
app.include_router(tasks.router, prefix="/api/tasks", tags=["tasks"])
app.include_router(agents.router, prefix="/api/agents", tags=["agents"])
app.include_router(events.router, prefix="/api/events", tags=["events"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(websocket.router, tags=["websocket"])
app.include_router(legacy.router, prefix="/api/tasks", tags=["legacy"])

# ── 功能模块路由 ──
app.include_router(models.router, prefix="/api/models", tags=["models"])
app.include_router(task_ops.router, prefix="/api", tags=["task-ops"])
app.include_router(scheduler.router, prefix="/api", tags=["scheduler"])
app.include_router(skills.router, prefix="/api/skills", tags=["skills"])
app.include_router(morning.router, prefix="/api/morning", tags=["morning"])
app.include_router(officials.router, prefix="/api/officials", tags=["officials"])

# ── 旧路径兼容路由（前端 api.ts 使用的路径） ──
app.include_router(compat.router, tags=["compat"])


@app.get("/health")
async def health():
    return {"status": "ok", "version": "2.0.0", "engine": "edict"}


@app.get("/healthz")
async def healthz():
    """兼容旧 /healthz 端点。"""
    from pathlib import Path
    data_dir = Path("/app/data")
    import os
    checks = {
        "dataDir": data_dir.is_dir(),
        "dataWritable": os.access(str(data_dir), os.W_OK),
    }
    all_ok = all(checks.values())
    from datetime import datetime, timezone
    return {"status": "ok" if all_ok else "degraded", "ts": datetime.now(timezone.utc).isoformat(), "checks": checks}


@app.get("/api")
async def api_root():
    return {
        "name": "Edict 三省六部 API",
        "version": "2.0.0",
        "endpoints": {
            "tasks": "/api/tasks",
            "agents": "/api/agents",
            "events": "/api/events",
            "admin": "/api/admin",
            "models": "/api/models",
            "skills": "/api/skills",
            "morning": "/api/morning",
            "officials": "/api/officials",
            "websocket": "/ws",
            "health": "/health",
        },
    }

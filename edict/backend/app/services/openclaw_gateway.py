"""OpenClaw Gateway 通信服务 — 探测、派发任务、唤醒 Agent。

通过 HTTP API 与 OpenClaw Gateway 交互，替代旧架构中
dashboard/server.py 的 _gateway_agent_request / _check_gateway_probe 逻辑。
"""

import json
import logging
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import httpx

from ..config import get_settings

log = logging.getLogger("edict.gateway")

_SAFE_NAME_RE = re.compile(r"^[a-zA-Z0-9_\-\u4e00-\u9fff]+$")

# Agent 部门定义（与前端 agents-status 接口兼容）
AGENT_DEPTS = [
    {"id": "huanghou", "label": "皇后",  "emoji": "👑", "role": "皇后"},
    {"id": "zhongshu", "label": "中书省", "emoji": "📜", "role": "中书令"},
    {"id": "menxia",   "label": "门下省", "emoji": "🔍", "role": "侍中"},
    {"id": "shangshu", "label": "尚书省", "emoji": "📮", "role": "尚书令"},
    {"id": "hubu",     "label": "户部",  "emoji": "💰", "role": "户部尚书"},
    {"id": "libu",     "label": "礼部",  "emoji": "📝", "role": "礼部尚书"},
    {"id": "bingbu",   "label": "兵部",  "emoji": "⚔️", "role": "兵部尚书"},
    {"id": "xingbu",   "label": "刑部",  "emoji": "⚖️", "role": "刑部尚书"},
    {"id": "gongbu",   "label": "工部",  "emoji": "🔧", "role": "工部尚书"},
    {"id": "libu_hr",  "label": "吏部",  "emoji": "📋", "role": "吏部尚书"},
    {"id": "zaochao",  "label": "早朝官", "emoji": "🌅", "role": "早朝官"},
    {"id": "nvwa",     "label": "女娲",  "emoji": "🌸", "role": "灵魂守护"},
]


async def check_gateway_alive() -> bool:
    """探测 Gateway 是否可达。"""
    settings = get_settings()
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            resp = await client.get(f"{settings.openclaw_gateway_url}/")
            return resp.status_code == 200
    except Exception:
        return False


async def gateway_agent_request(agent_id: str, message: str, timeout: int = 130) -> dict:
    """通过 Gateway HTTP API 派发 Agent 任务。"""
    settings = get_settings()
    headers = {
        "Content-Type": "application/json",
        "x-openclaw-agent-id": agent_id,
    }
    if settings.openclaw_gateway_token:
        headers["Authorization"] = f"Bearer {settings.openclaw_gateway_token}"

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                f"{settings.openclaw_gateway_url}/v1/responses",
                json={"model": "openclaw", "input": message},
                headers=headers,
            )
            body = resp.text[:5000]
            return {"ok": resp.status_code == 200, "status": resp.status_code, "stdout": body}
    except Exception as e:
        return {"ok": False, "error": str(e), "stdout": "", "status": -1}


def _get_agent_session_status(agent_id: str) -> tuple[int, int, bool]:
    """读取 Agent 的 sessions.json 获取活跃状态。返回 (last_active_ts_ms, session_count, is_busy)。"""
    settings = get_settings()
    sessions_file = settings.resolved_openclaw_home / "agents" / agent_id / "sessions" / "sessions.json"
    if not sessions_file.exists():
        return 0, 0, False
    try:
        data = json.loads(sessions_file.read_text())
        if not isinstance(data, dict):
            return 0, 0, False
        session_count = len(data)
        last_ts = 0
        for v in data.values():
            ts = v.get("updatedAt", 0)
            if isinstance(ts, (int, float)) and ts > last_ts:
                last_ts = ts
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        age_ms = now_ms - last_ts if last_ts else 9999999999
        is_busy = age_ms <= 2 * 60 * 1000
        return last_ts, session_count, is_busy
    except Exception:
        return 0, 0, False


def _check_agent_process(agent_id: str) -> bool:
    """检测是否有该 Agent 的 openclaw-agent 进程正在运行。"""
    try:
        result = subprocess.run(
            ["pgrep", "-f", f"openclaw.*--agent.*{agent_id}"],
            capture_output=True, text=True, timeout=5,
        )
        return result.returncode == 0
    except Exception:
        return False


def _check_agent_workspace(agent_id: str) -> bool:
    """检查 Agent 工作空间是否存在。"""
    settings = get_settings()
    return (settings.resolved_openclaw_home / f"workspace-{agent_id}").is_dir()


async def get_agents_status() -> dict:
    """获取所有 Agent 的在线状态（兼容旧 /api/agents-status 格式）。"""
    gateway_alive = await check_gateway_alive()

    agents = []
    seen_ids: set[str] = set()
    for dept in AGENT_DEPTS:
        aid = dept["id"]
        if aid in seen_ids:
            continue
        seen_ids.add(aid)

        has_workspace = _check_agent_workspace(aid)
        last_ts, sess_count, is_busy = _get_agent_session_status(aid)
        process_alive = _check_agent_process(aid)

        if not has_workspace:
            status, status_label = "unconfigured", "❌ 未配置"
        elif not gateway_alive:
            status, status_label = "offline", "🔴 Gateway 离线"
        elif process_alive or is_busy:
            status, status_label = "running", "🟢 运行中"
        elif last_ts > 0:
            now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
            age_ms = now_ms - last_ts
            if age_ms <= 10 * 60 * 1000:
                status, status_label = "idle", "🟡 待命"
            elif age_ms <= 3600 * 1000:
                status, status_label = "idle", "⚪ 空闲"
            else:
                status, status_label = "idle", "⚪ 休眠"
        else:
            status, status_label = "idle", "⚪ 无记录"

        last_active_str = None
        if last_ts > 0:
            try:
                last_active_str = datetime.fromtimestamp(last_ts / 1000, tz=timezone.utc).strftime("%m-%d %H:%M")
            except Exception:
                pass

        agents.append({
            "id": aid,
            "label": dept["label"],
            "emoji": dept["emoji"],
            "role": dept["role"],
            "status": status,
            "statusLabel": status_label,
            "lastActive": last_active_str,
            "lastActiveTs": last_ts,
            "sessions": sess_count,
            "hasWorkspace": has_workspace,
            "processAlive": process_alive,
        })

    return {
        "ok": True,
        "gateway": {
            "alive": gateway_alive,
            "probe": gateway_alive,
            "status": "🟢 运行中" if gateway_alive else "🔴 未启动",
        },
        "agents": agents,
        "checkedAt": datetime.now(timezone.utc).isoformat(),
    }


async def wake_agent(agent_id: str, message: str = "") -> dict:
    """唤醒指定 Agent，发送一条心跳/唤醒消息。"""
    if not _SAFE_NAME_RE.match(agent_id):
        return {"ok": False, "error": f"agent_id 非法: {agent_id}"}
    if not _check_agent_workspace(agent_id):
        return {"ok": False, "error": f"{agent_id} 工作空间不存在，请先配置"}
    if not await check_gateway_alive():
        return {"ok": False, "error": "Gateway 未启动，请先运行 openclaw gateway start"}

    msg = message or f"🔔 系统心跳检测 — 请回复 OK 确认在线。当前时间: {datetime.now(timezone.utc).isoformat()}"

    # 异步调用 Gateway
    import asyncio
    asyncio.create_task(_do_wake(agent_id, msg))

    return {"ok": True, "message": f"{agent_id} 唤醒指令已发出，约10-30秒后生效"}


async def _do_wake(agent_id: str, message: str):
    """后台执行唤醒请求（最多重试 2 次）。"""
    import asyncio
    for attempt in range(1, 3):
        try:
            result = await gateway_agent_request(agent_id, message, timeout=130)
            if result["ok"]:
                log.info(f"✅ {agent_id} 已唤醒")
                return
            log.warning(f"⚠️ {agent_id} 唤醒失败(第{attempt}次): {result.get('error', '')[:200]}")
        except Exception as e:
            log.warning(f"⚠️ {agent_id} 唤醒失败(第{attempt}次): {e}")
        if attempt < 2:
            await asyncio.sleep(5)
    log.error(f"❌ {agent_id} 唤醒最终失败")

"""同步 Worker — 定时从 OpenClaw 运行时同步数据。

替代旧架构的 run_loop.sh + 5 个 Python 脚本。
以 subprocess 方式调用已有脚本，确保兼容性：
- sync_from_openclaw_runtime.py → tasks_source.json
- sync_agent_config.py → agent_config.json + 部署 SOUL.md
- apply_model_changes.py → 应用模型变更到 openclaw.json
- sync_officials_stats.py → officials_stats.json
- refresh_live_data.py → live_status.json

运行方式：python -m app.workers.sync_worker
"""

import asyncio
import logging
import os
import subprocess
import sys
import time
from pathlib import Path

import httpx

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
log = logging.getLogger("edict.sync_worker")

SCRIPTS_DIR = Path("/app/scripts")
SYNC_INTERVAL = int(os.environ.get("SYNC_INTERVAL", "15"))
SCAN_INTERVAL = int(os.environ.get("SCAN_INTERVAL", "120"))
BACKEND_URL = os.environ.get("BACKEND_URL", "http://backend:8000")


def _run_script(name: str):
    """执行单个同步脚本，将脚本输出转发到 sync_worker 日志，不中断循环。"""
    script = SCRIPTS_DIR / name
    if not script.exists():
        log.warning(f"脚本不存在: {script}")
        return
    try:
        result = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True, text=True, timeout=120,
            cwd=str(SCRIPTS_DIR),
            env={**os.environ, "PYTHONPATH": str(SCRIPTS_DIR)},
        )
        # 将脚本 stdout 中含有关键词的行提升到 INFO，其余保持 DEBUG（避免日志爆量）
        _keywords = ("✅", "❌", "⚠️", "注册", "修正", "无法读取", "Agent", "soul", "SOUL", "error", "Error", "warning", "Warning")
        for line in (result.stdout or "").splitlines():
            line = line.strip()
            if not line:
                continue
            if any(kw in line for kw in _keywords):
                log.info(f"[{name}] {line}")
            else:
                log.debug(f"[{name}] {line}")
        if result.returncode != 0:
            stderr = (result.stderr or "")[:800]
            log.warning(f"❌ {name} 退出码 {result.returncode}: {stderr}")
        else:
            log.info(f"✅ {name} 完成")
    except subprocess.TimeoutExpired:
        log.warning(f"⏰ {name} 超时（120s）")
    except Exception as e:
        log.warning(f"⚠️ {name} 异常: {e}")


async def _scheduler_scan():
    """调用后端 scheduler-scan 接口检测卡住的任务。"""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{BACKEND_URL}/api/scheduler-scan",
                json={"thresholdSec": 180},
            )
            if resp.status_code == 200:
                data = resp.json()
                count = data.get("count", 0)
                if count > 0:
                    log.info(f"🔍 巡检发现 {count} 个停滞任务")
    except Exception as e:
        log.debug(f"巡检调用失败（可能后端未就绪）: {e}")


async def main():
    log.info(f"🏛️ Sync Worker 启动 (间隔={SYNC_INTERVAL}s, 巡检间隔={SCAN_INTERVAL}s)")

    scan_counter = 0

    while True:
        start = time.monotonic()

        # 执行同步脚本
        _run_script("sync_from_openclaw_runtime.py")
        _run_script("sync_agent_config.py")
        _run_script("apply_model_changes.py")
        _run_script("sync_officials_stats.py")
        _run_script("refresh_live_data.py")

        # 定期巡检
        scan_counter += SYNC_INTERVAL
        if scan_counter >= SCAN_INTERVAL:
            scan_counter = 0
            await _scheduler_scan()

        elapsed = time.monotonic() - start
        sleep_time = max(0, SYNC_INTERVAL - elapsed)
        if sleep_time > 0:
            await asyncio.sleep(sleep_time)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Sync Worker 收到退出信号")

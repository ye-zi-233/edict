"""新闻 Worker — 定时采集 RSS 新闻生成早报。

替代旧架构中 run_loop.sh 外部触发的 fetch_morning_news.py。
每小时自动采集一次，也可通过 API 手动触发。

运行方式：python -m app.workers.news_worker
"""

import asyncio
import logging
import os
import subprocess
import sys
import time
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
log = logging.getLogger("edict.news_worker")

SCRIPTS_DIR = Path("/app/scripts")
NEWS_INTERVAL = int(os.environ.get("NEWS_INTERVAL", "3600"))  # 默认 1 小时


def _run_fetch():
    """执行早报采集脚本。"""
    script = SCRIPTS_DIR / "fetch_morning_news.py"
    if not script.exists():
        log.warning(f"脚本不存在: {script}")
        return
    try:
        result = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True, text=True, timeout=300,
            cwd=str(SCRIPTS_DIR),
            env={**os.environ, "PYTHONPATH": str(SCRIPTS_DIR)},
        )
        if result.returncode != 0:
            stderr = result.stderr[:500] if result.stderr else ""
            log.warning(f"❌ fetch_morning_news.py 退出码 {result.returncode}: {stderr}")
        else:
            log.info("✅ 早报采集完成")
    except subprocess.TimeoutExpired:
        log.warning("⏰ 早报采集超时（300s）")
    except Exception as e:
        log.warning(f"⚠️ 早报采集异常: {e}")


async def main():
    log.info(f"📰 News Worker 启动 (采集间隔={NEWS_INTERVAL}s)")

    while True:
        _run_fetch()
        await asyncio.sleep(NEWS_INTERVAL)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("News Worker 收到退出信号")

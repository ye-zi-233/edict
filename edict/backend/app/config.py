"""Edict 配置管理 — 从环境变量加载所有配置。"""

import os
from pathlib import Path

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # ── Postgres ──
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "edict"
    postgres_user: str = "edict"
    postgres_password: str = "edict_secret_change_me"
    database_url_override: str | None = None  # 直接设置 DATABASE_URL 环境变量时用

    # ── Redis ──
    redis_url: str = "redis://localhost:6379/0"

    # ── Server ──
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    port: int = 8000
    secret_key: str = "change-me-in-production"
    debug: bool = False

    # ── OpenClaw ──
    openclaw_gateway_url: str = "http://localhost:18789"
    openclaw_gateway_token: str = ""
    openclaw_bin: str = "openclaw"
    openclaw_project_dir: str | None = None
    openclaw_home: str = ""  # 运行时自动从 HOME 环境变量推导

    # ── Legacy 兼容 ──
    legacy_data_dir: str = "../data"
    legacy_tasks_file: str = "../data/tasks_source.json"

    # ── 数据同步 ──
    sync_interval: int = 15  # 从 OpenClaw 运行时同步数据的间隔（秒）

    # ── 调度参数 ──
    stall_threshold_sec: int = 180
    max_dispatch_retry: int = 3
    dispatch_timeout_sec: int = 300
    heartbeat_interval_sec: int = 30
    scheduler_scan_interval_seconds: int = 60

    # ── 飞书 ──
    feishu_deliver: bool = True
    feishu_channel: str = "feishu"
    feishu_webhook: str = ""

    @property
    def database_url(self) -> str:
        # 优先读取 DATABASE_URL 环境变量（Docker Compose 场景），
        # 其次使用 database_url_override 字段，最后从各字段拼接
        env_url = os.environ.get("DATABASE_URL")
        if env_url:
            return env_url
        if self.database_url_override:
            return self.database_url_override
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def resolved_openclaw_home(self) -> Path:
        """解析 OpenClaw 主目录路径，优先使用 OPENCLAW_HOME 环境变量。"""
        if self.openclaw_home:
            return Path(self.openclaw_home)
        home = os.environ.get("HOME", os.path.expanduser("~"))
        return Path(home) / ".openclaw"

    @property
    def database_url_sync(self) -> str:
        """同步 URL，供 Alembic 使用。"""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "env_prefix": "",
        "alias_generator": None,
        "populate_by_name": True,
        "extra": "ignore",
    }


@lru_cache
def get_settings() -> Settings:
    return Settings()

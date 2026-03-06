# ⚔️ Edict 三省六部 — 后端 + Worker 共用镜像
#
# 用途：backend / orchestrator / dispatcher / sync / news 共用
# 构建上下文为项目根目录（context: ..）

FROM python:3.12-slim

WORKDIR /app

# 安装系统依赖（curl 用于 healthcheck 和 Gateway 通信）
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY edict/backend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# 复制后端代码
COPY edict/backend/ /app/

# 复制 Alembic 配置与迁移
COPY edict/alembic.ini /app/alembic.ini
COPY edict/migration/ /app/migration/

# 复制 Agent 定义和脚本（sync worker 需要读取）
COPY agents/ /app/agents/
COPY scripts/ /app/scripts/

# 创建数据目录和用户 home（运行时通过 volume 挂载覆盖）
RUN mkdir -p /app/data /home/appuser/.openclaw \
    && chmod 777 /home/appuser /app /app/data

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start_period=20s --retries=3 \
    CMD curl -f http://127.0.0.1:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

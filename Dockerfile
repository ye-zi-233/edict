# ⚔️ 三省六部 · Dashboard + Sync 镜像
#
# 用途：dashboard 服务（server.py）和 sync 服务（run_loop.sh）共用此镜像
# 构建：docker compose build dashboard

# Stage 1: 构建 React 前端
FROM node:20-alpine AS frontend-build
WORKDIR /build
COPY edict/frontend/package.json edict/frontend/package-lock.json ./
RUN npm ci --silent
COPY edict/frontend/ ./
RUN npx vite build --outDir /build/dist

# Stage 2: 运行时
FROM python:3.11-slim

WORKDIR /app

# run_loop.sh 中 curl 调用 scheduler-scan 需要
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制看板核心文件
COPY dashboard/ ./dashboard/
COPY scripts/ ./scripts/
COPY agents/ ./agents/

# 复制 React 构建产物
COPY --from=frontend-build /build/dist ./dashboard/dist/

# 创建 data 目录（运行时通过 volume 挂载覆盖）
RUN mkdir -p /app/data

# 创建默认用户目录（运行时通过 compose user: 指定实际 UID:GID）
RUN mkdir -p /home/appuser && chmod 777 /home/appuser /app /app/data

EXPOSE 7891

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:7891/healthz')" || exit 1

CMD ["python3", "dashboard/server.py", "--host", "0.0.0.0", "--port", "7891"]

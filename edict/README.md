# Edict 三省六部 — Docker 部署指南

## 职责

Edict 是三省六部的事件驱动后端架构，基于 PostgreSQL + Redis + FastAPI，提供完整的 AI Agent 协作平台部署方案。

## 核心服务

| 服务 | 用途 | 技术栈 | 端口 |
|------|------|--------|------|
| **postgres** | 任务/事件/统计持久化 | PostgreSQL 16 Alpine | 5432 |
| **redis** | 事件总线 + 消息队列 | Redis 7 Alpine | 6379 |
| **backend** | REST API + WebSocket | Python 3.12 + FastAPI | 8000 |
| **orchestrator** | 任务编排（状态机驱动） | Redis Streams 消费者 | - |
| **dispatcher** | Agent 派发（调用 OpenClaw） | Redis Streams 消费者 | - |
| **sync** | 数据同步（OpenClaw 运行时） | 定时脚本循环 | - |
| **news** | RSS 新闻采集（每小时） | 定时脚本 | - |
| **frontend** | 军机处看板 UI | React 18 + Nginx | 3000 |

## 快速开始

### 前置条件

- Docker + Docker Compose
- [OpenClaw](https://openclaw.ai) Gateway 已运行且网络可达

### 启动

```bash
cd edict
cp .env.example .env
# 编辑 .env，设置 EDICT_ROOT、OPENCLAW_HOME 为宿主机绝对路径，以及 POSTGRES_PASSWORD
docker compose up -d
```

打开 http://localhost:3000 即可使用。数据子目录（postgres/redis/edict）由 `init-data-dirs` 服务在首次启动时自动创建。

### 配置说明

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `EDICT_ROOT` | 项目根目录绝对路径，控制 agents/scripts（代码）和 data/（数据）的挂载位置 | 必填 |
| `OPENCLAW_HOME` | 宿主机 OpenClaw 主目录绝对路径 | 必填 |
| `PUID` / `PGID` | 容器运行用户 UID/GID，与宿主机目录所有者一致 | `1000` |
| `OPENCLAW_GATEWAY_URL` | Gateway 地址（容器内用 `host.docker.internal`） | `http://host.docker.internal:18789` |
| `OPENCLAW_GATEWAY_TOKEN` | Gateway 认证 Token（无认证留空） | 空 |
| `POSTGRES_PASSWORD` | PostgreSQL 密码 | `edict_secret_change_me` |
| `FRONTEND_PORT` | 看板前端端口 | `3000` |
| `BACKEND_PORT` | API 后端端口 | `8000` |
| `SYNC_INTERVAL` | 数据同步间隔（秒） | `15` |
| `STALL_THRESHOLD_SEC` | 任务停滞检测阈值（秒） | `180` |
| `MAX_DISPATCH_RETRY` | 派发最大重试次数 | `3` |
| `FEISHU_DELIVER` | 是否推送飞书 | `true` |

### 常用命令

```bash
# 查看服务状态
docker compose ps

# 查看后端日志
docker compose logs -f backend

# 查看同步日志
docker compose logs -f sync

# 重启后端
docker compose restart backend

# 停止全部服务
docker compose down

# 完全清除（含数据卷）
docker compose down -v
```

## 使用示例

### 通过 API 创建旨意

```bash
curl -X POST http://localhost:8000/api/create-task \
  -H "Content-Type: application/json" \
  -d '{"title": "设计用户注册系统", "priority": "high"}'
```

### 通过 API 查看任务状态

```bash
curl http://localhost:8000/api/live-status
```

### 通过 WebSocket 订阅实时事件

```javascript
const ws = new WebSocket('ws://localhost:8000/ws');
ws.onmessage = (e) => console.log(JSON.parse(e.data));
```

## 架构

```
┌─────────────┐    ┌─────────────┐
│   Frontend   │────│   Nginx     │
│  React 18    │    │  :3000      │
└──────┬───────┘    └──────┬──────┘
       │ /api/, /ws        │ proxy
       └───────────────────┤
                    ┌──────▼──────┐
                    │   Backend    │
                    │  FastAPI     │
                    │  :8000       │
                    └──┬────┬─────┘
                       │    │
              ┌────────┘    └────────┐
              ▼                      ▼
       ┌─────────────┐       ┌─────────────┐
       │  PostgreSQL  │       │    Redis     │
       │    :5432     │       │    :6379     │
       └─────────────┘       └──────┬──────┘
                                    │ Streams
                 ┌──────────────────┼──────────────┐
                 ▼                  ▼              ▼
          ┌────────────┐   ┌────────────┐   ┌──────────┐
          │Orchestrator │   │ Dispatcher  │   │  Sync    │
          │  Worker     │   │  Worker     │   │  Worker  │
          └────────────┘   └──────┬─────┘   └──────┬───┘
                                  │                 │
                                  ▼                 ▼
                           ┌──────────┐      ┌──────────┐
                           │ OpenClaw  │      │~/.openclaw│
                           │ Gateway   │      │  目录     │
                           └──────────┘      └──────────┘
```

## 注意事项

1. **必须设置绝对路径**：`EDICT_ROOT` 和 `OPENCLAW_HOME` 均需填写宿主机绝对路径，`~` 或相对路径可能解析异常
2. **首次启动**：`docker compose up -d` 会先由 `init-data-dirs` 创建数据子目录并设置权限，再运行 Alembic 迁移建表
3. **数据目录权限**：`data/postgres` 由 postgres 镜像自动 chown；`data/redis` 设为 777（redis 内部 uid 999）；`data/edict` chown 给 `PUID:PGID`
4. **OpenClaw 目录**：通过 volume 挂载到容器，sync worker 需要读取会话文件
5. **Gateway 通信**：容器内通过 `host.docker.internal` 访问宿主机 Gateway
6. **生产部署**：务必修改 `POSTGRES_PASSWORD`，关闭 `DEBUG`

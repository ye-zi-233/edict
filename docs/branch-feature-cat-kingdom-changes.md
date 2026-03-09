# feature/cat-kingdom 分支修改总结

> 基准分支：`origin/docker` | 当前分支：`feature/cat-kingdom`
> 生成日期：2026-03-06
> 提交数：1 | 涉及文件：76 | 净变更：+1793 / -5459

---

## 提交记录

| 提交 | 日期 | 说明 |
|------|------|------|
| `1d5be5f` | 2026-03-06 17:09:18 +0800 | feat: 架构重构 — 新增皇后/女娲角色，移除太子，清理 demo 数据 |

---

## 改动分类总览

### 1. 新增文件（7 个）

| 文件 | 用途 |
|------|------|
| `.env.example` | 根目录 Docker 部署环境变量模板 |
| `Dockerfile` | 根目录 Docker 镜像构建文件 |
| `docker-compose.yaml` | 根目录 Docker Compose 全功能部署编排 |
| `agents/huanghou/SOUL.md` | 新角色「皇后」— 消息分拣（闲聊直接回/旨意建任务） |
| `agents/nvwa/SOUL.md` | 新角色「女娲」— 灵魂守护 meta-agent（只读分析、起草提案） |
| `scripts/nvwa_tools.py` | 女娲工具脚本（list-agents/read-soul/read-logs/propose） |
| `scripts/apply_nvwa_proposal.py` | 女娲提案审批脚本（list/show/approve/reject） |

### 2. 删除文件（21 个）

**移除太子角色：**
- `agents/taizi/SOUL.md`

**清理 demo 数据（整个 docker/demo_data/ 目录）：**
- `docker/demo_data/agent_config.json`
- `docker/demo_data/last_model_change_result.json`
- `docker/demo_data/live_status.json`（1493 行，最大的被删文件）
- `docker/demo_data/model_change_log.json`
- `docker/demo_data/morning_brief.json`
- `docker/demo_data/officials_stats.json`
- `docker/demo_data/pending_model_changes.json`
- `docker/demo_data/tasks_source.json`

**精简 edict 后端 API（移除冗余模块）：**
- `edict/backend/app/api/compat.py` — 兼容层
- `edict/backend/app/api/models.py` — 模型接口
- `edict/backend/app/api/morning.py` — 早朝接口
- `edict/backend/app/api/officials.py` — 官员接口
- `edict/backend/app/api/scheduler.py` — 调度器
- `edict/backend/app/api/skills.py` — 技能管理
- `edict/backend/app/api/task_ops.py` — 任务操作（537 行）
- `edict/backend/app/services/openclaw_gateway.py` — OpenClaw 网关服务
- `edict/backend/app/workers/news_worker.py` — 新闻采集 worker
- `edict/backend/app/workers/sync_worker.py` — 同步 worker

**其他删除：**
- `edict/README.md` — edict 子目录独立 README
- `edict/migration/versions/002_sync_tables.py` — 数据库迁移脚本

### 3. 修改文件（48 个）

**Agent SOUL 重构（11 个 Agent 全部重写）：**
- `agents/bingbu/SOUL.md`、`agents/gongbu/SOUL.md`、`agents/hubu/SOUL.md`
- `agents/libu/SOUL.md`、`agents/libu_hr/SOUL.md`、`agents/menxia/SOUL.md`
- `agents/shangshu/SOUL.md`、`agents/xingbu/SOUL.md`、`agents/zaochao/SOUL.md`
- `agents/zhongshu/SOUL.md`（变动最大，+136/-）

**文档更新：**
- `README.md` — 主 README，新增皇后/女娲描述、权限矩阵更新
- `README_EN.md` — 英文 README 同步更新
- `ROADMAP.md` — 路线图调整
- `docs/getting-started.md` — 快速开始文档
- `docs/task-dispatch-architecture.md` — 任务分发架构文档（大量修改 +112/-）

**dashboard（看板）：**
- `dashboard/dashboard.html` — 前端看板界面调整
- `dashboard/server.py` — API 服务器（+152/-，逻辑变动较大）

**edict 前后端：**
- `edict/.env.example` — 环境变量模板调整
- `edict/Dockerfile` — 镜像构建调整
- `edict/docker-compose.yaml` — 编排大幅重构（+157/-）
- `edict/backend/app/api/__init__.py` — API 模块注册精简
- `edict/backend/app/api/agents.py` — Agent 接口修改
- `edict/backend/app/config.py` — 配置模块
- `edict/backend/app/main.py` — 应用入口
- `edict/backend/app/models/task.py` — 任务模型
- `edict/backend/app/services/task_service.py` — 任务服务
- `edict/backend/app/workers/orchestrator_worker.py` — 编排 worker
- `edict/migration/migrate_json_to_pg.py` — JSON 到 PG 迁移脚本
- `edict/migration/versions/001_initial.py` — 初始迁移
- `edict/frontend/.env.development` — 前端开发环境变量
- `edict/frontend/Dockerfile` — 前端镜像构建
- `edict/frontend/nginx.conf` — Nginx 配置
- `edict/frontend/src/components/EdictBoard.tsx` — 主看板组件
- `edict/frontend/src/components/MemorialPanel.tsx` — 奏折面板
- `edict/frontend/src/components/TaskModal.tsx` — 任务弹窗
- `edict/frontend/src/index.css` — 全局样式
- `edict/frontend/src/store.ts` — Zustand 状态管理
- `edict/frontend/vite.config.ts` — Vite 构建配置
- `edict/scripts/kanban_update_edict.py` — edict 版看板更新脚本

**根目录脚本/测试/部署：**
- `.dockerignore` — Docker 忽略规则
- `install.sh` — 安装脚本
- `scripts/apply_model_changes.py` — 模型切换脚本
- `scripts/kanban_update.py` — 看板更新脚本
- `scripts/run_loop.sh` — 数据刷新循环
- `scripts/sync_agent_config.py` — Agent 配置同步
- `scripts/sync_from_openclaw_runtime.py` — OpenClaw 运行时同步
- `scripts/sync_officials_stats.py` — 官员统计同步
- `tests/test_e2e_kanban.py` — 端到端测试

---

## 核心改动意图

1. **角色架构调整**：移除太子(taizi)，新增皇后(huanghou) + 女娲(nvwa)，重写全部 11 个 Agent 的 SOUL.md
2. **demo 数据清理**：删除 `docker/demo_data/` 硬编码演示数据，改为 `.env.example` 配置化方式
3. **edict 后端精简**：移除大量冗余 API 模块（compat/models/morning/officials/scheduler/skills/task_ops）和对应 service/worker
4. **Docker 部署重构**：根目录新增独立 Dockerfile + docker-compose.yaml + .env.example，支持一键部署
5. **女娲 meta-agent**：新增提案审批工作流（nvwa_tools.py + apply_nvwa_proposal.py）
6. **文档全面更新**：README/ROADMAP/架构文档同步反映新架构

---

## 合并 docker 分支时需重点关注

- 被删除的 `docker/demo_data/` 和 edict 后端模块：若 docker 分支有对这些文件的修改，合并时会产生冲突，应选择**删除（ours）**
- Agent SOUL.md 全部重写：若 docker 分支也改过 SOUL.md，冲突时应以**当前分支为准**
- 根目录 `Dockerfile` / `docker-compose.yaml` / `.env.example` 是本分支新增的，docker 分支可能也有，需逐文件对比
- `edict/docker-compose.yaml` 大幅重构，合并时注意服务定义是否兼容
- `dashboard/server.py` 改动大，若 docker 分支也有改动需手动对比逻辑

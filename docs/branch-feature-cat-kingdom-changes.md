# feature/cat-kingdom 分支修改总结

> 基准分支：`docker` | 当前分支：`feature/cat-kingdom`
> 生成日期：2026-03-13（更新）
> 提交数：22 | 涉及文件：63 | 净变更：+2044 / -3352

---

## 提交记录

| 提交 | 日期 | 说明 |
|------|------|------|
| `613fca1` | 2026-03-13 11:30 +0800 | merge(cat): 合并 docker 分支 — docs/scripts/P0修复 + 公众号入口 |
| `f191606` | 2026-03-13 10:25 +0800 | feat(cat): 补全 nvwa/gongzhu agent 映射，修正 kanban 状态，新增 install.sh |
| `fbbef47` | 2026-03-13 10:24 +0800 | refactor(cat/edict): taizi 全面替换为 gongzhu，修复数据库 schema 与 API |
| `3cc3343` | 2026-03-10 23:22 +0800 | merge(docker): 合并 docker 分支 CI 修复 — 按分支名隔离镜像 tag |
| `072329f` | 2026-03-10 23:02 +0800 | Merge branch 'docker' into feature/cat-kingdom |
| `c0c825f` | 2026-03-10 22:53 +0800 | refactor(edict): Docker-only 部署，女娲移除创建 Agent 能力，sync 自动注册 Agent |
| `8fba80d` | 2026-03-10 22:41 +0800 | fix(docker): gosu entrypoint 替代 init-data-dirs + 修复 TaskCreate 遗留太子命名 |
| `d602009` | 2026-03-10 22:06 +0800 | merge(docker): 合并 docker 分支修复和重构，保留 cat 命名约定 |
| `19eb8ca` | 2026-03-10 20:29 +0800 | refactor: 全局重命名皇后(huanghou)为公主(gongzhu) |
| `865b54e` | 2026-03-10 20:21 +0800 | merge: 合并 docker 分支，解决 Task 模型适配冲突 |
| `1d5be5f` | 2026-03-06 17:09 +0800 | feat: 架构重构 — 新增公主/女娲角色，移除太子，清理 demo 数据 |

---

## 改动分类总览

### 1. 新增文件（7 个）

| 文件 | 用途 |
|------|------|
| `.env.example` | 根目录 Docker 部署环境变量模板 |
| `Dockerfile` | 根目录 Docker 镜像构建文件 |
| `docker-compose.yaml` | 根目录 Docker Compose 全功能部署编排 |
| `agents/gongzhu/SOUL.md` | 新角色「公主」— 消息分拣（闲聊直接回/旨意建任务） |
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
- `README.md` — 主 README，新增公主/女娲描述、权限矩阵更新
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
- `scripts/apply_model_changes.py` — 模型切换脚本
- `scripts/kanban_update.py` — 看板更新脚本
- `scripts/run_loop.sh` — 数据刷新循环
- `scripts/sync_agent_config.py` — Agent 配置同步
- `scripts/sync_from_openclaw_runtime.py` — OpenClaw 运行时同步
- `scripts/sync_officials_stats.py` — 官员统计同步
- `tests/test_e2e_kanban.py` — 端到端测试

---

## 核心改动意图

1. **角色架构调整**：移除太子(taizi)，新增公主(gongzhu) + 女娲(nvwa)，重写全部 11 个 Agent 的 SOUL.md
2. **taizi→gongzhu 全面替换**：数据库 schema、API 层、前端、worker、脚本全部将 taizi 命名统一为 gongzhu
3. **kanban 状态修正**：修正任务状态映射，补全 nvwa/gongzhu 的 agent 映射
4. **demo 数据清理**：删除 `docker/demo_data/` 硬编码演示数据，改为 `.env.example` 配置化方式
5. **edict 后端精简**：移除大量冗余 API 模块（compat/models/morning/officials/scheduler/skills/task_ops）和对应 service/worker
6. **女娲 meta-agent**：新增提案审批工作流（nvwa_tools.py + apply_nvwa_proposal.py）
7. **文档全面更新**：README/ROADMAP/架构文档同步反映新架构

---

## 即将合入的 docker 新提交（`2fd6147`）

docker 分支新增一个修复提交，内容：
- `scripts/utils.py`：新增 `parse_json5()`，解决 OpenClaw JSON5 配置文件无法用 `json.loads()` 解析的问题
- `scripts/sync_agent_config.py`：使用 `parse_json5`、新增 `_openclaw_host_ws()`（workspace 路径用宿主机绝对路径）、移除无效的 `openclaw gateway restart` 调用
- `scripts/apply_model_changes.py`：使用 `parse_json5` 读取配置
- `edict/docker-compose.yaml`：sync 服务新增 `OPENCLAW_HOST_HOME: ${OPENCLAW_HOME}` 透传宿主机路径
- `edict/README.md`：更新注意事项第 3 条说明

合并后不需要额外操作，直接生效。

---

## 合并 docker 分支时需重点关注

- 被删除的 `docker/demo_data/` 和 edict 后端模块：若 docker 分支有对这些文件的修改，合并时会产生冲突，应选择**删除（ours）**
- Agent SOUL.md 全部重写：若 docker 分支也改过 SOUL.md，冲突时应以**当前分支为准**
- `scripts/utils.py` / `scripts/sync_agent_config.py` / `scripts/apply_model_changes.py`：docker `2fd6147` 为权威版本（含 parse_json5 修复），合并冲突时选 **docker 侧**
- `edict/docker-compose.yaml`：docker `2fd6147` 新增了 `OPENCLAW_HOST_HOME` 环境变量，合并时保留该行
- `dashboard/server.py` 改动大，若 docker 分支也有改动需手动对比逻辑

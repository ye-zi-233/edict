# sync-docker-branch 参考

## 常用 Git 命令速查

| 用途 | 命令 |
|------|------|
| 当前分支名 | `git branch --show-current` |
| 工作区状态 | `git status --short` |
| 当前分支相对 docker 的提交 | `git log origin/docker..HEAD --oneline` |
| 当前分支相对 docker 的变更统计 | `git diff origin/docker..HEAD --stat` |
| 新增文件列表 | `git diff origin/docker..HEAD --diff-filter=A --name-only` |
| 删除文件列表 | `git diff origin/docker..HEAD --diff-filter=D --name-only` |
| 修改文件列表 | `git diff origin/docker..HEAD --diff-filter=M --name-only` |
| 拉取远程 docker | `git fetch origin docker` |
| 合并 docker 到当前分支 | `git merge origin/docker` |
| 冲突文件列表 | `git diff --name-only --diff-filter=U` 或 `git status` |
| 合并后「来自 docker 的提交」 | `git log HEAD^2..HEAD --oneline`（双亲中第二个为 docker） |

## 本仓库分支约定

- **docker**：部署架构的权威分支（edict/ 下的 Dockerfile、docker-compose、.env、后端模块等），合并进当前分支以获取最新部署方案。冲突时部署相关内容以 docker 为准。
- **feature/cat-kingdom**：功能分支示例；当前分支可能为该分支或其他 feature 分支。
- **main**：主分支。Skill 不写死分支名，统一用「当前分支」与「源分支 docker」。

## 总结文档路径规则

- 文件名：`docs/branch-<当前分支名>-changes.md`
- 分支名中的 `/` 替换为 `-`，例如：`feature/cat-kingdom` → `branch-feature-cat-kingdom-changes.md`
- 结构参考：`docs/branch-feature-cat-kingdom-changes.md`（提交记录表、新增/删除/修改分类、核心意图、合并时需重点关注）

## 冲突解决策略简述

**核心原则：docker 分支是部署架构的权威来源。** 冲突时先用 `git log` 看 docker 侧提交信息，理解其意图再做决策。

| 场景 | 建议 |
|------|------|
| docker 删除了某文件（如根目录 Dockerfile/docker-compose/.env） | **跟随 docker 删除**，不保留当前分支版本 — docker 分支决定部署形态 |
| docker 新增或恢复了 edict/ 下的后端模块 | **接受 docker 的新增** — 这些是 edict 完整部署需要的模块，不应精简 |
| Agent SOUL.md 在当前分支已重写 | 以当前分支为准（ours），或手动合并保留本分支人格定义 |
| 当前分支已删除的非部署文件在 docker 中仍存在 | 保留删除（ours），不恢复该文件 |
| README / 文档两分支都改 | 部署相关内容（端口、启动命令、配置表）以 docker 为准；业务描述（Agent 架构、功能说明）以当前分支为准 |
| edict/ 下配置文件（docker-compose、.env、Dockerfile）冲突 | 以 docker 为准，它维护部署方案的最新状态 |

解决后务必 `git add` 已解决文件，再 `git commit` 完成合并；不执行 `git push`。

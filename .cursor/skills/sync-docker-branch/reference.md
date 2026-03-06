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

- **docker**：Docker 相关编排与配置的同步源，合并进当前分支以获取最新部署/脚本变更。
- **feature/cat-kingdom**：功能分支示例；当前分支可能为该分支或其他 feature 分支。
- **main**：主分支。Skill 不写死分支名，统一用「当前分支」与「源分支 docker」。

## 总结文档路径规则

- 文件名：`docs/branch-<当前分支名>-changes.md`
- 分支名中的 `/` 替换为 `-`，例如：`feature/cat-kingdom` → `branch-feature-cat-kingdom-changes.md`
- 结构参考：`docs/branch-feature-cat-kingdom-changes.md`（提交记录表、新增/删除/修改分类、核心意图、合并时需重点关注）

## 冲突解决策略简述

| 场景 | 建议 |
|------|------|
| 当前分支已删除的文件在 docker 中仍存在或修改 | 保留删除（ours），不恢复该文件 |
| Agent SOUL.md 在当前分支已重写 | 以当前分支为准（ours），或手动合并保留本分支人格定义 |
| 根目录 Dockerfile / docker-compose / .env 两分支都改 | 逐块对比，优先保留当前分支的部署形态，再选择性并入 docker 的修复或变量 |
| edict 子目录下后端/前端大量改动 | 以当前分支为主，docker 侧若为小修复可手动摘入 |

解决后务必 `git add` 已解决文件，再 `git commit` 完成合并；不执行 `git push`。

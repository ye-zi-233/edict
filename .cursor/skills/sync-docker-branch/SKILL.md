---
name: sync-docker-branch
description: Guides safe merge of the docker branch into the current branch. Ensures working tree is clean and current changes are committed, summarizes current-branch changes to a docs file to avoid forgetting, performs merge, then reviews incoming changes for follow-up edits. Use when the user asks to sync from docker, pull docker, or merge docker branch.
---

# 同步 docker 分支

在「当前分支修改已稳定」的前提下，先总结当前分支相对 docker 的修改并写入文档，再安全地将 docker 分支合并进当前分支，合并后检查新引入内容是否需要修改。

---

## 前置检查（必须先通过）

执行前请逐项确认：

- [ ] 工作区干净：`git status --short` 无输出（无未提交修改）
- [ ] 当前分支相对 `origin/docker` 的修改已全部提交
- [ ] （可选）若有测试或脚本可运行，先跑一遍确保当前分支无回归

**命令示例：**

```bash
git status --short
# 若有输出，先 commit 或 stash，再继续
```

---

## 步骤 1：总结当前分支的修改（避免合并后遗忘）

先收集当前分支相对 docker 的提交与文件变更，**将总结写入文档**，供合并后对照。

**1.1 收集信息（在仓库根目录执行）：**

```bash
# 当前分支名（用于生成文档路径）
git branch --show-current

# 提交列表
git log origin/docker..HEAD --oneline

# 详细提交信息（可选，用于填写「提交记录」表）
git log origin/docker..HEAD --format="提交: %h%n日期: %ai%n作者: %an%n%n%s%n%n%b"

# 文件变更统计
git diff origin/docker..HEAD --stat

# 新增 / 删除 / 修改 文件列表（用于分类）
git diff origin/docker..HEAD --diff-filter=A --name-only
git diff origin/docker..HEAD --diff-filter=D --name-only
git diff origin/docker..HEAD --diff-filter=M --name-only
```

**1.2 写入文档：**

- **路径规则**：`docs/branch-<当前分支名>-changes.md`  
  分支名中的 `/` 替换为 `-`。例如当前分支为 `feature/cat-kingdom` 时，文件名为 `docs/branch-feature-cat-kingdom-changes.md`。
- **内容结构**（与现有 `docs/branch-feature-cat-kingdom-changes.md` 保持一致）：
  - 顶部：基准分支、当前分支、生成日期、提交数、涉及文件数、净变更行数
  - **提交记录**：表格（提交 hash、日期、说明）
  - **改动分类总览**：新增文件（列表+用途）、删除文件（按类别分组）、修改文件（按模块分组）
  - **核心改动意图**：几条 bullet 概括本分支主要目的
  - **合并 docker 分支时需重点关注**：易冲突或需人工确认的文件/目录及建议（如「选 ours」「以当前分支为准」）

合并后可用该文档确认「当前分支的意图」未被覆盖、冲突处理正确。

---

## 步骤 2：合并 docker 分支

**2.1 拉取并合并：**

```bash
git fetch origin docker
# 或: git fetch
git merge origin/docker
# 若本地已有 docker 分支且已更新，也可: git merge docker
```

使用 merge（不 rebase），保留当前分支历史，不重写提交。

**2.2 若出现冲突：**

- 列出冲突文件：`git status` 或 `git diff --name-only --diff-filter=U`
- 逐文件打开，按「保留我方 / 接受对方 / 手动合并」处理；可对照步骤 1 生成的 `docs/branch-<当前分支>-changes.md` 中「核心改动意图」与「合并时需重点关注」
- 解决后：`git add <文件>`，再 `git commit` 完成合并
- **不要**在未与用户确认的情况下自动执行 `git push`

---

## 步骤 3：合并后检查（新内容是否要改）

**3.1 列出本次从 docker 引入的变更：**

```bash
# 合并后的 merge base 为合并前 HEAD，docker 侧提交为合并进来的
git log HEAD^2..HEAD --oneline
# 或按文件：git diff HEAD^1..HEAD --name-only
```

**3.2 简要审查：**

- 是否与当前分支约定冲突（如 SOUL.md、权限矩阵、目录结构）
- 是否需适配配置/路径/环境：本仓库有根目录与 `edict/` 下多份 Dockerfile、docker-compose、.env，需注意路径与变量是否与当前用法一致
- 输出「需人工确认或修改」的清单：**文件路径 + 简短原因**

**3.3 对照「当前分支摘要」：**

打开 `docs/branch-<当前分支>-changes.md`，确认本分支改动未被误覆盖，冲突解决结果与「合并时需重点关注」一致。

---

## 注意事项

- **不执行 `git push`**：Skill 仅指导合并与检查，不主动推送（遵守用户规则）。
- **源分支名**：默认以 `docker`（或 `origin/docker`）为同步源；若实际分支名不同，替换上述命令中的 `docker` 即可。
- **文档路径**：无 `docs/` 目录时需先创建；文件名中的分支名若含特殊字符，仅将 `/` 替换为 `-`，其余保持可读。

---

## 快速检查清单（复制使用）

```
Task Progress:
- [ ] 前置：工作区干净、已提交、可选运行测试
- [ ] 总结：执行 git log/diff，写入 docs/branch-<当前分支名>-changes.md
- [ ] 合并：git fetch origin docker && git merge origin/docker
- [ ] 冲突：若有，逐文件解决，对照「当前分支摘要」文档
- [ ] 合并后：列出 docker 引入的变更，输出「需修改」清单，对照摘要确认
```

---

## 延伸阅读

- 常用命令、分支约定与冲突策略详见 [reference.md](reference.md)

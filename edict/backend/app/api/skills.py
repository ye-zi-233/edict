"""Skills 管理 API — 读取、添加、更新、删除 Agent 技能。

端点：
- GET  /api/skills/content/{agentId}/{skillName} — 读取 SKILL.md
- GET  /api/skills/remote-list                   — 列出所有远程 Skills
- POST /api/skills/add                           — 为 Agent 创建新 skill
- POST /api/skills/add-remote                    — 从远程 URL 添加 skill
- POST /api/skills/update-remote                 — 更新远程 skill
- POST /api/skills/remove-remote                 — 移除远程 skill
"""

import json
import logging
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import httpx
from fastapi import APIRouter

from ..config import get_settings

log = logging.getLogger("edict.api.skills")
router = APIRouter()

DATA = Path("/app/data")
_SAFE_NAME_RE = re.compile(r"^[a-zA-Z0-9_\-\u4e00-\u9fff]+$")


def _read_json(path: Path, default=None):
    if not path.exists():
        return default if default is not None else {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, IOError):
        return default if default is not None else {}


def _oclaw_home() -> Path:
    return get_settings().resolved_openclaw_home


@router.get("/content/{agent_id}/{skill_name}")
async def read_skill_content(agent_id: str, skill_name: str):
    """读取指定 Agent 的 SKILL.md 内容。"""
    if not _SAFE_NAME_RE.match(agent_id) or not _SAFE_NAME_RE.match(skill_name):
        return {"ok": False, "error": "参数含非法字符"}

    cfg = _read_json(DATA / "agent_config.json", {})
    agents = cfg.get("agents", [])
    ag = next((a for a in agents if a.get("id") == agent_id), None)

    if ag:
        ws = ag.get("workspace", "")
        skill_path = Path(ws) / "skills" / skill_name / "SKILL.md" if ws else None
    else:
        skill_path = _oclaw_home() / f"workspace-{agent_id}" / "skills" / skill_name / "SKILL.md"

    if not skill_path:
        skill_path = _oclaw_home() / f"workspace-{agent_id}" / "skills" / skill_name / "SKILL.md"

    if not skill_path.exists():
        return {"ok": True, "name": skill_name, "agent": agent_id, "content": "(SKILL.md 文件不存在)", "path": str(skill_path)}

    try:
        content = skill_path.read_text(encoding="utf-8")
        return {"ok": True, "name": skill_name, "agent": agent_id, "content": content, "path": str(skill_path)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/remote-list")
async def remote_skills_list():
    """列出所有远程 skills 及源信息。"""
    oclaw = _oclaw_home()
    all_skills = []
    for ws_dir in sorted(oclaw.glob("workspace-*")):
        agent_id = ws_dir.name.replace("workspace-", "")
        skills_dir = ws_dir / "skills"
        if not skills_dir.exists():
            continue
        for skill_dir in sorted(skills_dir.iterdir()):
            source_json = skill_dir / ".source.json"
            if not source_json.exists():
                continue
            try:
                source = json.loads(source_json.read_text(encoding="utf-8"))
                skill_md = skill_dir / "SKILL.md"
                all_skills.append({
                    "agentId": agent_id,
                    "skillName": skill_dir.name,
                    "source": source.get("url", ""),
                    "addedAt": source.get("addedAt", ""),
                    "updatedAt": source.get("updatedAt", ""),
                    "size": skill_md.stat().st_size if skill_md.exists() else 0,
                    "localPath": str(skill_dir),
                })
            except Exception:
                pass

    return {"ok": True, "remoteSkills": all_skills, "count": len(all_skills), "listedAt": datetime.now(timezone.utc).isoformat()}


@router.post("/add")
async def add_skill(body: dict):
    """为 Agent 创建新 skill。"""
    agent_id = body.get("agentId", "")
    skill_name = body.get("skillName", "")
    description = body.get("description", "")
    trigger = body.get("trigger", "")

    if not _SAFE_NAME_RE.match(agent_id):
        return {"ok": False, "error": f"agentId 含非法字符: {agent_id}"}
    if not _SAFE_NAME_RE.match(skill_name):
        return {"ok": False, "error": f"skillName 含非法字符: {skill_name}"}

    workspace = _oclaw_home() / f"workspace-{agent_id}" / "skills" / skill_name
    workspace.mkdir(parents=True, exist_ok=True)
    skill_md = workspace / "SKILL.md"
    desc_line = description or skill_name
    trigger_section = f"\n## 触发条件\n{trigger}\n" if trigger else ""
    template = (
        f"---\nname: {skill_name}\ndescription: {desc_line}\n---\n\n"
        f"# {skill_name}\n\n{desc_line}\n{trigger_section}"
    )
    skill_md.write_text(template, encoding="utf-8")

    _sync_agent_config()
    return {"ok": True, "message": f"Skill {skill_name} 已创建", "path": str(skill_md)}


@router.post("/add-remote")
async def add_remote_skill(body: dict):
    """从远程 URL 添加 skill。"""
    agent_id = body.get("agentId", "")
    skill_name = body.get("skillName", "")
    source_url = body.get("sourceUrl", "")
    description = body.get("description", "")

    if not _SAFE_NAME_RE.match(agent_id):
        return {"ok": False, "error": f"agentId 含非法字符: {agent_id}"}
    if not _SAFE_NAME_RE.match(skill_name):
        return {"ok": False, "error": f"skillName 含非法字符: {skill_name}"}
    if not source_url:
        return {"ok": False, "error": "sourceUrl 必填"}

    source_url = source_url.strip()
    if not source_url.startswith("https://"):
        return {"ok": False, "error": "仅支持 HTTPS URL"}

    # 下载内容（异步，避免阻塞 Event Loop）
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(source_url, headers={"User-Agent": "Edict-SkillManager/2.0"})
        if resp.status_code != 200:
            return {"ok": False, "error": f"下载失败: HTTP {resp.status_code}"}
        content = resp.text
        if len(content) > 500_000:
            return {"ok": False, "error": "文件过大（>500KB）"}
    except Exception as e:
        return {"ok": False, "error": f"下载失败: {e}"}

    workspace = _oclaw_home() / f"workspace-{agent_id}" / "skills" / skill_name
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "SKILL.md").write_text(content, encoding="utf-8")
    (workspace / ".source.json").write_text(json.dumps({
        "url": source_url, "description": description,
        "addedAt": datetime.now(timezone.utc).isoformat(),
        "updatedAt": datetime.now(timezone.utc).isoformat(),
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    _sync_agent_config()
    return {
        "ok": True,
        "message": f"远程 Skill {skill_name} 已添加到 {agent_id}",
        "skillName": skill_name, "agentId": agent_id,
        "source": source_url, "localPath": str(workspace),
        "size": len(content), "addedAt": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/update-remote")
async def update_remote_skill(body: dict):
    """更新远程 skill 到最新版本。"""
    agent_id = body.get("agentId", "")
    skill_name = body.get("skillName", "")
    if not _SAFE_NAME_RE.match(agent_id) or not _SAFE_NAME_RE.match(skill_name):
        return {"ok": False, "error": "参数含非法字符"}

    workspace = _oclaw_home() / f"workspace-{agent_id}" / "skills" / skill_name
    source_json = workspace / ".source.json"
    if not source_json.exists():
        return {"ok": False, "error": f"技能 {skill_name} 不是远程 skill（无 .source.json）"}

    source = json.loads(source_json.read_text(encoding="utf-8"))
    url = source.get("url", "")
    if not url:
        return {"ok": False, "error": "无源 URL"}

    # 下载内容（异步，避免阻塞 Event Loop；同步补全状态码和大小校验）
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, headers={"User-Agent": "Edict-SkillManager/2.0"})
        if resp.status_code != 200:
            return {"ok": False, "error": f"更新下载失败: HTTP {resp.status_code}"}
        content = resp.text
        if len(content) > 500_000:
            return {"ok": False, "error": "文件过大（>500KB）"}
    except Exception as e:
        return {"ok": False, "error": f"更新下载失败: {e}"}

    (workspace / "SKILL.md").write_text(content, encoding="utf-8")
    source["updatedAt"] = datetime.now(timezone.utc).isoformat()
    source_json.write_text(json.dumps(source, ensure_ascii=False, indent=2), encoding="utf-8")

    _sync_agent_config()
    return {"ok": True, "message": f"{skill_name} 已更新", "newVersion": source["updatedAt"]}


@router.post("/remove-remote")
async def remove_remote_skill(body: dict):
    """移除远程 skill。"""
    agent_id = body.get("agentId", "")
    skill_name = body.get("skillName", "")
    if not _SAFE_NAME_RE.match(agent_id) or not _SAFE_NAME_RE.match(skill_name):
        return {"ok": False, "error": "参数含非法字符"}

    workspace = _oclaw_home() / f"workspace-{agent_id}" / "skills" / skill_name
    if not workspace.exists():
        return {"ok": False, "error": f"技能不存在: {skill_name}"}

    import shutil
    shutil.rmtree(workspace, ignore_errors=True)

    _sync_agent_config()
    return {"ok": True, "message": f"{skill_name} 已移除"}


def _sync_agent_config():
    """触发 Agent 配置同步。"""
    try:
        subprocess.Popen(
            ["python3", "/app/scripts/sync_agent_config.py"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass

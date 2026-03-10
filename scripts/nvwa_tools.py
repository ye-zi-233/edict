#!/usr/bin/env python3
"""
女娲专用工具 — 只读分析 + 灵魂调优提案生成（不直接修改任何 Agent 配置）。

供女娲在对话中调用，用于：
- 读取其他 Agent 的 SOUL.md（感应灵魂）
- 列出所有 Agent
- 读取 Agent 近期对话日志
- 生成修改 Agent 灵魂的提案，提交主人审批

用法:
  python3 nvwa_tools.py list-agents
  python3 nvwa_tools.py read-soul <agent_id>
  python3 nvwa_tools.py read-logs <agent_id> [--days 1]
  python3 nvwa_tools.py propose modify-soul <agent_id> --reason "..." --content "<full SOUL.md content>"
"""
import argparse
import json
import pathlib
import sys
from datetime import datetime, timedelta

# 脚本所在目录的上一级：从 repo/scripts 运行则为 repo，从 workspace/scripts 运行则为 workspace
BASE = pathlib.Path(__file__).resolve().parent.parent
OCLAW_HOME = pathlib.Path.home() / '.openclaw'

# 提案存放目录：脚本在 repo/scripts 时用 repo/data；在 workspace/scripts 时用 workspace/data（供 apply 脚本从 workspace-nvwa 读取）
def _proposals_dir():
    return BASE / 'data' / 'nvwa_proposals'

# 已知 Agent 列表（与 sync_agent_config 的 _SOUL_DEPLOY_MAP 保持一致，供 list-agents / read-soul 使用）
KNOWN_AGENT_IDS = [
    'gongzhu', 'zhongshu', 'menxia', 'shangshu',
    'hubu', 'libu', 'bingbu', 'xingbu', 'gongbu', 'libu_hr', 'zaochao', 'nvwa',
]


def cmd_list_agents():
    """列出所有已部署的 Agent（从 workspace 存在性判断）。"""
    lines = []
    for aid in KNOWN_AGENT_IDS:
        soul = OCLAW_HOME / f'workspace-{aid}' / 'soul.md'
        exists = soul.exists()
        lines.append(f"{aid}\t{'有' if exists else '无'} soul")
    return '\n'.join(lines)


def cmd_read_soul(agent_id: str) -> str:
    """读取指定 Agent 的 SOUL.md 内容（只读，来自其 workspace 的 soul.md）。"""
    if agent_id not in KNOWN_AGENT_IDS:
        return f"未知 Agent ID: {agent_id}\n已知: {', '.join(KNOWN_AGENT_IDS)}"
    soul_path = OCLAW_HOME / f'workspace-{agent_id}' / 'soul.md'
    if not soul_path.exists():
        return f"未找到灵魂文件: {soul_path}"
    try:
        return soul_path.read_text(encoding='utf-8', errors='replace')
    except Exception as e:
        return f"读取失败: {e}"


def _parse_jsonl_message(msg: dict) -> str:
    """从 session jsonl 的 message 中提取可读文本（用于日志摘要）。"""
    if not msg:
        return ''
    role = msg.get('role', '')
    content = msg.get('content') or []
    parts = []
    for c in content if isinstance(content, list) else [content]:
        if isinstance(c, dict):
            t = c.get('text') or c.get('content') or ''
            if t:
                parts.append(str(t)[:500])
        elif isinstance(c, str):
            parts.append(c[:500])
    return (role + ': ' + ' '.join(parts)) if parts else ''


def cmd_read_logs(agent_id: str, days: int = 1) -> str:
    """读取指定 Agent 近期对话日志（来自 ~/.openclaw/agents/<id>/sessions/*.jsonl）。"""
    if agent_id not in KNOWN_AGENT_IDS:
        return f"未知 Agent ID: {agent_id}"
    sessions_dir = OCLAW_HOME / 'agents' / agent_id / 'sessions'
    if not sessions_dir.exists():
        return f"无会话目录: {sessions_dir}"
    jsonl_files = sorted(
        sessions_dir.glob('*.jsonl'),
        key=lambda f: f.stat().st_mtime,
        reverse=True
    )
    if not jsonl_files:
        return "暂无 .jsonl 会话文件"
    cutoff = (datetime.now() - timedelta(days=days)).timestamp()
    lines_out = []
    total = 0
    for jf in jsonl_files[:5]:
        if jf.stat().st_mtime < cutoff:
            break
        try:
            for ln in jf.read_text(errors='ignore').splitlines():
                try:
                    item = json.loads(ln)
                    msg = item.get('message') or {}
                    text = _parse_jsonl_message(msg)
                    if text:
                        lines_out.append(text)
                        total += 1
                        if total >= 50:
                            break
                except Exception:
                    continue
        except Exception:
            continue
        if total >= 50:
            break
    if not lines_out:
        return f"近 {days} 天内无对话记录"
    return "\n".join(lines_out[-30:])  # 最多返回最近 30 条


def _next_proposal_id() -> str:
    """生成提案 ID：NW-YYYYMMDD-NNN。"""
    d = _proposals_dir()
    d.mkdir(parents=True, exist_ok=True)
    prefix = f"NW-{datetime.now().strftime('%Y%m%d')}-"
    existing = list(d.glob(f'{prefix}*.json'))
    n = 1
    for f in existing:
        try:
            idx = int(f.stem.split('-')[-1])
            n = max(n, idx + 1)
        except ValueError:
            pass
    return f"{prefix}{n:03d}"


def cmd_propose_modify_soul(agent_id: str, reason: str, content: str) -> str:
    """生成「修改某 Agent 灵魂」的提案（仅写入提案文件，不修改实际 SOUL）。"""
    if agent_id not in KNOWN_AGENT_IDS:
        return f"未知 Agent ID: {agent_id}"
    pid = _next_proposal_id()
    prop = {
        'id': pid,
        'type': 'modify-soul',
        'target': agent_id,
        'reason': reason,
        'proposed_content': content,
        'status': 'pending',
        'created_at': datetime.now().isoformat(),
    }
    proposals_dir = _proposals_dir()
    proposals_dir.mkdir(parents=True, exist_ok=True)
    out_path = proposals_dir / f"{pid}.json"
    try:
        out_path.write_text(json.dumps(prop, ensure_ascii=False, indent=2), encoding='utf-8')
    except Exception as e:
        return f"写入提案失败: {e}"
    return f"提案已生成: {pid}\n路径: {out_path}\n请主人审阅后使用 apply_nvwa_proposal.py approve {pid} 执行。"


def main():
    parser = argparse.ArgumentParser(description='女娲工具：只读分析 + 灵魂调优提案')
    sub = parser.add_subparsers(dest='cmd', help='命令')

    sub.add_parser('list-agents', help='列出所有 Agent')
    r = sub.add_parser('read-soul', help='读取某 Agent 的 SOUL.md')
    r.add_argument('agent_id', help='Agent ID')
    l = sub.add_parser('read-logs', help='读取某 Agent 近期对话日志')
    l.add_argument('agent_id', help='Agent ID')
    l.add_argument('--days', type=int, default=1, help='最近几天')

    prop = sub.add_parser('propose', help='生成提案')
    prop_sub = prop.add_subparsers(dest='propose_type')
    m = prop_sub.add_parser('modify-soul', help='提案：修改某 Agent 的 SOUL')
    m.add_argument('agent_id', help='目标 Agent ID')
    m.add_argument('--reason', required=True, help='修改原因')
    m.add_argument('--content', default='', help='完整的新 SOUL.md 内容')
    m.add_argument('--content-file', default='', help='或从文件读取 SOUL.md 内容（与 --content 二选一）')

    args = parser.parse_args()

    if args.cmd == 'list-agents':
        print(cmd_list_agents())
    elif args.cmd == 'read-soul':
        print(cmd_read_soul(args.agent_id))
    elif args.cmd == 'read-logs':
        print(cmd_read_logs(args.agent_id, args.days))
    elif args.cmd == 'propose':
        if args.propose_type == 'modify-soul':
            content = args.content
            if getattr(args, 'content_file', '') and pathlib.Path(args.content_file).exists():
                content = pathlib.Path(args.content_file).read_text(encoding='utf-8')
            if not content:
                print("请提供 --content 或 --content-file")
                sys.exit(1)
            print(cmd_propose_modify_soul(args.agent_id, args.reason, content))
        else:
            prop.print_help()
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()

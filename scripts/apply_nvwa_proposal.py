#!/usr/bin/env python3
"""
主人审批女娲提案 — 审阅、批准或驳回女娲提交的灵魂调优提案。

女娲只能生成提案，不能直接改配置；本脚本由主人在项目根目录执行，批准后写入 SOUL.md。

用法:
  python3 scripts/apply_nvwa_proposal.py list
  python3 scripts/apply_nvwa_proposal.py show <proposal_id>
  python3 scripts/apply_nvwa_proposal.py approve <proposal_id>
  python3 scripts/apply_nvwa_proposal.py reject <proposal_id>
"""
import argparse
import json
import pathlib
import sys
from typing import Optional

# 项目根目录（脚本在 scripts/ 下）
REPO_BASE = pathlib.Path(__file__).resolve().parent.parent
OCLAW_HOME = pathlib.Path.home() / '.openclaw'

# 提案目录：先查 repo，再查女娲 workspace（女娲在 workspace 下 propose 时写在 workspace/data/nvwa_proposals）
def _proposal_dirs():
    dirs = [REPO_BASE / 'data' / 'nvwa_proposals']
    nvwa_ws = OCLAW_HOME / 'workspace-nvwa' / 'data' / 'nvwa_proposals'
    if nvwa_ws.exists():
        dirs.append(nvwa_ws)
    return dirs


def _find_proposal(proposal_id: str) -> Optional[pathlib.Path]:
    """在 repo 与 workspace-nvwa 的提案目录中查找提案文件。"""
    for d in _proposal_dirs():
        p = d / f"{proposal_id}.json"
        if p.exists():
            return p
    return None


def _list_proposals():
    """收集所有提案（去重，同一 id 只保留一份）。"""
    seen = {}
    for d in _proposal_dirs():
        if not d.exists():
            continue
        for f in d.glob('*.json'):
            try:
                data = json.loads(f.read_text(encoding='utf-8'))
                pid = data.get('id') or f.stem
                if pid not in seen:
                    seen[pid] = data
            except Exception:
                continue
    return list(seen.values())


def cmd_list():
    """列出所有提案。"""
    props = _list_proposals()
    props.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    if not props:
        print("暂无提案")
        return
    print(f"{'ID':<24} {'类型':<14} {'目标':<12} {'状态':<10} 创建时间")
    print("-" * 72)
    for p in props:
        pid = p.get('id', '')
        typ = p.get('type', '')
        target = p.get('target', '')
        status = p.get('status', '')
        created = (p.get('created_at') or '')[:19]
        print(f"{pid:<24} {typ:<14} {target:<12} {status:<10} {created}")


def cmd_show(proposal_id: str):
    """显示提案详情。"""
    path = _find_proposal(proposal_id)
    if not path:
        print(f"未找到提案: {proposal_id}")
        sys.exit(1)
    data = json.loads(path.read_text(encoding='utf-8'))
    print(json.dumps(data, ensure_ascii=False, indent=2))
    if data.get('proposed_content'):
        print("\n--- 拟写入的 SOUL.md 内容（前 2000 字）---")
        print((data['proposed_content'] or '')[:2000])


def _write_proposal_status(path: pathlib.Path, status: str):
    """更新提案文件中的 status 字段。"""
    data = json.loads(path.read_text(encoding='utf-8'))
    data['status'] = status
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def cmd_approve(proposal_id: str):
    """批准提案并执行：将调优后的 SOUL.md 写入 agents 目录。"""
    path = _find_proposal(proposal_id)
    if not path:
        print(f"未找到提案: {proposal_id}")
        sys.exit(1)
    data = json.loads(path.read_text(encoding='utf-8'))
    if data.get('status') != 'pending':
        print(f"提案状态为 {data.get('status')}，无法批准")
        sys.exit(1)
    typ = data.get('type')
    target = data.get('target', '')
    content = data.get('proposed_content', '')
    if not content:
        print("提案缺少 proposed_content")
        sys.exit(1)

    if typ == 'modify-soul':
        soul_path = REPO_BASE / 'agents' / target / 'SOUL.md'
        soul_path.parent.mkdir(parents=True, exist_ok=True)
        soul_path.write_text(content, encoding='utf-8')
        print(f"已写入: {soul_path}")
    else:
        print(f"未知提案类型: {typ}")
        sys.exit(1)

    _write_proposal_status(path, 'approved')
    print(f"提案 {proposal_id} 已批准并执行。")


def cmd_reject(proposal_id: str):
    """驳回提案。"""
    path = _find_proposal(proposal_id)
    if not path:
        print(f"未找到提案: {proposal_id}")
        sys.exit(1)
    data = json.loads(path.read_text(encoding='utf-8'))
    if data.get('status') != 'pending':
        print(f"提案状态为 {data.get('status')}，无需重复驳回")
        return
    _write_proposal_status(path, 'rejected')
    print(f"提案 {proposal_id} 已驳回。")


def main():
    parser = argparse.ArgumentParser(description='主人审批女娲提案')
    sub = parser.add_subparsers(dest='cmd', help='命令')
    sub.add_parser('list', help='列出所有提案')
    s = sub.add_parser('show', help='显示提案详情')
    s.add_argument('proposal_id', help='提案 ID，如 NW-20260306-001')
    a = sub.add_parser('approve', help='批准并执行提案')
    a.add_argument('proposal_id', help='提案 ID')
    r = sub.add_parser('reject', help='驳回提案')
    r.add_argument('proposal_id', help='提案 ID')

    args = parser.parse_args()
    if args.cmd == 'list':
        cmd_list()
    elif args.cmd == 'show':
        cmd_show(args.proposal_id)
    elif args.cmd == 'approve':
        cmd_approve(args.proposal_id)
    elif args.cmd == 'reject':
        cmd_reject(args.proposal_id)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()

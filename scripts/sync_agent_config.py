#!/usr/bin/env python3
"""
同步 openclaw.json 中的 agent 配置 → data/agent_config.json
支持自动发现 agent workspace 下的 Skills 目录

首次运行时会自动检测 openclaw.json 中缺失的三省六部 Agent 并补写注册信息，
创建 workspace/skills 目录，后续周期幂等跳过（已存在则不重复写入）。
"""
import json, os, pathlib, datetime, logging, shutil
from file_lock import atomic_json_write
from utils import parse_json5

log = logging.getLogger('sync_agent_config')
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(message)s', datefmt='%H:%M:%S')

# Auto-detect project root (parent of scripts/)
BASE = pathlib.Path(__file__).parent.parent
DATA = BASE / 'data'
OPENCLAW_CFG = pathlib.Path.home() / '.openclaw' / 'openclaw.json'

ID_LABEL = {
    'gongzhu':  {'label': '公主',   'role': '公主',     'duty': '枢纽协调与总揽全局',  'emoji': '👸'},
    'main':     {'label': '公主',   'role': '公主',     'duty': '枢纽协调与总揽全局',  'emoji': '👸'},  # 兼容旧配置（原 taizi）
    'nvwa':     {'label': '女娲',   'role': '灵魂守护', 'duty': '灵魂文件守护与管理',  'emoji': '🌸'},
    'zhongshu': {'label': '中书省', 'role': '中书令',   'duty': '起草任务令与优先级',  'emoji': '📜'},
    'menxia':   {'label': '门下省', 'role': '侍中',     'duty': '审议与退回机制',      'emoji': '🔍'},
    'shangshu': {'label': '尚书省', 'role': '尚书令',   'duty': '派单与升级裁决',      'emoji': '📮'},
    'libu':     {'label': '礼部',   'role': '礼部尚书', 'duty': '文档/汇报/规范',      'emoji': '📝'},
    'hubu':     {'label': '户部',   'role': '户部尚书', 'duty': '资源/预算/成本',      'emoji': '💰'},
    'bingbu':   {'label': '兵部',   'role': '兵部尚书', 'duty': '应急与巡检',          'emoji': '⚔️'},
    'xingbu':   {'label': '刑部',   'role': '刑部尚书', 'duty': '合规/审计/红线',      'emoji': '⚖️'},
    'gongbu':   {'label': '工部',   'role': '工部尚书', 'duty': '工程交付与自动化',    'emoji': '🔧'},
    'libu_hr':  {'label': '吏部',   'role': '吏部尚书', 'duty': '人事/培训/Agent管理',  'emoji': '👔'},
    'zaochao':  {'label': '钦天监', 'role': '朝报官',   'duty': '每日新闻采集与简报',  'emoji': '📰'},
}

KNOWN_MODELS = [
    {'id': 'anthropic/claude-sonnet-4-6', 'label': 'Claude Sonnet 4.6', 'provider': 'Anthropic'},
    {'id': 'anthropic/claude-opus-4-5',   'label': 'Claude Opus 4.5',   'provider': 'Anthropic'},
    {'id': 'anthropic/claude-haiku-3-5',  'label': 'Claude Haiku 3.5',  'provider': 'Anthropic'},
    {'id': 'openai/gpt-4o',               'label': 'GPT-4o',            'provider': 'OpenAI'},
    {'id': 'openai/gpt-4o-mini',          'label': 'GPT-4o Mini',       'provider': 'OpenAI'},
    {'id': 'openai-codex/gpt-5.3-codex',  'label': 'GPT-5.3 Codex',    'provider': 'OpenAI Codex'},
    {'id': 'google/gemini-2.0-flash',     'label': 'Gemini 2.0 Flash',  'provider': 'Google'},
    {'id': 'google/gemini-2.5-pro',       'label': 'Gemini 2.5 Pro',    'provider': 'Google'},
    {'id': 'copilot/claude-sonnet-4',     'label': 'Claude Sonnet 4',   'provider': 'Copilot'},
    {'id': 'copilot/claude-opus-4.5',     'label': 'Claude Opus 4.5',   'provider': 'Copilot'},
    {'id': 'github-copilot/claude-opus-4.6', 'label': 'Claude Opus 4.6', 'provider': 'GitHub Copilot'},
    {'id': 'copilot/gpt-4o',              'label': 'GPT-4o',            'provider': 'Copilot'},
    {'id': 'copilot/gemini-2.5-pro',      'label': 'Gemini 2.5 Pro',    'provider': 'Copilot'},
    {'id': 'copilot/o3-mini',             'label': 'o3-mini',           'provider': 'Copilot'},
]


# 三省六部 Agent 注册表（与 install.sh register_agents() 保持一致）
# 首次运行时，缺失的 Agent 会被自动写入 openclaw.json
# gongzhu / nvwa 为扩展角色，subagents 待业务设计确定后补充
_AGENTS_TO_REGISTER = [
    {"id": "gongzhu",  "subagents": {"allowAgents": ["zhongshu", "menxia", "shangshu"]}},
    {"id": "nvwa",     "subagents": {"allowAgents": []}},
    {"id": "zhongshu", "subagents": {"allowAgents": ["menxia", "shangshu"]}},
    {"id": "menxia",   "subagents": {"allowAgents": ["shangshu", "zhongshu"]}},
    {"id": "shangshu", "subagents": {"allowAgents": ["zhongshu", "menxia", "hubu", "libu", "bingbu", "xingbu", "gongbu", "libu_hr"]}},
    {"id": "hubu",     "subagents": {"allowAgents": ["shangshu"]}},
    {"id": "libu",     "subagents": {"allowAgents": ["shangshu"]}},
    {"id": "bingbu",   "subagents": {"allowAgents": ["shangshu"]}},
    {"id": "xingbu",   "subagents": {"allowAgents": ["shangshu"]}},
    {"id": "gongbu",   "subagents": {"allowAgents": ["shangshu"]}},
    {"id": "libu_hr",  "subagents": {"allowAgents": ["shangshu"]}},
    {"id": "zaochao",  "subagents": {"allowAgents": []}},
]


def _openclaw_host_ws(ag_id: str) -> str:
    """返回可写入 openclaw.json 的 workspace 路径字符串。

    优先使用 OPENCLAW_HOST_HOME 环境变量（Docker Compose 通过该变量透传宿主机绝对路径），
    回退到波浪号记法（适用于非 Docker 场景，OpenClaw 自行展开 ~）。
    """
    host_home = os.environ.get('OPENCLAW_HOST_HOME', '').strip()
    if host_home:
        return str(pathlib.Path(host_home) / f'workspace-{ag_id}')
    return f'~/.openclaw/workspace-{ag_id}'


def _is_wrong_workspace(ws_str: str, ag_id: str) -> bool:
    """判断 openclaw.json 中记录的 workspace 路径是否是容器内绝对路径（旧版本遗留问题）。

    容器内 HOME=/home/appuser，旧版本写入的路径形如 /home/appuser/.openclaw/workspace-xxx。
    宿主机无此路径，OpenClaw 找不到 workspace，导致 Agent 无法正常工作。
    """
    if not ws_str:
        return True
    p = pathlib.Path(ws_str)
    # 如果是绝对路径且指向 /home/appuser（容器内路径），认为是错误路径
    if p.is_absolute() and str(p).startswith('/home/appuser/'):
        return True
    return False


def register_missing_agents():
    """检测 openclaw.json 中缺失或 workspace 路径错误的三省六部 Agent，自动补写/修正（幂等）。

    - 缺失的 Agent：添加完整注册条目
    - 已存在但 workspace 路径为容器内绝对路径（旧版本遗留）的 Agent：更新为正确的宿主机路径
    写入后 OpenClaw Gateway 会通过文件监听自动热重载（agents 变更无需重启）。
    返回 True 表示有变更，False 表示无变更。
    """
    try:
        # 使用 parse_json5 支持 OpenClaw 配置文件中的注释、无引号键等 JSON5 语法
        cfg = parse_json5(OPENCLAW_CFG.read_text())
    except Exception as e:
        log.warning(f'无法读取 openclaw.json，跳过 Agent 自动注册: {e}')
        return False

    agents_cfg = cfg.setdefault('agents', {})
    agents_list = agents_cfg.get('list', [])

    # 构建 id → 列表索引的映射，方便原地修改
    id_to_idx = {a['id']: i for i, a in enumerate(agents_list) if isinstance(a, dict)}

    added = []
    fixed = []
    for ag in _AGENTS_TO_REGISTER:
        ag_id = ag['id']
        correct_ws = _openclaw_host_ws(ag_id)

        if ag_id not in id_to_idx:
            # Agent 完全不存在 → 添加
            entry = {'id': ag_id, 'workspace': correct_ws}
            entry.update({k: v for k, v in ag.items() if k != 'id'})
            agents_list.append(entry)
            id_to_idx[ag_id] = len(agents_list) - 1
            added.append(ag_id)
            log.info(f'  + 自动注册 Agent: {ag_id}')
        else:
            # Agent 已存在 → 检查 workspace 路径是否是容器内错误路径
            existing = agents_list[id_to_idx[ag_id]]
            old_ws = existing.get('workspace', '')
            if _is_wrong_workspace(old_ws, ag_id):
                existing['workspace'] = correct_ws
                fixed.append(ag_id)
                log.info(f'  ~ 修正 Agent workspace: {ag_id}: {old_ws!r} → {correct_ws!r}')

    if not added and not fixed:
        log.debug('所有三省六部 Agent 已存在于 openclaw.json 且路径正确，跳过注册')
        return False

    # 备份原始 openclaw.json（与 apply_model_changes.py 策略一致）
    bak = OPENCLAW_CFG.parent / f'openclaw.json.bak.register-{datetime.datetime.now().strftime("%Y%m%d-%H%M%S")}'
    try:
        shutil.copy2(OPENCLAW_CFG, bak)
    except Exception as e:
        log.warning(f'备份 openclaw.json 失败（继续写入）: {e}')

    agents_cfg['list'] = agents_list
    try:
        OPENCLAW_CFG.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding='utf-8')
        if added:
            log.info(f'✅ 已向 openclaw.json 注册 {len(added)} 个 Agent: {", ".join(added)}')
        if fixed:
            log.info(f'✅ 已修正 {len(fixed)} 个 Agent 的 workspace 路径: {", ".join(fixed)}')
    except Exception as e:
        log.warning(f'写入 openclaw.json 失败: {e}')
        return False

    # 创建 workspace 和 skills 子目录（供 OpenClaw 运行时识别）
    # 容器内通过 volume 挂载写入，实际落盘到宿主机的 OPENCLAW_HOME 目录
    for ag_id in added:
        ws_dir = pathlib.Path.home() / f'.openclaw/workspace-{ag_id}'
        try:
            (ws_dir / 'skills').mkdir(parents=True, exist_ok=True)
        except Exception as e:
            log.warning(f'创建 workspace 目录失败 ({ag_id}): {e}')

    # OpenClaw Gateway 默认以 hybrid 热重载模式监听 openclaw.json 变更，
    # agents.* 字段变更无需重启即可生效，无需调用 openclaw gateway restart。
    log.info('✅ openclaw.json 已更新，Gateway 将通过文件监听自动热重载新 Agent')

    return True


def normalize_model(model_value, fallback='unknown'):
    if isinstance(model_value, str) and model_value:
        return model_value
    if isinstance(model_value, dict):
        return model_value.get('primary') or model_value.get('id') or fallback
    return fallback


def get_skills(workspace: str):
    skills_dir = pathlib.Path(workspace) / 'skills'
    skills = []
    try:
        if skills_dir.exists():
            for d in sorted(skills_dir.iterdir()):
                if d.is_dir():
                    md = d / 'SKILL.md'
                    desc = ''
                    if md.exists():
                        try:
                            for line in md.read_text(encoding='utf-8', errors='ignore').splitlines():
                                line = line.strip()
                                if line and not line.startswith('#') and not line.startswith('---'):
                                    desc = line[:100]
                                    break
                        except Exception:
                            desc = '(读取失败)'
                    skills.append({'name': d.name, 'path': str(md), 'exists': md.exists(), 'description': desc})
    except PermissionError as e:
        log.warning(f'Skills 目录访问受限: {e}')
    return skills


def main():
    # 自动注册缺失 Agent（首次运行写入，后续幂等跳过）
    register_missing_agents()

    cfg = {}
    try:
        cfg = parse_json5(OPENCLAW_CFG.read_text())
    except Exception as e:
        log.warning(f'cannot read openclaw.json: {e}')
        return

    agents_cfg = cfg.get('agents', {})
    default_model = normalize_model(agents_cfg.get('defaults', {}).get('model', {}), 'unknown')
    agents_list = agents_cfg.get('list', [])

    result = []
    seen_ids = set()
    for ag in agents_list:
        ag_id = ag.get('id', '')
        if ag_id not in ID_LABEL:
            continue
        meta = ID_LABEL[ag_id]
        workspace = ag.get('workspace', str(pathlib.Path.home() / f'.openclaw/workspace-{ag_id}'))
        result.append({
            'id': ag_id,
            'label': meta['label'], 'role': meta['role'], 'duty': meta['duty'], 'emoji': meta['emoji'],
            'model': normalize_model(ag.get('model', default_model), default_model),
            'defaultModel': default_model,
            'workspace': workspace,
            'skills': get_skills(workspace),
            'allowAgents': ag.get('subagents', {}).get('allowAgents', []),
        })
        seen_ids.add(ag_id)

    # 补充不在 openclaw.json agents list 中的 agent（兼容旧版 main）
    EXTRA_AGENTS = {
        'gongzhu': {'model': default_model, 'workspace': str(pathlib.Path.home() / '.openclaw/workspace-gongzhu'),
                    'allowAgents': ['zhongshu']},
        'main':    {'model': default_model, 'workspace': str(pathlib.Path.home() / '.openclaw/workspace-main'),
                    'allowAgents': ['zhongshu','menxia','shangshu','hubu','libu','bingbu','xingbu','gongbu','libu_hr']},
        'zaochao': {'model': default_model, 'workspace': str(pathlib.Path.home() / '.openclaw/workspace-zaochao'),
                    'allowAgents': []},
        'libu_hr': {'model': default_model, 'workspace': str(pathlib.Path.home() / '.openclaw/workspace-libu_hr'),
                    'allowAgents': ['shangshu']},
    }
    for ag_id, extra in EXTRA_AGENTS.items():
        if ag_id in seen_ids or ag_id not in ID_LABEL:
            continue
        meta = ID_LABEL[ag_id]
        result.append({
            'id': ag_id,
            'label': meta['label'], 'role': meta['role'], 'duty': meta['duty'], 'emoji': meta['emoji'],
            'model': extra['model'],
            'defaultModel': default_model,
            'workspace': extra['workspace'],
            'skills': get_skills(extra['workspace']),
            'allowAgents': extra['allowAgents'],
            'isDefaultModel': True,
        })

    payload = {
        'generatedAt': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'defaultModel': default_model,
        'knownModels': KNOWN_MODELS,
        'agents': result,
    }
    DATA.mkdir(exist_ok=True)
    atomic_json_write(DATA / 'agent_config.json', payload)
    log.info(f'{len(result)} agents synced')

    # 自动部署 SOUL.md 到 workspace（如果项目里有更新）
    deploy_soul_files()
    # 同步 scripts/ 到各 workspace（保持 kanban_update.py 等最新）
    sync_scripts_to_workspaces()


# 项目 agents/ 目录名 → 运行时 agent_id 映射
_SOUL_DEPLOY_MAP = {
    'gongzhu': 'gongzhu',
    'nvwa': 'nvwa',
    'zhongshu': 'zhongshu',
    'menxia': 'menxia',
    'shangshu': 'shangshu',
    'libu': 'libu',
    'hubu': 'hubu',
    'bingbu': 'bingbu',
    'xingbu': 'xingbu',
    'gongbu': 'gongbu',
    'libu_hr': 'libu_hr',
    'zaochao': 'zaochao',
}

def sync_scripts_to_workspaces():
    """将项目 scripts/ 目录同步到各 agent workspace（保持 kanban_update.py 等最新）"""
    scripts_src = BASE / 'scripts'
    if not scripts_src.is_dir():
        return
    synced = 0
    for proj_name, runtime_id in _SOUL_DEPLOY_MAP.items():
        ws_scripts = pathlib.Path.home() / f'.openclaw/workspace-{runtime_id}' / 'scripts'
        ws_scripts.mkdir(parents=True, exist_ok=True)
        for src_file in scripts_src.iterdir():
            if src_file.suffix not in ('.py', '.sh') or src_file.stem.startswith('__'):
                continue
            dst_file = ws_scripts / src_file.name
            try:
                src_text = src_file.read_bytes()
            except Exception:
                continue
            try:
                dst_text = dst_file.read_bytes() if dst_file.exists() else b''
            except Exception:
                dst_text = b''
            if src_text != dst_text:
                dst_file.write_bytes(src_text)
                synced += 1
    # also sync to workspace-main for legacy compatibility
    ws_main_scripts = pathlib.Path.home() / '.openclaw/workspace-main/scripts'
    ws_main_scripts.mkdir(parents=True, exist_ok=True)
    for src_file in scripts_src.iterdir():
        if src_file.suffix not in ('.py', '.sh') or src_file.stem.startswith('__'):
            continue
        dst_file = ws_main_scripts / src_file.name
        try:
            src_text = src_file.read_bytes()
            dst_text = dst_file.read_bytes() if dst_file.exists() else b''
            if src_text != dst_text:
                dst_file.write_bytes(src_text)
                synced += 1
        except Exception:
            pass
    if synced:
        log.info(f'{synced} script files synced to workspaces')


def deploy_soul_files():
    """将项目 agents/xxx/SOUL.md 部署到 ~/.openclaw/workspace-xxx/soul.md"""
    agents_dir = BASE / 'agents'
    deployed = 0
    for proj_name, runtime_id in _SOUL_DEPLOY_MAP.items():
        src = agents_dir / proj_name / 'SOUL.md'
        if not src.exists():
            continue
        ws_dst = pathlib.Path.home() / f'.openclaw/workspace-{runtime_id}' / 'soul.md'
        ws_dst.parent.mkdir(parents=True, exist_ok=True)
        # 只在内容不同时更新（避免不必要的写入）
        src_text = src.read_text(encoding='utf-8', errors='ignore')
        try:
            dst_text = ws_dst.read_text(encoding='utf-8', errors='ignore')
        except FileNotFoundError:
            dst_text = ''
        if src_text != dst_text:
            ws_dst.write_text(src_text, encoding='utf-8')
            deployed += 1
        # 太子兼容：同步一份到 legacy main agent 目录
        if runtime_id == 'gongzhu':
            ag_dst = pathlib.Path.home() / '.openclaw/agents/main/SOUL.md'
            ag_dst.parent.mkdir(parents=True, exist_ok=True)
            try:
                ag_text = ag_dst.read_text(encoding='utf-8', errors='ignore')
            except FileNotFoundError:
                ag_text = ''
            if src_text != ag_text:
                ag_dst.write_text(src_text, encoding='utf-8')
        # 确保 sessions 目录存在
        sess_dir = pathlib.Path.home() / f'.openclaw/agents/{runtime_id}/sessions'
        sess_dir.mkdir(parents=True, exist_ok=True)
    if deployed:
        log.info(f'{deployed} SOUL.md files deployed')


if __name__ == '__main__':
    main()

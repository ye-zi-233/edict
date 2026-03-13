#!/usr/bin/env python3
"""
三省六部 · 公共工具函数
避免 read_json / now_iso 等基础函数在多个脚本中重复定义
"""
import json, pathlib, datetime, re


def _strip_json5_comments(text: str) -> str:
    """逐字符扫描，剔除 // 单行注释与 /* */ 多行注释（跳过字符串内容）。"""
    result = []
    i = 0
    in_string = False
    while i < len(text):
        if in_string:
            # 处理转义字符
            if text[i] == '\\' and i + 1 < len(text):
                result.append(text[i])
                result.append(text[i + 1])
                i += 2
            elif text[i] == '"':
                result.append(text[i])
                in_string = False
                i += 1
            else:
                result.append(text[i])
                i += 1
        else:
            if text[i] == '"':
                in_string = True
                result.append(text[i])
                i += 1
            elif text[i:i + 2] == '//':
                # 跳到行尾
                while i < len(text) and text[i] != '\n':
                    i += 1
            elif text[i:i + 2] == '/*':
                # 跳过多行注释
                i += 2
                while i < len(text) - 1 and text[i:i + 2] != '*/':
                    i += 1
                i += 2
            else:
                result.append(text[i])
                i += 1
    return ''.join(result)


def parse_json5(text: str):
    """解析 JSON5 文本（OpenClaw 配置文件格式）。
    
    处理以下 JSON5 特性：
    - // 单行注释 与 /* */ 多行注释
    - 对象/数组的尾随逗号
    - 无引号键（如 agents: {...} ）
    
    先尝试原生 json.loads；失败时应用预处理后重试。
    """
    # 快速路径：纯 JSON 直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 预处理：剔除注释
    cleaned = _strip_json5_comments(text)

    # 移除尾随逗号（} 或 ] 前的逗号）
    cleaned = re.sub(r',\s*([\]}])', r'\1', cleaned)

    # 为无引号键加引号：匹配 { 或 , 后的标识符 + 冒号
    # 仅匹配字母/下划线/$开头、后跟空白+冒号的模式，避免误处理值中的字符
    cleaned = re.sub(
        r'((?:^|[{,\[])\s*)([a-zA-Z_$][a-zA-Z0-9_$]*)(\s*:)',
        lambda m: m.group(1) + '"' + m.group(2) + '"' + m.group(3),
        cleaned,
    )

    return json.loads(cleaned)


def read_json(path, default=None):
    """安全读取 JSON 文件，失败返回 default"""
    try:
        return json.loads(pathlib.Path(path).read_text())
    except Exception:
        return default if default is not None else {}


def now_iso():
    """返回 UTC ISO 8601 时间字符串（末尾 Z）"""
    return datetime.datetime.now(datetime.timezone.utc).isoformat().replace('+00:00', 'Z')


def today_str(fmt='%Y%m%d'):
    """返回今天日期字符串，默认 YYYYMMDD"""
    return datetime.date.today().strftime(fmt)


def safe_name(s: str) -> bool:
    """检查名称是否只含安全字符（字母、数字、下划线、连字符、中文）"""
    import re
    return bool(re.match(r'^[a-zA-Z0-9_\-\u4e00-\u9fff]+$', s))


def validate_url(url: str, allowed_schemes=('https',), allowed_domains=None) -> bool:
    """校验 URL 合法性，防 SSRF"""
    from urllib.parse import urlparse
    try:
        parsed = urlparse(url)
        if parsed.scheme not in allowed_schemes:
            return False
        if allowed_domains and parsed.hostname not in allowed_domains:
            return False
        if not parsed.hostname:
            return False
        # 禁止内网地址
        import ipaddress
        try:
            ip = ipaddress.ip_address(parsed.hostname)
            if ip.is_private or ip.is_loopback or ip.is_reserved:
                return False
        except ValueError:
            pass  # hostname 不是 IP，放行
        return True
    except Exception:
        return False

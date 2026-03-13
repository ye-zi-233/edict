#!/bin/sh
set -e

# gosu 降权启动：以 root 身份修复数据目录权限，然后切换到 PUID:PGID 执行业务进程
# 此脚本替代原 init-data-dirs 容器，避免 NAS Docker UI 因已退出容器显示"异常"
if [ "$(id -u)" = '0' ]; then
    target_uid="${PUID:-1000}"
    target_gid="${PGID:-1000}"

    mkdir -p /app/data /home/appuser/.openclaw
    chown -R "$target_uid:$target_gid" /app/data
    # 递归修改 .openclaw 目录及其内部文件所有权，确保容器进程（PUID:PGID）
    # 可读写 openclaw.json，避免 "Permission denied" 错误
    chown -R "$target_uid:$target_gid" /home/appuser /home/appuser/.openclaw

    exec gosu "$target_uid:$target_gid" "$@"
fi

exec "$@"

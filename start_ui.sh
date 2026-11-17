#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "=========================================="
echo "🚀 启动 安仔 恩妞任务小分队系统 (Task Force Hub)"
echo "=========================================="

if command -v python3 &>/dev/null; then
    python3 -u app.py
elif command -v py3 &>/dev/null; then
    py3 -u app.py
else
    python -u app.py
fi

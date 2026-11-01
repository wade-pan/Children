#!/bin/bash
# 启动 潘翼芃 潘一柠任务小分队系统 (Port: 5088)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=================================================="
echo "🚀 正在启动 潘翼芃 潘一柠任务小分队系统..."
echo "📂 运行目录: $SCRIPT_DIR"
echo "📍 访问地址: http://localhost:5088"
echo "=================================================="

# 使用可用的 python 或 python3
if command -v python3 &>/dev/null; then
    exec python3 app.py
elif command -v python &>/dev/null; then
    exec python app.py
else
    echo "❌ 错误: 未检测到 python 或 python3 环境"
    exit 1
fi

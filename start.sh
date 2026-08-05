#!/bin/bash
# AI自主交易事业部 一键启动（runner + Dashboard）
# 用法: ./start.sh       启动（幂等：已在运行则跳过）
#       ./start.sh stop  停止全部相关进程
set -euo pipefail
cd "$(dirname "$0")"

PY="${PYTHON:-/opt/homebrew/bin/python3.14}"
if [ ! -x "$PY" ]; then
  PY="$(command -v python3 || true)"
fi
echo "使用 Python: $PY"

stop_all() {
  pkill -f "scripts/runner.py" 2>/dev/null && echo "runner 已停止" || echo "runner 未在运行"
  pkill -f "dashboard_server.py" 2>/dev/null && echo "dashboard 已停止" || echo "dashboard 未在运行"
}

start_runner() {
  if pgrep -f "scripts/runner.py" > /dev/null 2>&1; then
    echo "✅ runner 已在运行"
  else
    mkdir -p artifacts
    nohup "$PY" scripts/runner.py --interval 15 >> artifacts/runner.log 2>&1 &
    echo "✅ runner 已启动（PID $!，每 15 分钟一轮，日志 artifacts/runner.log）"
  fi
}

start_dashboard() {
  if pgrep -f "dashboard_server.py" > /dev/null 2>&1; then
    echo "✅ Dashboard 已在运行"
  else
    mkdir -p artifacts
    nohup "$PY" dashboard_server.py >> artifacts/dash.log 2>&1 &
    echo "✅ Dashboard 已启动（http://127.0.0.1:8765/dashboard.html）"
  fi
}

case "${1:-start}" in
  stop) stop_all ;;
  start)
    start_runner
    start_dashboard
    echo ""
    echo "验证: curl -s http://127.0.0.1:8765/api/status | head -c 300"
    ;;
  *) echo "用法: $0 [start|stop]"; exit 1 ;;
esac

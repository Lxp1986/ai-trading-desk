#!/bin/bash
# AI自主交易事业部 一键启动（runner + Dashboard）
# 用法: ./start.sh       启动（幂等：已在运行则跳过）
#       ./start.sh stop  停止全部相关进程
set -euo pipefail
cd "$(dirname "$0")"

# 加载交易所凭证（BINANCE_TESTNET_API_KEY 等；仅在用户环境存在时读取，绝不写入仓库）
if [ -f ~/.zshrc ]; then
  set +e
  . ~/.zshrc
  set -e
fi

PY="${PYTHON:-/opt/homebrew/bin/python3.14}"
if [ ! -x "$PY" ]; then
  PY="$(command -v python3 || true)"
fi
echo "使用 Python: $PY"

stop_all() {
  pkill -f "scripts/runner.py" 2>/dev/null && echo "runner 已停止" || echo "runner 未在运行"
  pkill -f "scripts/guardian.py" 2>/dev/null && echo "guardian 已停止" || echo "guardian 未在运行"
  pkill -f "dashboard_server.py" 2>/dev/null && echo "dashboard 已停止" || echo "dashboard 未在运行"
}

start_guardian() {
  if pgrep -f "scripts/guardian.py" > /dev/null 2>&1; then
    echo "✅ guardian 已在运行"
  else
    mkdir -p artifacts
    nohup "$PY" scripts/guardian.py >> artifacts/guardian.log 2>&1 &
    echo "✅ guardian 已启动（PID $!，分层调度：价格1m/新闻5m/链上15m/情绪60m，日志 artifacts/guardian.log）"
  fi
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
    start_guardian
    start_dashboard
    echo ""
    echo "验证: curl -s http://127.0.0.1:8765/api/status | head -c 300"
    ;;
  *) echo "用法: $0 [start|stop]"; exit 1 ;;
esac

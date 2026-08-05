#!/usr/bin/env python3
"""AI自主交易事业部 · 系统健康检查（一键巡检）。

用法：PYTHONPATH=src /opt/homebrew/bin/python3.14 scripts/health_check.py

检查项：
1. 常驻进程（runner / guardian / dashboard）；
2. 数据文件完整性（分析任务依赖的文件必须永续存在，缺一个即报错）；
3. cron 任务状态（通过 hermes cron list 检查 error 任务）；
4. 事件中心（L3 严重事件计数）。

任何异常以非零退出码 + 🚨 输出提示。
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# 分析任务依赖的数据文件（必须永续存在——成功失败都写状态的规范）
# 注意：仅列"被读取的依赖文件"；模型 cron 的产出文件（news_analysis.jsonl 等）
# 不在其列（产出缺失只影响该任务自身，下次运行会生成）。
REQUIRED_FILES = [
    "state.json", "audit.jsonl", "orders.jsonl", "events.jsonl",
    "signals.jsonl", "token_usage.json", "opportunities.json",
    "onchain.jsonl", "movers.json", "macro.json", "strategy_weights.json",
    "analysis_log.jsonl",
]

PROCESSES = [
    ("scripts/runner.py", "runner（15分钟常规运营）"),
    ("scripts/guardian.py", "guardian（分层调度守护）"),
    ("dashboard_server.py", "dashboard（127.0.0.1:8765）"),
]


def check_processes() -> list[str]:
    issues: list[str] = []
    for pattern, label in PROCESSES:
        r = subprocess.run(["pgrep", "-f", pattern], capture_output=True, text=True)
        if not r.stdout.strip():
            issues.append(f"进程缺失: {label} ({pattern})")
    return issues


def check_files() -> list[str]:
    issues: list[str] = []
    for name in REQUIRED_FILES:
        path = ROOT / "artifacts" / name
        if not path.exists():
            issues.append(f"数据文件缺失: {name}")
        elif path.stat().st_size == 0:
            issues.append(f"数据文件为空: {name}")
    return issues


def check_events() -> list[str]:
    issues: list[str] = []
    events_path = ROOT / "artifacts" / "events.jsonl"
    if not events_path.exists():
        return issues  # 已在文件检查报
    try:
        lines = [l for l in events_path.read_text(encoding="utf-8").strip().splitlines() if l]
        l3 = [json.loads(l) for l in lines if '"L3"' in l]
        if l3:
            issues.append(f"存在 {len(l3)} 条 L3 严重事件（最近: {l3[-1].get('detail', '')[:60]}）")
    except (OSError, json.JSONDecodeError):
        issues.append("events.jsonl 读取失败")
    return issues


def main() -> int:
    print("🔍 AI自主交易事业部 · 系统健康检查")
    print(f"时间: {__import__('time').strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    all_issues: list[str] = []
    checks = [
        ("进程", check_processes()),
        ("数据文件", check_files()),
        ("事件中心", check_events()),
    ]
    for name, issues in checks:
        if issues:
            print(f"🚨 [{name}] 异常 {len(issues)} 项:")
            for i in issues:
                print(f"    - {i}")
            all_issues.extend(issues)
        else:
            print(f"✅ [{name}] 正常")

    # cron 检查（可选，hermes 命令）
    try:
        r = subprocess.run(["hermes", "cron", "list"], capture_output=True, text=True, timeout=30)
        if r.returncode == 0 and "error" in r.stdout.lower():
            # 粗略扫描 error 状态
            error_lines = [l for l in r.stdout.splitlines() if "error" in l.lower()]
            if error_lines:
                print(f"🚨 [cron] 存在异常任务 {len(error_lines)} 个:")
                for l in error_lines[:5]:
                    print(f"    - {l.strip()[:90]}")
                all_issues.append("cron 任务存在 error")
            else:
                print("✅ [cron] 正常")
        else:
            print("ℹ️ [cron] 跳过（hermes cron list 不可用）")
    except Exception:
        print("ℹ️ [cron] 跳过（hermes 命令异常）")

    print()
    if all_issues:
        print(f"🚨 检查完成：发现 {len(all_issues)} 项异常，需处理")
        return 1
    print("✅ 全部正常 —— 系统健康")
    return 0


if __name__ == "__main__":
    sys.exit(main())

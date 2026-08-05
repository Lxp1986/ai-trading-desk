#!/usr/bin/env python3
"""AI自主交易事业部异常看门狗（Telegram 静默告警）。

用法: python3 scripts/watchdog.py
- 无异常: 无输出（cron no_agent 模式下静默，不打扰）
- 有异常: 输出 Markdown 告警文本（cron 会原样发到 Telegram）

检查项（分层，与研讨纪要 6.1 一致）：
1. Dashboard / 项目进程是否存活
2. 审计记录异常增长（最近 N 条全部被否决 → 策略失效预警）
3. Token 用量异常（调用次数突增 → 成本预警）
4. 审计文件可读性（损坏 → 数据完整性预警）
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "artifacts" / "audit.jsonl"
TOKEN_USAGE = ROOT / "artifacts" / "token_usage.json"

ALERT_THRESHOLD_REJECTED = 5      # 连续否决数
ALERT_THRESHOLD_TOKENS = 100_000  # 单日 token 突增阈值


def now_cn() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M")


def dashboard_alive() -> bool:
    try:
        import urllib.request

        with urllib.request.urlopen("http://127.0.0.1:8765/api/status", timeout=3) as resp:
            return resp.status == 200
    except Exception:
        return False


def main() -> None:
    alerts: list[str] = []

    # 1. Dashboard 存活
    if not dashboard_alive():
        alerts.append("❌ **Dashboard 未运行**（127.0.0.1:8765 无响应）——控制平面可能已停止。")

    # 2. 审计文件可读性
    records: list[dict] = []
    if AUDIT.exists():
        try:
            for line in AUDIT.read_text(encoding="utf-8").splitlines():
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        except OSError as exc:
            alerts.append(f"❌ **审计文件不可读**：{exc}")
    else:
        alerts.append("⚠️ **审计文件不存在**：`artifacts/audit.jsonl` 缺失，项目可能尚未运行过。")

    # 3. 连续否决 → 策略失效预警（hold 观望不计入否决）
    if records:
        recent = records[-ALERT_THRESHOLD_REJECTED:]
        rejected = [
            r for r in recent
            if not r.get("decision", {}).get("approved")
            and r.get("decision", {}).get("intent", {}).get("side") != "hold"
        ]
        if len(rejected) >= ALERT_THRESHOLD_REJECTED:
            alerts.append(
                f"⚠️ **策略失效预警**：最近 {len(rejected)} 条交易假设全部被风控否决。"
                "建议复核当前市场状态与假设质量。"
            )

    # 4. Token 用量异常
    if TOKEN_USAGE.exists():
        try:
            usage = json.loads(TOKEN_USAGE.read_text(encoding="utf-8"))
            calls = int(usage.get("api_calls", 0))
            total = int(usage.get("total_tokens", 0))
            if calls > 0 and total > ALERT_THRESHOLD_TOKENS:
                alerts.append(
                    f"⚠️ **Token 成本预警**：本项目累计 {total} tokens / {calls} 次调用，"
                    "超过预警阈值，建议检查调用频率与模型选择。"
                )
        except (OSError, ValueError):
            alerts.append("⚠️ **Token 用量文件损坏**：`artifacts/token_usage.json` 无法解析。")

    if alerts:
        print(f"🚨 **AI自主交易事业部 · 异常告警**（{now_cn()}）")
        print("")
        for alert in alerts:
            print(alert)
        print("")
        print("*此消息由本地看门狗脚本自动生成。*")


if __name__ == "__main__":
    main()

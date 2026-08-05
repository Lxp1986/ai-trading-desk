#!/usr/bin/env python3
"""生成 AI自主交易事业部经营报告（Markdown 文本，供 Telegram/日报使用）。

用法: python3 scripts/trading_report.py [--json]

输出按「已验证/推断/状态」分层，不把模拟值写成实盘收益。
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "artifacts" / "audit.jsonl"
TOKEN_USAGE = ROOT / "artifacts" / "token_usage.json"
STARTING_CAPITAL_USDT = 277.0


def now_cn() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M")


def load_audit() -> list[dict]:
    records: list[dict] = []
    if AUDIT.exists():
        for line in AUDIT.read_text(encoding="utf-8").splitlines():
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records


def load_token_usage() -> dict:
    if TOKEN_USAGE.exists():
        try:
            return json.loads(TOKEN_USAGE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            pass
    return {}


def server_alive() -> bool:
    try:
        import urllib.request

        with urllib.request.urlopen("http://127.0.0.1:8765/api/status", timeout=3) as resp:
            return resp.status == 200
    except Exception:
        return False


def build_report() -> dict:
    audit = load_audit()
    tokens = load_token_usage()
    approved = [r for r in audit if r.get("decision", {}).get("approved")]
    rejected = [r for r in audit if not r.get("decision", {}).get("approved")]
    latest = audit[-1] if audit else None

    realized = 0.0  # 模拟盘：尚未平仓，无已实现盈亏（状态：推断为0）
    nav = STARTING_CAPITAL_USDT

    status = {
        "generated_at": now_cn(),
        "mode": "simulation",
        "network": "Binance Spot Testnet",
        "dashboard_alive": server_alive(),
        "starting_capital": STARTING_CAPITAL_USDT,
        "nav": nav,
        "realized_pnl": realized,
        "audit_records": len(audit),
        "approved_decisions": len(approved),
        "rejected_decisions": len(rejected),
        "latest_decision": latest,
        "token_usage": {
            "total_tokens": tokens.get("total_tokens", 0),
            "api_calls": tokens.get("api_calls", 0),
            "provider": tokens.get("provider", "未调用"),
            "model": tokens.get("model", "未调用"),
            "updated_at": tokens.get("updated_at"),
        },
    }
    return status


def render_markdown(s: dict) -> str:
    lines = [
        "📊 **AI自主交易事业部 · 经营报告**",
        f"生成时间：{s['generated_at']}",
        "",
        "## 运行状态",
        f"- 模式：**{s['mode']}**（模拟盘，无真实资金）",
        f"- 网络：{s['network']}",
        f"- Dashboard：{'✅ 运行中' if s['dashboard_alive'] else '❌ 未运行'}",
        f"- 初始资金：{s['starting_capital']} USDT",
        f"- 当前净值：{s['nav']} USDT（模拟）",
        f"- 已实现盈亏：{s['realized_pnl']} USDT（模拟盘未平仓，恒为0）",
        "",
        "## 决策记录",
        f"- 审计记录总数：{s['audit_records']}",
        f"- 已批准：{s['approved_decisions']} / 被风控否决：{s['rejected_decisions']}",
    ]
    latest = s.get("latest_decision")
    if latest:
        decision = latest.get("decision", {})
        intent = decision.get("intent", {})
        snap = latest.get("snapshot", {})
        lines += [
            "",
            "**最近一次决策**：",
            f"- 品种：{snap.get('symbol')} @ {snap.get('price')}（来源：{snap.get('source')}）",
            f"- 方向：{intent.get('side')} / 数量 {intent.get('quantity')} / 置信度 {intent.get('confidence')}",
            f"- 结论：{'✅ 风控批准' if decision.get('approved') else '❌ 风控否决'}（{', '.join(decision.get('reasons', []))}）",
            f"- 假设：{intent.get('thesis', '')[:120]}",
        ]
    else:
        lines.append("- （暂无决策记录）")
    lines += [
        "",
        "## Token 消耗（本项目内）",
        f"- 累计：{s['token_usage']['total_tokens']} tokens / {s['token_usage']['api_calls']} 次调用",
        f"- Provider：{s['token_usage']['provider']} / Model：{s['token_usage']['model']}",
        f"- 更新时间：{s['token_usage']['updated_at'] or '从未调用'}",
        "",
        "## 说明",
        "- 以上为**模拟盘状态**，非实盘收益；净值=初始资金（模拟仓未平仓不计浮动盈亏）。",
        "- 报告由本地脚本生成，仅统计本项目 Token，不混入其他项目。",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="输出 JSON 而非 Markdown")
    args = parser.parse_args()
    status = build_report()
    if args.json:
        print(json.dumps(status, ensure_ascii=False, indent=2))
    else:
        print(render_markdown(status))


if __name__ == "__main__":
    main()

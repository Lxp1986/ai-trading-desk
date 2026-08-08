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
STARTING_CAPITAL_USDT = 80000.0  # OKX Demo 账户重置后初始（虚拟 USDT 主）


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
    held = [r for r in audit if r.get("decision", {}).get("intent", {}).get("side") == "hold"]
    rejected = [
        r for r in audit
        if not r.get("decision", {}).get("approved")
        and r.get("decision", {}).get("intent", {}).get("side") != "hold"
    ]
    latest = audit[-1] if audit else None

    # 真实账本/运行状态（runner.py 写入的 state.json）
    state: dict = {}
    state_path = ROOT / "artifacts" / "state.json"
    if state_path.exists():
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            state = {}
    portfolio = state.get("portfolio", {}) or {}
    market = state.get("snapshot", {}) or {}
    indicators = state.get("indicators", {}) or {}
    risk = state.get("risk", {}) or {}
    # 实时持仓（优先 OKX 合约同步/账本聚合；实时成功即采用，空仓也是结果）
    live_positions = {}
    try:
        from autotrader.position_manager import load_positions
        live_positions = load_positions()
    except Exception:
        live_positions = portfolio.get("positions", {}) or {}  # 仅读取失败才回退旧快照
    # 浮盈实时重算（基于实时持仓 + live_prices 最新价；空仓 = 0）
    live_unrealized = 0.0
    try:
        import json as _json
        from pathlib import Path as _Path
        lpx_path = _Path(__file__).resolve().parents[1] / "artifacts" / "live_prices.json"
        if lpx_path.exists():
            lpx = _json.loads(lpx_path.read_text(encoding="utf-8")).get("prices", {})
            for sym, p in live_positions.items():
                row = lpx.get(sym) or {}
                px = row.get("price") if isinstance(row, dict) else None
                if not px:
                    continue
                side = p.get("side", "long")
                live_unrealized += p["quantity"] * ((px - p["avg_cost"]) if side == "long" else (p["avg_cost"] - px))
    except Exception:
        live_unrealized = portfolio.get("unrealized_pnl", 0.0)

    status = {
        "generated_at": now_cn(),
        "mode": "simulation",
        "network": "OKX Demo Trading（模拟盘）",
        "dashboard_alive": server_alive(),
        "state_updated_at": state.get("updated_at"),
        "starting_capital": STARTING_CAPITAL_USDT,
        "nav": portfolio.get("equity", STARTING_CAPITAL_USDT),
        "cash": portfolio.get("cash", STARTING_CAPITAL_USDT),
        "positions": live_positions,
        "position_value": portfolio.get("position_value", 0.0),
        "realized_pnl": portfolio.get("realized_pnl", 0.0),
        "unrealized_pnl": live_unrealized,
        "max_drawdown_pct": portfolio.get("max_drawdown_pct", 0.0),
        "market": {
            "symbol": market.get("symbol", "BTC/USDT"),
            "price": market.get("price"),
            "trend": market.get("trend", "unknown"),
            "volume_ratio": market.get("volume_ratio"),
            "rsi14": indicators.get("rsi14"),
            "atr14": indicators.get("atr14"),
            "change_24h_pct": indicators.get("change_24h_pct"),
        },
        "risk": risk,
        "audit_records": len(audit),
        "approved_decisions": len(approved),
        "held_decisions": len(held),
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
    """通俗版经营报告——用人话，不费力（董事长风格要求）。

    原则：先给结论（赚/亏、正常/异常），再给关键数字，术语全部换成大白话。
    """
    market = s.get("market", {})
    risk = s.get("risk", {})
    halt = risk.get("trading_halted")
    trend_cn = {"trend_up": "📈 偏强", "trend_down": "📉 偏弱"}.get(market.get("trend"), "↔️ 横盘")
    # 盈亏人话
    realized = float(s.get("realized_pnl", 0) or 0)
    unrealized = float(s.get("unrealized_pnl", 0) or 0)
    total_pnl = realized + unrealized
    pnl_word = "赚了" if total_pnl >= 0 else "亏了"
    pnl_smile = "😀" if total_pnl >= 0 else "😟"
    # 状态结论
    status_ok = s.get("dashboard_alive") and not halt
    lines = [
        "📊 **AI交易 · 每日经营报告**",
        f"（{s['generated_at']} · {s['mode']}，模拟盘，不是真钱）",
        "",
        f"**一句话：{pnl_smile} 目前{pnl_word} {abs(total_pnl):.2f} USDT，系统{'一切正常 ✅' if status_ok else '有点问题 ⚠️'}。**",
    ]
    if halt:
        lines.append(f"🚨 **注意：风控已熔断！** 原因：{'；'.join(risk.get('halt_reasons', []))}")
    lines += [
        "",
        "## 行情怎么看",
        f"- {market.get('symbol')} 现在 ${market.get('price') or '--'}，24 小时{'涨' if float(market.get('change_24h_pct') or 0) >= 0 else '跌'} {abs(float(market.get('change_24h_pct') or 0)):.2f}%，整体{trend_cn}。",
        f"- 热度指标 RSI {market.get('rsi14') or '--'}（>70 偏热、<30 偏冷），量比 {market.get('volume_ratio') or '--'}（>1 说明买卖比平时活跃）。",
        "",
        "## 账户情况",
        f"- 总资产：{s['nav']} USDT（一开始是 {s['starting_capital']} USDT）",
        f"- 手头现金：{s['cash']} USDT，股票/币的市值：{s['position_value']} USDT",
        f"- 已经落袋：{realized:+.2f} USDT，还在浮动的：{unrealized:+.2f} USDT",
        f"- 最惨时回撤：{s['max_drawdown_pct']}%（超过 25% 系统会强制清仓止损）",
    ]
    if s.get("positions"):
        pos_desc = "；".join(
            f"{k} {v['quantity']}（成本 {v['avg_cost']:.2f}）" for k, v in s["positions"].items()
        )
        lines.append(f"- 现在拿着：{pos_desc}")
    else:
        lines.append("- 现在拿着：空仓，没持仓")
    lines += [
        "",
        "## 最近拍板",
        f"- 一共做了 {s['audit_records']} 次决策：{s['approved_decisions']} 次动手、{s.get('held_decisions', 0)} 次观望、{s['rejected_decisions']} 次被风控拦下（拦得对，安全第一）。",
    ]
    latest = s.get("latest_decision")
    if latest:
        decision = latest.get("decision", {})
        intent = decision.get("intent", {})
        snap = latest.get("snapshot", {})
        verdict = "✅ 批准了" if decision.get("approved") else "❌ 拦下了"
        sym_name = snap.get("symbol") or "（记录里没写品种）"
        side_raw = str(intent.get("side") or "").upper()
        side_word = "买" if side_raw == "BUY" else ("卖" if side_raw == "SELL" else "（方向没记录）")
        lines.append(
            f"- 最近一次：想{side_word} {sym_name}，"
            f"{verdict}（{'，'.join(decision.get('reasons', [])[:2]) or '没记录原因'}）"
        )
    else:
        lines.append("- （还没拍过板）")
    lines += [
        "",
        "## AI 花了多少",
        f"- 累计 {s['token_usage']['total_tokens']} tokens / {s['token_usage']['api_calls']} 次调用（项目内预算 3 元/天，打满即停，不会超支）",
        "",
        "## 说明",
        "- 以上全是**模拟盘数据**，不是真实收益；30 天验证通过前不会碰真钱。",
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

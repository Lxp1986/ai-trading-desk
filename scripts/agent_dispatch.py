#!/usr/bin/env python3
"""员工调度器（CEO 一键调度任意岗位立即进入工作状态）。

用法：
    python3 scripts/agent_dispatch.py --list                  # 列出全部员工与状态
    python3 scripts/agent_dispatch.py 策略研究员              # 调度单个岗位
    python3 scripts/agent_dispatch.py 数据工程师 技术分析员    # 调度多个
    python3 scripts/agent_dispatch.py --all-deterministic     # 全部确定性岗位

每个岗位对应一个可执行入口（函数）。确定性岗位直接运行；研究型岗位（新闻/
链上/聪明钱包/情绪）由 CEO（Hermes）调用时执行数据采集后走记录接口——本调度器
保证每个岗位有可调用的工作入口，实现"随时待命"。
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from autotrader import market, portfolio, risk, strategy  # noqa: E402
from autotrader.news_research import load_events, record_event  # noqa: E402
from autotrader.onchain import load_signals, record_signal, signal_confidence  # noqa: E402
from autotrader.sentiment import assess_sentiment, fetch_funding_rate, save_sentiment  # noqa: E402
from autotrader.event_trader import checklist, plan  # noqa: E402
from autotrader.team import EMPLOYEES, counts, snapshot  # noqa: E402

ARTIFACTS = ROOT / "artifacts"


def _read_state() -> dict[str, Any] | None:
    """读取 state.json（runner 同构：snapshot/indicators/risk/portfolio）。"""
    state_path = ARTIFACTS / "state.json"
    if not state_path.exists():
        return None
    try:
        return json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _run_market_state() -> dict[str, Any]:
    """数据工程师 + 技术分析员 + 市场状态官：行情采集→指标→市场状态→落盘。"""
    from autotrader.binance_testnet import BinanceSpotTestnet
    client = BinanceSpotTestnet()
    klines = client.klines("BTCUSDT", "15m", 60)
    market.store_klines(klines)
    ind: dict[str, Any] = market.compute_indicators(klines)
    ind["trend"] = market.classify_market(ind)
    snapshot = {
        "symbol": "BTC/USDT", "price": ind["price"],
        "volume_ratio": round(ind["volume_ratio"], 2), "trend": ind["trend"],
        "liquidity_ok": ind["volume_ratio"] >= 0.3 and (ind["atr14"] / ind["price"]) < 0.05,
        "source": "binance_testnet",
    }
    state = {
        "updated_at": market.now_iso(),
        "snapshot": snapshot,
        "indicators": {k: (round(v, 4) if isinstance(v, (int, float)) else v) for k, v in ind.items()},
    }
    (ARTIFACTS / "state.json").parent.mkdir(parents=True, exist_ok=True)
    (ARTIFACTS / "state.json").write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"price": snapshot["price"], "trend": snapshot["trend"],
            "rsi14": ind["rsi14"], "atr14": ind["atr14"], "volume_ratio": snapshot["volume_ratio"]}


def _run_strategy() -> dict[str, Any]:
    """策略研究员：读取最新指标+事件 → 运行策略库。"""
    state = _read_state()
    if state is None:
        return {"error": "state.json 不存在，先调度 数据工程师/市场状态官"}
    ind = dict(state.get("indicators") or {})
    if not ind.get("price"):
        snap = state.get("snapshot") or {}
        ind["price"] = snap.get("price")
    events = load_events(limit=10)
    signals = [s.to_dict() for s in strategy.apply_strategies(ind, events)]
    return {"signals": signals, "event_count": len(events)}


def _run_sentiment() -> dict[str, Any]:
    """情绪与传播研究员：资金费率 + 指标 → 情绪状态。"""
    state = _read_state()
    ind = None
    if state:
        indicators = state.get("indicators") or {}
        if indicators.get("rsi14") is not None:
            ind = {"rsi14": indicators["rsi14"], "volume_ratio": indicators.get("volume_ratio", 1.0)}
    funding = fetch_funding_rate()
    sentiment = assess_sentiment(ind=ind, funding=funding)
    save_sentiment(sentiment)
    return sentiment.to_dict()


def _run_portfolio() -> dict[str, Any]:
    """组合经理：账本 → 持仓/净值/回撤快照。"""
    orders = portfolio.load_orders(ARTIFACTS / "orders.jsonl")
    state = _read_state()
    price = (state.get("snapshot") or {}).get("price") if state else None
    prices = {"BTC/USDT": price} if price else {}
    return portfolio.portfolio_snapshot(orders, prices=prices)


def _run_risk() -> dict[str, Any]:
    """风险官：账本 → 连亏/回撤/熔断状态。"""
    orders = portfolio.load_orders(ARTIFACTS / "orders.jsonl")
    state = _read_state()
    price = (state.get("snapshot") or {}).get("price") if state else None
    prices = {"BTC/USDT": price} if price else {}
    from dataclasses import asdict
    return asdict(risk.compute_state(orders, prices=prices))


def _run_event_trader() -> dict:
    """事件交易员：读取 A/B 级事件 → 阶段判定 + 检查清单 + 计划。"""
    events = load_events(limit=20)
    active = [e for e in events if e.get("grade") in ("A", "B")]
    if not active:
        return {"plans": [], "note": "当前无 A/B 级事件，事件交易员待命"}
    plans = [plan(e).to_dict() for e in active[-5:]]
    return {"plans": plans}


def _run_news_research() -> dict:
    """宏观与新闻研究员：列出当前事件（采集由 CEO 联网执行）。"""
    events = load_events(limit=20)
    return {"events": events, "note": "新闻采集由 CEO 联网执行后 record_event 落盘"}


def _run_onchain() -> dict:
    """链上数据分析员 + 聪明钱包研究员：列出链上信号（采集由 CEO 用链上工具执行）。"""
    signals = load_signals(limit=20)
    return {"signals": signals, "note": "链上采集由 CEO 使用链上工具执行后 record_signal 落盘"}


# 岗位 → 工作入口映射（"随时待命"：CEO 点名即可执行）
DISPATCH = {
    "数据工程师": _run_market_state,
    "技术分析员": _run_market_state,
    "市场状态官": _run_market_state,
    "策略研究员": _run_strategy,
    "情绪与传播研究员": _run_sentiment,
    "组合经理": _run_portfolio,
    "风险官": _run_risk,
    "事件交易员": _run_event_trader,
    "宏观与新闻研究员": _run_news_research,
    "链上数据分析员": _run_onchain,
    "聪明钱包研究员": _run_onchain,
}


def main(argv: list[str]) -> int:
    if not argv or "--list" in argv:
        print("员工花名册（随时待命状态）：")
        for employee in EMPLOYEES:
            print(f"  {employee.name}  [{employee.status}] {employee.responsibility[:40]}")
        print("\n确定性岗位已接入调度器：", ", ".join(sorted(DISPATCH)))
        print("\n用法: agent_dispatch.py <岗位名...> | --all-deterministic | --list")
        return 0

    if "--all-deterministic" in argv:
        names = ["数据工程师", "技术分析员", "市场状态官", "策略研究员",
                 "情绪与传播研究员", "组合经理", "风险官", "事件交易员"]
    else:
        names = [a for a in argv if not a.startswith("-")]

    results: dict[str, dict] = {}
    for name in names:
        task = DISPATCH.get(name)
        if task is None:
            results[name] = {"error": "该岗位未接入调度器（研究型岗位由 CEO 手动调度）"}
            continue
        try:
            results[name] = task()
        except Exception as exc:  # 岗位异常不阻断其他岗位
            results[name] = {"error": f"{type(exc).__name__}: {exc}"}
        print(f"[{name}] {json.dumps(results[name], ensure_ascii=False)[:300]}")

    out_path = ARTIFACTS / "dispatch_last.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n结果已写入 {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

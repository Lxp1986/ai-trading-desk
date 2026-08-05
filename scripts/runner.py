#!/usr/bin/env python3
"""30 天模拟运行循环（数据采集与状态维护常驻进程）。

职责（确定性本地计算，不调用模型、不产生 Token 成本）：
1. 每轮拉取 Binance Spot Testnet 行情 + K 线，分类市场状态并落盘历史；
2. 从本地账本计算风控状态（连亏/回撤/熔断）；
3. 计算组合快照（现金/持仓/净值/盈亏/回撤）；
4. 事件检测（波动、量能、风控状态变化）→ 写 ``artifacts/events.jsonl``；
5. 汇总写入 ``artifacts/state.json``（Hermes 介入草拟、Dashboard、报告共用）。

交易决策不在此进程内：Hermes（CEO）按事件/定时介入草拟假设，经风控
审核后由执行层下单；本进程只负责“看得见、算得清、记得住”。

用法:
    python3 scripts/runner.py --interval 15 --once
    python3 scripts/runner.py --interval 15          # 常驻
"""
from __future__ import annotations

import argparse
import json
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from autotrader.binance_testnet import BinanceSpotTestnet  # noqa: E402
from autotrader.market import build_snapshot, compute_indicators, load_klines  # noqa: E402
from autotrader.portfolio import load_orders, portfolio_snapshot  # noqa: E402
from autotrader.risk import compute_state  # noqa: E402

STATE_PATH = ROOT / "artifacts" / "state.json"
EVENTS_PATH = ROOT / "artifacts" / "events.jsonl"
LOG_PATH = ROOT / "artifacts" / "runner.log"

# 事件阈值（基础版，后续可扩展研讨纪要的 11 类事件）
EVENT_VOLATILITY_PCT = 1.5    # 24h 波动
EVENT_VOLUME_RATIO = 2.5      # 量比
EVENT_ATR_PCT = 2.0           # 单根 K 线波动（ATR/价格）


def now_cn() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S")


def log(message: str) -> None:
    line = f"[{now_cn()}] {message}"
    print(line, flush=True)
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def detect_events(snapshot, indicators: dict, risk_state, prev_state) -> list[dict]:
    """事件检测（基础版）。返回新事件列表。"""
    events: list[dict] = []
    change = indicators["change_24h_pct"]
    if abs(change) >= EVENT_VOLATILITY_PCT:
        events.append({
            "type": "volatility",
            "level": "L2",
            "detail": f"24h 波动 {change:+.2f}% 超过阈值 ±{EVENT_VOLATILITY_PCT}%",
            "symbol": snapshot.symbol,
            "at": now_cn(),
        })
    if indicators["volume_ratio"] >= EVENT_VOLUME_RATIO:
        events.append({
            "type": "volume_surge",
            "level": "L2",
            "detail": f"量比 {indicators['volume_ratio']:.2f} 超过阈值 {EVENT_VOLUME_RATIO}",
            "symbol": snapshot.symbol,
            "at": now_cn(),
        })
    if indicators["atr14"] / indicators["price"] * 100 >= EVENT_ATR_PCT:
        events.append({
            "type": "high_volatility",
            "level": "L2",
            "detail": f"ATR 占价 {indicators['atr14'] / indicators['price'] * 100:.2f}% 超过阈值 {EVENT_ATR_PCT}%",
            "symbol": snapshot.symbol,
            "at": now_cn(),
        })
    if risk_state.trading_halted and not prev_state.trading_halted:
        events.append({
            "type": "risk_halt",
            "level": "L4",
            "detail": "；".join(risk_state.halt_reasons) or "风控熔断触发",
            "symbol": snapshot.symbol,
            "at": now_cn(),
        })
    return events


def run_once(client: BinanceSpotTestnet, prev_state: dict) -> dict:
    """执行一轮采集+计算，返回本轮状态。"""
    symbol = "BTCUSDT"
    snapshot = build_snapshot(client, symbol, "15m", 60)
    indicators = compute_indicators(load_klines(symbol, "15m", 60))
    prices = {snapshot.symbol: snapshot.price}
    orders = load_orders()
    risk_state = compute_state(orders, prices)
    portfolio = portfolio_snapshot(orders, prices)

    prev_risk = prev_state.get("risk", {})
    prev_halted = prev_risk.get("trading_halted", False)
    events = detect_events(snapshot, indicators, risk_state, type("_PS", (), {"trading_halted": prev_halted})())

    for event in events:
        with EVENTS_PATH.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")
        log(f"⚠️ 事件: {event['type']} | {event['detail']}")

    state = {
        "updated_at": now_cn(),
        "snapshot": {
            "symbol": snapshot.symbol, "price": snapshot.price,
            "volume_ratio": snapshot.volume_ratio, "trend": snapshot.trend,
            "liquidity_ok": snapshot.liquidity_ok, "source": snapshot.source,
        },
        "indicators": {k: round(v, 4) for k, v in indicators.items()},
        "risk": {
            "consecutive_losses": risk_state.consecutive_losses,
            "drawdown_pct": risk_state.drawdown_pct,
            "trading_halted": risk_state.trading_halted,
            "halt_reasons": list(risk_state.halt_reasons),
        },
        "portfolio": portfolio,
        "events_recent": len(events),
    }
    with STATE_PATH.open("w", encoding="utf-8") as handle:
        json.dump(state, handle, ensure_ascii=False, indent=2)
    log(
        f"轮次完成: {snapshot.symbol} @ {snapshot.price} | trend={snapshot.trend} | "
        f"量比={snapshot.volume_ratio} | 净值={portfolio['equity']} | "
        f"连亏={risk_state.consecutive_losses} | 回撤={risk_state.drawdown_pct}%"
    )
    return state


def main() -> None:
    parser = argparse.ArgumentParser(description="AI自主交易 30 天运行循环")
    parser.add_argument("--interval", type=int, default=15, help="轮询间隔（分钟），默认 15")
    parser.add_argument("--once", action="store_true", help="只跑一轮后退出")
    args = parser.parse_args()

    client = BinanceSpotTestnet()
    prev_state: dict = {}
    if STATE_PATH.exists():
        try:
            prev_state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            prev_state = {}

    def _stop(_sig, _frame):
        log("收到停止信号，优雅退出")
        sys.exit(0)

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    log(f"运行循环启动: 间隔 {args.interval} 分钟 | 测试网执行 + 本地账本主记录")
    while True:
        try:
            prev_state = run_once(client, prev_state)
        except Exception as exc:  # 单轮失败不阻塞循环
            log(f"本轮失败（继续下一轮）: {exc}")
        if args.once:
            break
        time.sleep(args.interval * 60)


if __name__ == "__main__":
    main()

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
from autotrader.strategy import apply_strategies  # noqa: E402
from autotrader.sentiment import assess_sentiment, fetch_funding_rate, save_sentiment  # noqa: E402
from autotrader.event_trader import plan as event_plan  # noqa: E402
from autotrader.news_research import load_events  # noqa: E402

STATE_PATH = ROOT / "artifacts" / "state.json"
EVENTS_PATH = ROOT / "artifacts" / "events.jsonl"
SIGNALS_PATH = ROOT / "artifacts" / "signals.jsonl"
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


def run_agents_work(indicators: dict, prev_state: dict,
                    snapshot=None, risk_state=None, portfolio=None) -> dict:
    """员工主动履职（策略/情绪/事件交易）：平时自动干本职工作，不等待点名。

    返回各岗位最近工作摘要，写入 state.json["agents"] 供 Dashboard 展示。
    """
    agents: dict = {}
    events = load_events(limit=10)
    now = now_cn()

    # —— 数据/技术/市场状态/风险/组合：runner 每轮主动采集与计算 ——
    if snapshot is not None:
        agents["数据工程师"] = {"last_run": now, "status": "ok",
                               "output": f"K线采集落盘 | {snapshot.symbol} @ {snapshot.price}"}
        agents["技术分析员"] = {"last_run": now, "status": "ok",
                               "output": f"RSI {indicators.get('rsi14', 0):.1f} | ATR {indicators.get('atr14', 0):.0f} | 量比 {indicators.get('volume_ratio', 0):.2f}"}
        agents["市场状态官"] = {"last_run": now, "status": "ok",
                               "output": f"状态: {snapshot.trend} | 流动性 {'正常' if snapshot.liquidity_ok else '异常'}"}
    if risk_state is not None:
        agents["风险官"] = {"last_run": now, "status": "ok",
                           "output": f"连亏 {risk_state.consecutive_losses} | 回撤 {risk_state.drawdown_pct}% | {'⚠ 熔断' if risk_state.trading_halted else '正常'}"}
    if portfolio is not None:
        agents["组合经理"] = {"last_run": now, "status": "ok",
                             "output": f"净值 {portfolio['equity']:.2f} | 持仓 {len(portfolio.get('positions', {}))} 个 | 回撤 {portfolio.get('max_drawdown_pct', 0):.1f}%"}

    # —— 运营/执行/报告岗位：持续在岗说明 ——
    agents["审计员"] = {"last_run": now, "status": "ok", "output": "审计与账本持续写入（audit.jsonl / orders.jsonl）"}
    agents["经营报告员"] = {"last_run": now, "status": "ok", "output": "每日 09:00 经营报告（cron 自动）"}
    agents["成本与资源管理员"] = {"last_run": now, "status": "ok", "output": "Token 用量登记与成本监控（record_usage）"}
    agents["API与应急响应官"] = {"last_run": now, "status": "ok", "output": "看门狗每 30 分钟巡检，异常立即告警"}
    agents["执行交易员"] = {"last_run": now, "status": "ok",
                           "output": "测试网适配器就绪（Binance/Hyperliquid），订单经风控后执行"}
    agents["CEO / 总交易代理"] = {"last_run": now, "status": "ok",
                                 "output": "每日 10/22 点研究+决策介入（cron），重大事件立即处理"}

    # —— 策略研究员：主动出信号（应用自适应权重）并落盘 ——
    try:
        from autotrader.strategy_tracker import apply_weights, update_weights
        weights = update_weights()  # 按绩效更新权重（连亏降权/停用）
        signals = [s.to_dict() for s in apply_weights(apply_strategies(indicators, events), weights)]
        with SIGNALS_PATH.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({"time": now, "signals": signals}, ensure_ascii=False) + "\n")
        summary = f"{len(signals)} 个信号"
        if signals:
            top = signals[0]
            summary += f" | 最强: {top['strategy']} {top['action']} @ {top['strength']}"
        disabled = [k for k, v in weights.items() if v <= 0]
        if disabled:
            summary += f" | 已停用: {','.join(disabled)}"
        agents["策略研究员"] = {"last_run": now, "status": "ok", "output": summary}
    except Exception as exc:
        agents["策略研究员"] = {"last_run": now, "status": "error", "output": f"{type(exc).__name__}: {exc}"}

    # —— 情绪与传播研究员：主动更新情绪状态（资金费率 8h 结算，每小时重拉一次）——
    try:
        last_sent = prev_state.get("agents", {}).get("情绪与传播研究员", {}).get("last_run", "")
        should_fetch = True
        if last_sent:
            try:
                from datetime import datetime as _dt
                last_dt = _dt.strptime(last_sent, "%Y-%m-%d %H:%M:%S")
                current_dt = _dt.strptime(now, "%Y-%m-%d %H:%M:%S")
                should_fetch = (current_dt - last_dt).total_seconds() >= 3600
            except ValueError:
                should_fetch = True
        funding = fetch_funding_rate() if should_fetch else {"cached": True}
        ind = {"rsi14": indicators.get("rsi14", 50), "volume_ratio": indicators.get("volume_ratio", 1.0)}
        sentiment = assess_sentiment(ind=ind, funding=funding)
        save_sentiment(sentiment)
        agents["情绪与传播研究员"] = {"last_run": now, "status": "ok",
                                     "output": f"{sentiment.state} (score {sentiment.score})"}
    except Exception as exc:
        agents["情绪与传播研究员"] = {"last_run": now, "status": "error", "output": f"{type(exc).__name__}: {exc}"}

    # —— 事件交易员：主动跟踪活跃事件进展 ——
    try:
        active = [e for e in events if e.get("grade") in ("A", "B")]
        if active:
            plans = [event_plan(e).to_dict() for e in active[-5:]]
            phases = {p["event_id"]: p["phase"] for p in plans}
            agents["事件交易员"] = {"last_run": now, "status": "ok",
                                   "output": f"跟踪 {len(plans)} 个事件 | 阶段: {phases}"}
        else:
            agents["事件交易员"] = {"last_run": now, "status": "idle", "output": "无活跃事件，持续监控"}
    except Exception as exc:
        agents["事件交易员"] = {"last_run": now, "status": "error", "output": f"{type(exc).__name__}: {exc}"}

    # —— 宏观与新闻研究员：由 guardian 按 5 分钟粒度抓取更新，这里汇总最新状态 ——
    try:
        from autotrader.news_research import load_events as _load_ev
        recent_news = [e for e in _load_ev(50) if e.get("source", "").startswith("rss")]
        a_grade = sum(1 for e in recent_news if e["grade"] == "A")
        b_grade = sum(1 for e in recent_news if e["grade"] == "B")
        agents["宏观与新闻研究员"] = {"last_run": now, "status": "ok",
            "output": f"事件库 {len(recent_news)} 条新闻事件 (A级 {a_grade} / B级 {b_grade})，5分钟粒度抓取"}
    except Exception as exc:
        agents["宏观与新闻研究员"] = {"last_run": now, "status": "error", "output": f"{type(exc).__name__}: {exc}"}

    # —— 链上数据分析员：由 guardian 15 分钟粒度更新，这里读最新信号 ——
    try:
        from autotrader.onchain import load_signals
        signals = load_signals(limit=10)
        latest = signals[-1] if signals else None
        detail = latest.get("detail", "") if latest else "暂无信号"
        agents["链上数据分析员"] = {"last_run": now, "status": "ok",
            "output": f"链上信号库 {len(signals)} 条 | 最新: {detail}"}
        agents["聪明钱包研究员"] = agents["链上数据分析员"]
    except Exception as exc:
        agents["链上数据分析员"] = {"last_run": now, "status": "error", "output": f"{type(exc).__name__}: {exc}"}
    return agents


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

    # 多标的主动机会扫描（策略研究员 · 机会扫描；失败不影响主循环）
    opportunities = {}
    try:
        from autotrader.opportunities import save_opportunities, scan_opportunities
        opportunities = scan_opportunities(client)
        save_opportunities(opportunities)
        if opportunities.get("opportunities"):
            log(f"🎯 机会扫描: {len(opportunities['opportunities'])} 个机会 "
                f"({', '.join(o['symbol'] for o in opportunities['opportunities'][:3])})")
    except Exception as exc:
        log(f"⚠️ 机会扫描失败: {exc}")

    state = {
        "updated_at": now_cn(),
        "opportunities": opportunities,
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
        "agents": run_agents_work(indicators, prev_state, snapshot, risk_state, portfolio),
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

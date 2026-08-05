#!/usr/bin/env python3
"""AI自主交易事业部 · 高频守护进程（分层调度器）。

按信息时效性分层运行（董事长要求：不能千篇一律，关键信息分秒必争）：

- L0 实时守护：价格异常检测（每 1 分钟，Binance ticker 免费接口）
- L1 高频情报：新闻抓取（每 5 分钟，RSS 免费）
- L1 常规：链上检测（每 15 分钟，mempool/blockchain.info 免费）
- L2 情绪：情绪状态更新（每 60 分钟，资金费率 8h 结算无需高频）

全部确定性计算，零 Token。异常 → events.jsonl + alert_pending.json（看门狗转发告警）。
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

EVENTS_PATH = ROOT / "artifacts" / "events.jsonl"
ALERT_PENDING = ROOT / "artifacts" / "alert_pending.json"

# ---- L0 价格异常阈值（5 秒粒度）----
PRICE_SPIKE_PCT = 0.15    # 5 秒波动 ≥0.15% → 事件（BTC；≈1.8%/分钟）
PRICE_SPIKE_ALT = 0.2     # 其他标的 0.2%（alt 波动大）
PRICE_SYMBOL = "BTCUSDT"

# ---- 分层频率（秒）----
TICK = 5                       # 基础 tick：价格 5 秒一次（REST 轮询极限内最密）
NEWS_EVERY = 60                # 新闻 5 分钟（60 tick）
ONCHAIN_EVERY = 180            # 链上 15 分钟（180 tick）
MOVERS_EVERY = 180             # 鱼群 15 分钟
SENTIMENT_EVERY = 720          # 情绪 60 分钟（720 tick）
MACRO_EVERY = 720              # 宏观 60 分钟

_last_price: float | None = None
_last_prices: dict[str, float] = {}


def now_cn() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def log(msg: str) -> None:
    print(f"[{now_cn()}] {msg}", flush=True)


def write_event(event: dict) -> None:
    with EVENTS_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")


def raise_alert(level: str, summary: str) -> None:
    """写行动级告警标记（看门狗巡检时转发 Telegram）。"""
    ALERT_PENDING.write_text(json.dumps(
        {"generated_at": now_cn(), "level": level, "summary": summary},
        ensure_ascii=False), encoding="utf-8")


def check_price() -> None:
    """L0：1 分钟粒度多标的实时价格（突发暴涨/暴跌分秒必争）。

    18 标的价格快照写 live_prices.json（Dashboard 实时看板数据源）；
    每个标的检测 1 分钟异常：BTC 阈值 1%，其他标的 1.5%（alt 波动大）。
    """
    global _last_price
    try:
        from autotrader.live_prices import scan_live_prices
        data = scan_live_prices()
        prices = data.get("prices") or {}
    except Exception as exc:
        log(f"⚠️ 价格获取失败: {exc}")
        return
    if not prices:
        return

    for symbol, row in prices.items():
        try:
            price = float(row["price"])
        except (TypeError, ValueError):
            continue
        threshold = PRICE_SPIKE_PCT if symbol == "BTCUSDT" else PRICE_SPIKE_ALT
        prev = _last_prices.get(symbol)
        if prev is not None:
            change = (price - prev) / prev * 100
            if abs(change) >= threshold:
                direction = "暴涨" if change > 0 else "暴跌"
                event = {
                    "type": "price_spike",
                    "level": "L2" if abs(change) < 3 else "L3",
                    "detail": f"5秒内 {symbol} {direction} {change:+.2f}% ({prev:.4g} → {price:.4g})",
                    "symbol": symbol,
                    "at": now_cn(),
                }
                write_event(event)
                log(f"⚠️ {event['detail']}")
                if abs(change) >= 2.0:
                    raise_alert("action", f"{symbol} 1分钟{direction} {change:+.2f}%！{event['detail']}")
        _last_prices[symbol] = price


def scan_news_every_5m() -> None:
    """L1：新闻抓取（5 分钟粒度，重大新闻不漏）。"""
    try:
        from autotrader.news_research import scan_news
        news = scan_news()
        if news["recorded"]:
            log(f"📰 新闻: 抓 {news['fetched']} 条 | 新增 {news['recorded']} 事件 (A{news['a_grade']}/B{news['b_grade']})")
            if news["a_grade"]:
                # 告警自带内容：A级新闻标题直接进 summary，董事长收到即看到
                titles = "；".join(news.get("a_titles", [])[:3])
                raise_alert("action", f"新增 {news['a_grade']} 条 A级新闻：{titles}")
    except Exception as exc:
        log(f"⚠️ 新闻抓取失败: {exc}")


def scan_onchain_every_15m() -> None:
    """L1：链上检测（15 分钟粒度）。"""
    try:
        from autotrader.onchain import scan_btc_onchain
        chain = scan_btc_onchain()
        parts = []
        if chain.get("congestion_fee_sat_vb"):
            parts.append(f"拥堵 {chain['congestion_fee_sat_vb']} sats/vB")
        if chain.get("whale_txns"):
            parts.append(f"巨鲸异动 {chain['whale_txns']} 笔")
        log(f"⛓ 链上: {' | '.join(parts) if parts else '网络正常'} | 新信号 {chain['signals_recorded']}")
    except Exception as exc:
        log(f"⚠️ 链上检测失败: {exc}")


def scan_macro_every_60m() -> None:
    """L2：宏观数据采集（恐惧贪婪/全球市值/DVOL/稳定币，60 分钟粒度）。"""
    try:
        from autotrader.macro_data import scan_macro
        m = scan_macro()
        parts = []
        if m.get("fng"):
            parts.append(f"恐惧贪婪 {m['fng']['value']}({m['fng']['label']})")
        if m.get("dvol_btc"):
            parts.append(f"BTC DVOL {m['dvol_btc']['dvol']}")
        if m.get("stablecoins"):
            parts.append(f"稳定币 ${m['stablecoins']['pegged_usd_total']/1e9:.0f}B")
        log("🌐 宏观: " + (" | ".join(parts) if parts else "数据源不可用"))
    except Exception as exc:
        log(f"⚠️ 宏观采集失败: {exc}")


def scan_movers_every_15m() -> None:
    """L1：全市场鱼群扫描（异动标的 + 热点板块，15 分钟粒度）。"""
    try:
        from autotrader.binance import BinanceAdapter
        from autotrader.movers import scan_movers
        client = BinanceAdapter(mode="testnet")
        movers = scan_movers(client, top_n=8, min_volume_usdt=100)
        if "error" in movers:
            log(f"🎣 鱼群扫描失败: {movers['error']}")
            return
        top = movers["gainers"][0]
        hot = movers["hot_sectors"][0] if movers["hot_sectors"] else None
        msg = f"🎣 鱼群: 扫描 {movers['scanned']} 标的 | 领涨 {top['symbol']} {top['change_24h_pct']:+.1f}%"
        if hot:
            msg += f" | 热点板块 {hot['sector']} {hot['avg_change_24h_pct']:+.1f}%"
        log(msg)
    except Exception as exc:
        log(f"⚠️ 鱼群扫描失败: {exc}")


def update_sentiment_every_60m() -> None:
    """L2：情绪状态（60 分钟粒度，资金费率 8h 结算）。"""
    try:
        from autotrader.sentiment import assess_sentiment, fetch_funding_rate, save_sentiment
        funding = fetch_funding_rate()
        state = assess_sentiment(funding=funding)
        save_sentiment(state)
        log(f"🧭 情绪: {state.state} (score {state.score})")
    except Exception as exc:
        log(f"⚠️ 情绪更新失败: {exc}")


def main() -> None:
    log("高频守护进程启动（分层调度: 价格5s / 新闻5m / 链上15m / 情绪60m）")
    tick = 0
    while True:
        try:
            check_price()  # L0 每 tick（1 分钟）
            if tick % NEWS_EVERY == 0:
                scan_news_every_5m()
            if tick % ONCHAIN_EVERY == 0:
                scan_onchain_every_15m()
            if tick % MOVERS_EVERY == 0:
                scan_movers_every_15m()
            if tick % SENTIMENT_EVERY == 0:
                update_sentiment_every_60m()
            if tick % MACRO_EVERY == 0:
                scan_macro_every_60m()
            tick += 1
            time.sleep(TICK)
        except KeyboardInterrupt:
            log("守护进程停止")
            break
        except Exception as exc:
            log(f"⚠️ 守护循环异常: {exc}（继续运行）")
            time.sleep(TICK)


if __name__ == "__main__":
    main()

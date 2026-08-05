"""市场状态分类器与历史行情落盘（数据工程师/技术分析员/市场状态官落地）。

职责：
- 从 Binance Spot Testnet 拉取 K 线并计算技术指标（EMA/RSI/ATR/量比）；
- 根据指标自动分类市场状态，生成 ``MarketSnapshot``（trend / volume_ratio /
  liquidity_ok 不再靠人工填写）；
- 历史 K 线落盘 SQLite（stdlib sqlite3，零第三方依赖），作为回测与
  复盘的数据基础（“全量保存、分层计算、按事件调用AI”原则的本地层）。

所有计算均为确定性本地计算，不调用模型、不产生 Token 成本。
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .binance_testnet import BinanceSpotTestnet
from .models import MarketSnapshot

DB_PATH = Path(__file__).resolve().parents[2] / "artifacts" / "market.db"
DEFAULT_SYMBOL = "BTCUSDT"
DEFAULT_INTERVAL = "15m"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def init_db(db_path: Path = DB_PATH) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS klines (
                symbol TEXT NOT NULL,
                interval TEXT NOT NULL,
                open_time INTEGER NOT NULL,
                open REAL, high REAL, low REAL, close REAL,
                volume REAL, quote_volume REAL, trades INTEGER,
                PRIMARY KEY (symbol, interval, open_time)
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_klines_time ON klines(symbol, interval, open_time)")


def store_klines(
    klines: list[dict[str, Any]],
    symbol: str = DEFAULT_SYMBOL,
    interval: str = DEFAULT_INTERVAL,
    db_path: Path = DB_PATH,
) -> int:
    """Persist klines; returns number of rows written."""
    klines = normalize_klines(klines)
    init_db(db_path)
    rows = [
        (
            symbol, interval,
            int(k["open_time"]), float(k["open"]), float(k["high"]),
            float(k["low"]), float(k["close"]), float(k["volume"]),
            float(k["quote_volume"]), int(k["trades"]),
        )
        for k in klines
    ]
    with sqlite3.connect(db_path) as conn:
        conn.executemany(
            "INSERT OR REPLACE INTO klines VALUES (?,?,?,?,?,?,?,?,?,?)",
            rows,
        )
    return len(rows)


def load_klines(
    symbol: str = DEFAULT_SYMBOL,
    interval: str = DEFAULT_INTERVAL,
    limit: int = 500,
    db_path: Path = DB_PATH,
) -> list[dict[str, Any]]:
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM klines WHERE symbol=? AND interval=? ORDER BY open_time DESC LIMIT ?",
            (symbol, interval, limit),
        ).fetchall()
    return [dict(row) for row in reversed(rows)]


def ema(values: list[float], period: int) -> float:
    """Simple EMA over the given values (seeded with SMA of first `period`)."""
    if not values:
        return 0.0
    if len(values) < period:
        period = len(values)
    alpha = 2.0 / (period + 1)
    result = sum(values[:period]) / period
    for v in values[period:]:
        result = alpha * v + (1 - alpha) * result
    return result


def rsi(closes: list[float], period: int = 14) -> float:
    if len(closes) < 2:
        return 50.0
    window = min(period, len(closes) - 1)
    gains, losses = 0.0, 0.0
    for i in range(len(closes) - window, len(closes)):
        delta = closes[i] - closes[i - 1]
        if delta >= 0:
            gains += delta
        else:
            losses -= delta
    if losses == 0:
        return 100.0 if gains > 0 else 50.0
    rs = (gains / window) / (losses / window)
    return 100.0 - 100.0 / (1.0 + rs)


def atr(klines: list[dict[str, Any]], period: int = 14) -> float:
    if len(klines) < 2:
        return 0.0
    trs: list[float] = []
    for i in range(1, len(klines)):
        high, low, prev_close = float(klines[i]["high"]), float(klines[i]["low"]), float(klines[i - 1]["close"])
        trs.append(max(high - low, abs(high - prev_close), abs(low - prev_close)))
    window = trs[-period:]
    return sum(window) / len(window)


def normalize_klines(klines: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """K 线字段归一化：兼容 Binance（open_time/open/high/low/close/volume/quote_volume/trades）
    与 Hyperliquid（t/o/h/l/c/v/n/q）两种交易所返回格式。

    统一输出：open_time/open/high/low/close/volume/quote_volume/trades。
    """
    if not klines:
        return klines
    first = klines[0]
    if "close" in first:
        return klines  # 已是标准格式
    norm = []
    for k in klines:
        norm.append({
            "open_time": k.get("t", k.get("open_time", 0)),
            "open": k.get("o", k.get("open", 0)),
            "high": k.get("h", k.get("high", 0)),
            "low": k.get("l", k.get("low", 0)),
            "close": k.get("c", k.get("close", 0)),
            "volume": k.get("v", k.get("volume", 0)),
            "quote_volume": k.get("q", k.get("quote_volume", 0)),
            "trades": k.get("n", k.get("trades", 0)),
        })
    return norm


def compute_indicators(klines: list[dict[str, Any]]) -> dict[str, float]:
    klines = normalize_klines(klines)
    closes = [float(k["close"]) for k in klines]
    volumes = [float(k["volume"]) for k in klines]
    price = closes[-1] if closes else 0.0
    ema20 = ema(closes, 20)
    ema50 = ema(closes, 50) if len(closes) >= 10 else ema20
    # 量比 = 最新量 / 前 N-1 根均量（不含最新，避免自比）
    prior = volumes[:-1]
    avg_volume = sum(prior) / len(prior) if prior else 0.0
    return {
        "price": price,
        "ema20": ema20,
        "ema50": ema50,
        "rsi14": rsi(closes),
        "atr14": atr(klines),
        "volume_ratio": (volumes[-1] / avg_volume) if avg_volume else 1.0,
        # 24 周期变化（最近 24 根 K 线；1h 周期即 24h，4h 周期即 96h——语义为"近24周期"）
        "change_24h_pct": ((closes[-1] / closes[-24]) - 1) * 100 if len(closes) > 24 else 0.0,
        "high_24h": max(float(k["high"]) for k in klines) if klines else 0.0,
        "low_24h": min(float(k["low"]) for k in klines) if klines else 0.0,
    }


def classify_market(ind: dict[str, float]) -> str:
    """Classify market state: trend_up / trend_down / sideways."""
    price, ema20, ema50 = ind["price"], ind["ema20"], ind["ema50"]
    if price > ema20 > ema50 and ind["rsi14"] > 50:
        return "trend_up"
    if price < ema20 < ema50 and ind["rsi14"] < 50:
        return "trend_down"
    return "sideways"


def build_snapshot(
    client: BinanceSpotTestnet,
    symbol: str = "BTCUSDT",
    interval: str = DEFAULT_INTERVAL,
    kline_limit: int = 60,
    db_path: Path = DB_PATH,
) -> MarketSnapshot:
    """Fetch live klines, classify market state and persist history.

    Returns a fully-populated MarketSnapshot (source=binance_testnet).
    """
    klines = client.klines(symbol, interval, kline_limit)
    if not klines:
        raise RuntimeError(f"no klines returned for {symbol}")
    store_klines(klines, symbol=symbol, interval=interval, db_path=db_path)

    ind = compute_indicators(klines)
    trend = classify_market(ind)
    volume_ratio = round(ind["volume_ratio"], 2)
    # 流动性判断：量比过低或 ATR 占比过高视为不健康
    liquidity_ok = volume_ratio >= 0.3 and (ind["atr14"] / ind["price"]) < 0.05

    return MarketSnapshot(
        symbol=symbol.replace("USDT", "/USDT"),
        price=round(ind["price"], 2),
        volume_ratio=volume_ratio,
        trend=trend,
        liquidity_ok=liquidity_ok,
        source="binance_testnet",
    )

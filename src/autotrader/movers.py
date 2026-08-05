"""全市场鱼群探测器（板块轮动研究员 + 资金流研究员 · 数据管线）。

董事长战略："蓝海撒网"——查看水域（全市场扫描）、发现鱼群（异动标的/热点板块）、
撒网（策略覆盖）。本模块免费确定性扫描（零 Token）：

- ``scan_movers``：全市场 24h 涨跌幅榜 → 异动标的（暴涨/暴跌 Top N）
- ``detect_sectors``：按板块映射聚合 → 热点板块识别（哪个板块在启动）
- ``sector_map``：标的 → 板块映射表（可扩展）

落盘 artifacts/movers.json（供机会榜/模型分析/Dashboard 使用）。
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
MOVERS_PATH = ROOT / "artifacts" / "movers.json"

# 标的 → 板块映射（按关键词，可扩展）
SECTOR_MAP: dict[str, list[str]] = {
    "AI": ["FET", "RNDR", "AGIX", "OCEAN", "TAO", "WLD", "GRT", "LPT", "AKT", "AR"],
    "DeFi": ["UNI", "AAVE", "COMP", "MKR", "LINK", "CRV", "SUSHI", "CAKE", "SNX", "1INCH"],
    "L2": ["ARB", "OP", "MATIC", "IMX", "MAGIC", "STRK", "ZK", "BASE"],
    "Meme": ["DOGE", "SHIB", "PEPE", "WIF", "BONK", "FLOKI", "MEME", "DGB"],
    "公链": ["ETH", "SOL", "ADA", "AVAX", "DOT", "ATOM", "NEAR", "APT", "SUI", "TON"],
    "存储": ["FIL", "AR", "BLZ", "STORJ", "SC", "RLC"],
    "GameFi": ["AXS", "SAND", "MANA", "GALA", "ENJ", "ILV"],
    "支付": ["XRP", "XLM", "ALGO", "HBAR", "TRX", "DASH"],
    "预言机": ["LINK", "BAND", "API3", "PYTH", "TRB"],
    "交易所币": ["BNB", "OKB", "LEO", "CRO", "GT"],
}

# 未映射板块的标的 → "其他"


def _fetch_ticker_24h(client) -> list[dict[str, Any]]:
    """抓取全市场 24h 行情（免费接口）。"""
    return client.ticker_24hr()


def _sector_of(symbol: str) -> str:
    base = symbol.replace("USDT", "").replace("BTC", "")
    for sector, tokens in SECTOR_MAP.items():
        if base in tokens:
            return sector
    return "其他"


def scan_movers(client, top_n: int = 10, min_volume_usdt: float = 0.0) -> dict[str, Any]:
    """扫描全市场：24h 涨跌幅异动榜 + 板块热点。

    min_volume_usdt：过滤无交易量的标的（测试网流动性过滤，实盘可设 1_000_000）。
    """
    try:
        tickers = _fetch_ticker_24h(client)
    except Exception as exc:
        # 失败也落盘（保证 movers.json 永续存在，分析任务可读最新状态）
        result: dict[str, Any] = {
            "error": str(exc),
            "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "scanned": 0, "gainers": [], "losers": [], "hot_sectors": [], "cold_sectors": [],
        }
        MOVERS_PATH.parent.mkdir(parents=True, exist_ok=True)
        MOVERS_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
        return result

    rows: list[dict[str, Any]] = []
    for t in tickers:
        symbol = t.get("symbol", "")
        if not symbol.endswith("USDT") or "UP" in symbol or "DOWN" in symbol:
            continue
        try:
            change = float(t.get("priceChangePercent", 0) or 0)
            volume = float(t.get("quoteVolume", 0) or 0)
            price = float(t.get("lastPrice", 0) or 0)
        except (TypeError, ValueError):
            continue
        if volume < min_volume_usdt:
            continue
        rows.append({
            "symbol": symbol,
            "change_24h_pct": round(change, 2),
            "volume_24h_usdt": round(volume, 0),
            "price": price,
            "sector": _sector_of(symbol),
        })

    if not rows:
        return {"error": "no data", "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")}

    rows.sort(key=lambda r: r["change_24h_pct"], reverse=True)
    gainers = rows[:top_n]
    losers = rows[-top_n:][::-1]

    # 板块聚合（平均涨幅 + 上涨家数占比）
    sector_agg: dict[str, dict[str, Any]] = {}
    for r in rows:
        s = r["sector"]
        agg = sector_agg.setdefault(s, {"count": 0, "sum_change": 0.0, "up_count": 0})
        agg["count"] += 1
        agg["sum_change"] += r["change_24h_pct"]
        if r["change_24h_pct"] > 0:
            agg["up_count"] += 1
    sectors = [
        {
            "sector": s,
            "avg_change_24h_pct": round(agg["sum_change"] / agg["count"], 2),
            "up_ratio": round(agg["up_count"] / agg["count"], 2),
            "count": agg["count"],
        }
        for s, agg in sector_agg.items()
        if agg["count"] >= 2
    ]
    sectors.sort(key=lambda s: s["avg_change_24h_pct"], reverse=True)

    result = {
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "scanned": len(rows),
        "gainers": gainers,
        "losers": losers,
        "hot_sectors": sectors[:6],
        "cold_sectors": sectors[-3:],
    }
    MOVERS_PATH.parent.mkdir(parents=True, exist_ok=True)
    MOVERS_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    return result


def load_movers() -> dict[str, Any]:
    if not MOVERS_PATH.exists():
        return {}
    try:
        return json.loads(MOVERS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

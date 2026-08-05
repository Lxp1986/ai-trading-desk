"""实时价格看板数据（CEO 观察池，双数据源）。

董事长要求：看板要有实时价格（数字货币等所有计划交易的品种）。
本模块提供 1 分钟粒度的多标的价格快照：

- 主源：Binance 测试网 ticker（与模拟盘成交一致）；
- 兜底：CoinGecko 免费行情（真实市场价，测试网 502 时自动切换）；
- 落盘：artifacts/live_prices.json（成功失败都写状态，永续存在规范）。

观察池为 CEO 精选：主流 + 计划交易标的（可交易、有流动性、涵盖板块代表）。
"""

from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
LIVE_PRICES = ROOT / "artifacts" / "live_prices.json"

# CEO 精选观察池：Binance 测试网交易对 + CoinGecko id + 中文名
WATCHLIST: list[dict[str, str]] = [
    {"symbol": "BTCUSDT", "cg_id": "bitcoin", "name": "比特币"},
    {"symbol": "ETHUSDT", "cg_id": "ethereum", "name": "以太坊"},
    {"symbol": "BNBUSDT", "cg_id": "binancecoin", "name": "BNB"},
    {"symbol": "SOLUSDT", "cg_id": "solana", "name": "索拉纳"},
    {"symbol": "XRPUSDT", "cg_id": "xrp", "name": "瑞波"},
    {"symbol": "DOGEUSDT", "cg_id": "dogecoin", "name": "狗狗币"},
    {"symbol": "ADAUSDT", "cg_id": "cardano", "name": "艾达"},
    {"symbol": "AVAXUSDT", "cg_id": "avalanche-2", "name": "雪崩"},
    {"symbol": "LINKUSDT", "cg_id": "chainlink", "name": "链环"},
    {"symbol": "NEOUSDT", "cg_id": "neo", "name": "小蚁"},
    {"symbol": "LTCUSDT", "cg_id": "litecoin", "name": "莱特币"},
    {"symbol": "DOTUSDT", "cg_id": "polkadot", "name": "波卡"},
    {"symbol": "ATOMUSDT", "cg_id": "cosmos", "name": "宇宙"},
    {"symbol": "UNIUSDT", "cg_id": "uniswap", "name": "独角兽"},
    {"symbol": "TRXUSDT", "cg_id": "tron", "name": "波场"},
    {"symbol": "FILUSDT", "cg_id": "filecoin", "name": "文件币"},
    {"symbol": "ETCUSDT", "cg_id": "ethereum-classic", "name": "以太经典"},
    {"symbol": "XLMUSDT", "cg_id": "stellar", "name": "恒星"},
]


def _get_json(url: str, max_bytes: int = 1_000_000, timeout: float = 10) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read(max_bytes + 1).decode("utf-8"))


def _fetch_testnet() -> dict[str, dict[str, Any]] | None:
    """Binance 测试网单标的 ticker 循环（与模拟盘成交一致）。"""
    try:
        from autotrader.binance import BinanceAdapter
        client = BinanceAdapter(mode="testnet")
        rows: dict[str, dict[str, Any]] = {}
        for item in WATCHLIST:
            try:
                t = client.ticker_price(item["symbol"])
                price = float(t["price"])
                if price <= 0:
                    continue
                rows[item["symbol"]] = {
                    "price": price, "change_24h": None, "volume_24h": None, "name": item["name"],
                }
            except Exception:
                continue  # 单标的失败跳过（测试网常态 502）
        return rows or None
    except Exception:
        return None


def _fetch_coingecko() -> dict[str, dict[str, Any]] | None:
    """CoinGecko 免费真实行情（测试网不可用时的兜底）。"""
    try:
        ids = ",".join(item["cg_id"] for item in WATCHLIST)
        url = ("https://api.coingecko.com/api/v3/simple/price"
               f"?ids={ids}&vs_currencies=usd&include_24hr_change=true&include_24hr_vol=true")
        data = _get_json(url)
        rows: dict[str, dict[str, Any]] = {}
        for item in WATCHLIST:
            d = data.get(item["cg_id"]) or {}
            price = d.get("usd")
            if not price or price <= 0:
                continue
            rows[item["symbol"]] = {
                "price": float(price),
                "change_24h": d.get("usd_24h_change"),
                "volume_24h": d.get("usd_24h_vol"),
                "name": item["name"],
            }
        return rows or None
    except Exception:
        return None


def _fetch_hyperliquid() -> dict[str, dict[str, Any]] | None:
    """Hyperliquid 测试网行情（第二交易所源，实盘后自动切 Hyperliquid 实盘）。

    allMids 一次请求返回全部交易对价格（2548 标的，约 0.4s），
    本地解析观察池——比逐标的 ticker_price 快 18 倍，可支撑 10 秒级轮询。
    """
    try:
        from autotrader.hyperliquid import HyperliquidAdapter
        client = HyperliquidAdapter(mode="testnet")
        mids = client._info({"type": "allMids"})
        if not isinstance(mids, dict):
            return None
        rows: dict[str, dict[str, Any]] = {}
        for item in WATCHLIST:
            # HL 交易对符号无 USDT 后缀（BTC 而非 BTCUSDT）
            hl_symbol = item["symbol"].replace("USDT", "")
            raw = mids.get(hl_symbol)
            if raw is None:
                continue
            try:
                price = float(raw)
            except (TypeError, ValueError):
                continue
            if price <= 0:
                continue
            rows[item["symbol"]] = {
                "price": price, "change_24h": None, "volume_24h": None, "name": item["name"],
            }
        return rows or None
    except Exception:
        return None


# 24h 统计缓存（CoinGecko 有速率限制：5 分钟刷新一次，价格 10 秒级不受影响）
_stats_cache: dict[str, Any] = {"at": 0.0, "data": None}


def _fetch_24h_stats() -> dict[str, dict[str, Any]]:
    """24h 涨跌/成交额（CoinGecko，价格源不提供时的补充统计，5 分钟缓存）。"""
    global _stats_cache
    now = time.time()
    if _stats_cache["data"] is not None and now - _stats_cache["at"] < 300:
        return _stats_cache["data"]
    try:
        ids = ",".join(item["cg_id"] for item in WATCHLIST)
        url = ("https://api.coingecko.com/api/v3/simple/price"
               f"?ids={ids}&vs_currencies=usd&include_24hr_change=true&include_24hr_vol=true")
        data = _get_json(url)
        stats: dict[str, dict[str, Any]] = {}
        for item in WATCHLIST:
            d = data.get(item["cg_id"]) or {}
            stats[item["symbol"]] = {
                "change_24h": d.get("usd_24h_change"),
                "volume_24h": d.get("usd_24h_vol"),
            }
        _stats_cache = {"at": now, "data": stats}
        return stats
    except Exception:
        return _stats_cache["data"] or {}


def scan_live_prices() -> dict[str, Any]:
    """实时价格扫描（10 秒粒度，多交易所）：币安测试网 → Hyperliquid 测试网 → CoinGecko 兜底。

    每条价格带 exchange 字段（多交易所区分，实盘后自动切实盘源）；
    24h 涨跌/成交额由 CoinGecko 补充合并（价格源不提供时，5 分钟缓存）。
    返回 {"prices": {SYMBOL: {..., "exchange": "..."}}, "source": "...", "updated_at": "..."}
    """
    for fetcher, exchange in ((_fetch_testnet, "binance_testnet"),
                              (_fetch_hyperliquid, "hyperliquid_testnet"),
                              (_fetch_coingecko, "coingecko")):
        rows = fetcher()
        if rows:
            for row in rows.values():
                row["exchange"] = exchange
            # 24h 统计补充（不覆盖价格与交易所来源）
            stats = _fetch_24h_stats()
            for sym, row in rows.items():
                if row.get("change_24h") is None and sym in stats:
                    row["change_24h"] = stats[sym].get("change_24h")
                    row["volume_24h"] = stats[sym].get("volume_24h")
            result = {"prices": rows, "source": exchange, "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")}
            break
    else:
        result = {"prices": {}, "source": "unavailable", "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"), "error": "三源均不可用"}
    LIVE_PRICES.parent.mkdir(parents=True, exist_ok=True)
    LIVE_PRICES.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    return result


def load_live_prices() -> dict[str, Any]:
    """读取最近一次实时价格快照（Dashboard/分析用，永续存在）。"""
    if not LIVE_PRICES.exists():
        return {"prices": {}, "source": "none", "updated_at": None}
    try:
        return json.loads(LIVE_PRICES.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"prices": {}, "source": "corrupt", "updated_at": None}

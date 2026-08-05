"""宏观与市场数据采集（数据工程师扩展 · 免费确定性）。

董事长指令："没有API就去找API或通过网络查询增加数据量"。
本模块聚合多个免费公开数据源（零 Token），供情绪/宏观研究、模型分析使用：

- ``fetch_fng``：恐惧贪婪指数（alternative.me）
- ``fetch_global_metrics``：全球加密市值/24h量/市值占比（CoinGecko）
- ``fetch_deribit_dvol``：BTC/ETH 期权波动率指数 DVOL（Deribit）
- ``fetch_stablecoins``：稳定币总市值/交易量（DefiLlama）
- ``scan_macro``：汇总全部 → artifacts/macro.json

guardian 每 60 分钟调用 scan_macro（情绪 8h 结算级频率，60 分钟足够）。
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
MACRO_PATH = ROOT / "artifacts" / "macro.json"

FNG_URL = "https://api.alternative.me/fng/?limit=3"
COINGECKO_GLOBAL_URL = "https://api.coingecko.com/api/v3/global"
DERIBIT_DVOL_URL = ("https://www.deribit.com/api/v2/public/get_volatility_index_data"
                    "?currency={currency}&start_timestamp=0&end_timestamp=9999999999999&resolution=3600")
STABLECOINS_URL = "https://stablecoins.llama.fi/stablecoins?includePrices=true"


def _get_json(url: str, timeout: int = 12, max_bytes: int = 2_000_000) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (autotrader-research)"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read(max_bytes))


def fetch_fng() -> dict[str, Any] | None:
    """恐惧贪婪指数（0-100，0=极度恐惧 100=极度贪婪）。"""
    try:
        data = _get_json(FNG_URL)
        row = data["data"][0]
        return {"value": int(row["value"]), "label": row["value_classification"]}
    except (urllib.error.URLError, OSError, KeyError, ValueError):
        return None


def fetch_global_metrics() -> dict[str, Any] | None:
    """全球加密市场：总市值/24h 成交量/主导币占比。"""
    try:
        data = _get_json(COINGECKO_GLOBAL_URL)["data"]
        return {
            "total_mcap_usd": data["total_market_cap"]["usd"],
            "total_volume_usd": data["total_volume"]["usd"],
            "btc_dominance_pct": data["market_cap_percentage"]["btc"],
            "eth_dominance_pct": data["market_cap_percentage"]["eth"],
        }
    except (urllib.error.URLError, OSError, KeyError, ValueError):
        return None


def fetch_deribit_dvol(currency: str = "BTC") -> dict[str, Any] | None:
    """Deribit 期权波动率指数 DVOL（市场对 30 天波动率的预期）。"""
    try:
        data = _get_json(DERIBIT_DVOL_URL.format(currency=currency))
        rows = data["result"]["data"]
        if not rows:
            return None
        return {"currency": currency, "dvol": round(float(rows[-1][1]), 2)}
    except (urllib.error.URLError, OSError, KeyError, ValueError, IndexError):
        return None


def fetch_stablecoins() -> dict[str, Any] | None:
    """稳定币总市值/龙头占比（DefiLlama peggedAssets，场外资金面）。"""
    try:
        data = _get_json(STABLECOINS_URL, max_bytes=15_000_000)
        assets = data.get("peggedAssets", [])
        total = 0.0
        top: dict[str, float] = {}
        for a in assets:
            circ = (a.get("circulating") or {}).get("peggedUSD", 0) or 0
            total += circ
            sym = a.get("symbol", "?")
            top[sym] = circ
        usdt = top.get("USDT", 0)
        usdc = top.get("USDC", 0)
        return {
            "pegged_usd_total": round(total, 0),
            "usdt_usd": round(usdt, 0),
            "usdc_usd": round(usdc, 0),
            "usdt_share_pct": round(usdt / total * 100, 1) if total else 0.0,
            "assets_count": len(assets),
        }
    except (urllib.error.URLError, OSError, KeyError, ValueError):
        return None


def scan_macro() -> dict[str, Any]:
    """采集全部宏观数据 → 落盘 macro.json。单个源失败不影响整体。"""
    result: dict[str, Any] = {
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "fng": fetch_fng(),
        "global": fetch_global_metrics(),
        "dvol_btc": fetch_deribit_dvol("BTC"),
        "dvol_eth": fetch_deribit_dvol("ETH"),
        "stablecoins": fetch_stablecoins(),
    }
    MACRO_PATH.parent.mkdir(parents=True, exist_ok=True)
    MACRO_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    return result


def load_macro() -> dict[str, Any]:
    if not MACRO_PATH.exists():
        return {}
    try:
        return json.loads(MACRO_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

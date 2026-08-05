"""情绪与传播研究员（落地：资金费率/多空结构，确定性计算）。

数据源（公开接口，纯标准库）：
- Binance 资金费率/指数（premiumIndex）— 合约市场多空倾向；
- 波动率（ATR/价格）与量比 — 交易热度代理；
- 社媒热度由 CEO（Hermes）联网采集后经 ``record_heat`` 记录。

输出：情绪状态（fomo / greedy / neutral / fear / panic）+ 证据。
"""
from __future__ import annotations

import json
import time
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

SENTIMENT_PATH = Path(__file__).resolve().parents[2] / "artifacts" / "sentiment.json"


@dataclass
class SentimentState:
    state: str                       # fomo/greedy/neutral/fear/panic
    funding_annual_pct: float | None = None   # 年化资金费率
    score: float = 0.0               # -1(极度恐慌) ~ +1(极度贪婪)
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def fetch_funding_rate(symbol: str = "BTCUSDT",
                       base_url: str = "https://fapi.binance.com") -> dict[str, Any]:
    """拉取币安永续资金费率（公开接口）。测试网无资金费率，实盘/公开接口有。"""
    url = f"{base_url}/fapi/v1/premiumIndex?symbol={symbol}"
    try:
        with urllib.request.urlopen(url, timeout=8) as response:
            data = json.loads(response.read().decode("utf-8"))
        mark_price = float(data.get("markPrice", 0))
        index_price = float(data.get("indexPrice", 0))
        funding = float(data.get("lastFundingRate", 0))
        annual = funding * 3 * 365 * 100  # 每8小时结算，年化
        return {"mark_price": mark_price, "index_price": index_price,
                "funding_rate": funding, "funding_annual_pct": annual}
    except Exception as exc:  # 网络/不可达
        return {"error": str(exc)}


def assess_sentiment(ind: dict[str, float] | None = None,
                     funding: dict[str, Any] | None = None,
                     social_heat: float | None = None) -> SentimentState:
    """综合判断市场情绪。ind 来自 market.compute_indicators。"""
    score = 0.0
    evidence: dict[str, Any] = {}

    if funding and "funding_annual_pct" in funding:
        annual = funding["funding_annual_pct"] or 0.0
        evidence["funding_annual_pct"] = round(annual, 1)
        # 年化资金费率：>50% 贪婪，< -30% 恐慌
        score += max(-0.5, min(0.5, annual / 100))

    if ind:
        rsi = ind.get("rsi14", 50)
        score += (rsi - 50) / 50 * 0.3
        evidence["rsi14"] = round(rsi, 1)
        if ind.get("volume_ratio", 1) > 2.0:
            score += 0.1
            evidence["volume_spike"] = round(ind["volume_ratio"], 2)

    if social_heat is not None:
        score += max(-0.2, min(0.2, social_heat))
        evidence["social_heat"] = round(social_heat, 2)

    if score >= 0.6:
        state = "fomo"
    elif score >= 0.2:
        state = "greedy"
    elif score <= -0.6:
        state = "panic"
    elif score <= -0.2:
        state = "fear"
    else:
        state = "neutral"

    return SentimentState(state=state, funding_annual_pct=evidence.get("funding_annual_pct"),
                          score=round(score, 3), evidence=evidence)


def save_sentiment(state: SentimentState) -> None:
    SENTIMENT_PATH.parent.mkdir(parents=True, exist_ok=True)
    SENTIMENT_PATH.write_text(json.dumps(state.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")


def load_sentiment() -> dict[str, Any]:
    if not SENTIMENT_PATH.exists():
        return {}
    try:
        return json.loads(SENTIMENT_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}

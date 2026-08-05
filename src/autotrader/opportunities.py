"""多标的主动机会扫描器（策略研究员 · 机会扫描）。

从"守株待兔"（只盯 BTC 等信号）升级为"主动狩猎"：每轮扫描全市场候选池，
对每个标的计算指标 + 全部策略信号，输出**机会榜**（最强信号 Top N），
供 CEO 主动评估建仓——市场不给机会时也在持续搜寻，而非干等。

确定性计算，零 Token 成本。落盘 artifacts/opportunities.json。
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .strategy import apply_strategies

ROOT = Path(__file__).resolve().parents[2]
OPPORTUNITIES_PATH = ROOT / "artifacts" / "opportunities.json"

# 候选池：主流交易对（测试网已确认存在）。可扩展为全市场 431 对。
CANDIDATE_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT",
    "LTCUSDT", "TRXUSDT", "LINKUSDT", "XLMUSDT", "ETCUSDT",
    "VETUSDT", "ZILUSDT", "DASHUSDT", "THETAUSDT", "ENJUSDT",
    "FETUSDT", "ZECUSDT", "BATUSDT", "NEOUSDT", "QTUMUSDT",
    "ONTUSDT", "IOSTUSDT", "WAVESUSDT", "OMGUSDT", "ANKRUSDT",
    "SXPUSDT", "SKLUSDT", "BANDUSDT", "RSRUSDT", "STMXUSDT",
    "ARDRUSDT", "LSKUSDT", "SCUSDT", "DGBUSDT", "RVNUSDT",
    "HIVEUSDT", "NKNUSDT", "STPTUSDT", "BURGERUSDT", "HBARUSDT",
]

SCAN_INTERVAL = "15m"
KLINE_LIMIT = 60


@dataclass
class Opportunity:
    """一个标的当前的机会评估（含自适应周期选择）。"""

    symbol: str
    price: float
    trend: str
    rsi14: float
    volume_ratio: float
    change_24h_pct: float
    signals: list[dict[str, Any]] = field(default_factory=list)
    rank: int = 0
    timeframe: str = "1h"          # 该标的本阶段交易周期（自适应）
    horizon: str = "中长线"          # 视野：短线/短中线/中长线/长线
    timeframe_reason: str = ""      # 周期选择理由

    @property
    def best_signal(self) -> dict[str, Any] | None:
        """最强信号（按 strength 降序）。"""
        if not self.signals:
            return None
        return max(self.signals, key=lambda s: s.get("strength", 0))

    def to_dict(self) -> dict[str, Any]:
        best = self.best_signal
        d = {
            "symbol": self.symbol,
            "price": round(self.price, 4),
            "trend": self.trend,
            "rsi14": round(self.rsi14, 1),
            "volume_ratio": round(self.volume_ratio, 2),
            "timeframe": self.timeframe,
            "horizon": self.horizon,
            "timeframe_reason": self.timeframe_reason,
            "change_24h_pct": round(self.change_24h_pct, 2),
            "signals": self.signals,
            "best": best,
            "rank": self.rank,
        }
        if best:
            d["best"] = best
        return d


def scan_one_adaptive(client, symbol: str,
                      kline_limit: int = KLINE_LIMIT) -> Opportunity | None:
    """自适应周期扫描（多周期战略核心）：

    1. 拉 1h K 线 → 判断大方向/波动率/量比；
    2. choose_timeframe 智能选择该标的本阶段交易周期（5m~4h）；
    3. 用推荐周期 K 线计算指标 + 全部策略信号；
    4. 机会带 timeframe/horizon 标记（短线/短中/中长/长线）。

    推荐周期数据不可用时回退 1h（容错）。失败返回 None（跳过）。
    """
    from .market import classify_market, compute_indicators, store_klines
    from .timeframes import choose_timeframe

    try:
        # 1. 1h K 线判断大方向与波动率（交易所符号格式容错：BTCUSDT → BTC）
        try:
            k1h = client.klines(symbol, "1h", kline_limit)
        except Exception:
            k1h = client.klines(symbol.replace("USDT", ""), "1h", kline_limit)
        if not k1h or len(k1h) < 30:
            return None
        ind1h = compute_indicators(k1h)
        price1h = ind1h.get("price", 0.0)
        rsi1h = ind1h.get("rsi14", 0.0)
        if price1h <= 0 or not (0 < rsi1h <= 100):
            return None
        # 2. 智能周期选择
        choice = choose_timeframe(ind1h)
        tf = choice["timeframe"]
        # 3. 推荐周期 K 线（1h 复用现有数据，其他周期重新拉，符号格式容错）
        if tf == "1h":
            klines = k1h
        else:
            try:
                klines = client.klines(symbol, tf, kline_limit)
            except Exception:
                klines = client.klines(symbol.replace("USDT", ""), tf, kline_limit)
        if not klines or len(klines) < 30:
            klines, tf = k1h, "1h"
            choice["horizon"] = "中长线"
            choice["reason"] = f"{choice['reason']}（{choice['timeframe']}数据不可用，回退1h）"
            choice["timeframe"] = "1h"
        store_klines(klines, symbol=symbol, interval=tf)  # 历史落库积累
        ind = compute_indicators(klines)
        volume_ratio = ind.get("volume_ratio", 0.0)
        rsi14 = ind.get("rsi14", 0.0)
        price = ind.get("price", 0.0)
        if price <= 0 or rsi14 <= 0 or rsi14 > 100:
            return None
        signals = [s.to_dict() for s in apply_strategies(ind, [])]
        return Opportunity(
            symbol=symbol,
            price=ind.get("price", 0.0),
            trend=str(classify_market(ind)),
            rsi14=rsi14,
            volume_ratio=volume_ratio,
            change_24h_pct=ind.get("change_24h_pct", 0.0),
            signals=signals,
            timeframe=tf,
            horizon=choice["horizon"],
            timeframe_reason=choice["reason"],
        )
    except Exception:
        return None


def scan_one(client, symbol: str, interval: str = SCAN_INTERVAL,
             kline_limit: int = KLINE_LIMIT) -> Opportunity | None:
    """兼容旧接口：固定周期扫描（保留，测试/回退用）。"""
    from .market import classify_market, compute_indicators, store_klines

    try:
        klines = client.klines(symbol, interval, kline_limit)
        if not klines or len(klines) < 30:
            return None
        store_klines(klines, symbol=symbol, interval=interval)  # 历史落库积累
        ind = compute_indicators(klines)
        # 数据质量过滤：只滤硬异常（RSI 无效 / 价格无效），量比低仅提示流动性
        volume_ratio = ind.get("volume_ratio", 0.0)
        rsi14 = ind.get("rsi14", 0.0)
        price = ind.get("price", 0.0)
        if price <= 0 or rsi14 <= 0 or rsi14 > 100:
            return None
        signals = [s.to_dict() for s in apply_strategies(ind, [])]
        return Opportunity(
            symbol=symbol,
            price=ind.get("price", 0.0),
            trend=str(classify_market(ind)),
            rsi14=rsi14,
            volume_ratio=volume_ratio,
            change_24h_pct=ind.get("change_24h_pct", 0.0),
            signals=signals,
        )
    except Exception:
        return None


def scan_opportunities(client, symbols: list[str] | None = None,
                       top_n: int = 8) -> dict[str, Any]:
    """扫描候选池，返回机会榜：

    - ``ranked``：按最强信号强度排序的全部标的（含无信号标的，便于观察）；
    - ``opportunities``：至少一个买入/卖出信号且强度 ≥ 0.5 的标的（机会榜）；
    - ``updated_at``：扫描时间。
    """
    pool = symbols or CANDIDATE_SYMBOLS
    found: list[Opportunity] = []
    failures = 0
    for symbol in pool:
        opp = scan_one_adaptive(client, symbol)
        if opp is not None:
            found.append(opp)
        else:
            failures += 1
    if failures == len(pool) and not found:
        # 全部失败 = 数据源不可用（不是"无机会"）→ 抛给上层切换兜底客户端
        raise RuntimeError(f"全部 {len(pool)} 个标的数据获取失败（数据源不可用）")

    # 全部标的按最佳信号强度降序（无信号排后）
    found.sort(key=lambda o: (o.best_signal or {}).get("strength", -1), reverse=True)
    for i, opp in enumerate(found, 1):
        opp.rank = i

    # 机会榜：有 buy/sell 信号且强度 ≥ 0.5（低流动性标的自动降序排后）
    opportunities = [
        o.to_dict() for o in found
        if o.best_signal and o.best_signal.get("action") in ("buy", "sell")
        and o.best_signal.get("strength", 0) >= 0.5
    ]
    # 流动性加权排序：量比高者优先（同强度下）
    opportunities.sort(
        key=lambda o: (o["best"]["strength"] if o["best"] else 0) + min(o["volume_ratio"], 2.0) * 0.05,
        reverse=True,
    )
    for i, o in enumerate(opportunities, 1):
        o["rank"] = i
    return {
        "ranked": [o.to_dict() for o in found],
        "opportunities": opportunities,
        "scanned": len(found),
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }


def save_opportunities(result: dict[str, Any]) -> None:
    """落盘 opportunities.json。"""
    OPPORTUNITIES_PATH.parent.mkdir(exist_ok=True)
    OPPORTUNITIES_PATH.write_text(
        json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8"
    )


def load_opportunities() -> dict[str, Any]:
    """读取最近一次机会榜（Dashboard / CEO 用）。"""
    if not OPPORTUNITIES_PATH.exists():
        return {"ranked": [], "opportunities": [], "scanned": 0, "updated_at": ""}
    try:
        return json.loads(OPPORTUNITIES_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"ranked": [], "opportunities": [], "scanned": 0, "updated_at": ""}

"""策略库（策略研究员落地）。

确定性策略引擎：输入市场指标（market.compute_indicators 的输出）与可选事件，
输出带证据的策略信号（buy/sell/hold + 强度 + 理由），供 CEO 决策参考。

策略清单（研讨纪要 §3.12）：
- trend_breakout  趋势突破：顺势 + 量能确认
- pullback_rebound 回撤反弹：趋势中回踩均线 + RSI 转弱后修复
- range_reversion 震荡高抛低吸：布林带/RSI 边界反转
- defensive       防守策略：波动异常/放量异常 → 观望
- event_driven    事件驱动：仅 A 级事件 + 明确预期差（由 CEO 判定预期差，本模块只做闸门）

所有计算确定性本地完成，不调用模型、不产生 Token 成本。
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class StrategySignal:
    strategy: str          # 策略名
    action: str            # buy / sell / hold
    strength: float        # 0-1 信号强度
    reason: str            # 触发原因（可审计）
    conditions: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _ema_bias(ind: dict[str, float]) -> str:
    """趋势倾向：bull / bear / neutral。"""
    price, ema20, ema50 = ind["price"], ind["ema20"], ind["ema50"]
    if price > ema20 > ema50:
        return "bull"
    if price < ema20 < ema50:
        return "bear"
    return "neutral"


def trend_breakout(ind: dict[str, float]) -> StrategySignal | None:
    """趋势突破：价格站稳 EMA20 上方 + 量比≥1.2 + RSI 不超买。"""
    bias = _ema_bias(ind)
    rsi, vol_ratio = ind["rsi14"], ind["volume_ratio"]
    if bias == "bull" and vol_ratio >= 1.2 and 45 <= rsi <= 72:
        strength = min(0.9, 0.5 + (vol_ratio - 1.2) * 0.15 + (rsi - 45) * 0.005)
        return StrategySignal(
            "trend_breakout", "buy", round(strength, 2),
            f"上升趋势确认（价>EMA20>EMA50），量比 {vol_ratio:.2f}，RSI {rsi:.0f}",
            {"bias": bias, "volume_ratio": vol_ratio, "rsi": round(rsi, 1)},
        )
    if bias == "bear" and vol_ratio >= 1.2 and 28 <= rsi <= 55:
        strength = min(0.9, 0.5 + (vol_ratio - 1.2) * 0.15 + (55 - rsi) * 0.005)
        return StrategySignal(
            "trend_breakout", "sell", round(strength, 2),
            f"下降趋势确认（价<EMA20<EMA50），量比 {vol_ratio:.2f}，RSI {rsi:.0f}",
            {"bias": bias, "volume_ratio": vol_ratio, "rsi": round(rsi, 1)},
        )
    return None


def pullback_rebound(ind: dict[str, float]) -> StrategySignal | None:
    """回撤反弹：趋势中回踩 EMA50（±1.5 ATR）+ RSI 修复。

    趋势判定用均线排列（ema20>ema50 为多头），不要求价格在 EMA20 上方——
    回踩场景价格本来就会跌破 EMA20。
    """
    price, ema20, ema50, atr14, rsi = ind["price"], ind["ema20"], ind["ema50"], ind["atr14"], ind["rsi14"]
    if atr14 <= 0:
        return None
    distance = (price - ema50) / atr14
    if ema20 > ema50 and -1.5 <= distance <= 0.5 and 35 <= rsi <= 50:
        strength = 0.4 + (1.5 + distance) * 0.15 + (50 - rsi) * 0.01
        return StrategySignal(
            "pullback_rebound", "buy", round(min(strength, 0.8), 2),
            f"多头排列回踩 EMA50（{distance:.2f} ATR），RSI {rsi:.0f} 修复中",
            {"distance_atr": round(distance, 2), "rsi": round(rsi, 1)},
        )
    if ema20 < ema50 and -0.5 <= distance <= 1.5 and 50 <= rsi <= 65:
        strength = 0.4 + (1.5 - distance) * 0.15 + (rsi - 50) * 0.01
        return StrategySignal(
            "pullback_rebound", "sell", round(min(strength, 0.8), 2),
            f"空头排列反抽 EMA50（{distance:.2f} ATR），RSI {rsi:.0f} 转弱",
            {"distance_atr": round(distance, 2), "rsi": round(rsi, 1)},
        )
    return None


def range_reversion(ind: dict[str, float]) -> StrategySignal | None:
    """震荡高抛低吸：仅震荡市，RSI 边界反转。"""
    if ind.get("trend", _ema_bias(ind)) not in ("sideways", "neutral"):
        return None
    rsi = ind["rsi14"]
    if rsi <= 30:
        return StrategySignal(
            "range_reversion", "buy", 0.6,
            f"震荡市 RSI {rsi:.0f} 超卖（<30）低吸",
            {"rsi": round(rsi, 1)},
        )
    if rsi >= 70:
        return StrategySignal(
            "range_reversion", "sell", 0.6,
            f"震荡市 RSI {rsi:.0f} 超买（>70）高抛",
            {"rsi": round(rsi, 1)},
        )
    return None


def defensive(ind: dict[str, float]) -> StrategySignal | None:
    """防守：波动过大 / 放量异常 → 观望（hold），降低交易频率。"""
    price, atr14, vol_ratio = ind["price"], ind["atr14"], ind["volume_ratio"]
    reasons: list[str] = []
    if price > 0 and atr14 / price > 0.04:
        reasons.append(f"波动率过高（ATR {atr14 / price * 100:.1f}% > 4%）")
    if vol_ratio > 3.0:
        reasons.append(f"异常放量（量比 {vol_ratio:.2f} > 3）")
    if reasons:
        return StrategySignal(
            "defensive", "hold", 0.7, "防守模式：" + "；".join(reasons),
            {"atr_pct": round(atr14 / price * 100, 2) if price else 0, "volume_ratio": vol_ratio},
        )
    return None


def event_driven(events: list[dict[str, Any]]) -> StrategySignal | None:
    """事件驱动闸门：仅 A 级事件给出方向提示，B/C 级只提示观察。

    事件结构（news_research.record_event 产出）：
    {"id", "title", "grade": "A"|"B"|"C", "impact", "assets", "bias": "bull"|"bear"|None, ...}
    """
    for event in events:
        if event.get("grade") == "A" and event.get("bias") in ("bull", "bear"):
            action = "buy" if event["bias"] == "bull" else "sell"
            return StrategySignal(
                "event_driven", action, 0.8,
                f"A级事件「{event.get('title', '')}」方向 {event['bias']}（预期差需CEO复核）",
                {"event_id": event.get("id"), "impact": event.get("impact")},
            )
    for event in events:
        if event.get("grade") == "B":
            return StrategySignal(
                "event_driven", "hold", 0.4,
                f"B级事件「{event.get('title', '')}」仅观察，等待确认",
                {"event_id": event.get("id")},
            )
    return None


def apply_strategies(ind: dict[str, Any],
                     events: list[dict[str, Any]] | None = None) -> list[StrategySignal]:
    """运行全部策略，返回非空信号（按强度降序）。"""
    signals = [
        trend_breakout(ind), pullback_rebound(ind), range_reversion(ind), defensive(ind),
    ]
    if events:
        signals.append(event_driven(events))
    active = [s for s in signals if s is not None]
    active.sort(key=lambda s: s.strength, reverse=True)
    return active

"""多周期智能选择（CEO 多周期战略 · 短线到长线全覆盖）。

董事长要求：不能只做单一死板周期——5 分钟到 1 天到 1 周都要有，
短线长线结合，根据实际情况（波动率/趋势/量比）自动选择每个标的适合的周期，
并随市场自动应变。

本模块提供确定性周期选择（零 Token）：
- ``TIMEFRAMES``：全周期表（5m ~ 1w）；
- ``choose_timeframe(ind)``：根据 1h 指标的波动率/24h 幅度/趋势/量比，
  输出该标的本阶段适合的交易周期与视野（短线/短中/中长/长线）。

设计：先看 1h（判断大方向与波动率）→ 分级选择操作周期 →
     短线候选（高波动）用 5m/15m 快打，长线候选（平稳）用 4h/1d 慢做。
     市场变化（波动率放大/缩小）→ 周期自动切换（随机应变）。
"""

from __future__ import annotations

from typing import Any

# 全周期表：(K线周期, 视野标签, 秒数)
TIMEFRAMES: list[tuple[str, str, int]] = [
    ("5m", "短线", 300),
    ("15m", "短中线", 900),
    ("1h", "中长线", 3600),
    ("4h", "长线", 14400),
    ("1d", "超长线", 86400),
    ("1w", "极长线", 604800),
]


def choose_timeframe(ind: dict[str, Any]) -> dict[str, Any]:
    """智能周期选择（输入 1h 指标）。

    规则（波动率优先，趋势/量比修正）：
    1. 高波动（1h ATR ≥1.2%）或大行情（24h |幅度| ≥4%）→ 短线 5m 快打；
    2. 中波动（ATR ≥0.5% 或 |24h| ≥1.5%）→ 短中线 15m；
    3. 有趋势（trend_up/down）或放量（量比 ≥1.5）→ 中长线 1h 顺势；
    4. 平稳（低波动无趋势）→ 长线 4h 慢做（短线无肉，等长线价值回归）。

    返回 {"timeframe", "horizon", "reason", "atr_pct"}。
    """
    from .market import classify_market

    price = ind.get("price") or 0.0
    atr_pct = (ind.get("atr14", 0.0) / price * 100) if price else 0.0
    chg = abs(ind.get("change_24h_pct", 0.0))
    vol = ind.get("volume_ratio", 1.0)
    trend = classify_market(ind)

    if atr_pct >= 1.2 or chg >= 4.0:
        return {
            "timeframe": "5m", "horizon": "短线",
            "reason": f"高波动 ATR{atr_pct:.2f}%/24h±{chg:.1f}% → 5m 快打",
            "atr_pct": round(atr_pct, 2),
        }
    if atr_pct >= 0.5 or chg >= 1.5:
        return {
            "timeframe": "15m", "horizon": "短中线",
            "reason": f"中波动 ATR{atr_pct:.2f}%/24h±{chg:.1f}% → 15m 波段",
            "atr_pct": round(atr_pct, 2),
        }
    if trend != "sideways" or vol >= 1.5:
        return {
            "timeframe": "1h", "horizon": "中长线",
            "reason": f"{trend}/量比{vol:.2f} → 1h 顺趋势",
            "atr_pct": round(atr_pct, 2),
        }
    return {
        "timeframe": "4h", "horizon": "长线",
        "reason": f"平稳 ATR{atr_pct:.2f}% 无趋势 → 4h 慢做",
        "atr_pct": round(atr_pct, 2),
    }

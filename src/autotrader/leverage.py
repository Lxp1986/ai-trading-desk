"""动态杠杆引擎（USDT 本位永续 · 多因子自适应）。

像专业交易员一样思考：杠杆不是固定值，而是根据
**波动率 / 市场状态 / 信号置信度 / 策略历史胜率 / 账户防守状态**
动态调整的决策变量。

核心原则：
1. **风险预算永远不变**（总权益 1% 硬上限）——杠杆放大的是保证金效率，
   让系统在止损距离近（低波动）时能开更大名义仓位；
2. 低波动 + 顺势 + 高置信 + 高胜率 → 加杠杆（止损近，强平远，风险可控）；
3. 高波动 / 逆势 / 回撤 / 连亏 → 降杠杆（防守优先）；
4. 杠杆上限 5x、下限 1x（硬边界，绝不让系统裸奔或赌博）。

因子表（全部相乘，clamp [1, 5]）：

| 因子 | 条件 | 倍数 |
|------|------|------|
| 波动率 | ATR% ≤1.0% | ×1.6 |
|       | 1.0~2.0% | ×1.2 |
|       | 2.0~3.0% | ×1.0（基准）|
|       | 3.0~4.5% | ×0.6 |
|       | >4.5%    | ×0.4 |
| 顺势   | 顺势（buy+up / sell+down）| ×1.5 |
|       | 震荡（sideways）| ×0.8 |
|       | 逆势 | ×0.4 |
| 信号强度 | ≥0.75 | ×1.3 |
|         | 0.5~0.75 | ×1.0 |
| 策略胜率 | ≥60% | ×1.3 |
|（近20笔）| 45~60% | ×1.0 |
|         | 35~45% | ×0.8 |
|         | <35%   | ×0.5 |
| 回撤    | ≥10% | ×0.4 |
|        | 5~10% | ×0.6 |
| 连亏    | ≥4 笔 | ×0.5 |
|        | 2~3 笔 | ×0.8 |

用例（真实场景）：
- 低波动 0.8% + 顺势 + 强度 0.8 + 胜率 65% → 2×1.6×1.5×1.3×1.3 ≈ 8.1 → **5x**
- 高波动 4% + 逆势 + 强度 0.55 + 胜率 40% + 回撤 6% → 2×0.6×0.4×1×0.8×0.6 ≈ 0.23 → **1x**
- 中性条件 → **2x**
"""
from __future__ import annotations

from typing import Any

# 硬边界
MIN_LEVERAGE = 1.0
MAX_LEVERAGE = 5.0
BASE_LEVERAGE = 2.0


def _clamp(x: float, lo: float = MIN_LEVERAGE, hi: float = MAX_LEVERAGE) -> float:
    return max(lo, min(hi, x))


def vol_factor(atr_pct: float | None) -> float:
    """波动率因子：低波动 → 加杠杆（止损近、风险/保证金比高）。"""
    if atr_pct is None or atr_pct <= 0:
        return 1.0
    if atr_pct <= 1.0:
        return 1.6
    if atr_pct <= 2.0:
        return 1.2
    if atr_pct <= 3.0:
        return 1.0
    if atr_pct <= 4.5:
        return 0.6
    return 0.4


def trend_factor(action: str, trend: str) -> float:
    """顺势因子：顺势加杠杆，逆势/震荡降杠杆。"""
    action = (action or "").lower()
    trend = (trend or "").lower()
    if (action == "buy" and trend == "trend_up") or \
       (action == "sell" and trend == "trend_down"):
        return 1.5
    if trend == "sideways":
        return 0.8
    return 0.4  # 逆势


def strength_factor(strength: float) -> float:
    """信号置信度因子。"""
    if strength >= 0.75:
        return 1.3
    return 1.0


def winrate_factor(winrate: float | None) -> float:
    """策略历史胜率因子（学习反馈：胜率高 → 敢加杠杆）。"""
    if winrate is None:
        return 1.0
    if winrate >= 0.60:
        return 1.3
    if winrate >= 0.45:
        return 1.0
    if winrate >= 0.35:
        return 0.8
    return 0.5


def defense_factor(drawdown_pct: float | None, consecutive_losses: int | None) -> float:
    """账户防守因子：回撤/连亏越大，杠杆越保守。"""
    f = 1.0
    if drawdown_pct is not None:
        if drawdown_pct >= 10.0:
            f *= 0.4
        elif drawdown_pct >= 5.0:
            f *= 0.6
    if consecutive_losses is not None:
        if consecutive_losses >= 4:
            f *= 0.5
        elif consecutive_losses >= 2:
            f *= 0.8
    return f


def compute_leverage(*, action: str,
                     trend: str = "sideways",
                     atr_pct: float | None = None,
                     strength: float = 0.6,
                     strategy_winrate: float | None = None,
                     drawdown_pct: float | None = None,
                     consecutive_losses: int | None = None,
                     base_lever: float = BASE_LEVERAGE) -> float:
    """综合所有因子计算最终杠杆（clamp [1, 5]，保留 1 位小数）。

    输入缺失时因子取 1.0（中性），保证函数永不抛错。
    """
    f = (vol_factor(atr_pct)
         * trend_factor(action, trend)
         * strength_factor(strength)
         * winrate_factor(strategy_winrate)
         * defense_factor(drawdown_pct, consecutive_losses))
    lever = base_lever * f
    return round(_clamp(lever), 1)


def leverage_breakdown(*, action: str,
                       trend: str = "sideways",
                       atr_pct: float | None = None,
                       strength: float = 0.6,
                       strategy_winrate: float | None = None,
                       drawdown_pct: float | None = None,
                       consecutive_losses: int | None = None,
                       base_lever: float = BASE_LEVERAGE) -> dict[str, Any]:
    """计算杠杆并返回因子分解（审计/看板用）。"""
    factors = {
        "波动率": vol_factor(atr_pct),
        "顺势": trend_factor(action, trend),
        "信号强度": strength_factor(strength),
        "策略胜率": winrate_factor(strategy_winrate),
        "防守": defense_factor(drawdown_pct, consecutive_losses),
    }
    lever = compute_leverage(action=action, trend=trend, atr_pct=atr_pct,
                             strength=strength, strategy_winrate=strategy_winrate,
                             drawdown_pct=drawdown_pct,
                             consecutive_losses=consecutive_losses,
                             base_lever=base_lever)
    return {
        "leverage": lever,
        "base": base_lever,
        "factors": factors,
        "inputs": {
            "action": action, "trend": trend, "atr_pct": atr_pct,
            "strength": strength, "strategy_winrate": strategy_winrate,
            "drawdown_pct": drawdown_pct, "consecutive_losses": consecutive_losses,
        },
    }

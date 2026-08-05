"""独立风控引擎（风险官落地，含硬边界状态检查）。

在原有订单级风控（``review``）之上，补齐研讨会确认的硬风控：

- 连亏 N 笔暂停新仓（默认 5 笔）；
- 回撤 ≥15% 停止自动开仓（只允许减仓/平仓）；
- 回撤 ≥25% 强制平仓模式（禁止一切新仓）；
- 单笔风险预算：预期止损距离 × 数量 ≤ 现金 × risk_per_trade_pct
  （会议示例：单笔风险 0.5%~1%）。

风控状态（连续亏损、回撤、当日亏损）由本地账本计算，与交易冲动
完全隔离；硬边界不因 CEO 自信而突破。
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .models import MarketSnapshot, RiskLimits, Side, TradeIntent
from .portfolio import STARTING_CASH_USDT, load_orders, max_drawdown, positions

DEFAULT_MAX_CONSECUTIVE_LOSSES = 5
DEFAULT_DRAWDOWN_HALT_PCT = 15.0
DEFAULT_DRAWDOWN_LIQUIDATE_PCT = 25.0
DEFAULT_RISK_PER_TRADE_PCT = 1.0


@dataclass(frozen=True)
class HardRiskLimits:
    max_consecutive_losses: int = DEFAULT_MAX_CONSECUTIVE_LOSSES
    drawdown_halt_pct: float = DEFAULT_DRAWDOWN_HALT_PCT
    drawdown_liquidate_pct: float = DEFAULT_DRAWDOWN_LIQUIDATE_PCT
    risk_per_trade_pct: float = DEFAULT_RISK_PER_TRADE_PCT


@dataclass(frozen=True)
class RiskState:
    consecutive_losses: int = 0
    drawdown_pct: float = 0.0
    daily_loss: float = 0.0
    trading_halted: bool = False
    halt_reasons: tuple[str, ...] = field(default_factory=tuple)


def compute_state(orders: list[dict] | None = None, prices: dict[str, float] | None = None,
                  start_cash: float = STARTING_CASH_USDT) -> RiskState:
    """从本地账本计算风控状态（连亏、回撤）。

    ``orders`` 为 None 时从 ``artifacts/orders.jsonl`` 读取。
    """
    if orders is None:
        orders = load_orders()
    prices = prices or {}

    drawdown = max_drawdown(orders, prices, start_cash)

    # 连续亏损：按时间顺序统计已平仓 SELL 订单的单笔盈亏
    consecutive = 0
    for order in orders:
        if str(order.get("side", "")).upper() != "SELL":
            continue
        if order.get("status") not in (None, "FILLED", "filled"):
            continue
        qty = float(order.get("quantity") or order.get("executedQty") or 0.0)
        quote = float(order.get("quote_qty") or order.get("cummulativeQuoteQty") or 0.0)
        fee = float(order.get("fee") or 0.0)
        if qty <= 0:
            continue
        # 该时点前的平均成本（重放到此订单为止）
        prior = [o for o in orders if o.get("order_id") != order.get("order_id")
                 and str(o.get("side", "")).upper() == "BUY"
                 and o.get("status") in (None, "FILLED", "filled")
                 and _seq(o) < _seq(order)]
        cost = _avg_cost_of(prior, order.get("symbol", ""))
        pnl = (quote - fee) - qty * cost
        if pnl < 0:
            consecutive += 1
        else:
            consecutive = 0

    halt_reasons: list[str] = []
    if consecutive >= DEFAULT_MAX_CONSECUTIVE_LOSSES:
        halt_reasons.append(f"连续亏损 {consecutive} 笔达到暂停阈值")
    if drawdown >= DEFAULT_DRAWDOWN_LIQUIDATE_PCT:
        halt_reasons.append(f"回撤 {drawdown:.1f}% ≥ 全平阈值 {DEFAULT_DRAWDOWN_LIQUIDATE_PCT}%")
    elif drawdown >= DEFAULT_DRAWDOWN_HALT_PCT:
        halt_reasons.append(f"回撤 {drawdown:.1f}% ≥ 暂停阈值 {DEFAULT_DRAWDOWN_HALT_PCT}%")

    return RiskState(
        consecutive_losses=consecutive,
        drawdown_pct=drawdown,
        trading_halted=bool(halt_reasons),
        halt_reasons=tuple(halt_reasons),
    )


def _seq(order: dict) -> int:
    return int(order.get("seq") or order.get("order_id") or 0)


def _avg_cost_of(buy_orders: list[dict], symbol: str) -> float:
    qty, cost = 0.0, 0.0
    for o in buy_orders:
        if o.get("symbol") != symbol:
            continue
        qty += float(o.get("quantity") or o.get("executedQty") or 0.0)
        cost += float(o.get("quote_qty") or o.get("cummulativeQuoteQty") or 0.0) + float(o.get("fee") or 0.0)
    return cost / qty if qty else 0.0


def review(snapshot: MarketSnapshot, intent: TradeIntent, limits: RiskLimits,
           state: RiskState | None = None,
           hard: HardRiskLimits | None = None) -> tuple[bool, tuple[str, ...]]:
    """订单级 + 硬边界风控审核。

    ``state`` 为 None 时自动从本地账本计算（连亏/回撤）。
    """
    state = state or compute_state()
    hard = hard or HardRiskLimits()
    reasons: list[str] = []
    value = intent.quantity * snapshot.price

    # —— 原有订单级检查 ——
    if intent.side is Side.HOLD:
        reasons.append("hold intent does not create an order")
    if intent.quantity <= 0 and intent.side is not Side.HOLD:
        reasons.append("quantity must be positive")
    if value > limits.max_order_value:
        reasons.append("order value exceeds max_order_value")
    if intent.side is Side.BUY and value > limits.cash:
        reasons.append("buy value exceeds available cash")
    if value > limits.max_position_value:
        reasons.append("position value exceeds max_position_value")
    if not snapshot.liquidity_ok:
        reasons.append("market liquidity is not safe")
    if not 0 <= intent.confidence <= 1:
        reasons.append("confidence must be between 0 and 1")
    if not intent.thesis.strip():
        reasons.append("thesis is required")
    if not intent.invalidation.strip():
        reasons.append("invalidation is required")

    # —— 硬边界：连亏 / 回撤熔断 ——
    if state.trading_halted:
        # 熔断时只允许减少风险：卖出平仓或保持观望，禁止新买
        if intent.side is Side.BUY:
            reasons.extend(state.halt_reasons)
            reasons.append("trading halted: new buys frozen")
    else:
        if state.consecutive_losses >= hard.max_consecutive_losses:
            reasons.append(f"consecutive losses ({state.consecutive_losses}) hit pause threshold")
        if state.drawdown_pct >= hard.drawdown_liquidate_pct:
            reasons.append(f"drawdown {state.drawdown_pct:.1f}% hits liquidation threshold")
        elif state.drawdown_pct >= hard.drawdown_halt_pct:
            if intent.side is Side.BUY:
                reasons.append(f"drawdown {state.drawdown_pct:.1f}% halts new buys")

    # —— 单笔风险预算：|price − stop| × qty ≤ cash × risk% ——
    if intent.side is not Side.HOLD and intent.stop_price and intent.quantity > 0:
        risk_amount = abs(snapshot.price - intent.stop_price) * intent.quantity
        budget = limits.cash * (hard.risk_per_trade_pct / 100.0)
        if risk_amount > budget:
            reasons.append(
                f"risk per trade {risk_amount:.2f} exceeds budget {budget:.2f} "
                f"({hard.risk_per_trade_pct}% of cash)"
            )

    return not reasons, tuple(reasons) or ("approved within simulation limits",)

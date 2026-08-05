from __future__ import annotations

from .models import MarketSnapshot, RiskLimits, TradeIntent, Side


def review(snapshot: MarketSnapshot, intent: TradeIntent, limits: RiskLimits) -> tuple[bool, tuple[str, ...]]:
    reasons: list[str] = []
    value = intent.quantity * snapshot.price

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

    return not reasons, tuple(reasons) or ("approved within simulation limits",)

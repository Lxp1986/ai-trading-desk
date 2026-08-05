from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class Side(str, Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


@dataclass(frozen=True)
class MarketSnapshot:
    symbol: str
    price: float
    volume_ratio: float
    trend: str
    liquidity_ok: bool = True
    source: str = "simulated"
    observed_at: str = field(default_factory=now_iso)


@dataclass(frozen=True)
class TradeIntent:
    symbol: str
    side: Side
    quantity: float
    thesis: str
    invalidation: str
    stop_price: float | None
    confidence: float
    created_at: str = field(default_factory=now_iso)
    source: str = "ceo"


@dataclass(frozen=True)
class RiskLimits:
    max_position_value: float
    max_order_value: float
    max_daily_loss: float
    cash: float


@dataclass(frozen=True)
class Decision:
    intent: TradeIntent
    approved: bool
    reasons: tuple[str, ...]
    simulated_value: float
    decided_at: str = field(default_factory=now_iso)

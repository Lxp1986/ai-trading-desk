"""Tests for hard risk controls (consecutive losses, drawdown circuit breaker, per-trade risk)."""

from __future__ import annotations

import unittest

from autotrader.models import MarketSnapshot, RiskLimits, Side, TradeIntent
from autotrader.risk import HardRiskLimits, RiskState, compute_state, review


def _snapshot(price: float = 100.0, trend: str = "trend_up") -> MarketSnapshot:
    return MarketSnapshot("BTC/USDT", price, 1.5, trend)


def _limits(cash: float = 500.0) -> RiskLimits:
    return RiskLimits(max_position_value=200, max_order_value=100, max_daily_loss=20, cash=cash)


def _intent(side: Side = Side.BUY, quantity: float = 0.1, stop: float | None = 99.0) -> TradeIntent:
    return TradeIntent(
        symbol="BTC/USDT", side=side, quantity=quantity,
        thesis="test thesis", invalidation="test invalidation",
        stop_price=stop, confidence=0.6,
    )


class HardRiskTests(unittest.TestCase):
    def test_normal_buy_approved(self) -> None:
        state = RiskState(consecutive_losses=0, drawdown_pct=2.0)
        ok, reasons = review(_snapshot(), _intent(), _limits(), state=state)
        self.assertTrue(ok, reasons)

    def test_consecutive_losses_freeze_new_buys(self) -> None:
        state = RiskState(consecutive_losses=5, drawdown_pct=3.0, trading_halted=True,
                          halt_reasons=("连续亏损 5 笔达到暂停阈值",))
        ok, reasons = review(_snapshot(), _intent(Side.BUY), _limits(), state=state)
        self.assertFalse(ok)
        self.assertTrue(any("trading halted" in r for r in reasons))
        # 卖出（减风险）仍允许
        ok2, _ = review(_snapshot(), _intent(Side.SELL, 0.1), _limits(), state=state)
        self.assertTrue(ok2)

    def test_drawdown_halt_blocks_buy(self) -> None:
        state = RiskState(consecutive_losses=0, drawdown_pct=16.0, trading_halted=True,
                          halt_reasons=("回撤 16.0% ≥ 暂停阈值 15.0%",))
        ok, _ = review(_snapshot(), _intent(Side.BUY), _limits(), state=state)
        self.assertFalse(ok)

    def test_drawdown_liquidation_blocks_everything_new(self) -> None:
        state = RiskState(consecutive_losses=0, drawdown_pct=26.0, trading_halted=True,
                          halt_reasons=("回撤 26.0% ≥ 全平阈值 25.0%",))
        ok, _ = review(_snapshot(), _intent(Side.BUY), _limits(), state=state)
        self.assertFalse(ok)

    def test_risk_per_trade_budget(self) -> None:
        # 止损距离 1.0 × 数量 0.5 = 0.5；现金 500 × 1% = 5 → 通过
        ok, _ = review(_snapshot(100.0), _intent(Side.BUY, 0.5, stop=99.0), _limits(cash=500), state=RiskState())
        self.assertTrue(ok)
        # 止损距离 30 × 数量 1.0 = 30 > 5 → 拒绝
        ok2, reasons = review(_snapshot(100.0), _intent(Side.BUY, 1.0, stop=70.0), _limits(cash=500), state=RiskState())
        self.assertFalse(ok2)
        self.assertTrue(any("risk per trade" in r for r in reasons))

    def test_compute_state_from_orders(self) -> None:
        # 两笔亏损平仓 → 连续亏损 2
        orders = [
            {"order_id": 1, "seq": 1, "symbol": "BTC/USDT", "side": "BUY", "status": "FILLED",
             "quantity": 0.1, "quote_qty": 10.0, "fee": 0.0},
            {"order_id": 2, "seq": 2, "symbol": "BTC/USDT", "side": "SELL", "status": "FILLED",
             "quantity": 0.1, "quote_qty": 8.0, "fee": 0.0},
            {"order_id": 3, "seq": 3, "symbol": "BTC/USDT", "side": "BUY", "status": "FILLED",
             "quantity": 0.1, "quote_qty": 10.0, "fee": 0.0},
            {"order_id": 4, "seq": 4, "symbol": "BTC/USDT", "side": "SELL", "status": "FILLED",
             "quantity": 0.1, "quote_qty": 9.0, "fee": 0.0},
        ]
        state = compute_state(orders, prices={"BTC/USDT": 100.0}, start_cash=277.0)
        self.assertEqual(state.consecutive_losses, 2)

    def test_compute_state_resets_on_win(self) -> None:
        orders = [
            {"order_id": 1, "seq": 1, "symbol": "BTC/USDT", "side": "BUY", "status": "FILLED",
             "quantity": 0.1, "quote_qty": 10.0, "fee": 0.0},
            {"order_id": 2, "seq": 2, "symbol": "BTC/USDT", "side": "SELL", "status": "FILLED",
             "quantity": 0.1, "quote_qty": 8.0, "fee": 0.0},   # 亏
            {"order_id": 3, "seq": 3, "symbol": "BTC/USDT", "side": "BUY", "status": "FILLED",
             "quantity": 0.1, "quote_qty": 10.0, "fee": 0.0},
            {"order_id": 4, "seq": 4, "symbol": "BTC/USDT", "side": "SELL", "status": "FILLED",
             "quantity": 0.1, "quote_qty": 12.0, "fee": 0.0},  # 赚 → 重置
        ]
        state = compute_state(orders, prices={"BTC/USDT": 100.0}, start_cash=277.0)
        self.assertEqual(state.consecutive_losses, 0)


if __name__ == "__main__":
    unittest.main()

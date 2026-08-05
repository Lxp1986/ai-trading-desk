"""Tests for the local ledger / portfolio module."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from autotrader.portfolio import (
    STARTING_CASH_USDT, cash_balance, equity, load_orders, max_drawdown,
    open_positions, portfolio_snapshot, positions, realized_pnl, unrealized_pnl,
)


def _order(order_id: int, side: str, qty: float, quote: float, symbol: str = "BTC/USDT",
           status: str = "FILLED", fee: float = 0.0) -> dict:
    return {
        "order_id": order_id, "symbol": symbol, "side": side, "status": status,
        "quantity": qty, "quote_qty": quote, "fee": fee,
    }


class PortfolioTests(unittest.TestCase):
    def test_buy_creates_position(self) -> None:
        orders = [_order(1, "BUY", 0.001, 64.35)]
        pos = positions(orders)
        self.assertIn("BTC/USDT", pos)
        self.assertAlmostEqual(pos["BTC/USDT"].quantity, 0.001)
        self.assertAlmostEqual(pos["BTC/USDT"].avg_cost, 64350.0)

    def test_sell_realizes_pnl(self) -> None:
        orders = [
            _order(1, "BUY", 0.001, 64.35),
            _order(2, "SELL", 0.001, 66.0),
        ]
        pos = positions(orders)
        # 已平仓 symbol 保留（quantity=0，盈亏信息不丢），open_positions 为空
        self.assertEqual(pos["BTC/USDT"].quantity, 0.0)
        self.assertEqual(open_positions(orders), {})
        self.assertAlmostEqual(realized_pnl(orders), 1.65)

    def test_cash_balance(self) -> None:
        orders = [_order(1, "BUY", 0.001, 64.35)]
        self.assertAlmostEqual(cash_balance(orders), STARTING_CASH_USDT - 64.35)

    def test_equity_and_unrealized(self) -> None:
        orders = [_order(1, "BUY", 0.001, 64.35)]
        prices = {"BTC/USDT": 65_000.0}
        pos_value = 0.001 * 65_000
        self.assertAlmostEqual(equity(orders, prices), (STARTING_CASH_USDT - 64.35) + pos_value)
        self.assertAlmostEqual(unrealized_pnl(orders, prices), pos_value - 64.35)

    def test_ignores_non_filled(self) -> None:
        orders = [_order(1, "BUY", 0.001, 64.35, status="CANCELED")]
        self.assertEqual(positions(orders), {})
        self.assertAlmostEqual(cash_balance(orders), STARTING_CASH_USDT)

    def test_max_drawdown(self) -> None:
        orders = [_order(1, "BUY", 0.001, 64.35)]
        prices = {"BTC/USDT": 30_000.0}  # 价格大幅下跌
        dd = max_drawdown(orders, prices)
        self.assertGreater(dd, 0)

    def test_snapshot_shape(self) -> None:
        orders = [_order(1, "BUY", 0.001, 64.35)]
        snap = portfolio_snapshot(orders, {"BTC/USDT": 64_350.0})
        for key in ("starting_cash", "cash", "positions", "position_value",
                    "realized_pnl", "unrealized_pnl", "equity", "max_drawdown_pct"):
            self.assertIn(key, snap)
        self.assertAlmostEqual(snap["equity"], STARTING_CASH_USDT)

    def test_load_orders_from_disk(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "orders.jsonl"
            with path.open("w", encoding="utf-8") as f:
                f.write(json.dumps(_order(1, "BUY", 0.001, 64.35)) + "\n")
                f.write("not-json\n")  # 损坏行应被跳过
            records = load_orders(path)
            self.assertEqual(len(records), 1)


if __name__ == "__main__":
    unittest.main()

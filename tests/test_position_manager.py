"""Tests for position_manager (持仓实时监控 + 主动调仓引擎)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from autotrader import position_manager as pm


class _FakeClient:
    """假下单客户端：记录订单，不触达交易所。"""

    def __init__(self):
        self.orders: list[dict] = []

    def create_test_order(self, symbol, side, quantity):
        order = {"orderId": len(self.orders) + 1, "symbol": symbol, "side": side,
                 "status": "FILLED", "avgFillPrice": 64000.0, "quantity": quantity}
        self.orders.append(order)
        return order


def _seed_position(qty: float, avg_cost: float, symbol: str = "BTCUSDT") -> list[dict]:
    return [{
        "type": "testnet_order", "order_id": 1, "symbol": symbol, "side": "BUY",
        "order_type": "MARKET", "status": "FILLED", "price": "0", 
        "avg_fill_price": avg_cost, "quantity": str(qty),
        "quote_qty": str(qty * avg_cost), "fee": None, "created_at": 1,
        "logged_at": "2026-08-05T00:00:00+00:00", "note": "test seed",
    }]


class PositionManagerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_art = pm.ARTIFACTS
        self.old_atr = pm._atr_pct
        pm.ARTIFACTS = Path(self.tmp.name)
        pm.ORDERS_PATH = pm.ARTIFACTS / "orders.jsonl"
        pm.AUDIT_PATH = pm.ARTIFACTS / "audit.jsonl"
        pm.POSITIONS_PATH = pm.ARTIFACTS / "positions.json"
        pm.STATE_PATH = pm.ARTIFACTS / "state.json"
        self.client = _FakeClient()

    def tearDown(self):
        pm.ARTIFACTS = self.old_art
        pm._atr_pct = self.old_atr
        self.tmp.cleanup()

    def _write_orders(self, orders):
        with pm.ORDERS_PATH.open("w", encoding="utf-8") as f:
            for o in orders:
                f.write(json.dumps(o) + "\n")

    def test_zero_position_monitor(self):
        mon = pm.monitor_positions({})
        self.assertEqual(mon["count"], 0)
        self.assertIn("零持仓", mon["note"])

    def test_monitor_computes_pnl(self):
        self._write_orders(_seed_position(0.001, 64000.0))
        mon = pm.monitor_positions({"BTCUSDT": 66000.0})
        pos = mon["positions"]["BTCUSDT"]
        self.assertEqual(pos["quantity"], 0.001)
        self.assertAlmostEqual(pos["pnl_pct"], 3.12, places=1)  # 66000/64000-1=3.125
        self.assertGreater(pos["pnl"], 0)

    def test_stop_loss_triggers(self):
        """浮亏超止损线 → 紧急止损立即平仓。"""
        self._write_orders(_seed_position(0.001, 64000.0))
        # 价格跌 10% → 远超 3% 止损线
        emg = pm.emergency_stop_loss(self.client, {"BTCUSDT": 57600.0})
        self.assertEqual(emg["count"], 1)
        self.assertEqual(emg["executed"][0]["action"], "SELL_executed")
        # 账本有卖出记录
        orders = pm.load_positions()
        self.assertEqual(len(orders), 0)  # 平仓后无持仓

    def test_no_stop_loss_when_ok(self):
        self._write_orders(_seed_position(0.001, 64000.0))
        emg = pm.emergency_stop_loss(self.client, {"BTCUSDT": 63800.0})  # -0.3%
        self.assertEqual(emg["count"], 0)

    def test_take_profit_manage(self):
        """浮盈达标 → runner 调仓止盈平仓。"""
        self._write_orders(_seed_position(0.001, 64000.0))
        rep = pm.manage(self.client, prices={"BTCUSDT": 70000.0})  # +9.4%
        acts = rep["actions"]
        self.assertTrue(any(a["action"] == "SELL_executed" for a in acts))
        self.assertTrue(any("止盈" in a["reason"] for a in acts))

    def test_signal_reversal_closes(self):
        """多头持仓 + sell 信号 → 平仓。"""
        self._write_orders(_seed_position(0.001, 64000.0))
        signals = [{"symbol": "BTCUSDT", "action": "sell",
                    "strategy": "trend_breakout", "reason": "趋势转空"}]
        rep = pm.manage(self.client, signals=signals, prices={"BTCUSDT": 64000.0})
        self.assertTrue(any(a["action"] == "SELL_executed" and "信号翻转" in a["reason"]
                            for a in rep["actions"]))

    def test_add_position_budget(self):
        """同向 buy 信号 → 加仓（预算 = 现金 1%）。"""
        self._write_orders(_seed_position(0.001, 64000.0))
        signals = [{"symbol": "BTCUSDT", "action": "buy",
                    "strategy": "trend_breakout", "reason": "趋势向上"}]
        rep = pm.manage(self.client, signals=signals, prices={"BTCUSDT": 64000.0})
        buy_acts = [a for a in rep["actions"] if a["action"] == "BUY_executed"]
        # 现金 277 - 64 = 213 → 预算 2.13 USDT → qty ≈ 0.0000333 ≥ 持仓 10% (0.0001)？否 → no_add
        # 预算 2.13/64000 = 0.000033 < 0.0001 → 不加仓（预算不足保护）
        self.assertFalse(buy_acts)

    def test_levels_atr_adaptive(self):
        """高波动 → 止损线自动放宽（ATR 动态）。"""
        pm._atr_pct = lambda symbol: 5.0  # 5% ATR
        levels = pm.levels_for("BTCUSDT", atr_pct=5.0)
        self.assertGreater(levels["stop_loss_pct"], pm.DEFAULT_STOP_LOSS_PCT)

    def test_execute_writes_ledger_and_audit(self):
        self._write_orders(_seed_position(0.001, 64000.0))
        result = pm._execute(self.client, "BTCUSDT", "SELL", 0.001, "测试平仓")
        self.assertTrue(result["ok"])
        # 账本新增一条 SELL
        lines = pm.ORDERS_PATH.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 2)
        self.assertIn("SELL", lines[-1])
        # 审计新增
        audit_lines = pm.AUDIT_PATH.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(audit_lines), 1)
        self.assertIn("position_manage", audit_lines[0])


if __name__ == "__main__":
    unittest.main()

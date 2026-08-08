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

    def create_order(self, *, symbol, side, quantity, contract=False, pos_side=None):
        order = {"orderId": len(self.orders) + 1, "symbol": symbol, "side": side,
                 "status": "FILLED", "avgFillPrice": 64000.0, "quantity": quantity,
                 "contract": contract, "pos_side": pos_side}
        self.orders.append(order)
        return order

    def create_test_order(self, *, symbol, side, quantity):
        return self.create_order(symbol=symbol, side=side, quantity=quantity)


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
        pm._LAST_ORDERS.clear()  # 防重窗口测试隔离
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

    # —— 审查修复：熔断强制 / 防重 / 开仓引擎 / 参数学习 ——

    def test_halt_blocks_buy(self):
        """熔断时 BUY 冻结、SELL 放行（硬风控强制）。"""
        # 构造连亏 5 笔 → trading_halted
        orders = []
        for i in range(5):
            orders.append({"type": "testnet_order", "order_id": i + 10, "symbol": "BTCUSDT",
                           "side": "BUY", "order_type": "MARKET", "status": "FILLED",
                           "price": "0", "avg_fill_price": 64000.0, "quantity": "0.001",
                           "quote_qty": "64.0", "fee": None, "created_at": i,
                           "logged_at": "2026-08-05T00:00:00+00:00", "note": "losing"})
        # 卖出记录（亏损）——构造连亏
        for i in range(5):
            orders.append({"type": "testnet_order", "order_id": i + 20, "symbol": "BTCUSDT",
                           "side": "SELL", "order_type": "MARKET", "status": "FILLED",
                           "price": "0", "avg_fill_price": 63000.0, "quantity": "0.001",
                           "quote_qty": "63.0", "fee": None, "created_at": i,
                           "logged_at": "2026-08-05T00:00:00+00:00", "note": "loss"})
        self._write_orders(orders)
        # BUY 被冻结
        result = pm._execute(self.client, "BTCUSDT", "BUY", 0.001, "测试买入")
        self.assertFalse(result["ok"])
        self.assertEqual(result["action"], "BUY_blocked")
        # SELL 放行
        self.assertTrue(pm._risk_gate("BTCUSDT", "SELL")["ok"])

    def test_dedup_blocks_repeat(self):
        """防重：同一 symbol+side 窗口内只执行一次。"""
        pm._LAST_ORDERS.clear()
        self._write_orders(_seed_position(0.001, 64000.0))
        r1 = pm._execute(self.client, "BTCUSDT", "SELL", 0.001, "第一次")
        self.assertTrue(r1["ok"])
        r2 = pm._execute(self.client, "BTCUSDT", "SELL", 0.001, "第二次（应被防重拦截）")
        self.assertFalse(r2["ok"])
        self.assertEqual(r2["action"], "SELL_deduped")
        pm._LAST_ORDERS.clear()

    def test_open_position_gates(self):
        """开仓引擎：弱信号拒绝 / 已有持仓拒绝 / 非法方向拒绝 / sell 开空。"""
        pm._LAST_ORDERS.clear()
        self._write_orders([])  # 零持仓、现金 277
        # 弱信号
        weak = {"action": "buy", "strength": 0.3, "strategy": "test", "reason": "弱"}
        r = pm.open_position(self.client, "ETHUSDT", weak, 1800.0)
        self.assertFalse(r["ok"])
        self.assertIn("弱信号", r["reason"])
        # 非法方向（hold）拒绝
        r = pm.open_position(self.client, "ETHUSDT", {"action": "hold", "strength": 0.8},
                             1800.0)
        self.assertFalse(r["ok"])
        # sell 信号 → 合约开空（多空双向）
        pm.levels_for = lambda symbol, atr_pct=None: {"stop_loss_pct": 3.0,
                                                      "take_profit_pct": 6.0}
        r = pm.open_position(self.client, "ETHUSDT", {"action": "sell", "strength": 0.8},
                             1800.0, cash=1000.0)
        self.assertTrue(r["ok"])
        self.assertEqual(r["action"], "SELL_executed")
        self.assertEqual(self.client.orders[-1]["pos_side"], "short")
        # 正常开多：现金 277 → 风险预算 2.77 → risk_qty = 2.77/(1800*0.03)=0.0513；
        # 集中度上限 = 277*20%/1800 = 0.0308（cap 生效，单标的 ≤20% 现金）
        ok = {"action": "buy", "strength": 0.8, "strategy": "range_reversion",
              "reason": "震荡超卖低吸"}
        r = pm.open_position(self.client, "ETHUSDT", ok, 1800.0)
        self.assertTrue(r["ok"])
        self.assertEqual(r["action"], "BUY_executed")
        self.assertAlmostEqual(r["quantity"], 0.0308, places=3)  # 集中度 cap
        # 已有持仓 → 拒绝重复开仓
        pm._LAST_ORDERS.clear()
        r = pm.open_position(self.client, "ETHUSDT", ok, 1800.0)
        self.assertFalse(r["ok"])
        self.assertIn("已持有", r["reason"])
        pm._LAST_ORDERS.clear()

    def test_learn_params_writes_file(self):
        """参数自主升级：learn_params 产出 strategy_params.json（运行时生效）。"""
        from autotrader import learning_engine as le2
        from autotrader import strategy as strat
        le2.PARAMS_PATH = pm.ARTIFACTS / "strategy_params.json"
        le2.RULES_PATH = pm.ARTIFACTS / "event_rules.json"
        le2.ACTIONS_PATH = pm.ARTIFACTS / "learn_actions.jsonl"
        # 构造生效的偏空规则
        le2.RULES_PATH.write_text(json.dumps({
            "rules": [{"id": "bear_after_ab", "action": "deboost_buy", "active": True}]
        }), encoding="utf-8")
        report = le2.learn_params()
        self.assertTrue(report["learned"])
        p = json.loads(le2.PARAMS_PATH.read_text(encoding="utf-8"))
        self.assertIn("params", p)
        # 偏空规则 → 15m rsi_buy_max 下调（72→69）
        self.assertEqual(p["params"]["15m"]["rsi_buy_max"], 69.0)
        # apply_strategies 应读取外部参数（自主升级生效）
        ind = {"price": 100.0, "ema20": 101.0, "ema50": 102.0, "rsi14": 70.0,
               "atr14": 1.0, "volume_ratio": 1.5, "change_24h_pct": 1.0, "trend": "sideways"}
        orig = strat._load_external_params
        strat._load_external_params = lambda: {"15m": {"rsi_buy_max": 69.0}}
        try:
            sigs = strat.apply_strategies(ind, timeframe="15m")
            # rsi_buy_max=69 → RSI 70 不再触发 trend_breakout buy
            self.assertFalse(any(s.action == "buy" and s.strategy == "trend_breakout"
                                 for s in sigs))
        finally:
            strat._load_external_params = orig
        le2.PARAMS_PATH.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()

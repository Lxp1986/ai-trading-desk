"""Tests for strategy performance tracking & adaptive weighting."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from autotrader.strategy import StrategySignal
from autotrader.strategy_tracker import (
    PERF_PATH, WEIGHTS_PATH, apply_weights, load_perf, record_signal_result,
    strategy_weights, update_weights,
)


class TestStrategyTracker(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        import autotrader.strategy_tracker as module
        self._old_perf = module.PERF_PATH
        self._old_weights = module.WEIGHTS_PATH
        module.PERF_PATH = Path(self._tmp.name) / "perf.jsonl"
        module.WEIGHTS_PATH = Path(self._tmp.name) / "weights.json"
        self.module = module

    def tearDown(self) -> None:
        import autotrader.strategy_tracker as module
        module.PERF_PATH = self._old_perf
        module.WEIGHTS_PATH = self._old_weights
        self._tmp.cleanup()

    def test_record_and_load(self) -> None:
        self.module.record_signal_result(strategy="trend_breakout", symbol="BTC", pnl=5.0)
        records = self.module.load_perf("trend_breakout")
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["pnl"], 5.0)

    def test_no_records_default_weight(self) -> None:
        self.assertEqual(self.module.strategy_weights(), {})

    def test_loss_penalty(self) -> None:
        for _ in range(4):
            self.module.record_signal_result(strategy="trend_breakout", symbol="BTC", pnl=-1.0)
        weights = self.module.strategy_weights()
        # 4 笔全亏：最近5笔亏损4 ≥3 → 降权 0.5；连续4 <5 未停用
        self.assertEqual(weights["trend_breakout"], 0.5)

    def test_disabled_after_streak(self) -> None:
        for _ in range(5):
            self.module.record_signal_result(strategy="range_reversion", symbol="BTC", pnl=-1.0)
        weights = self.module.strategy_weights()
        self.assertEqual(weights["range_reversion"], 0.0)

    def test_apply_weights_filters_and_scales(self) -> None:
        for _ in range(5):
            self.module.record_signal_result(strategy="defensive", symbol="BTC", pnl=-2.0)
        self.module.record_signal_result(strategy="trend_breakout", symbol="BTC", pnl=3.0)
        weights = self.module.strategy_weights()
        signals = [
            StrategySignal("defensive", "hold", 0.7, "防守"),
            StrategySignal("trend_breakout", "buy", 0.8, "突破"),
        ]
        filtered = apply_weights(signals, weights)
        self.assertEqual(len(filtered), 1)  # defensive 被停用过滤
        self.assertEqual(filtered[0].strategy, "trend_breakout")
        self.assertEqual(filtered[0].strength, 0.8)  # 权重 1.0 不缩放

    def test_update_weights_persists(self) -> None:
        for _ in range(5):
            self.module.record_signal_result(strategy="event_driven", symbol="BTC", pnl=-1.0)
        weights = self.module.update_weights()
        self.assertEqual(weights["event_driven"], 0.0)
        self.assertTrue(self.module.WEIGHTS_PATH.exists())


if __name__ == "__main__":
    unittest.main()

"""Tests for multi-symbol opportunity scanner."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from autotrader.opportunities import (
    CANDIDATE_SYMBOLS, Opportunity, load_opportunities, scan_opportunities,
    scan_one, save_opportunities,
)


class FakeKlines:
    """构造 60 根单调 K 线（含完整 OHLCV 字段）。"""

    def __init__(self, base: float, step: float, vol: float = 100.0):
        self.base = base
        self.step = step
        self.vol = vol

    def __call__(self, symbol, interval, limit):
        rows = []
        for i in range(limit):
            o = self.base + self.step * i
            c = o + self.step
            rows.append({
                "open_time": 1700000000000 + i * 900_000,
                "open": str(o), "high": str(max(o, c) + 1),
                "low": str(min(o, c) - 1), "close": str(c),
                "volume": str(self.vol),
                "quote_volume": str(self.vol * c), "trades": 10,
            })
        return rows


class TestOpportunities(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        import autotrader.opportunities as module
        self._old_path = module.OPPORTUNITIES_PATH
        module.OPPORTUNITIES_PATH = Path(self._tmp.name) / "opportunities.json"
        self.module = module
        self.client = MagicMock()
        self.client.klines = FakeKlines(base=100, step=0.1)

    def tearDown(self) -> None:
        import autotrader.opportunities as module
        module.OPPORTUNITIES_PATH = self._old_path
        self._tmp.cleanup()

    def test_scan_one_returns_opportunity(self) -> None:
        opp = scan_one(self.client, "TESTUSDT")
        self.assertIsNotNone(opp)
        assert opp is not None
        self.assertEqual(opp.symbol, "TESTUSDT")
        self.assertGreater(opp.price, 0)
        self.assertIn(opp.trend, ("trend_up", "trend_down", "sideways"))
        self.assertTrue(0 < opp.rsi14 <= 100)

    def test_scan_one_filters_invalid_data(self) -> None:
        # RSI 无效（全平 K 线 → RSI 计算可能为 50 恒值）→ 至少不抛异常
        flat = MagicMock()
        flat.klines = FakeKlines(base=100, step=0.0, vol=0.0)
        opp = scan_one(flat, "FLATUSDT")
        # step=0 时 RSI 可能为 NaN 被过滤，也可能 50——两种都合法
        if opp is not None:
            self.assertTrue(0 < opp.rsi14 <= 100)

    def test_scan_opportunities_shape(self) -> None:
        result = scan_opportunities(self.client, symbols=["BTCUSDT", "ETHUSDT"])
        self.assertEqual(result["scanned"], 2)
        self.assertIsInstance(result["ranked"], list)
        self.assertIsInstance(result["opportunities"], list)
        self.assertTrue(result["updated_at"])

    def test_save_and_load_roundtrip(self) -> None:
        payload = {"ranked": [], "opportunities": [], "scanned": 3, "updated_at": "now"}
        save_opportunities(payload)
        loaded = load_opportunities()
        self.assertEqual(loaded["scanned"], 3)
        self.assertEqual(loaded["updated_at"], "now")

    def test_load_missing_file(self) -> None:
        self.module.OPPORTUNITIES_PATH = Path(self._tmp.name) / "nope.json"
        result = load_opportunities()
        self.assertEqual(result["scanned"], 0)

    def test_best_signal_ordering(self) -> None:
        opp = Opportunity("X", 1.0, "sideways", 50, 1.0, 0.0,
                          signals=[{"strategy": "a", "action": "buy", "strength": 0.5},
                                   {"strategy": "b", "action": "buy", "strength": 0.8}])
        best = opp.best_signal
        self.assertIsNotNone(best)
        assert best is not None
        self.assertEqual(best["strategy"], "b")

    def test_candidate_pool(self) -> None:
        self.assertGreaterEqual(len(CANDIDATE_SYMBOLS), 15)
        self.assertIn("BTCUSDT", CANDIDATE_SYMBOLS)


if __name__ == "__main__":
    unittest.main()

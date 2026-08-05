"""Tests for the Hermes integration layer (thesis registration, usage tracking, fallback)."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from autotrader.llm import deterministic_fallback, record_usage, register_thesis
from autotrader.models import MarketSnapshot, Side


class HermesIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.usage_tmp = tempfile.TemporaryDirectory()
        self.usage_path = Path(self.usage_tmp.name) / "token_usage.json"
        import autotrader.llm as llm_mod

        self._orig_path = llm_mod._USAGE_PATH
        llm_mod._USAGE_PATH = self.usage_path

    def tearDown(self) -> None:
        import autotrader.llm as llm_mod

        llm_mod._USAGE_PATH = self._orig_path
        self.usage_tmp.cleanup()

    def test_record_usage_accumulates(self) -> None:
        first = record_usage("deepseek", "deepseek-v4-flash", 100, 50)
        self.assertEqual(first["total_tokens"], 150)
        self.assertEqual(first["api_calls"], 1)
        second = record_usage("deepseek", "deepseek-v4-flash", 10, 5)
        self.assertEqual(second["total_tokens"], 165)
        self.assertEqual(second["api_calls"], 2)
        self.assertEqual(second["input_tokens"], 110)
        self.assertEqual(second["output_tokens"], 55)

    def test_record_usage_ignores_negative(self) -> None:
        result = record_usage("deepseek", "deepseek-v4-flash", -5, 3)
        self.assertEqual(result["total_tokens"], 3)

    def test_register_hermes_thesis_buy(self) -> None:
        snapshot = MarketSnapshot("BTC/USDT", 100_000, 1.8, "trend_up")
        intent = register_thesis(snapshot, {
            "side": "buy",
            "thesis": "Hermes草拟：测试网行情趋势确认，等待小仓验证",
            "invalidation": "价格跌破结构失效位",
            "stop_price": 98_000,
            "confidence": 0.62,
        })
        self.assertEqual(intent.source, "hermes")
        self.assertEqual(intent.side, Side.BUY)
        self.assertGreater(intent.quantity, 0)
        self.assertEqual(intent.stop_price, 98_000.0)

    def test_register_thesis_hold_default(self) -> None:
        snapshot = MarketSnapshot("ETH/USDT", 3_000, 1.0, "sideways")
        intent = register_thesis(snapshot, {"side": "unknown", "confidence": 9.9})
        self.assertEqual(intent.side, Side.HOLD)
        self.assertEqual(intent.quantity, 0.0)
        self.assertEqual(intent.confidence, 1.0)  # clamped to [0,1]

    def test_register_thesis_bad_stop_price(self) -> None:
        snapshot = MarketSnapshot("BTC/USDT", 100_000, 1.8, "trend_up")
        intent = register_thesis(snapshot, {"side": "sell", "stop_price": "not-a-number", "confidence": 0.4})
        self.assertEqual(intent.side, Side.SELL)
        self.assertIsNone(intent.stop_price)

    def test_deterministic_fallback_buy_on_trend_confirmation(self) -> None:
        snapshot = MarketSnapshot("BTC/USDT", 100_000, 1.8, "trend_up")
        intent = deterministic_fallback(snapshot)
        self.assertEqual(intent.side, Side.BUY)
        self.assertGreater(intent.quantity, 0)
        self.assertEqual(intent.source, "deterministic_fallback")

    def test_deterministic_fallback_holds_otherwise(self) -> None:
        snapshot = MarketSnapshot("ETH/USDT", 3_000, 1.0, "sideways")
        intent = deterministic_fallback(snapshot)
        self.assertEqual(intent.side, Side.HOLD)
        self.assertEqual(intent.quantity, 0.0)


if __name__ == "__main__":
    unittest.main()

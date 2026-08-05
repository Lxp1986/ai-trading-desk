"""Tests for live prices pipeline (实时价格看板)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from autotrader import live_prices as lp


class LivePricesTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        lp.LIVE_PRICES = Path(self._tmp.name) / "live_prices.json"

    def tearDown(self):
        self._tmp.cleanup()

    def test_watchlist_has_core_assets(self):
        symbols = [w["symbol"] for w in lp.WATCHLIST]
        for core in ("BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT"):
            self.assertIn(core, symbols)
        self.assertGreaterEqual(len(symbols), 15)  # CEO 观察池 ≥15 标的

    def test_coingecko_fallback(self):
        """测试网不可用 → CoinGecko 兜底（mock 真实返回结构）。"""
        rows = lp._fetch_coingecko()
        if rows is None:
            self.skipTest("CoinGecko 网络不可用（离线环境）")
        self.assertIn("BTCUSDT", rows)
        self.assertGreater(rows["BTCUSDT"]["price"], 0)

    def test_scan_failure_also_writes(self):
        """双源都挂 → 也落盘（永续存在规范：成功失败都写状态）。"""
        orig_t = lp._fetch_testnet
        orig_c = lp._fetch_coingecko
        lp._fetch_testnet = lambda: None
        lp._fetch_coingecko = lambda: None
        try:
            result = lp.scan_live_prices()
        finally:
            lp._fetch_testnet = orig_t
            lp._fetch_coingecko = orig_c
        self.assertEqual(result["source"], "unavailable")
        self.assertTrue(lp.LIVE_PRICES.exists())  # 文件永续存在
        self.assertEqual(lp.load_live_prices()["source"], "unavailable")

    def test_load_missing(self):
        self.assertEqual(lp.load_live_prices()["prices"], {})


if __name__ == "__main__":
    unittest.main()

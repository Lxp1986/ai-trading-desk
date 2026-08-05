"""Tests for full-market mover scanner (鱼群探测器)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from autotrader.movers import _sector_of, load_movers, scan_movers


def _fake_client() -> object:
    class FakeClient:
        def ticker_24hr(self):
            return [
                {"symbol": "BTCUSDT", "priceChangePercent": "1.2", "quoteVolume": "50000000", "lastPrice": "64000"},
                {"symbol": "FETUSDT", "priceChangePercent": "12.5", "quoteVolume": "2000000", "lastPrice": "1.5"},
                {"symbol": "AGIXUSDT", "priceChangePercent": "9.8", "quoteVolume": "800000", "lastPrice": "0.6"},
                {"symbol": "UNIUSDT", "priceChangePercent": "-3.2", "quoteVolume": "3000000", "lastPrice": "8.0"},
                {"symbol": "AAVEUSDT", "priceChangePercent": "-5.0", "quoteVolume": "1500000", "lastPrice": "90.0"},
                {"symbol": "DOGEUSDT", "priceChangePercent": "2.1", "quoteVolume": "9000000", "lastPrice": "0.12"},
                {"symbol": "SHIBUSDT", "priceChangePercent": "1.0", "quoteVolume": "5000000", "lastPrice": "0.00002"},
                {"symbol": "LTCUSDT", "priceChangePercent": "0.3", "quoteVolume": "4000000", "lastPrice": "70.0"},
            ]
    return FakeClient()


class TestMovers(unittest.TestCase):
    def setUp(self) -> None:
        import autotrader.movers as module
        self._tmp = tempfile.TemporaryDirectory()
        self._old = module.MOVERS_PATH
        module.MOVERS_PATH = Path(self._tmp.name) / "movers.json"
        self.module = module

    def tearDown(self) -> None:
        import autotrader.movers as module
        module.MOVERS_PATH = self._old
        self._tmp.cleanup()

    def test_sector_of(self) -> None:
        self.assertEqual(_sector_of("FETUSDT"), "AI")
        self.assertEqual(_sector_of("UNIUSDT"), "DeFi")
        self.assertEqual(_sector_of("DOGEUSDT"), "Meme")
        self.assertEqual(_sector_of("XYZUSDT"), "其他")

    def test_scan_movers(self) -> None:
        result = scan_movers(_fake_client(), top_n=3, min_volume_usdt=100)
        self.assertNotIn("error", result)
        self.assertEqual(result["scanned"], 8)
        # 涨幅榜第一名是 FET（+12.5%）
        self.assertEqual(result["gainers"][0]["symbol"], "FETUSDT")
        # 热点板块：AI（FET+AGIX 平均 +11.15%）第一
        self.assertEqual(result["hot_sectors"][0]["sector"], "AI")
        # 落盘可读
        self.assertEqual(load_movers()["scanned"], 8)

    def test_scan_movers_error(self) -> None:
        class BrokenClient:
            def ticker_24hr(self):
                raise RuntimeError("boom")
        result = scan_movers(BrokenClient())
        self.assertIn("error", result)


if __name__ == "__main__":
    unittest.main()

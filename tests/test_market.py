"""Tests for market state classifier and kline persistence."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from autotrader.market import (
    atr, build_snapshot, classify_market, compute_indicators, ema,
    load_klines, rsi, store_klines,
)


def _mk_klines(closes: list[float], volumes: list[float] | None = None) -> list[dict]:
    result = []
    volumes = volumes or [1.0] * len(closes)
    for i, (c, v) in enumerate(zip(closes, volumes)):
        result.append({
            "open_time": 1_700_000_000_000 + i * 900_000,
            "open": c, "high": c * 1.01, "low": c * 0.99,
            "close": c, "volume": v, "quote_volume": c * v, "trades": 100,
        })
    return result


class MarketClassifierTests(unittest.TestCase):
    def test_ema_basic(self) -> None:
        self.assertAlmostEqual(ema([1.0] * 10, 5), 1.0)

    def test_rsi_extremes(self) -> None:
        self.assertGreater(rsi([1.0, 2.0, 3.0, 4.0, 5.0, 6.0]), 95)
        self.assertLess(rsi([6.0, 5.0, 4.0, 3.0, 2.0, 1.0]), 5)

    def test_atr_positive(self) -> None:
        klines = _mk_klines([100.0, 102.0, 101.0, 103.0, 105.0])
        self.assertGreater(atr(klines), 0)

    def test_classify_trend_up(self) -> None:
        closes = [100 + i * 0.5 for i in range(60)]
        ind = compute_indicators(_mk_klines(closes))
        self.assertEqual(classify_market(ind), "trend_up")

    def test_classify_trend_down(self) -> None:
        closes = [150 - i * 0.5 for i in range(60)]
        ind = compute_indicators(_mk_klines(closes))
        self.assertEqual(classify_market(ind), "trend_down")

    def test_classify_sideways(self) -> None:
        import math

        # 真实震荡序列：涨跌交替、价格围绕均值波动
        closes = [100 + math.sin(i * 0.7) * 0.5 for i in range(60)]
        ind = compute_indicators(_mk_klines(closes))
        self.assertEqual(classify_market(ind), "sideways")

    def test_volume_ratio(self) -> None:
        volumes = [1.0] * 59 + [3.0]
        ind = compute_indicators(_mk_klines([100.0] * 60, volumes))
        self.assertAlmostEqual(ind["volume_ratio"], 3.0, places=2)


class KlinePersistenceTests(unittest.TestCase):
    def test_store_and_load_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "market.db"
            klines = _mk_klines([100.0, 101.0, 102.0])
            written = store_klines(klines, symbol="BTCUSDT", interval="15m", db_path=db)
            self.assertEqual(written, 3)
            loaded = load_klines("BTCUSDT", "15m", db_path=db)
            self.assertEqual(len(loaded), 3)
            self.assertAlmostEqual(loaded[-1]["close"], 102.0)

    def test_store_upsert(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "market.db"
            k1 = _mk_klines([100.0])
            k2 = _mk_klines([110.0])
            store_klines(k1, db_path=db)
            store_klines(k2, db_path=db)
            loaded = load_klines(db_path=db)
            self.assertEqual(len(loaded), 1)
            self.assertAlmostEqual(loaded[0]["close"], 110.0)


if __name__ == "__main__":
    unittest.main()

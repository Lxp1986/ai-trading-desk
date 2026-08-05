"""Tests for multi-timeframe adaptive selection (多周期智能选择)."""

from __future__ import annotations

import unittest

from autotrader.market import compute_indicators
from autotrader.timeframes import TIMEFRAMES, choose_timeframe


def make_klines(prices: list[float], vol: float = 100.0) -> list[dict]:
    """构造 K 线序列（open_time 递增，用于指标计算）。"""
    klines = []
    for i, p in enumerate(prices):
        klines.append({
            "open_time": 1700000000000 + i * 60_000,
            "open": p, "high": p * 1.001, "low": p * 0.999,
            "close": p, "volume": vol, "quote_volume": p * vol,
            "trades": 10,
        })
    return klines


class TimeframesTest(unittest.TestCase):
    def test_timeline_full_coverage(self):
        """全周期覆盖：5m ~ 1w，短线到极长线。"""
        labels = [h for _, h, _ in TIMEFRAMES]
        self.assertIn("5m", [tf for tf, _, _ in TIMEFRAMES])
        self.assertIn("1w", [tf for tf, _, _ in TIMEFRAMES])
        self.assertEqual(labels[0], "短线")
        self.assertEqual(labels[-1], "极长线")

    def test_high_volatility_short(self):
        """高波动（ATR≥1.2%）→ 短线 5m。"""
        base = 100.0
        prices = []
        p = base
        for i in range(60):
            p = p * (1.015 if i % 2 else 0.985)  # ±1.5% 摆动（高波动）
            prices.append(p)
        ind = compute_indicators(make_klines(prices))
        choice = choose_timeframe(ind)
        self.assertEqual(choice["timeframe"], "5m")
        self.assertEqual(choice["horizon"], "短线")

    def test_low_volatility_long(self):
        """低波动无趋势（横向小幅摆动）→ 长线 4h。"""
        prices = [100.0 + (i % 7 - 3) * 0.005 for i in range(60)]  # ±0.015 摆动（无趋势）
        ind = compute_indicators(make_klines(prices))
        choice = choose_timeframe(ind)
        self.assertEqual(choice["timeframe"], "4h")
        self.assertEqual(choice["horizon"], "长线")

    def test_strong_trend_1h(self):
        """有趋势（EMA 多头排列）→ 1h 顺趋势。"""
        prices = [100.0 * (1.01 ** i) for i in range(60)]  # 稳定上涨趋势
        ind = compute_indicators(make_klines(prices))
        choice = choose_timeframe(ind)
        self.assertIn(choice["timeframe"], ("1h", "15m", "5m"))  # 趋势明确不得选长线
        self.assertNotEqual(choice["horizon"], "长线")

    def test_reason_always_present(self):
        ind = compute_indicators(make_klines([100.0] * 40))
        choice = choose_timeframe(ind)
        self.assertTrue(choice["reason"])


if __name__ == "__main__":
    unittest.main()

"""Tests for deterministic news & on-chain research pipelines."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from autotrader.news_research import keyword_grade, load_events, scan_news
from autotrader.onchain import load_signals, scan_btc_onchain, signal_confidence


class TestNewsPipeline(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        import autotrader.news_research as module
        self._old = module.EVENTS_PATH
        module.EVENTS_PATH = Path(self._tmp.name) / "events.jsonl"
        self.module = module

    def tearDown(self) -> None:
        import autotrader.news_research as module
        module.EVENTS_PATH = self._old
        self._tmp.cleanup()

    def test_keyword_grade_a_bull(self) -> None:
        grade, bias = keyword_grade("SEC Approves Spot Bitcoin ETF as institutions pile in")
        self.assertEqual(grade, "A")
        self.assertEqual(bias, "bull")

    def test_keyword_grade_a_bear(self) -> None:
        grade, bias = keyword_grade("Fed hikes rates, crypto regulation crackdown announced")
        self.assertEqual(grade, "A")
        self.assertEqual(bias, "bear")

    def test_keyword_grade_b(self) -> None:
        grade, _ = keyword_grade("Ethereum whale moves 50,000 ETH to exchange")
        self.assertEqual(grade, "B")

    def test_keyword_grade_b_bull(self) -> None:
        grade, bias = keyword_grade("New partnership launches whale investment fund inflows")
        self.assertEqual(grade, "B")
        self.assertEqual(bias, "bull")

    def test_keyword_grade_c(self) -> None:
        grade, _ = keyword_grade("Daily crypto market roundup and price action")
        self.assertEqual(grade, "C")

    def test_scan_news_dedup(self) -> None:
        # 第一次扫描（无网络则 errors 非空，不落盘也不报错）
        r1 = scan_news(max_items=10)
        self.assertIn("fetched", r1)
        self.assertIn("recorded", r1)


class TestOnchainPipeline(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        import autotrader.onchain as module
        self._old = module.ONCHAIN_PATH
        module.ONCHAIN_PATH = Path(self._tmp.name) / "onchain.jsonl"
        self.module = module

    def tearDown(self) -> None:
        import autotrader.onchain as module
        module.ONCHAIN_PATH = self._old
        self._tmp.cleanup()

    def test_scan_btc_onchain_shape(self) -> None:
        result = scan_btc_onchain()
        self.assertIn("congestion_fee_sat_vb", result)
        self.assertIn("whale_txns", result)
        self.assertIn("signals_recorded", result)

    def test_signal_confidence(self) -> None:
        wallets = [
            {"direction": "bullish"}, {"direction": "bullish"}, {"direction": "bearish"},
        ]
        # 2 钱包同意 → 0.2 + 0.15×2 + 0.15(量) + 0.2(突破) = 0.85
        self.assertEqual(signal_confidence(wallets, True, True), 0.85)
        self.assertEqual(signal_confidence([], True, True), 0.0)

    def test_load_signals_empty(self) -> None:
        self.assertEqual(load_signals(), [])


if __name__ == "__main__":
    unittest.main()

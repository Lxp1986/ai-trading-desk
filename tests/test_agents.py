"""Tests for strategy library, sentiment, news research, onchain, event trader."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from autotrader.event_trader import checklist, phase_of, plan
from autotrader.news_research import EVENTS_PATH, grade_event, load_events, record_event
from autotrader.onchain import load_signals, record_signal, signal_confidence
from autotrader.sentiment import SentimentState, assess_sentiment
from autotrader.strategy import apply_strategies, defensive, pullback_rebound, range_reversion, trend_breakout


class TestStrategy(unittest.TestCase):
    def test_trend_breakout_bull(self) -> None:
        ind = {"price": 100.0, "ema20": 99.0, "ema50": 97.0, "rsi14": 58.0,
               "atr14": 1.0, "volume_ratio": 1.8}
        signal = trend_breakout(ind)
        self.assertIsNotNone(signal)
        self.assertEqual(signal.action, "buy")  # type: ignore[union-attr]
        self.assertEqual(signal.strategy, "trend_breakout")

    def test_trend_breakout_bear(self) -> None:
        ind = {"price": 90.0, "ema20": 92.0, "ema50": 95.0, "rsi14": 42.0,
               "atr14": 1.0, "volume_ratio": 1.5}
        signal = trend_breakout(ind)
        self.assertIsNotNone(signal)
        self.assertEqual(signal.action, "sell")  # type: ignore[union-attr]

    def test_no_signal_in_neutral(self) -> None:
        ind = {"price": 100.0, "ema20": 100.5, "ema50": 99.0, "rsi14": 50.0,
               "atr14": 1.0, "volume_ratio": 1.0}
        self.assertIsNone(trend_breakout(ind))
        self.assertIsNone(pullback_rebound(ind))

    def test_pullback_rebound_bull(self) -> None:
        ind = {"price": 97.5, "ema20": 99.0, "ema50": 97.0, "rsi14": 42.0,
               "atr14": 1.0, "volume_ratio": 1.0}
        signal = pullback_rebound(ind)
        self.assertIsNotNone(signal)
        self.assertEqual(signal.action, "buy")  # type: ignore[union-attr]

    def test_range_reversion_only_sideways(self) -> None:
        ind = {"price": 100.0, "ema20": 100.0, "ema50": 100.0, "rsi14": 25.0,
               "atr14": 1.0, "volume_ratio": 1.0, "trend": "sideways"}
        signal = range_reversion(ind)
        self.assertIsNotNone(signal)
        self.assertEqual(signal.action, "buy")  # type: ignore[union-attr]

    def test_defensive_on_high_volatility(self) -> None:
        ind = {"price": 100.0, "ema20": 99.0, "ema50": 97.0, "rsi14": 50.0,
               "atr14": 5.0, "volume_ratio": 1.0}
        signal = defensive(ind)
        self.assertIsNotNone(signal)
        self.assertEqual(signal.action, "hold")  # type: ignore[union-attr]

    def test_event_driven_gate(self) -> None:
        events = [{"id": "e1", "title": "X", "grade": "A", "bias": "bull", "impact": "high"}]
        signals = apply_strategies(
            {"price": 100.0, "ema20": 99.0, "ema50": 97.0, "rsi14": 50.0,
             "atr14": 1.0, "volume_ratio": 1.0, "trend": "sideways"},
            events=events,
        )
        self.assertTrue(any(s.strategy == "event_driven" and s.action == "buy" for s in signals))


class TestSentiment(unittest.TestCase):
    def test_fomo_with_high_funding(self) -> None:
        state = assess_sentiment(
            ind={"rsi14": 75.0, "volume_ratio": 2.5},
            funding={"funding_annual_pct": 80.0},
        )
        self.assertIsInstance(state, SentimentState)
        self.assertEqual(state.state, "fomo")
        self.assertGreater(state.score, 0)

    def test_panic_with_negative_funding(self) -> None:
        state = assess_sentiment(
            ind={"rsi14": 15.0},
            funding={"funding_annual_pct": -40.0},
        )
        self.assertEqual(state.state, "panic")
        self.assertLess(state.score, 0)

    def test_neutral(self) -> None:
        state = assess_sentiment(ind={"rsi14": 50.0}, funding={"funding_annual_pct": 5.0})
        self.assertEqual(state.state, "neutral")


class TestNewsResearch(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._old = EVENTS_PATH
        import autotrader.news_research as module
        module.EVENTS_PATH = Path(self._tmp.name) / "events.jsonl"
        self.module = module

    def tearDown(self) -> None:
        import autotrader.news_research as module
        module.EVENTS_PATH = self._old
        self._tmp.cleanup()

    def test_grade_rules(self) -> None:
        self.assertEqual(grade_event(verified=True, official=True, expected_gap=True, persistence=True, source_quality="official"), "A")
        self.assertEqual(grade_event(verified=False, official=False, expected_gap=False, persistence=False, source_quality="rumor"), "C")

    def test_record_and_load_roundtrip(self) -> None:
        event = self.module.record_event(title="测试", impact="high", assets=["BTC"], grade="A", bias="bull")
        loaded = self.module.load_events()
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0]["title"], "测试")
        self.assertEqual(loaded[0]["grade"], "A")


class TestOnchain(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._old = None
        import autotrader.onchain as module
        self._old = module.ONCHAIN_PATH
        module.ONCHAIN_PATH = Path(self._tmp.name) / "onchain.jsonl"
        self.module = module

    def tearDown(self) -> None:
        import autotrader.onchain as module
        module.ONCHAIN_PATH = self._old
        self._tmp.cleanup()

    def test_signal_roundtrip(self) -> None:
        self.module.record_signal(kind="whale", symbol="BTC", direction="bullish",
                                  evidence={"qty": 100}, confidence=0.6)
        signals = self.module.load_signals()
        self.assertEqual(len(signals), 1)
        self.assertEqual(signals[0]["direction"], "bullish")

    def test_confidence_requires_consensus(self) -> None:
        one = [{"direction": "bullish"}]
        self.assertLess(signal_confidence(one, volume_confirmed=False, breakout_confirmed=False), 0.5)
        three = [{"direction": "bullish"} for _ in range(3)]
        high = signal_confidence(three, volume_confirmed=True, breakout_confirmed=True)
        self.assertGreater(high, 0.7)


class TestEventTrader(unittest.TestCase):
    def test_phase_progression(self) -> None:
        from datetime import datetime, timedelta, timezone
        base = datetime.now(timezone.utc)
        self.assertEqual(phase_of(base.isoformat(), now=base.isoformat()), "confirmation")
        later = (base + timedelta(hours=2)).isoformat()
        self.assertEqual(phase_of(base.isoformat(), now=later), "first_wave")
        day_later = (base + timedelta(hours=30)).isoformat()
        self.assertEqual(phase_of(base.isoformat(), now=day_later), "distribution")

    def test_checklist_per_phase(self) -> None:
        self.assertTrue(any("分批" in item for item in checklist("first_wave")))

    def test_plan_wait_without_bias(self) -> None:
        p = plan({"id": "e1", "title": "X", "time": None, "bias": None})
        self.assertEqual(p.direction, "wait")


if __name__ == "__main__":
    unittest.main()

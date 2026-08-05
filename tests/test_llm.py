"""Tests for the LLM research layer (degradation and usage tracking)."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from autotrader.llm import LLMUnavailableError, chat_json, deterministic_fallback, draft_thesis, record_usage
from autotrader.models import MarketSnapshot, Side


class LLMTests(unittest.TestCase):
    def setUp(self) -> None:
        self.usage_tmp = tempfile.TemporaryDirectory()
        self.usage_path = Path(self.usage_tmp.name) / "token_usage.json"
        # Point the module at a temp usage file by monkeypatching the path.
        import autotrader.llm as llm_mod

        self._orig_path = llm_mod._USAGE_PATH
        llm_mod._USAGE_PATH = self.usage_path

    def tearDown(self) -> None:
        import autotrader.llm as llm_mod

        llm_mod._USAGE_PATH = self._orig_path
        self.usage_tmp.cleanup()

    def test_chat_json_requires_key(self) -> None:
        with self._env({"LLM_API_KEY": "", "DEEPSEEK_API_KEY": ""}):
            with self.assertRaises(LLMUnavailableError):
                chat_json([{"role": "user", "content": "hi"}])

    def test_record_usage_accumulates(self) -> None:
        first = record_usage("deepseek", "deepseek-chat", 100, 50)
        self.assertEqual(first["total_tokens"], 150)
        self.assertEqual(first["api_calls"], 1)
        second = record_usage("deepseek", "deepseek-chat", 10, 5)
        self.assertEqual(second["total_tokens"], 165)
        self.assertEqual(second["api_calls"], 2)
        self.assertEqual(second["input_tokens"], 110)
        self.assertEqual(second["output_tokens"], 55)

    def test_record_usage_ignores_negative(self) -> None:
        result = record_usage("deepseek", "deepseek-chat", -5, 3)
        self.assertEqual(result["total_tokens"], 3)

    def test_draft_thesis_degrades_without_key(self) -> None:
        snapshot = MarketSnapshot("BTC/USDT", 100_000, 1.8, "trend_up")
        with self._env({"LLM_API_KEY": "", "DEEPSEEK_API_KEY": ""}):
            intent, meta = draft_thesis(snapshot, "强趋势，量能放大", use_llm=True)
        self.assertTrue(meta["degraded"])
        self.assertEqual(intent.source, "deterministic_fallback")
        self.assertIn("确定性降级", intent.thesis)

    def test_deterministic_fallback_buy_on_trend_confirmation(self) -> None:
        snapshot = MarketSnapshot("BTC/USDT", 100_000, 1.8, "trend_up")
        intent = deterministic_fallback(snapshot)
        self.assertEqual(intent.side, Side.BUY)
        self.assertGreater(intent.quantity, 0)

    def test_deterministic_fallback_holds_otherwise(self) -> None:
        snapshot = MarketSnapshot("ETH/USDT", 3_000, 1.0, "sideways")
        intent = deterministic_fallback(snapshot)
        self.assertEqual(intent.side, Side.HOLD)
        self.assertEqual(intent.quantity, 0.0)

    def test_draft_thesis_disabled_flag(self) -> None:
        snapshot = MarketSnapshot("BTC/USDT", 100_000, 1.8, "trend_up")
        intent, meta = draft_thesis(snapshot, "强趋势", use_llm=False)
        self.assertTrue(meta["degraded"])
        self.assertEqual(intent.source, "deterministic_fallback")

    def _env(self, overrides: dict[str, str]):
        return _EnvOverride(overrides)


class _EnvOverride:
    def __init__(self, overrides: dict[str, str]) -> None:
        self.overrides = overrides
        self.saved: dict[str, str | None] = {}

    def __enter__(self):
        for key, value in self.overrides.items():
            self.saved[key] = os.environ.get(key)
            if value:
                os.environ[key] = value
            else:
                os.environ.pop(key, None)
        return self

    def __exit__(self, *args):
        for key, value in self.saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


if __name__ == "__main__":
    unittest.main()

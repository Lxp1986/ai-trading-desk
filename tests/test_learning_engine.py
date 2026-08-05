"""Tests for learning_engine (事件驱动学习闭环 · 确定性可验证)."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from autotrader import learning_engine as le


class LearningEngineTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_art = le.ARTIFACTS
        le.ARTIFACTS = Path(self.tmp.name)
        le.PERF_PATH = le.ARTIFACTS / "perf.jsonl"
        le.EVENTS_PATH = le.ARTIFACTS / "events.jsonl"
        le.WEIGHTS_PATH = le.ARTIFACTS / "strategy_weights.json"
        le.RULES_PATH = le.ARTIFACTS / "event_rules.json"
        le.ACTIONS_PATH = le.ARTIFACTS / "learn_actions.jsonl"

    def tearDown(self):
        le.ARTIFACTS = self.old_art
        self.tmp.cleanup()

    def test_no_perf_returns_not_learned(self):
        report = le.learn_from_trades()
        self.assertFalse(report["learned"])

    def test_trade_learning_weights(self):
        """胜率高的策略保持 1.0，连亏的降权/停用。"""
        now = datetime.now(timezone.utc)
        with le.PERF_PATH.open("w", encoding="utf-8") as f:
            # trend_breakout: 4 笔 3 胜 1 负 → 胜率 75% → 1.0
            for pnl in [5.0, 3.0, -2.0, 4.0]:
                f.write(json.dumps({"strategy": "trend_breakout", "pnl": pnl,
                                    "symbol": "BTCUSDT", "timeframe": "15m",
                                    "time": now.isoformat()}) + "\n")
            # range_reversion: 5 笔 1 胜 4 负 → 胜率 20% 亏损 → 0.0 停用
            for pnl in [-1.0, -2.0, -1.5, -3.0, 0.5]:
                f.write(json.dumps({"strategy": "range_reversion", "pnl": pnl,
                                    "symbol": "ETHUSDT", "timeframe": "15m",
                                    "time": now.isoformat()}) + "\n")
            # pullback_rebound: 2 笔（样本不足）→ 1.0 探索
            for pnl in [-1.0, 1.0]:
                f.write(json.dumps({"strategy": "pullback_rebound", "pnl": pnl,
                                    "symbol": "SOLUSDT", "timeframe": "15m",
                                    "time": now.isoformat()}) + "\n")
        report = le.learn_from_trades()
        self.assertTrue(report["learned"])
        w15 = report["weights_by_timeframe"]["15m"]
        self.assertEqual(w15["trend_breakout"], 1.0)
        self.assertEqual(w15["range_reversion"], 0.0)
        self.assertEqual(w15["pullback_rebound"], 1.0)
        # 落盘验证
        disk = json.loads(le.WEIGHTS_PATH.read_text(encoding="utf-8"))
        self.assertIn("weights_by_timeframe", disk)

    def test_event_learning_generates_rule(self):
        """偏空事件 3 次全部后 12h 下行 → 生成 deboost_buy 规则。"""
        now = datetime.now(timezone.utc)
        base = int(now.timestamp() * 1000)
        # 构造 BTC K 线：覆盖过去 40h，每 1h 一根，价格持续下行
        klines = []
        for i in range(40):
            klines.append({"open_time": base - (40 - i) * 3_600_000,
                           "close": 60_000 - i * 200.0})
        le._load_btc_klines = lambda limit=500: klines
        # 3 个偏空事件（13~15h 前 → 12h 窗口已完成，且事件后价格下行）
        with le.EVENTS_PATH.open("w", encoding="utf-8") as f:
            for i in range(3):
                ev_time = now - timedelta(hours=13 + i)
                f.write(json.dumps({"time": ev_time.isoformat(), "grade": "A",
                                    "title": f"bear event {i}",
                                    "assessment": "偏空"}) + "\n")
        report = le.learn_from_events(window_h=12, min_samples=3)
        self.assertTrue(report["learned"])
        self.assertEqual(report["bear_total"], 3)
        self.assertEqual(len(report["rules"]), 1)
        self.assertEqual(report["rules"][0]["action"], "deboost_buy")
        self.assertEqual(report["rules"][0]["factor"], 0.5)
        # 落盘验证
        disk = json.loads(le.RULES_PATH.read_text(encoding="utf-8"))
        self.assertEqual(len(disk["rules"]), 1)

    def test_event_learning_no_rule_when_unreliable(self):
        """偏空事件后 12h 只有 1/3 下行 → 不生成规则（有效性 33%<60%）。"""
        now = datetime.now(timezone.utc)
        base = int(now.timestamp() * 1000)
        # 覆盖 40h，价格持续上行 → 偏空事件后实际向上（无效）
        klines = []
        for i in range(40):
            klines.append({"open_time": base - (40 - i) * 3_600_000,
                           "close": 60_000 + i * 50.0})
        le._load_btc_klines = lambda limit=500: klines
        with le.EVENTS_PATH.open("w", encoding="utf-8") as f:
            for i in range(3):
                ev_time = now - timedelta(hours=13 + i)
                f.write(json.dumps({"time": ev_time.isoformat(), "grade": "A",
                                    "title": f"bear event {i}",
                                    "assessment": "偏空"}) + "\n")
        report = le.learn_from_events(window_h=12, min_samples=3)
        self.assertEqual(len(report["rules"]), 0)

    def test_run_learning_all_channels(self):
        report = le.run_learning()
        self.assertIn("trades", report)
        self.assertIn("events", report)
        self.assertIn("quality", report)


if __name__ == "__main__":
    unittest.main()

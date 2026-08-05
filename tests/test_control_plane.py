import unittest

from autotrader.engine import DecisionEngine
from autotrader.models import MarketSnapshot, RiskLimits, Side, TradeIntent


def make_engine():
    return DecisionEngine(RiskLimits(200, 100, 20, 500))


def make_snapshot(liquidity_ok=True):
    return MarketSnapshot("BTC/USDT", 100_000, 1.5, "trend_up", liquidity_ok=liquidity_ok)


def make_intent(quantity=0.0005):
    return TradeIntent("BTC/USDT", Side.BUY, quantity, "test thesis", "test invalidation", 98_000, 0.6)


class ControlPlaneTests(unittest.TestCase):
    def test_approved_intent_stays_inside_limits(self):
        decision = make_engine().evaluate(make_snapshot(), make_intent())
        self.assertTrue(decision.approved)
        self.assertIn("approved", decision.reasons[0])


    def test_risk_rejects_order_over_limit(self):
        decision = make_engine().evaluate(make_snapshot(), make_intent(quantity=0.002))
        self.assertFalse(decision.approved)
        self.assertIn("max_order_value", " ".join(decision.reasons))


    def test_risk_rejects_bad_liquidity(self):
        decision = make_engine().evaluate(make_snapshot(False), make_intent())
        self.assertFalse(decision.approved)
        self.assertIn("liquidity", " ".join(decision.reasons))


    def test_hold_is_recorded_but_not_an_order(self):
        intent = TradeIntent("BTC/USDT", Side.HOLD, 0, "wait", "thesis not confirmed", None, 0.4)
        decision = make_engine().evaluate(make_snapshot(), intent)
        self.assertFalse(decision.approved)
        self.assertIn("hold", " ".join(decision.reasons))

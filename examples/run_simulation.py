from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from autotrader.engine import DecisionEngine
from autotrader.models import MarketSnapshot, RiskLimits, Side, TradeIntent


snapshot = MarketSnapshot("BTC/USDT", 100_000, 1.8, "trend_up")
limits = RiskLimits(max_position_value=200, max_order_value=100, max_daily_loss=20, cash=500)
engine = DecisionEngine(limits, Path("artifacts/audit.jsonl"))
intent = TradeIntent(
    symbol="BTC/USDT",
    side=Side.BUY,
    quantity=0.0005,
    thesis="模拟：趋势和成交量同时确认，等待小仓验证",
    invalidation="价格跌破结构失效位",
    stop_price=98_000,
    confidence=0.62,
)
print(engine.evaluate(snapshot, intent))

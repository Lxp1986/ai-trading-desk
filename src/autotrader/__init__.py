"""Research-first autonomous trading control plane."""

from .engine import DecisionEngine
from .models import MarketSnapshot, TradeIntent, RiskLimits
from .binance_testnet import BinanceSpotTestnet, BinanceTestnetError
from .binance import BinanceAdapter, BinanceConfig
from .exchange import ExchangeAdapter, ExchangeError, OrderResult, live_trading_enabled
from .hyperliquid import HyperliquidAdapter
from .strategy import StrategySignal, apply_strategies
from .news_research import grade_event, load_events, record_event
from .onchain import load_signals, record_signal, signal_confidence
from .sentiment import SentimentState, assess_sentiment, fetch_funding_rate
from .event_trader import EventTradePlan, checklist, phase_of, plan
from .team import EMPLOYEES
from .llm import register_thesis, record_usage, deterministic_fallback

__all__ = [
    "DecisionEngine", "MarketSnapshot", "TradeIntent", "RiskLimits",
    "BinanceSpotTestnet", "BinanceTestnetError",
    "BinanceAdapter", "BinanceConfig",
    "ExchangeAdapter", "ExchangeError", "OrderResult", "live_trading_enabled",
    "HyperliquidAdapter",
    "StrategySignal", "apply_strategies",
    "grade_event", "load_events", "record_event",
    "load_signals", "record_signal", "signal_confidence",
    "SentimentState", "assess_sentiment", "fetch_funding_rate",
    "EventTradePlan", "checklist", "phase_of", "plan",
    "EMPLOYEES",
    "register_thesis", "record_usage", "deterministic_fallback",
]

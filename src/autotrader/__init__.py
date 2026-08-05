"""Research-first autonomous trading control plane."""

from .engine import DecisionEngine
from .models import MarketSnapshot, TradeIntent, RiskLimits
from .binance_testnet import BinanceSpotTestnet, BinanceTestnetError
from .binance import BinanceAdapter, BinanceConfig
from .exchange import ExchangeAdapter, ExchangeError, OrderResult, live_trading_enabled
from .hyperliquid import HyperliquidAdapter
from .team import EMPLOYEES
from .llm import register_thesis, record_usage, deterministic_fallback

__all__ = [
    "DecisionEngine", "MarketSnapshot", "TradeIntent", "RiskLimits",
    "BinanceSpotTestnet", "BinanceTestnetError",
    "BinanceAdapter", "BinanceConfig",
    "ExchangeAdapter", "ExchangeError", "OrderResult", "live_trading_enabled",
    "HyperliquidAdapter",
    "EMPLOYEES",
    "register_thesis", "record_usage", "deterministic_fallback",
]

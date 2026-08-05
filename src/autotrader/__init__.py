"""Research-first autonomous trading control plane."""

from .engine import DecisionEngine
from .models import MarketSnapshot, TradeIntent, RiskLimits
from .binance_testnet import BinanceSpotTestnet, BinanceTestnetError
from .team import EMPLOYEES
from .llm import chat_json, draft_thesis, record_usage, deterministic_fallback, LLMUnavailableError

__all__ = [
    "DecisionEngine", "MarketSnapshot", "TradeIntent", "RiskLimits",
    "BinanceSpotTestnet", "BinanceTestnetError", "EMPLOYEES",
    "chat_json", "draft_thesis", "record_usage", "deterministic_fallback",
    "LLMUnavailableError",
]

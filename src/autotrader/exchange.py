"""交易所适配器统一接口（实盘就绪层）。

架构：决策/风控/账本/审计全部只依赖本接口返回的数据，不感知具体交易所。
新增交易所 = 实现一个 ExchangeAdapter 子类（如 BinanceAdapter/HyperliquidAdapter/OKXAdapter），
无需改动风控、账本、决策层。

实盘安全开关：
- 所有适配器默认只允许测试网/模拟；
- 实盘模式必须同时满足：
  1) 环境变量 ``LIVE_TRADING_ENABLED=1``（董事会授权）；
  2) 创建适配器时显式 ``mode="live"``；
- 否则任何实盘 URL/下单尝试都会被拒绝（raise ExchangeError）。
"""
from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


class ExchangeError(RuntimeError):
    """交易所请求失败。"""


def live_trading_enabled() -> bool:
    """董事会实盘授权开关：LIVE_TRADING_ENABLED=1。"""
    return os.environ.get("LIVE_TRADING_ENABLED", "") == "1"


def require_live_authorized(exchange_name: str) -> None:
    if not live_trading_enabled():
        raise ExchangeError(
            f"{exchange_name} 实盘未授权：需董事会设置 LIVE_TRADING_ENABLED=1 并显式 mode=\"live\"。"
            "当前仅允许测试网/模拟。"
        )


@dataclass(frozen=True)
class OrderResult:
    order_id: str
    symbol: str
    side: str
    status: str          # FILLED / NEW / PARTIALLY_FILLED / CANCELED / REJECTED
    quantity: float
    price: float | None
    avg_fill_price: float | None = None
    quote_qty: float = 0.0
    raw: dict[str, Any] = None  # type: ignore[assignment]


class ExchangeAdapter(ABC):
    """统一交易所适配器接口。"""

    name: str = "base"
    is_live: bool = False

    @abstractmethod
    def exchange_info(self, symbol: str | None = None) -> dict[str, Any]:
        """交易规则/交易对信息。"""

    @abstractmethod
    def ticker_price(self, symbol: str) -> dict[str, Any]:
        """最新价。"""

    @abstractmethod
    def klines(self, symbol: str, interval: str = "15m", limit: int = 60) -> list[dict[str, Any]]:
        """K线。"""

    @abstractmethod
    def account(self) -> dict[str, Any]:
        """账户余额/权益。"""

    @abstractmethod
    def create_order(self, *, symbol: str, side: str, quantity: float,
                     order_type: str = "MARKET", price: float | None = None) -> OrderResult:
        """下单。side: buy/sell。"""

    @abstractmethod
    def cancel_order(self, *, symbol: str, order_id: str | None = None,
                     client_order_id: str | None = None) -> dict[str, Any]:
        """撤单。"""

    @abstractmethod
    def order_status(self, *, symbol: str, order_id: str | None = None) -> dict[str, Any]:
        """订单状态。"""

    def position(self, symbol: str | None = None) -> dict[str, Any]:
        """持仓（现货默认从账本核算；永续/合约由适配器实现）。"""
        raise ExchangeError(f"{self.name} 未实现持仓接口")

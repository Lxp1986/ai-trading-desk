"""Binance Spot Testnet 适配器（向后兼容薄封装）。

真实实现见 :mod:`autotrader.binance` 的 ``BinanceAdapter(mode="testnet")``。
本模块保留旧的 ``BinanceSpotTestnet`` 类名与行为，供现有代码与测试使用。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .binance import BinanceAdapter, BinanceConfig
from .exchange import ExchangeError as BinanceTestnetError  # 兼容旧异常名

TESTNET_BASE_URL = "https://testnet.binance.vision"


class BinanceSpotTestnet(BinanceAdapter):
    """Read-only/public and virtual-order operations against Spot Testnet.

    固定测试网模式，绝不访问正式网；凭证只从进程环境读取。
    """

    def __init__(self, config: BinanceConfig | None = None) -> None:
        super().__init__(mode="testnet", config=config)

    @property
    def base_url(self) -> str:  # type: ignore[override]
        return TESTNET_BASE_URL

    def create_test_order(self, *, symbol: str, side: str, quantity: str,
                          order_type: str = "MARKET", price: str | None = None) -> dict[str, Any]:
        """Validate an order without placing it on the test network."""
        return self._order("/api/v3/order/test", symbol=symbol, side=side,
                           quantity=quantity, order_type=order_type, price=price)

    def create_order(self, *, symbol: str, side: str, quantity: str,
                     order_type: str = "MARKET", price: str | None = None) -> dict[str, Any]:
        """Place a virtual order on Spot Testnet; never on production Binance."""
        return self._order("/api/v3/order", symbol=symbol, side=side,
                           quantity=quantity, order_type=order_type, price=price)

    def _order(self, path: str, *, symbol: str, side: str, quantity: str,
               order_type: str, price: str | None) -> dict[str, Any]:
        params: dict[str, str] = {
            "symbol": symbol, "side": side, "type": order_type, "quantity": quantity,
        }
        if price is not None:
            params["price"] = price
            params["timeInForce"] = "GTC"
        return self._request("POST", path, params, signed=True)

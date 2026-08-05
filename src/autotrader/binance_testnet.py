"""Minimal Binance Spot Testnet adapter.

This module is deliberately testnet-only. It never accepts a production URL and
reads credentials only from the process environment at call time.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any


TESTNET_BASE_URL = "https://testnet.binance.vision"


class BinanceTestnetError(RuntimeError):
    """Raised when the Spot Testnet request cannot be completed."""


@dataclass(frozen=True)
class BinanceTestnetConfig:
    api_key_env: str = "BINANCE_TESTNET_API_KEY"
    api_secret_env: str = "BINANCE_TESTNET_API_SECRET"
    timeout_seconds: float = 10.0


class BinanceSpotTestnet:
    """Read-only/public and virtual-order operations against Spot Testnet."""

    def __init__(self, config: BinanceTestnetConfig | None = None) -> None:
        self.config = config or BinanceTestnetConfig()

    @property
    def base_url(self) -> str:
        return TESTNET_BASE_URL

    def exchange_info(self, symbol: str | None = None) -> dict[str, Any]:
        params = {"symbol": symbol} if symbol else {}
        return self._request("GET", "/api/v3/exchangeInfo", params)

    def ticker_price(self, symbol: str) -> dict[str, Any]:
        return self._request("GET", "/api/v3/ticker/price", {"symbol": symbol})

    def klines(self, symbol: str, interval: str = "15m", limit: int = 24) -> list[dict[str, Any]]:
        """Public candlestick data (open, high, low, close, volume...)."""
        payload = self._request("GET", "/api/v3/klines", {"symbol": symbol, "interval": interval, "limit": limit})
        if not isinstance(payload, list):
            raise BinanceTestnetError("unexpected klines response format")
        keys = ("open_time", "open", "high", "low", "close", "volume", "close_time",
                "quote_volume", "trades", "taker_base", "taker_quote", "ignore")
        result: list[dict[str, Any]] = []
        for row in payload:
            if isinstance(row, list):
                result.append(dict(zip(keys, row)))
        return result

    def account(self) -> dict[str, Any]:
        return self._request("GET", "/api/v3/account", {}, signed=True)

    def create_test_order(self, *, symbol: str, side: str, quantity: str, order_type: str = "MARKET", price: str | None = None) -> dict[str, Any]:
        """Validate an order without placing it on the test network."""
        return self._order("/api/v3/order/test", symbol=symbol, side=side, quantity=quantity, order_type=order_type, price=price)

    def create_order(self, *, symbol: str, side: str, quantity: str, order_type: str = "MARKET", price: str | None = None) -> dict[str, Any]:
        """Place a virtual order on Spot Testnet; never on production Binance."""
        return self._order("/api/v3/order", symbol=symbol, side=side, quantity=quantity, order_type=order_type, price=price)

    def cancel_order(self, *, symbol: str, order_id: int | None = None, client_order_id: str | None = None) -> dict[str, Any]:
        if order_id is None and client_order_id is None:
            raise BinanceTestnetError("order_id or client_order_id is required")
        params: dict[str, Any] = {"symbol": symbol, "orderId": order_id, "origClientOrderId": client_order_id}
        return self._request("DELETE", "/api/v3/order", params, signed=True)

    def _order(self, path: str, *, symbol: str, side: str, quantity: str, order_type: str, price: str | None) -> dict[str, Any]:
        params: dict[str, str] = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "quantity": quantity,
        }
        if price is not None:
            params["price"] = price
            params["timeInForce"] = "GTC"
        return self._request("POST", path, params, signed=True)

    def _request(self, method: str, path: str, params: dict[str, Any], signed: bool = False) -> Any:
        query = {key: value for key, value in params.items() if value is not None}
        headers: dict[str, str] = {}
        if signed:
            api_key = os.environ.get(self.config.api_key_env)
            secret = os.environ.get(self.config.api_secret_env)
            if not api_key or not secret:
                raise BinanceTestnetError(
                    f"missing {self.config.api_key_env}/{self.config.api_secret_env}; "
                    "credentials are never stored by this adapter"
                )
            query["timestamp"] = int(time.time() * 1000)
            query_string = urllib.parse.urlencode(query)
            query["signature"] = hmac.new(
                secret.encode("utf-8"), query_string.encode("utf-8"), hashlib.sha256
            ).hexdigest()
            headers["X-MBX-APIKEY"] = api_key

        encoded = urllib.parse.urlencode(query).encode("utf-8")
        url = f"{self.base_url}{path}"
        request = urllib.request.Request(url, data=encoded if method != "GET" else None, headers=headers, method=method)
        if method == "GET" and encoded:
            request = urllib.request.Request(f"{url}?{encoded.decode()}", headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            raise BinanceTestnetError(f"Binance Spot Testnet request failed: {exc}") from exc
        if not isinstance(payload, (dict, list)):
            raise BinanceTestnetError("unexpected Binance response format")
        return payload

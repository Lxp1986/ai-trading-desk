"""Binance 适配器（测试网 / 实盘双模式）。

- 默认 ``mode="testnet"``：固定 https://testnet.binance.vision，虚拟资产；
- ``mode="live"``：https://api.binance.com，**必须** ``LIVE_TRADING_ENABLED=1`` 才允许；
- 凭证只从环境变量读取：测试网 BINANCE_TESTNET_API_KEY/SECRET，实盘 BINANCE_API_KEY/SECRET；
- 签名 HMAC-SHA256（stdlib hmac/hashlib），零第三方依赖；
- 实盘模式拒绝提现类接口（本项目无提现需求）。
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

from .exchange import ExchangeAdapter, ExchangeError, OrderResult, require_live_authorized

TESTNET_BASE_URL = "https://testnet.binance.vision"
LIVE_BASE_URL = "https://api.binance.com"


@dataclass(frozen=True)
class BinanceConfig:
    api_key_env: str = "BINANCE_TESTNET_API_KEY"
    api_secret_env: str = "BINANCE_TESTNET_API_SECRET"
    timeout_seconds: float = 10.0


class BinanceAdapter(ExchangeAdapter):
    name = "binance"

    def __init__(self, mode: str = "testnet", config: BinanceConfig | None = None) -> None:
        if mode not in ("testnet", "live"):
            raise ExchangeError(f"unsupported binance mode: {mode}")
        self.mode = mode
        self.is_live = mode == "live"
        if self.is_live:
            require_live_authorized("Binance")
            config = config or BinanceConfig(
                api_key_env="BINANCE_API_KEY",
                api_secret_env="BINANCE_API_SECRET",
            )
        else:
            config = config or BinanceConfig()
        self.config = config

    @property
    def base_url(self) -> str:
        return LIVE_BASE_URL if self.is_live else TESTNET_BASE_URL

    # ---------- 公开行情 ----------
    def exchange_info(self, symbol: str | None = None) -> dict[str, Any]:
        params = {"symbol": symbol} if symbol else {}
        return self._request("GET", "/api/v3/exchangeInfo", params)

    def ticker_price(self, symbol: str) -> dict[str, Any]:
        return self._request("GET", "/api/v3/ticker/price", {"symbol": symbol})

    def klines(self, symbol: str, interval: str = "15m", limit: int = 60) -> list[dict[str, Any]]:
        payload = self._request("GET", "/api/v3/klines", {"symbol": symbol, "interval": interval, "limit": limit})
        if not isinstance(payload, list):
            raise ExchangeError("unexpected klines response format")
        keys = ("open_time", "open", "high", "low", "close", "volume", "close_time",
                "quote_volume", "trades", "taker_base", "taker_quote", "ignore")
        result: list[dict[str, Any]] = []
        for row in payload:
            if isinstance(row, list):
                result.append(dict(zip(keys, row)))
        return result

    # ---------- 账户与订单 ----------
    def account(self) -> dict[str, Any]:
        return self._request("GET", "/api/v3/account", {}, signed=True)

    def create_order(self, *, symbol: str, side: str, quantity: float,
                     order_type: str = "MARKET", price: float | None = None) -> OrderResult:
        side = side.upper()
        params: dict[str, Any] = {
            "symbol": symbol, "side": side, "type": order_type,
            "quantity": f"{quantity:.8f}",
        }
        if price is not None:
            params["price"] = f"{price:.8f}"
            params["timeInForce"] = "GTC"
        payload = self._request("POST", "/api/v3/order", params, signed=True)
        fills = payload.get("fills") or []
        avg_fill = None
        quote = 0.0
        if fills:
            avg_fill = sum(float(f.get("price", 0)) * float(f.get("qty", 0)) for f in fills) / \
                sum(float(f.get("qty", 0)) for f in fills) if fills else None
            quote = sum(float(f.get("price", 0)) * float(f.get("qty", 0)) for f in fills)
        return OrderResult(
            order_id=str(payload.get("orderId", "")),
            symbol=symbol,
            side=side.lower(),
            status=payload.get("status", "UNKNOWN"),
            quantity=float(payload.get("executedQty", quantity)),
            price=float(payload["price"]) if payload.get("price") else None,
            avg_fill_price=avg_fill,
            quote_qty=quote,
            raw=payload,
        )

    def cancel_order(self, *, symbol: str, order_id: str | None = None,
                     client_order_id: str | None = None) -> dict[str, Any]:
        if order_id is None and client_order_id is None:
            raise ExchangeError("order_id or client_order_id is required")
        params: dict[str, Any] = {"symbol": symbol, "orderId": order_id, "origClientOrderId": client_order_id}
        return self._request("DELETE", "/api/v3/order", params, signed=True)

    def order_status(self, *, symbol: str, order_id: str | None = None) -> dict[str, Any]:
        if order_id is None:
            raise ExchangeError("order_id is required")
        return self._request("GET", "/api/v3/order", {"symbol": symbol, "orderId": order_id}, signed=True)

    # ---------- 底层 ----------
    def _request(self, method: str, path: str, params: dict[str, Any], signed: bool = False) -> Any:
        query = {key: value for key, value in params.items() if value is not None}
        headers: dict[str, str] = {}
        if signed:
            api_key = os.environ.get(self.config.api_key_env)
            secret = os.environ.get(self.config.api_secret_env)
            if not api_key or not secret:
                raise ExchangeError(
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
        request = urllib.request.Request(url, data=encoded if method != "GET" else None,
                                         headers=headers, method=method)
        if method == "GET" and encoded:
            request = urllib.request.Request(f"{url}?{encoded.decode()}", headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            raise ExchangeError(f"Binance request failed ({self.mode}): {exc}") from exc
        if not isinstance(payload, (dict, list)):
            raise ExchangeError("unexpected Binance response format")
        return payload

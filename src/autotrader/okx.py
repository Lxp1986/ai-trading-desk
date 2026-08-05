"""OKX Demo Trading（模拟盘）适配器——零第三方依赖，urllib + hmac。

- 环境：https://www.okx.com（Demo Trading 模式，请求头 x-simulated-trading: 1）
- 凭证：OKX_API_KEY / OKX_API_SECRET / OKX_API_PASSPHRASE（Demo Trading 生成的 key，
  无需真实充值，自带虚拟 USDT）
- 签名：HMAC-SHA256(timestamp + method + requestPath + body, secret)
- 符号：系统内用 BTCUSDT，OKX 用 BTC-USDT（内部转换）

实盘红线：本适配器固定 Demo Trading 模式（x-simulated-trading: 1），
即使误配实盘 key 也不会触达真实资金。
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Any

from .exchange import ExchangeAdapter, ExchangeError, OrderResult

BASE_URL = "https://www.okx.com"

_INTERVAL_MS = {
    "1m": 60_000, "3m": 180_000, "5m": 300_000, "15m": 900_000,
    "30m": 1_800_000, "1h": 3_600_000, "4h": 14_400_000,
    "1d": 86_400_000, "1w": 604_800_000,
}

# OKX 杠/横线符号转换
def _to_okx(symbol: str) -> str:
    return symbol.replace("/", "").replace("USDT", "-USDT")


def _from_okx(inst_id: str) -> str:
    return inst_id.replace("-", "")


class OkxDemoAdapter(ExchangeAdapter):
    """OKX Demo Trading（模拟盘）适配器。"""

    name = "okx-demo"

    def __init__(self, api_key_env: str = "OKX_API_KEY",
                 secret_env: str = "OKX_API_SECRET",
                 passphrase_env: str = "OKX_API_PASSPHRASE",
                 timeout_seconds: float = 15.0) -> None:
        self.api_key_env = api_key_env
        self.secret_env = secret_env
        self.passphrase_env = passphrase_env
        self.timeout_seconds = timeout_seconds
        self.is_live = False  # Demo Trading 永远非实盘

    @property
    def base_url(self) -> str:
        return BASE_URL

    # ---------- 底层 ----------

    def _credentials(self) -> tuple[str, str, str]:
        key = os.environ.get(self.api_key_env, "")
        secret = os.environ.get(self.secret_env, "")
        passphrase = os.environ.get(self.passphrase_env, "")
        if not key or not secret or not passphrase:
            raise ExchangeError(
                f"missing {self.api_key_env}/{self.secret_env}/{self.passphrase_env}; "
                "OKX Demo Trading API key 只从环境变量读取"
            )
        return key, secret, passphrase

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

    def _sign(self, ts: str, method: str, path: str, body: str, secret: str) -> str:
        message = ts + method + path + body
        return hmac.new(secret.encode("utf-8"), message.encode("utf-8"),
                        hashlib.sha256).hexdigest()

    def _request(self, method: str, path: str, params: dict[str, Any] | None = None,
                 body: dict[str, Any] | None = None, signed: bool = False,
                 public: bool = False) -> Any:
        url = BASE_URL + path
        if params:
            query = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
            url = url + "?" + query
        data = json.dumps(body).encode("utf-8") if body is not None else b""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
        }
        # Demo Trading 模式标志（公共行情也带，确保 demo 环境）
        headers["x-simulated-trading"] = "1"
        if signed:
            key, secret, passphrase = self._credentials()
            ts = self._timestamp()
            headers["OK-ACCESS-KEY"] = key
            headers["OK-ACCESS-SIGN"] = self._sign(ts, method, path, data.decode("utf-8") or "", secret)
            headers["OK-ACCESS-TIMESTAMP"] = ts
            headers["OK-ACCESS-PASSPHRASE"] = passphrase
        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                result = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise ExchangeError(f"OKX HTTP {exc.code}: {exc.read().decode()[:200]}") from exc
        except Exception as exc:
            raise ExchangeError(f"OKX request failed: {exc}") from exc
        if isinstance(result, dict) and result.get("code") != "0":
            raise ExchangeError(f"OKX error {result.get('code')}: {result.get('msg')}")
        return result

    # ---------- 行情（公开，无需签名） ----------

    def ticker_price(self, symbol: str) -> dict[str, Any]:
        result = self._request("GET", "/api/v5/market/ticker",
                               {"instId": _to_okx(symbol)}, public=True)
        data = result.get("data", [])
        if not data:
            raise ExchangeError(f"OKX ticker empty: {symbol}")
        return {"symbol": symbol, "price": float(data[0]["last"]),
                "change_24h_pct": float(data[0].get("last", 0)) / float(data[0].get("open24h", 1)) - 1
                if float(data[0].get("open24h", 0)) else 0.0}

    def klines(self, symbol: str, interval: str = "15m", limit: int = 60) -> list[dict[str, Any]]:
        result = self._request("GET", "/api/v5/market/candles",
                               {"instId": _to_okx(symbol), "bar": interval, "limit": min(limit, 300)},
                               public=True)
        candles: list[dict[str, Any]] = []
        for row in result.get("data", []):
            # OKX candles: [ts, o, h, l, c, vol, volCcy, ...]（最新在前）
            candles.append({
                "t": int(row[0]), "o": float(row[1]), "h": float(row[2]),
                "l": float(row[3]), "c": float(row[4]), "v": float(row[5]),
            })
        candles.reverse()  # 升序（与 Binance/HL 一致）
        return candles

    # ---------- 账户 ----------

    def account(self) -> dict[str, Any]:
        result = self._request("GET", "/api/v5/account/balance", signed=True)
        data = result.get("data", [])
        if not data:
            return {"address": "okx-demo", "balances": []}
        details = data[0].get("details", [])
        balances = [{"coin": d.get("ccy"), "total": float(d.get("cashBal", 0) or 0),
                     "hold": float(d.get("frozenBal", 0) or 0)} for d in details]
        return {"address": "okx-demo", "balances": balances,
                "total_usd": float(data[0].get("totalEq", 0) or 0)}

    # ---------- 订单 ----------

    def create_order(self, *, symbol: str, side: str, quantity: float,
                     order_type: str = "MARKET", price: float | None = None) -> OrderResult:
        inst_id = _to_okx(symbol)
        body: dict[str, Any] = {
            "instId": inst_id, "tdMode": "cash", "side": side.lower(),
            "ordType": "market" if order_type.upper() == "MARKET" or price is None else "limit",
            "sz": f"{quantity:.6f}",
        }
        if body["ordType"] == "limit" and price:
            body["px"] = f"{price:.6f}"
        result = self._request("POST", "/api/v5/trade/order", body=body, signed=True)
        data = result.get("data", [{}])[0]
        if data.get("sCode") != "0":
            raise ExchangeError(f"OKX order rejected: {data.get('sMsg')}")
        order_id = str(data.get("ordId", ""))
        # 查询成交价（市场单需等待填充）
        avg_fill = None
        try:
            time.sleep(0.5)
            detail = self._request("GET", "/api/v5/trade/order",
                                   {"instId": inst_id, "ordId": order_id}, signed=True)
            d = (detail.get("data") or [{}])[0]
            fill = d.get("fillPx", "")
            avg_fill = float(fill) if fill else None
            status = "FILLED" if d.get("state") == "filled" else d.get("state", "NEW")
        except Exception:
            status = "NEW"
        return OrderResult(
            order_id=order_id, symbol=symbol, side=side.lower(),
            status=status, quantity=quantity, price=price,
            avg_fill_price=avg_fill, quote_qty=quantity * (avg_fill or price or 0.0),
            raw=result,
        )

    def order_status(self, *, symbol: str, order_id: str | None = None) -> dict[str, Any]:
        if order_id is None:
            raise ExchangeError("order_id is required")
        result = self._request("GET", "/api/v5/trade/order",
                               {"instId": _to_okx(symbol), "ordId": order_id}, signed=True)
        d = (result.get("data") or [{}])[0]
        return {"order_id": order_id, "status": d.get("state", "unknown"),
                "avg_fill_price": d.get("fillPx")}

    def exchange_info(self, symbol: str | None = None) -> dict[str, Any]:
        """OKX 交易对信息（instId 格式）。"""
        if symbol is None:
            result = self._request("GET", "/api/v5/public/instruments",
                                   {"instType": "SPOT"}, public=True)
            return {"instruments": [i.get("instId") for i in result.get("data", [])]}
        result = self._request("GET", "/api/v5/public/instruments",
                               {"instType": "SPOT", "instId": _to_okx(symbol)}, public=True)
        data = result.get("data", [])
        if not data:
            raise ExchangeError(f"OKX instrument not found: {symbol}")
        inst = data[0]
        return {"symbol": symbol, "instId": inst.get("instId"),
                "minSz": inst.get("minSz"), "lotSz": inst.get("lotSz"),
                "tickSz": inst.get("tickSz")}

    def cancel_order(self, *, symbol: str, order_id: str | None = None,
                     client_order_id: str | None = None) -> dict[str, Any]:
        if order_id is None:
            raise ExchangeError("order_id is required")
        body = {"instId": _to_okx(symbol), "ordId": order_id}
        result = self._request("POST", "/api/v5/trade/cancel-order", body=body, signed=True)
        return {"order_id": order_id, "ok": True, "raw": result}

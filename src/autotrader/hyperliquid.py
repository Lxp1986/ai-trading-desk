"""Hyperliquid 适配器（去中心化交易所，测试网/实盘双模式）。

- 测试网：https://api.hyperliquid-testnet.xyz（默认，安全）；
- 实盘：https://api.hyperliquid.xyz，**必须** LIVE_TRADING_ENABLED=1；
- 签名：L2 ed25519 agent key（官方推荐），消息 = keccak256(规范JSON{action,nonce})；
  私钥只从环境变量读取（HYPERLIQUID_TESTNET_PRIVATE_KEY / HYPERLIQUID_PRIVATE_KEY），
  从不写入代码/文件；
- 依赖：ed25519 签名需要 ``cryptography`` 库（可选依赖，未安装时交易接口给出清晰报错；
  行情/查询接口不依赖它）。

地址推导：ed25519 公钥即账户地址（0x + 32字节hex）。
"""
from __future__ import annotations

import json
import os
import time
import urllib.request
from typing import Any

from .exchange import ExchangeAdapter, ExchangeError, OrderResult, require_live_authorized
from .keccak import keccak256

TESTNET_URL = "https://api.hyperliquid-testnet.xyz"
LIVE_URL = "https://api.hyperliquid.xyz"

# MARKET 单用 Ioc + 极端价格模拟（Hyperliquid 无原生市价单）
_IOC_SLIPPAGE = 0.02  # 2%


class HyperliquidAdapter(ExchangeAdapter):
    name = "hyperliquid"

    def __init__(self, mode: str = "testnet",
                 private_key_env: str | None = None,
                 wallet_address: str | None = None,
                 timeout_seconds: float = 10.0) -> None:
        if mode not in ("testnet", "live"):
            raise ExchangeError(f"unsupported hyperliquid mode: {mode}")
        self.mode = mode
        self.is_live = mode == "live"
        if self.is_live:
            require_live_authorized("Hyperliquid")
            private_key_env = private_key_env or "HYPERLIQUID_PRIVATE_KEY"
        else:
            private_key_env = private_key_env or "HYPERLIQUID_TESTNET_PRIVATE_KEY"
        self.private_key_env = private_key_env
        self.wallet_address = wallet_address
        self.timeout_seconds = timeout_seconds
        self._meta_cache: dict[str, Any] = {}
        self._spot_meta_cache: dict[str, Any] = {}

    @property
    def base_url(self) -> str:
        return LIVE_URL if self.is_live else TESTNET_URL

    # ---------- 底层 ----------
    def _post(self, path: str, payload: dict[str, Any]) -> Any:
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            raise ExchangeError(f"Hyperliquid request failed ({self.mode}): {exc}") from exc

    def _info(self, payload: dict[str, Any]) -> Any:
        return self._post("/info", payload)

    def _exchange(self, payload: dict[str, Any]) -> dict[str, Any]:
        result = self._post("/exchange", payload)
        if isinstance(result, dict) and result.get("status") == "err":
            raise ExchangeError(f"Hyperliquid exchange error: {result.get('response')}")
        if not isinstance(result, dict):
            raise ExchangeError("unexpected Hyperliquid exchange response format")
        return result

    # ---------- 元数据 / 资产索引 ----------
    def _load_meta(self) -> dict[str, Any]:
        if not self._meta_cache:
            meta = self._info({"type": "meta"})
            if not isinstance(meta, dict) or "universe" not in meta:
                raise ExchangeError("unexpected meta response")
            self._meta_cache = meta
        return self._meta_cache

    def _load_spot_meta(self) -> dict[str, Any]:
        if not self._spot_meta_cache:
            meta = self._info({"type": "spotMeta"})
            if not isinstance(meta, dict) or "tokens" not in meta:
                raise ExchangeError("unexpected spotMeta response")
            self._spot_meta_cache = meta
        return self._spot_meta_cache

    def _asset_index(self, symbol: str) -> int:
        """symbol → asset index。永续用 universe index；现货（symbol@xxx）用 10000+index。"""
        if "@" in symbol:
            name = symbol.split("@")[0]
            spot_meta = self._load_spot_meta()
            tokens = spot_meta.get("tokens", [])
            for i, pair in enumerate(spot_meta.get("universe", [])):
                if pair.get("name") == symbol:
                    return 10000 + i
            for i, token in enumerate(tokens):
                if token.get("name") == name:
                    return 10000 + i
            raise ExchangeError(f"spot symbol not found in spotMeta: {symbol}")
        meta = self._load_meta()
        for index, entry in enumerate(meta.get("universe", [])):
            if entry.get("name") == symbol:
                return index
        raise ExchangeError(f"symbol not found in universe: {symbol}")

    # ---------- 公开行情 ----------
    def exchange_info(self, symbol: str | None = None) -> dict[str, Any]:
        meta = self._load_meta()
        if symbol is None:
            return meta
        for entry in meta.get("universe", []):
            if entry.get("name") == symbol:
                return entry
        raise ExchangeError(f"symbol not found: {symbol}")

    def ticker_price(self, symbol: str) -> dict[str, Any]:
        mids = self._info({"type": "allMids"})
        if not isinstance(mids, dict):
            raise ExchangeError("unexpected allMids response")
        key = symbol
        if "@" in symbol:
            # 现货：allMids 用 "@1" 形式（spotMeta index）
            name = symbol.split("@")[0]
            spot_meta = self._load_spot_meta()
            for i, token in enumerate(spot_meta.get("tokens", [])):
                if token.get("name") == name:
                    key = f"{name}@{i}"
                    break
        if key not in mids:
            raise ExchangeError(f"symbol not found in allMids: {symbol}")
        return {"symbol": symbol, "price": float(mids[key])}

    def klines(self, symbol: str, interval: str = "15m", limit: int = 60) -> list[dict[str, Any]]:
        end_time = int(time.time() * 1000)
        start_time = end_time - limit * _INTERVAL_MS.get(interval, 15 * 60_000)
        payload = {
            "type": "candleSnapshot",
            "req": {"coin": symbol, "interval": interval,
                    "startTime": start_time, "endTime": end_time, "limit": limit},
        }
        candles = self._info(payload)
        if not isinstance(candles, list):
            raise ExchangeError("unexpected candleSnapshot response")
        result: list[dict[str, Any]] = []
        for c in candles:
            if not isinstance(c, dict):
                continue
            result.append({
                "t": c.get("t"), "o": float(c.get("o", 0)), "h": float(c.get("h", 0)),
                "l": float(c.get("l", 0)), "c": float(c.get("c", 0)),
                "v": float(c.get("v", 0)), "n": c.get("n", 0),
            })
        return result

    # ---------- 签名 ----------
    def _crypto(self):
        try:
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
            return Ed25519PrivateKey
        except ImportError as exc:  # pragma: no cover
            raise ExchangeError(
                "Hyperliquid 交易需要 cryptography 库（ed25519 签名）：pip install cryptography"
            ) from exc

    def _private_key_hex(self) -> str:
        key = os.environ.get(self.private_key_env, "")
        if not key:
            raise ExchangeError(
                f"missing {self.private_key_env}; Hyperliquid 私钥只从环境变量读取"
            )
        return key.strip().lower().replace("0x", "")

    def _derive_address(self) -> str:
        if self.wallet_address:
            return self.wallet_address
        Ed25519PrivateKey = self._crypto()
        raw = bytes.fromhex(self._private_key_hex())
        private_key = Ed25519PrivateKey.from_private_bytes(raw)
        public_bytes = private_key.public_key().public_bytes_raw()
        return "0x" + public_bytes.hex()

    def _sign(self, action: dict[str, Any]) -> dict[str, Any]:
        """构造签名请求：{action, nonce, signature}。"""
        Ed25519PrivateKey = self._crypto()
        nonce = int(time.time() * 1000)
        message = {"action": action, "nonce": nonce}
        canonical = json.dumps(message, separators=(",", ":"), sort_keys=True)
        digest = keccak256(canonical.encode("utf-8"))
        private_key = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(self._private_key_hex()))
        signature = private_key.sign(digest).hex()
        return {"action": action, "nonce": nonce, "signature": signature}

    # ---------- 账户 ----------
    def account(self) -> dict[str, Any]:
        address = self._derive_address()
        result: dict[str, Any] = {"address": address}
        try:
            spot = self._info({"type": "spotUserState", "user": address})
            if isinstance(spot, dict):
                balances = spot.get("balances", [])
                result["balances"] = [
                    {"coin": b.get("coin"), "total": float(b.get("total", 0)),
                     "hold": float(b.get("hold", 0))}
                    for b in balances if isinstance(b, dict)
                ]
        except ExchangeError:
            pass  # 现货未开通等，不阻断
        try:
            perp = self._info({"type": "clearinghouseState", "user": address})
            if isinstance(perp, dict):
                result["margin_summary"] = perp.get("marginSummary", {})
                positions = []
                for p in perp.get("assetPositions", []):
                    pos = p.get("position", {}) if isinstance(p, dict) else {}
                    positions.append({
                        "coin": pos.get("coin"), "szi": float(pos.get("szi", 0)),
                        "entry": float(pos.get("entryPx", 0)),
                        "uPnL": float(pos.get("unrealizedPnl", 0)),
                        "leverage": pos.get("leverage", {}),
                    })
                result["positions"] = positions
        except ExchangeError:
            pass
        return result

    # ---------- 订单 ----------
    def create_order(self, *, symbol: str, side: str, quantity: float,
                     order_type: str = "MARKET", price: float | None = None) -> OrderResult:
        asset_index = self._asset_index(symbol)
        is_buy = side.lower() == "buy"
        if order_type.upper() == "MARKET" or price is None:
            mid = float(self.ticker_price(symbol)["price"])
            price = mid * (1 + _IOC_SLIPPAGE) if is_buy else mid * (1 - _IOC_SLIPPAGE)
            tif = "Ioc"
        else:
            tif = "Gtc"
        order = {
            "a": asset_index, "b": is_buy, "p": f"{price:.6f}", "s": f"{quantity:.6f}",
            "r": False, "t": {"limit": {"tif": tif}},
        }
        response = self._exchange(self._sign({"type": "order", "orders": [order]}))
        statuses = (response.get("response") or {}).get("data", {}).get("statuses", [])
        status = statuses[0] if statuses else {}
        if "error" in status:
            raise ExchangeError(f"Hyperliquid order rejected: {status['error']}")
        oid = str((status.get("resting") or {}).get("oid") or (status.get("filled") or {}).get("oid") or "")
        return OrderResult(
            order_id=oid, symbol=symbol, side=side.lower(),
            status="FILLED" if "filled" in status else "NEW",
            quantity=quantity, price=price, avg_fill_price=price,
            quote_qty=quantity * price, raw=response,
        )

    def cancel_order(self, *, symbol: str, order_id: str | None = None,
                     client_order_id: str | None = None) -> dict[str, Any]:
        if order_id is None:
            raise ExchangeError("order_id is required")
        action = {"type": "cancel", "cancels": [{"a": self._asset_index(symbol), "o": int(order_id)}]}
        return self._exchange(self._sign(action))

    def order_status(self, *, symbol: str, order_id: str | None = None) -> dict[str, Any]:
        if order_id is None:
            raise ExchangeError("order_id is required")
        address = self._derive_address()
        orders = self._info({"type": "orderStatus", "user": address, "oid": int(order_id)})
        if not isinstance(orders, dict):
            raise ExchangeError("unexpected orderStatus response")
        return orders


_INTERVAL_MS = {
    "1m": 60_000, "3m": 180_000, "5m": 300_000, "15m": 900_000,
    "30m": 1_800_000, "1h": 3_600_000, "4h": 14_400_000, "1d": 86_400_000,
}

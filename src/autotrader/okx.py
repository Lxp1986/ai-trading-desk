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


def _to_okx_swap(symbol: str) -> str:
    """USDT 本位永续合约 instId：BTCUSDT → BTC-USDT-SWAP。"""
    return symbol.replace("/", "").replace("USDT", "-USDT-SWAP")


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
        self._lot_cache: dict[str, float] = {}

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
        # OKX 官方：HMAC-SHA256(timestamp + method + path + body, secret)，输出 base64
        import base64
        message = ts + method + body
        if path:
            message = ts + method + path + body
        digest = hmac.new(secret.encode("utf-8"), message.encode("utf-8"),
                          hashlib.sha256).digest()
        return base64.b64encode(digest).decode("ascii")

    def _request(self, method: str, path: str, params: dict[str, Any] | None = None,
                 body: dict[str, Any] | None = None, signed: bool = False,
                 public: bool = False) -> Any:
        url = BASE_URL + path
        query = ""
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
            # OKX 签名路径 = request path + query（完整）
            sign_path = path + ("?" + query if query else "")
            headers["OK-ACCESS-KEY"] = key
            headers["OK-ACCESS-SIGN"] = self._sign(ts, method, sign_path,
                                                   data.decode("utf-8") or "", secret)
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

    def ticker_price(self, symbol: str, contract: bool = False) -> dict[str, Any]:
        result = self._request("GET", "/api/v5/market/ticker",
                               {"instId": _to_okx_swap(symbol) if contract else _to_okx(symbol)},
                               public=True)
        data = result.get("data", [])
        if not data:
            raise ExchangeError(f"OKX ticker empty: {symbol}")
        return {"symbol": symbol, "price": float(data[0]["last"]),
                "change_24h_pct": float(data[0].get("last", 0)) / float(data[0].get("open24h", 1)) - 1
                if float(data[0].get("open24h", 0)) else 0.0}

    def klines(self, symbol: str, interval: str = "15m", limit: int = 60) -> list[dict[str, Any]]:
        # OKX bar 单位大写：1h→1H / 1d→1D / 1w→1W（分钟单位不变）
        bar = interval
        if bar.endswith("h"):
            bar = bar[:-1] + "H"
        elif bar.endswith("d"):
            bar = bar[:-1] + "D"
        elif bar.endswith("w"):
            bar = bar[:-1] + "W"
        result = self._request("GET", "/api/v5/market/candles",
                               {"instId": _to_okx(symbol), "bar": bar, "limit": min(limit, 300)},
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

    def position(self, symbol: str | None = None) -> dict[str, Any]:
        """现货持仓（通过账户余额查询该币可用数量）。"""
        if symbol is None:
            return {"symbol": None, "free": 0.0, "total": 0.0, "ccy": None}
        inst_id = _to_okx(symbol)
        base = inst_id.split("-")[0]
        result = self._request("GET", "/api/v5/account/balance", signed=True)
        details = (result.get("data") or [{}])[0].get("details", [])
        for bal in details:
            if bal.get("ccy") == base:
                return {"symbol": symbol, "free": float(bal.get("availBal", 0) or 0),
                        "total": float(bal.get("cashBal", 0) or 0), "ccy": base}
        return {"symbol": symbol, "free": 0.0, "total": 0.0, "ccy": base}

    def positions(self) -> list[dict[str, Any]]:
        """现货全部持仓（余额中数量 > 0 的币）。"""
        result = self._request("GET", "/api/v5/account/balance", signed=True)
        out = []
        details = (result.get("data") or [{}])[0].get("details", [])
        for bal in details:
            qty = float(bal.get("cashBal", 0) or 0)
            if qty > 0 and bal.get("ccy") not in ("USDT", "USDC"):
                out.append({"symbol": f"{bal['ccy']}USDT",
                            "free": float(bal.get("availBal", 0) or 0),
                            "total": qty, "ccy": bal["ccy"]})
        return out

    # ---------- 订单 ----------

    def _lot_size(self, symbol: str) -> float:
        """合约 lot size（最小下单数量，缓存；BTC/ETH-USDT-SWAP 均为 0.01）。"""
        if symbol not in self._lot_cache:
            inst_id = _to_okx_swap(symbol)
            result = self._request("GET", "/api/v5/public/instruments",
                                   {"instType": "SWAP", "instId": inst_id}, public=True)
            data = result.get("data", [])
            self._lot_cache[symbol] = float(data[0].get("lotSz", 0.01)) if data else 0.01
        return self._lot_cache[symbol]

    def funding_rate(self, symbol: str) -> dict[str, Any]:
        """永续资金费率（每 8h 结算；正费率多头付费、空头收费）。"""
        result = self._request("GET", "/api/v5/public/funding-rate",
                               {"instId": _to_okx_swap(symbol)}, public=True)
        data = result.get("data", [])
        if not data:
            return {"symbol": symbol, "funding_rate": 0.0}
        return {"symbol": symbol, "funding_rate": float(data[0].get("fundingRate", 0) or 0),
                "next_funding_time": int(data[0].get("nextFundingTime", 0) or 0)}

    def set_leverage(self, symbol: str, lever: int, mgn_mode: str = "cross") -> dict[str, Any]:
        """设置 USDT 本位永续杠杆（long/short 双向统一）。"""
        inst_id = _to_okx_swap(symbol)
        result = self._request("POST", "/api/v5/account/set-leverage", body={
            "instId": inst_id, "lever": str(lever), "mgnMode": mgn_mode,
        }, signed=True)
        return {"ok": True, "raw": result}

    def contract_position(self, symbol: str) -> dict[str, Any] | None:
        """合约持仓查询（net 模式：pos>0 多头 / pos<0 空头；双向模式按 posSide）。"""
        inst_id = _to_okx_swap(symbol)
        result = self._request("GET", "/api/v5/account/positions",
                               {"instId": inst_id}, signed=True)
        for p in result.get("data", []):
            pos = float(p.get("pos", 0) or 0)
            if abs(pos) > 0:
                side = p.get("posSide") or ("long" if pos > 0 else "short")
                return {
                    "symbol": symbol, "instId": inst_id,
                    "side": side,
                    "quantity": abs(pos),
                    "avg_cost": float(p.get("avgPx", 0) or 0),
                    "mark_price": float(p.get("markPx", 0) or 0),
                    "unrealized_pnl": float(p.get("upl", 0) or 0),
                    "liq_price": float(p.get("liqPx", 0) or 0),
                    "leverage": float(p.get("lever", 0) or 0),
                    "margin_mode": p.get("mgnMode", ""),
                }
        return None

    def contract_positions(self) -> list[dict[str, Any]]:
        """全部合约持仓。"""
        result = self._request("GET", "/api/v5/account/positions", signed=True)
        out = []
        for p in result.get("data", []):
            pos = float(p.get("pos", 0) or 0)
            if abs(pos) > 0:
                side = p.get("posSide") or ("long" if pos > 0 else "short")
                out.append({
                    "symbol": _from_okx(p.get("instId", "")).replace("-SWAP", ""),
                    "instId": p.get("instId"),
                    "side": side,
                    "quantity": abs(pos),
                    "avg_cost": float(p.get("avgPx", 0) or 0),
                    "mark_price": float(p.get("markPx", 0) or 0),
                    "unrealized_pnl": float(p.get("upl", 0) or 0),
                    "liq_price": float(p.get("liqPx", 0) or 0),
                })
        return out

    def create_order(self, *, symbol: str, side: str, quantity: float,
                     order_type: str = "MARKET", price: float | None = None,
                     contract: bool = False,
                     pos_side: str | None = None) -> OrderResult:
        """下单。contract=True 时为 USDT 本位永续（SWAP，多空双向，cross 保证金）。"""
        inst_id = _to_okx_swap(symbol) if contract else _to_okx(symbol)
        is_market = order_type.upper() == "MARKET" or price is None
        body: dict[str, Any] = {
            "instId": inst_id,
            "tdMode": "cross" if contract else "cash",
            "side": side.lower(),
            "ordType": "market" if is_market else "limit",
        }
        if contract and pos_side:
            body["posSide"] = pos_side  # long/short（双向持仓模式）
        if is_market:
            if contract:
                # 合约市价单 sz 为币数量，须对齐 lot size（BTC/ETH 0.01 起）
                lot = self._lot_size(symbol)
                import math
                sz = max(lot, math.floor(quantity / lot) * lot)
                body["sz"] = f"{sz:.8f}".rstrip("0").rstrip(".")
            elif side.upper() == "BUY":
                # 模拟盘市价买单必须按金额（quote_ccy）；金额 = 数量 × 当前价
                px = float(self.ticker_price(symbol)["price"])
                amt = round(quantity * px, 2)
                body["sz"] = f"{amt:.2f}"
                body["tgtCcy"] = "quote_ccy"
            else:
                body["sz"] = f"{quantity:.8f}".rstrip("0").rstrip(".")
                body["tgtCcy"] = "base_ccy"
        else:
            body["sz"] = f"{quantity:.8f}".rstrip("0").rstrip(".")
            if price:
                body["px"] = f"{price:.1f}"
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

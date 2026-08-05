"""Tests for okx (OKX Demo Trading 适配器)."""

from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from autotrader import okx
from autotrader.okx import OkxDemoAdapter


class OkxSymbolTest(unittest.TestCase):
    def test_symbol_conversion(self):
        self.assertEqual(okx._to_okx("BTCUSDT"), "BTC-USDT")
        self.assertEqual(okx._to_okx("ETH/USDT"), "ETH-USDT")
        self.assertEqual(okx._from_okx("BTC-USDT"), "BTCUSDT")


class OkxAdapterTest(unittest.TestCase):
    def setUp(self):
        self.adapter = OkxDemoAdapter()

    def test_signature_format(self):
        """签名 = base64(HMAC-SHA256(ts + method + path + body, secret))——官方规范。"""
        ts = "2026-08-05T12:00:00.000Z"
        sig = self.adapter._sign(ts, "POST", "/api/v5/trade/order",
                                 '{"instId":"BTC-USDT"}', "secret123")
        import base64
        import hashlib
        import hmac as _hmac
        digest = _hmac.new(b"secret123",
                           (ts + "POST" + "/api/v5/trade/order" + '{"instId":"BTC-USDT"}').encode(),
                           hashlib.sha256).digest()
        expected = base64.b64encode(digest).decode("ascii")
        self.assertEqual(sig, expected)
        self.assertNotIn("=", sig[:-2])  # base64 特征

    @patch.object(okx.OkxDemoAdapter, "_request")
    def test_ticker(self, mock_request):
        mock_request.return_value = {"code": "0",
                                     "data": [{"last": "64321.5", "open24h": "64000"}]}
        result = self.adapter.ticker_price("BTCUSDT")
        self.assertEqual(result["price"], 64321.5)
        mock_request.assert_called_once_with(
            "GET", "/api/v5/market/ticker", {"instId": "BTC-USDT"}, public=True)

    @patch.object(okx.OkxDemoAdapter, "_request")
    def test_klines_normalized(self, mock_request):
        mock_request.return_value = {"code": "0", "data": [
            ["1785942000000", "64000", "64100", "63900", "64050", "123.5"],
            ["1785941100000", "63900", "64000", "63800", "63950", "100.0"],
        ]}
        candles = self.adapter.klines("BTCUSDT", "15m", 2)
        self.assertEqual(len(candles), 2)
        self.assertEqual(candles[0]["t"], 1785941100000)  # 升序
        self.assertEqual(candles[0]["c"], 63950.0)
        self.assertEqual(candles[1]["o"], 64000.0)

    @patch.object(okx.OkxDemoAdapter, "_request")
    @patch.object(okx.OkxDemoAdapter, "_credentials")
    def test_create_order(self, mock_creds, mock_request):
        mock_creds.return_value = ("key", "secret", "pass")
        mock_request.side_effect = [
            {"code": "0", "data": [{"last": "64350.0", "open24h": "64000"}]},  # ticker（市价买单查价）
            {"code": "0", "data": [{"sCode": "0", "ordId": "12345"}]},  # 下单
            {"code": "0", "data": [{"state": "filled", "fillPx": "64350"}]},  # 状态查询
        ]
        result = self.adapter.create_order(symbol="BTCUSDT", side="BUY", quantity=0.001)
        self.assertEqual(result.order_id, "12345")
        self.assertEqual(result.status, "FILLED")
        self.assertEqual(result.avg_fill_price, 64350.0)
        # 下单请求体校验（第 2 个 call 是下单 POST，第 1 个是 ticker GET）
        calls = mock_request.call_args_list
        order_call = calls[1]
        self.assertEqual(order_call.args[0], "POST")
        self.assertEqual(order_call.args[1], "/api/v5/trade/order")
        body = order_call.kwargs["body"] if "body" in order_call.kwargs else order_call.args[2]
        self.assertEqual(body["instId"], "BTC-USDT")
        self.assertEqual(body["tdMode"], "cash")
        self.assertTrue(body["sz"])
        self.assertEqual(body["tgtCcy"], "quote_ccy")

    def test_live_guard(self):
        """Demo 适配器永远非实盘。"""
        self.assertFalse(self.adapter.is_live)


if __name__ == "__main__":
    unittest.main()

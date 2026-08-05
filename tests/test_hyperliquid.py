"""Tests for the Hyperliquid adapter (signing, authorization, public market data)."""

from __future__ import annotations

import json
import os
import unittest
from unittest import mock

from autotrader.exchange import ExchangeError
from autotrader.hyperliquid import HyperliquidAdapter, TESTNET_URL


def _has_cryptography() -> bool:
    try:
        import cryptography  # noqa: F401
        return True
    except ImportError:
        return False


def _has_network() -> bool:
    import urllib.request
    try:
        request = urllib.request.Request(
            "https://api.hyperliquid-testnet.xyz/info",
            data=b'{"type":"allMids"}',
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=8) as response:
            return response.status == 200
    except Exception:
        return False


class TestAuthorization(unittest.TestCase):
    def test_live_requires_authorization(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ExchangeError) as ctx:
                HyperliquidAdapter(mode="live")
            self.assertIn("LIVE_TRADING_ENABLED", str(ctx.exception))

    def test_live_allowed_when_authorized(self) -> None:
        with mock.patch.dict(os.environ, {"LIVE_TRADING_ENABLED": "1"}, clear=True):
            adapter = HyperliquidAdapter(mode="live", private_key_env="HL_TEST_KEY")
            self.assertTrue(adapter.is_live)
            self.assertIn("api.hyperliquid.xyz", adapter.base_url)

    def test_testnet_default(self) -> None:
        adapter = HyperliquidAdapter()
        self.assertFalse(adapter.is_live)
        self.assertEqual(adapter.base_url, TESTNET_URL)


class TestSigning(unittest.TestCase):
    def setUp(self) -> None:
        # 32 字节 ed25519 私钥（64 hex 字符），仅测试用
        self.private_key = "e1d3e2c0f0f1f2f3f4f5f6f7f8f9fafbfcfdfeff000102030405060708090a0b"

    @unittest.skipUnless(_has_cryptography(), "需要 cryptography 库")
    def test_signed_request_shape(self) -> None:
        with mock.patch.dict(os.environ, {"HL_TEST_KEY": self.private_key}, clear=True):
            adapter = HyperliquidAdapter(private_key_env="HL_TEST_KEY")
            action = {"type": "order", "orders": [{"a": 0, "b": True, "p": "100", "s": "1", "r": False,
                                                    "t": {"limit": {"tif": "Gtc"}}}]}
            signed = adapter._sign(action)
            self.assertEqual(signed["action"], action)
            self.assertIsInstance(signed["nonce"], int)
            signature = signed["signature"]
            self.assertIsInstance(signature, str)
            self.assertEqual(len(signature), 128)  # 64 字节 hex
            try:
                bytes.fromhex(signature)
            except ValueError:
                self.fail("signature not hex")

    @unittest.skipUnless(_has_cryptography(), "需要 cryptography 库")
    def test_derive_address_is_hex(self) -> None:
        with mock.patch.dict(os.environ, {"HL_TEST_KEY": self.private_key}, clear=True):
            adapter = HyperliquidAdapter(private_key_env="HL_TEST_KEY")
            address = adapter._derive_address()
            self.assertTrue(address.startswith("0x"))
            self.assertEqual(len(address), 66)  # 0x + 64 hex


class TestPublicMarket(unittest.TestCase):
    """真实测试网行情验证（无网络时跳过）。"""

    @unittest.skipUnless(_has_network(), "测试网不可达")
    def test_ticker_price_btc(self) -> None:
        adapter = HyperliquidAdapter()
        ticker = adapter.ticker_price("BTC")
        self.assertIn("price", ticker)
        self.assertGreater(ticker["price"], 0)

    @unittest.skipUnless(_has_network(), "测试网不可达")
    def test_klines_shape(self) -> None:
        adapter = HyperliquidAdapter()
        candles = adapter.klines("BTC", interval="15m", limit=10)
        self.assertGreaterEqual(len(candles), 1)
        self.assertIn("c", candles[0])
        self.assertGreater(candles[0]["c"], 0)


if __name__ == "__main__":
    unittest.main()

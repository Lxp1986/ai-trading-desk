import os
import unittest
from unittest.mock import patch

from autotrader.binance_testnet import BinanceSpotTestnet, BinanceTestnetError, TESTNET_BASE_URL


class BinanceTestnetAdapterTests(unittest.TestCase):
    def test_adapter_is_testnet_only(self):
        self.assertEqual(BinanceSpotTestnet().base_url, TESTNET_BASE_URL)
        self.assertNotIn("api.binance.com", BinanceSpotTestnet().base_url)

    def test_signed_call_requires_environment_credentials(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(BinanceTestnetError):
                BinanceSpotTestnet().account()

    def test_public_url_uses_testnet(self):
        adapter = BinanceSpotTestnet()
        with patch("urllib.request.urlopen") as urlopen:
            class Response:
                def __enter__(self): return self
                def __exit__(self, *args): pass
                def read(self): return b'{"symbol":"BTCUSDT","price":"1"}'
            urlopen.return_value = Response()
            adapter.ticker_price("BTCUSDT")
            request = urlopen.call_args.args[0]
            self.assertTrue(request.full_url.startswith(TESTNET_BASE_URL))

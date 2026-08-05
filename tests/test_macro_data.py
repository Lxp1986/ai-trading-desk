"""Tests for macro data pipeline (宏观数据源)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from autotrader.macro_data import load_macro, scan_macro


class TestMacroData(unittest.TestCase):
    def setUp(self) -> None:
        import autotrader.macro_data as module
        self._tmp = tempfile.TemporaryDirectory()
        self._old = module.MACRO_PATH
        module.MACRO_PATH = Path(self._tmp.name) / "macro.json"
        self.module = module

    def tearDown(self) -> None:
        import autotrader.macro_data as module
        module.MACRO_PATH = self._old
        self._tmp.cleanup()

    def test_scan_macro_shape(self) -> None:
        result = scan_macro()
        self.assertIn("updated_at", result)
        self.assertIn("fng", result)
        self.assertIn("global", result)
        self.assertIn("dvol_btc", result)
        self.assertIn("dvol_eth", result)
        self.assertIn("stablecoins", result)
        # 至少一个源成功（网络可用时）
        any_ok = any(result[k] is not None for k in ("fng", "global", "dvol_btc", "stablecoins"))
        self.assertTrue(any_ok, "至少一个宏观数据源应可用")

    def test_load_macro_empty(self) -> None:
        self.assertEqual(load_macro(), {})


if __name__ == "__main__":
    unittest.main()

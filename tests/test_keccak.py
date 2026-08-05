"""Tests for Keccak-256 (Hyperliquid signing primitive)."""

from __future__ import annotations

import unittest

from autotrader.keccak import keccak256

# NIST / 社区标准向量
_VECTORS = [
    (b"", "c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470"),
    (b"abc", "4e03657aea45a94fc7d47ba826c8d667c0d1e6e33a64a036ec44f58fa12d6c45"),
    (b"hello world", "47173285a8d7341e5e972fc677286384f802f8ef42a5ec5f03bbfa254cb01fad"),
    (b"The quick brown fox jumps over the lazy dog",
     "4d741b6f1eb29cb2a9b9911c82f56fa8d73b04959d3d9d222895df6c0b28aa15"),
]


class TestKeccak256(unittest.TestCase):
    def test_standard_vectors(self) -> None:
        for data, expected in _VECTORS:
            self.assertEqual(keccak256(data).hex(), expected, f"vector: {data!r}")

    def test_empty_message(self) -> None:
        self.assertEqual(len(keccak256(b"")), 32)

    def test_deterministic(self) -> None:
        self.assertEqual(keccak256(b"same"), keccak256(b"same"))


if __name__ == "__main__":
    unittest.main()

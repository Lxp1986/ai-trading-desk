"""Tests for hl_crypto (Hyperliquid 官方签名方案，纯 stdlib)."""

from __future__ import annotations

import unittest

from autotrader import hl_crypto as hc
from autotrader.keccak import keccak256
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat


def _pubkey_tuple(pk):
    pb = pk.public_key().public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)
    return (int.from_bytes(pb[1:33], "big"), int.from_bytes(pb[33:65], "big"))


class HlCryptoTest(unittest.TestCase):
    def test_float_to_wire(self):
        self.assertEqual(hc.float_to_wire(65000.0), "65000")
        self.assertEqual(hc.float_to_wire(0.0001), "0.0001")
        self.assertEqual(hc.float_to_wire(64521.5), "64521.5")

    def test_point_math(self):
        self.assertEqual(hc._point_mul(1, hc._G), hc._G)
        self.assertIsNone(hc._point_mul(hc._N, hc._G))
        two_g = hc._point_mul(2, hc._G)
        self.assertEqual(two_g[0], 0xC6047F9441ED7D6D3045406E95C07CD85C778E4B8CEF3CA7ABAC09B95C709EE5)

    def test_signature_roundtrip(self):
        """签名 → (r,s,v) → 恢复公钥 == 真实公钥（10 轮）。"""
        for i in range(10):
            key = bytes.fromhex(f"{i+3:02d}" * 32)
            pk = ec.derive_private_key(int.from_bytes(key, "big"), ec.SECP256K1())
            digest = keccak256(f"round {i}".encode())
            r, s, v = hc._ecdsa_v(pk, digest)
            q = hc._recover_public_key(r, s, digest, v)
            self.assertEqual(q, _pubkey_tuple(pk), f"round {i}")
            # low-s 强制
            self.assertLessEqual(s, hc._N // 2)

    def test_sign_l1_action_structure(self):
        action = {"type": "order", "orders": [{"a": 3, "b": True, "p": "65000",
                 "s": "0.0001", "r": False, "t": {"limit": {"tif": "Ioc"}}}],
                 "grouping": "na"}
        signed = hc.sign_l1_action("0x" + "11" * 32, action, None, 12345, None, False)
        self.assertEqual(signed["nonce"], 12345)
        sig = signed["signature"]
        self.assertEqual(sorted(sig.keys()), ["r", "s", "v"])
        self.assertTrue(sig["v"] in (27, 28))
        self.assertTrue(sig["r"].startswith("0x"))
        # 恢复地址 == EVM 地址
        q = hc._recover_public_key(int(sig["r"], 16), int(sig["s"], 16),
                                   hc._eip712_digest(
                                       {"name": "Exchange", "version": "1", "chainId": 1337,
                                        "verifyingContract": "0x0000000000000000000000000000000000000000"},
                                       "Agent", [("source", "string"), ("connectionId", "bytes32")],
                                       {"source": "b",
                                        "connectionId": "0x" + hc.action_hash(action, None, 12345, None).hex()}),
                                   sig["v"])
        pub = b"\x04" + q[0].to_bytes(32, "big") + q[1].to_bytes(32, "big")
        recovered = "0x" + keccak256(pub[1:])[-20:].hex()
        from cryptography.hazmat.primitives.asymmetric import ec as _ec
        pk = _ec.derive_private_key(int.from_bytes(bytes.fromhex("11" * 32), "big"), _ec.SECP256K1())
        pb = pk.public_key().public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)
        expect = "0x" + keccak256(pb[1:])[-20:].hex()
        self.assertEqual(recovered, expect)


if __name__ == "__main__":
    unittest.main()

"""Keccak-256（纯 Python，Hyperliquid 签名用）。

Hyperliquid L2 (ed25519 agent key) 签名的消息是 keccak256(规范 JSON)，而 Python
标准库的 hashlib.sha3_256 是 SHA3-256（填充字节 0x06），与 Keccak-256（0x01）
不同。这里提供精简的 keccak-f[1600] 实现，仅用于短消息签名场景。

验证向量（keccak256 空消息）：
    keccak256(b"") == c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470
"""
from __future__ import annotations

import struct

# keccak-f[1600] 24 轮轮常数
_RC = [
    0x0000000000000001, 0x0000000000008082, 0x800000000000808A,
    0x8000000080008000, 0x000000000000808B, 0x0000000080000001,
    0x8000000080008081, 0x8000000000008009, 0x000000000000008A,
    0x0000000000000088, 0x0000000080008009, 0x000000008000000A,
    0x000000008000808B, 0x800000000000008B, 0x8000000000008089,
    0x8000000000008003, 0x8000000000008002, 0x8000000000000080,
    0x000000000000800A, 0x800000008000000A, 0x8000000080008081,
    0x8000000000008080, 0x0000000080000001, 0x8000000080008008,
]

_ROTATION = [
    [0, 36, 3, 41, 18],
    [1, 44, 10, 45, 2],
    [62, 6, 43, 15, 61],
    [28, 55, 25, 21, 56],
    [27, 20, 39, 8, 14],
]

_MASK = (1 << 64) - 1


def _rotl(x: int, n: int) -> int:
    return ((x << n) | (x >> (64 - n))) & _MASK


def _keccak_f(state: list[int]) -> None:
    """state: 25 个 64-bit lanes（A[x][y] 按 x + 5y 排布）。"""
    for rc in _RC:
        # θ
        c = [state[x] ^ state[x + 5] ^ state[x + 10] ^ state[x + 15] ^ state[x + 20] for x in range(5)]
        d = [c[(x - 1) % 5] ^ _rotl(c[(x + 1) % 5], 1) for x in range(5)]
        for x in range(5):
            for y in range(5):
                state[x + 5 * y] ^= d[x]
        # ρ + π
        b = [0] * 25
        for x in range(5):
            for y in range(5):
                b[y + 5 * ((2 * x + 3 * y) % 5)] = _rotl(state[x + 5 * y], _ROTATION[x][y])
        # χ
        for y in range(5):
            row = [b[x + 5 * y] for x in range(5)]
            for x in range(5):
                state[x + 5 * y] = row[x] ^ ((~row[(x + 1) % 5]) & row[(x + 2) % 5]) & _MASK
        # ι
        state[0] ^= rc


def keccak256(data: bytes) -> bytes:
    """Keccak-256 摘要（rate=136 字节，suffix 0x01，final 0x80）。"""
    rate = 136
    state = [0] * 25

    # 吸收完整块
    block_count = len(data) // rate
    for i in range(block_count):
        block = data[i * rate:(i + 1) * rate]
        for j in range(rate // 8):
            state[j] ^= struct.unpack("<Q", block[j * 8:(j + 1) * 8])[0]
        _keccak_f(state)

    # 最后一块 + 填充（keccak: 0x01 ... 0x80）
    last = data[block_count * rate:]
    padded = bytearray(last)
    padded.append(0x01)
    padded.extend(b"\x00" * (rate - len(padded) - 1))
    padded.append(0x80)
    for j in range(rate // 8):
        state[j] ^= struct.unpack("<Q", padded[j * 8:(j + 1) * 8])[0]
    _keccak_f(state)

    # 挤出 32 字节
    result = bytearray()
    for j in range(4):
        result.extend(struct.pack("<Q", state[j]))
    return bytes(result)

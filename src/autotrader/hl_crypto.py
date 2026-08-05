"""Hyperliquid 官方签名方案（纯 stdlib 实现，零第三方依赖）。

参照 hyperliquid-python-sdk（signing.py）：
- action_hash：msgpack 编码 action + nonce(8B big) + vault 标记 + expiresAfter 标记 → keccak256
- EIP-712 typed-data（phantom agent: {source, connectionId}，domain: Exchange/1/1337/0x000..0）
- ECDSA secp256k1 签名（私钥 = 用户 EVM 私钥）→ 返回 {r, s, v}

模块内提供：
- msgpack_pack()  mini msgpack 编码器（覆盖本项目 action 所需类型）
- secp256k1 点运算（公钥恢复用，求 v）
- hl_sign_order()  完整签名入口
"""
from __future__ import annotations

from typing import Any

from .keccak import keccak256

# ---------- secp256k1 参数 ----------
_P = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
_N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
_G = (0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798,
      0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8)


def _inv(a: int, m: int) -> int:
    """模逆（扩展欧几里得）。"""
    return pow(a, m - 2, m)


def _point_add(p1: tuple[int, int] | None, p2: tuple[int, int] | None):
    """椭圆曲线点加法（None = 无穷远点）。"""
    if p1 is None:
        return p2
    if p2 is None:
        return p1
    x1, y1 = p1
    x2, y2 = p2
    if x1 == x2 and (y1 + y2) % _P == 0:
        return None
    if p1 == p2:
        lam = (3 * x1 * x1) * _inv(2 * y1, _P) % _P
    else:
        lam = (y2 - y1) * _inv(x2 - x1, _P) % _P
    x3 = (lam * lam - x1 - x2) % _P
    y3 = (lam * (x1 - x3) - y1) % _P
    return (x3, y3)


def _point_mul(k: int, point: tuple[int, int]) -> tuple[int, int] | None:
    """标量乘法。"""
    result = None
    addend = point
    while k:
        if k & 1:
            result = _point_add(result, addend)
        addend = _point_add(addend, addend)
        k >>= 1
    return result


def _recover_public_key(r: int, s: int, digest: bytes, v: int):
    """从 (r, s, v) 恢复公钥（标准 secp256k1 恢复）。

    R = (x=r, y 按 recid 奇偶)；Q = r⁻¹(s·R − e·G)。recid = v − 27（EVM 传统 v 为 27/28）。
    """
    return _recover_with_parity(r, s, digest, (v - 27) & 1)


def _recover_with_parity(r: int, s: int, digest: bytes, parity: int):
    """按指定 y-parity 恢复公钥。"""
    e = int.from_bytes(digest, "big") % _N
    x = r % _P
    y_sq = (pow(x, 3, _P) + 7) % _P
    y = pow(y_sq, (_P + 1) // 4, _P)  # 二次剩余平方根（P ≡ 3 mod 4）
    if (y * y) % _P != y_sq:
        raise ValueError("recover: invalid r point")
    if (y & 1) != parity:
        y = _P - y
    r_point = (x, y)
    r_inv = _inv(r, _N)
    e_g = _point_mul(e % _N, _G)
    s_r = _point_mul(s, r_point)
    tmp = _point_add(s_r, (e_g[0], _P - e_g[1]) if e_g else None)
    q = _point_mul(r_inv, tmp) if tmp is not None else None
    if q is None:
        raise ValueError("recover: infinity")
    return q


def _ecdsa_v(private_key, digest: bytes) -> tuple[int, int, int]:
    """ECDSA 签名（low-s 规范化，与 eth_keys 一致）并确定 v。

    关键：eth_keys/eth_account 强制 low-s——若 s > N/2 则 s' = N − s 且
    v = 27 + (y_parity XOR 1)；否则 v = 27 + y_parity。
    """
    from cryptography.hazmat.primitives.asymmetric import ec, utils
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

    sig_der = private_key.sign(digest, ec.ECDSA(utils.Prehashed(hashes.SHA256())))
    r, s = _der_to_rs(sig_der)
    pub_bytes = private_key.public_key().public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)
    true_q = (int.from_bytes(pub_bytes[1:33], "big"), int.from_bytes(pub_bytes[33:65], "big"))
    y_parity: int | None = None
    for candidate_parity in (0, 1):
        try:
            q = _recover_with_parity(r, s, digest, candidate_parity)
        except ValueError:
            continue
        if q == true_q:
            y_parity = candidate_parity
            break
    if y_parity is None:
        raise ValueError("ECDSA v recovery failed")
    if s > _N // 2:
        # low-s 规范化（eth_keys 同款）：s 翻转 + v parity 翻转
        return r, _N - s, 27 + (y_parity ^ 1)
    return r, s, 27 + y_parity


def _der_to_rs(der: bytes) -> tuple[int, int]:
    """DER 编码签名 → (r, s)。"""
    assert der[0] == 0x30
    i = 2
    assert der[i] == 0x02
    r_len = der[i + 1]
    r = int.from_bytes(der[i + 2:i + 2 + r_len], "big")
    i += 2 + r_len
    assert der[i] == 0x02
    s_len = der[i + 1]
    s = int.from_bytes(der[i + 2:i + 2 + s_len], "big")
    return r, s


# ---------- mini msgpack（action_hash 用，参照 msgpack 默认行为） ----------

def msgpack_pack(obj: Any) -> bytes:
    """最小 msgpack 编码器：覆盖 str/int/bool/dict/list（本项目 action 结构）。"""
    out = bytearray()

    def enc(value: Any) -> None:
        if isinstance(value, bool):
            out.append(0xC3 if value else 0xC2)
        elif isinstance(value, int):
            if 0 <= value <= 0x7F:
                out.append(value)
            elif value < 0:
                out.append(0xE0 | (value & 0x1F))
            else:
                raise ValueError(f"msgpack int too large: {value}")
        elif isinstance(value, str):
            data = value.encode("utf-8")
            n = len(data)
            if n <= 31:
                out.append(0xA0 | n)
            elif n <= 255:
                out.append(0xD9)
                out.append(n)
            else:
                raise ValueError("msgpack str too long")
            out.extend(data)
        elif isinstance(value, (list, tuple)):
            n = len(value)
            if n <= 15:
                out.append(0x90 | n)
            else:
                raise ValueError("msgpack array too long")
            for item in value:
                enc(item)
        elif isinstance(value, dict):
            n = len(value)
            if n <= 15:
                out.append(0x80 | n)
            else:
                raise ValueError("msgpack map too long")
            for key, val in value.items():
                enc(key)
                enc(val)
        else:
            raise ValueError(f"msgpack unsupported type: {type(value)}")

    enc(obj)
    return bytes(out)


# ---------- EIP-712 ----------

def _encode_type(types: list[tuple[str, str]]) -> bytes:
    """类型定义 → typeHash 输入（如 "Agent(string source,bytes32 connectionId)"）。"""
    return ("Agent(" + ",".join(f"{t} {n}" for n, t in types) + ")").encode()


def _encode_data_string(value: str) -> bytes:
    return keccak256(value.encode("utf-8"))


def _encode_uint(value: int) -> bytes:
    return value.to_bytes(32, "big")


def _encode_address(value: str) -> bytes:
    raw = bytes.fromhex(value[2:] if value.startswith("0x") else value)
    return raw.rjust(32, b"\x00")


def _eip712_struct_hash(primary_type: str, types: list[tuple[str, str]],
                        message: dict[str, Any]) -> bytes:
    """EIP-712 struct hash（Agent 结构：string → keccak，bytes32 → 原样）。"""
    type_hash = keccak256(_encode_type(types))
    parts = [type_hash]
    for name, typ in types:
        value = message[name]
        if typ == "string":
            parts.append(_encode_data_string(str(value)))
        elif typ == "bytes32":
            raw = bytes.fromhex(value[2:] if isinstance(value, str) and value.startswith("0x") else value)
            parts.append(raw.rjust(32, b"\x00"))
        elif typ == "uint256":
            parts.append(_encode_uint(int(value)))
        elif typ == "address":
            parts.append(_encode_address(str(value)))
        else:
            raise ValueError(f"unsupported EIP712 type: {typ}")
    return keccak256(b"".join(parts))


def _eip712_domain_separator(domain: dict[str, Any]) -> bytes:
    domain_types = [
        ("name", "string"), ("version", "string"),
        ("chainId", "uint256"), ("verifyingContract", "address"),
    ]
    type_hash = keccak256(
        b"EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)")
    parts = [type_hash,
             _encode_data_string(domain["name"]),
             _encode_data_string(domain["version"]),
             _encode_uint(int(domain["chainId"])),
             _encode_address(domain["verifyingContract"])]
    return keccak256(b"".join(parts))


def _eip712_digest(domain: dict[str, Any], primary_type: str,
                   types: list[tuple[str, str]], message: dict[str, Any]) -> bytes:
    domain_separator = _eip712_domain_separator(domain)
    struct_hash = _eip712_struct_hash(primary_type, types, message)
    return keccak256(b"\x19\x01" + domain_separator + struct_hash)


# ---------- Hyperliquid 官方签名入口 ----------

def float_to_wire(x: float) -> str:
    """SDK float_to_wire：8 位小数 → normalize → 固定小数格式（去尾零）。"""
    from decimal import Decimal
    rounded = f"{x:.8f}"
    if abs(float(rounded) - x) >= 1e-12:
        raise ValueError(f"float_to_wire causes rounding: {x}")
    if rounded == "-0":
        rounded = "0"
    normalized = Decimal(rounded).normalize()
    return f"{normalized:f}"


def action_hash(action: dict[str, Any], vault_address: str | None,
                nonce: int, expires_after: int | None) -> bytes:
    """官方 action_hash：msgpack(action) + nonce(8B big) + vault 标记 + expires 标记。"""
    data = msgpack_pack(action)
    data += nonce.to_bytes(8, "big")
    if vault_address is None:
        data += b"\x00"
    else:
        data += b"\x01" + bytes.fromhex(vault_address[2:])
    if expires_after is not None:
        data += b"\x00" + expires_after.to_bytes(8, "big")
    return keccak256(data)


def sign_l1_action(private_key_hex: str, action: dict[str, Any],
                   vault_address: str | None, nonce: int,
                   expires_after: int | None, is_mainnet: bool) -> dict[str, Any]:
    """官方 sign_l1_action：构造 phantom agent → EIP-712 → ECDSA → {r, s, v}。

    private_key_hex: EVM 私钥（hex，可带 0x 前缀）。
    """
    from cryptography.hazmat.primitives.asymmetric import ec

    hash_bytes = action_hash(action, vault_address, nonce, expires_after)
    phantom_agent = {"source": "a" if is_mainnet else "b", "connectionId": "0x" + hash_bytes.hex()}
    domain = {
        "name": "Exchange", "version": "1", "chainId": 1337,
        "verifyingContract": "0x0000000000000000000000000000000000000000",
    }
    agent_types = [("source", "string"), ("connectionId", "bytes32")]
    digest = _eip712_digest(domain, "Agent", agent_types, phantom_agent)

    key = bytes.fromhex(private_key_hex.strip().lower().replace("0x", ""))
    private_key = ec.derive_private_key(int.from_bytes(key, "big"), ec.SECP256K1())
    r, s, v = _ecdsa_v(private_key, digest)
    return {
        "action": action,
        "nonce": nonce,
        "signature": {"r": hex(r), "s": hex(s), "v": v},
    }

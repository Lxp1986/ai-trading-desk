"""链上数据分析员 + 聪明钱包研究员（接口落地：信号记录与回放）。

数据采集由 CEO（Hermes）通过链上工具（如 OnchainOS）执行后，调用
``record_signal`` 落盘，本模块提供：
- ``record_signal`` 记录资金流/巨鲸/集中度/钱包画像信号到 artifacts/onchain.jsonl；
- ``load_signals`` 读取（供报告与策略参考）；
- ``signal_confidence`` 多钱包共识置信度计算（研讨纪要 §3.14 规则）。

链上信号是辅助证据，不等于直接跟单；至少多钱包共同动作 + 成交量确认
+ 突破成立才提高评分。
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ONCHAIN_PATH = Path(__file__).resolve().parents[2] / "artifacts" / "onchain.jsonl"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def record_signal(*, kind: str, symbol: str, direction: str,
                  evidence: dict[str, Any], confidence: float,
                  detail: str = "") -> dict[str, Any]:
    """记录链上信号。kind: inflow/outflow/whale/concentration/wallet_profile。"""
    signal = {
        "id": uuid.uuid4().hex[:12],
        "time": now_iso(),
        "kind": kind,
        "symbol": symbol,
        "direction": direction,       # bullish / bearish / neutral
        "confidence": round(confidence, 2),
        "evidence": evidence,
        "detail": detail,
    }
    ONCHAIN_PATH.parent.mkdir(parents=True, exist_ok=True)
    with ONCHAIN_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(signal, ensure_ascii=False) + "\n")
    return signal


def load_signals(limit: int = 50) -> list[dict[str, Any]]:
    if not ONCHAIN_PATH.exists():
        return []
    signals: list[dict[str, Any]] = []
    with ONCHAIN_PATH.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                signals.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return signals[-limit:]


def signal_confidence(wallet_signals: list[dict[str, Any]], volume_confirmed: bool,
                      breakout_confirmed: bool) -> float:
    """多钱包共识置信度：基础 0.2 + 钱包数加权 + 成交量/突破加成。

    研讨纪要：至少多钱包共同动作 + 成交量确认 + 突破成立才提高评分。
    """
    if not wallet_signals:
        return 0.0
    agreeing = [w for w in wallet_signals if w.get("direction") == wallet_signals[0].get("direction")]
    base = 0.2 + 0.15 * len(agreeing)
    if volume_confirmed:
        base += 0.15
    if breakout_confirmed:
        base += 0.2
    return round(min(base, 0.95), 2)


# ---------------------------------------------------------------- 确定性链上采集
# 免费公开 API（mempool.space / blockchain.info，零 Token）。供"链上数据分析员"
# 每轮主动履职：BTC 网络拥堵度 + 大额未确认交易异动检测。

MEMPOOL_FEES_URL = "https://mempool.space/api/v1/fees/recommended"
MEMPOOL_RECENT_URL = "https://mempool.space/api/mempool/recent"
UNCONFIRMED_URL = "https://blockchain.info/unconfirmed-transactions?format=json"

CONGESTION_FEE_THRESHOLD = 50    # fastestFee sats/vB 超过 → 拥堵 L2
WHALE_USD_THRESHOLD = 500_000    # 单笔未确认交易 ≥ 50 万美元 → 巨鲸异动


def _get_json(url: str, timeout: int = 10) -> Any:
    import urllib.request

    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (autotrader-research)"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read(500_000))


def scan_btc_onchain() -> dict[str, Any]:
    """链上数据分析员主动履职：抓取 BTC 网络指标 → 异动检测 → 信号落盘。

    检测项：
    1. 网络拥堵（fastestFee 超阈值）→ 拥堵事件；
    2. 大额未确认交易（≥ 50 万美元）→ 巨鲸异动信号；
    返回统计（供 Dashboard 展示当日产出）。
    """
    import urllib.error

    signals_recorded = 0
    congestion = None
    whale_txns = []
    errors: list[str] = []

    # 1) 手续费/拥堵
    try:
        fees = _get_json(MEMPOOL_FEES_URL)
        fastest = int(fees.get("fastestFee", 0))
        if fastest >= CONGESTION_FEE_THRESHOLD:
            congestion = fastest
            record_signal(
                kind="congestion", symbol="BTC", direction="neutral",
                evidence={"fastest_fee_sat_vb": fastest},
                confidence=0.5,
                detail=f"BTC 网络拥堵：fastestFee {fastest} sats/vB ≥ {CONGESTION_FEE_THRESHOLD}",
            )
            signals_recorded += 1
    except (urllib.error.URLError, OSError, ValueError) as exc:
        errors.append(f"fees: {type(exc).__name__}")

    # 2) 大额未确认交易（巨鲸异动）
    try:
        data = _get_json(UNCONFIRMED_URL)
        for tx in (data.get("txs") or [])[:200]:
            value = float(tx.get("value", 0) or 0) / 1e8 * 0  # BTC→USD 需价格，下面用 BTC 量
            btc_amount = float(tx.get("value", 0) or 0) / 1e8
            # 以 BTC 数量近似：≥ WHALE_USD_THRESHOLD/64000 ≈ 7.8 BTC
            if btc_amount >= 7.0:
                whale_txns.append({
                    "hash": (tx.get("hash") or "")[:16],
                    "btc": round(btc_amount, 2),
                    "inputs": len(tx.get("inputs", [])),
                    "outputs": len(tx.get("out", [])),
                })
        if whale_txns:
            record_signal(
                kind="whale", symbol="BTC", direction="neutral",
                evidence={"whale_txns": whale_txns[:5], "count": len(whale_txns)},
                confidence=0.4,
                detail=f"检测到 {len(whale_txns)} 笔大额未确认交易（≥7 BTC）",
            )
            signals_recorded += 1
    except (urllib.error.URLError, OSError, ValueError) as exc:
        errors.append(f"unconfirmed: {type(exc).__name__}")

    return {
        "congestion_fee_sat_vb": congestion,
        "whale_txns": len(whale_txns),
        "signals_recorded": signals_recorded,
        "errors": errors,
    }

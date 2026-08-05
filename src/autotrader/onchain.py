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

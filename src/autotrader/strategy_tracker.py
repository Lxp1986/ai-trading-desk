"""策略绩效跟踪与自适应调整（策略研究员核心职责落地）。

研讨纪要 §3.12："策略退化时降权或停用，不因过去优秀永久保留"。

机制：
- ``record_signal_result`` 平仓时按策略归因盈亏（由组合层/CEO 调用）；
- ``strategy_weights`` 从绩效计算每个策略当前权重：
  - 记录不足 3 笔 → 权重 1.0（默认信任）；
  - 最近 5 笔亏损 ≥3 笔 → 权重 0.5（降权观察）；
  - 连续亏损 ≥5 笔 → 权重 0（停用，信号不再采纳）；
  - 停用后出现盈利记录 → 恢复 0.8 观察；
- ``apply_weights`` 调整策略信号强度：strength × weight；
- 权重表落盘 ``artifacts/strategy_weights.json``，runner 每轮更新。
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PERF_PATH = Path(__file__).resolve().parents[2] / "artifacts" / "strategy_perf.jsonl"
WEIGHTS_PATH = Path(__file__).resolve().parents[2] / "artifacts" / "strategy_weights.json"

# 自适应参数
MIN_RECORDS = 3          # 少于该笔数不做降权
LOSS_RECENT = 3          # 最近 5 笔中亏损 ≥ 该数 → 降权
LOSS_STREAK = 5          # 连续亏损 ≥ 该数 → 停用
WEIGHT_PENALTY = 0.5     # 降权系数
WEIGHT_REHAB = 0.8       # 停用后恢复观察权重


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def record_signal_result(*, strategy: str, symbol: str, pnl: float,
                         closed_at: str | None = None) -> dict[str, Any]:
    """平仓后按策略归因记录一笔结果。pnl 为该笔交易已实现盈亏（USDT）。"""
    record = {
        "time": closed_at or now_iso(),
        "strategy": strategy,
        "symbol": symbol,
        "pnl": round(pnl, 4),
    }
    PERF_PATH.parent.mkdir(parents=True, exist_ok=True)
    with PERF_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def load_perf(strategy: str | None = None, limit: int = 200) -> list[dict[str, Any]]:
    if not PERF_PATH.exists():
        return []
    records: list[dict[str, Any]] = []
    with PERF_PATH.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    if strategy:
        records = [r for r in records if r.get("strategy") == strategy]
    return records[-limit:]


def strategy_weights() -> dict[str, float]:
    """按绩效计算各策略权重。"""
    if not PERF_PATH.exists():
        return {}
    by_strategy: dict[str, list[dict[str, Any]]] = {}
    for record in load_perf():
        by_strategy.setdefault(record.get("strategy", "?"), []).append(record)

    weights: dict[str, float] = {}
    for name, records in by_strategy.items():
        if len(records) < MIN_RECORDS:
            weights[name] = 1.0
            continue
        recent = records[-5:]
        losses_recent = sum(1 for r in recent if r.get("pnl", 0) < 0)
        # 连续亏损
        streak = 0
        for r in reversed(records):
            if r.get("pnl", 0) < 0:
                streak += 1
            else:
                break
        if streak >= LOSS_STREAK:
            weights[name] = 0.0
        elif losses_recent >= LOSS_RECENT:
            weights[name] = WEIGHT_PENALTY
        else:
            # 曾停用（权重文件里有 0）且最近盈利 → 恢复观察
            weights[name] = WEIGHT_REHAB if _was_disabled(name) else 1.0
    return weights


def _was_disabled(name: str) -> bool:
    if not WEIGHTS_PATH.exists():
        return False
    try:
        saved = json.loads(WEIGHTS_PATH.read_text(encoding="utf-8"))
        return saved.get(name, 1.0) == 0.0
    except (OSError, ValueError):
        return False


def save_weights(weights: dict[str, float]) -> None:
    WEIGHTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {"updated_at": now_iso(), "weights": weights}
    WEIGHTS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def apply_weights(signals: list[Any], weights: dict[str, float] | None = None) -> list[Any]:
    """按权重调整信号强度；权重 0 的策略信号标注停用并过滤。"""
    if weights is None:
        weights = strategy_weights()
    result: list[Any] = []
    for signal in signals:
        weight = weights.get(signal.strategy, 1.0)
        if weight <= 0:
            signal.reason = f"{signal.reason}（策略已停用：近期连续亏损）"
            continue
        signal.strength = round(signal.strength * weight, 2)
        if weight < 1.0:
            signal.reason = f"{signal.reason}（权重 {weight}：近期表现降权）"
        result.append(signal)
    return result


def update_weights() -> dict[str, float]:
    """计算并落盘当前权重（runner 每轮调用）。"""
    weights = strategy_weights()
    save_weights(weights)
    return weights

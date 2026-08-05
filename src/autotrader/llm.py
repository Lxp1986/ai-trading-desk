"""Hermes 模型集成层（研究层）。

设计原则（2026-08-05 董事长确认）：本项目**不额外搭建模型 API 服务、
不配置 LLM API Key**。Hermes 本身就是模型执行者——交易假设草拟、
新闻归纳、证据冲突分析、持仓复核、报告文字化均由 Hermes 实际操作，
把结果写入项目，而不是由项目代码自己去调用某个模型 API。

本模块职责：

1. ``register_thesis()``：接收 Hermes 草拟的交易假设（结构化 dict），
   校验后生成 ``TradeIntent``（source="hermes"）。生成的意图仍必须
   经过独立风控审核，Hermes 草拟不等于下单。
2. ``record_usage()``：Hermes 每次为本项目完成模型型任务后，登记
   Token 用量到 ``artifacts/token_usage.json``（仅统计本项目，不读取
   Hermes 全局用量，不混入其他项目）。
3. ``deterministic_fallback()``：Hermes 不可用/预算不足时的确定性
   观察模式降级策略，保证安全监控与模拟链路不中断。
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import MarketSnapshot, Side, TradeIntent

_USAGE_PATH = Path(__file__).resolve().parents[2] / "artifacts" / "token_usage.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def record_usage(provider: str, model: str, input_tokens: int, output_tokens: int) -> dict[str, Any]:
    """Accumulate project token usage into artifacts/token_usage.json.

    Called by Hermes after it performs a model-type task for this project
    (thesis drafting, news summarisation, review, report writing). The
    provider/model reflect whatever Hermes is currently routed to.
    """
    usage: dict[str, Any] = {
        "project": "AI自主交易事业部",
        "currency": "tokens",
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
        "api_calls": 0,
        "updated_at": None,
        "note": "仅统计本项目通过本地记录器登记的模型调用；不读取Hermes全局或其他项目消耗。",
        "provider": provider,
        "model": model,
    }
    _USAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if _USAGE_PATH.exists():
        try:
            with _USAGE_PATH.open("r", encoding="utf-8") as handle:
                current = json.load(handle)
            for key in ("input_tokens", "output_tokens", "total_tokens", "api_calls"):
                usage[key] = int(current.get(key, 0))
            if current.get("provider"):
                usage["provider"] = current["provider"]
            if current.get("model"):
                usage["model"] = current["model"]
        except (OSError, ValueError, TypeError):
            pass  # corrupted/unreadable usage file: start fresh counters
    usage["input_tokens"] += max(0, int(input_tokens))
    usage["output_tokens"] += max(0, int(output_tokens))
    usage["total_tokens"] += max(0, int(input_tokens)) + max(0, int(output_tokens))
    usage["api_calls"] += 1
    usage["updated_at"] = _now_iso()
    with _USAGE_PATH.open("w", encoding="utf-8") as handle:
        json.dump(usage, handle, ensure_ascii=False, indent=2)
    return usage


def deterministic_fallback(snapshot: MarketSnapshot) -> TradeIntent:
    """Deterministic observation-mode thesis when Hermes is unavailable."""
    if snapshot.trend == "trend_up" and snapshot.volume_ratio >= 1.5 and snapshot.liquidity_ok:
        quantity = round(50.0 / snapshot.price, 8)  # ~50 USDT small probe position
        return TradeIntent(
            symbol=snapshot.symbol,
            side=Side.BUY,
            quantity=quantity,
            thesis="确定性降级：趋势与成交量同时确认，按最小仓观察规则试探",
            invalidation="价格跌破最近结构低点或成交量萎缩",
            stop_price=round(snapshot.price * 0.98, 2),
            confidence=0.55,
            source="deterministic_fallback",
        )
    return TradeIntent(
        symbol=snapshot.symbol,
        side=Side.HOLD,
        quantity=0.0,
        thesis="确定性降级：市场状态不满足趋势确认条件，保持观察",
        invalidation="无",
        stop_price=None,
        confidence=0.5,
        source="deterministic_fallback",
    )


def register_thesis(snapshot: MarketSnapshot, thesis: dict[str, Any]) -> TradeIntent:
    """Validate and register a thesis drafted by Hermes.

    ``thesis`` keys: ``side`` (buy/sell/hold), ``thesis``, ``invalidation``,
    ``stop_price`` (number or null), ``confidence`` (0..1).

    The result carries ``source="hermes"`` and still must pass the
    independent risk review before it becomes a decision.
    """
    side_raw = str(thesis.get("side", "hold")).lower()
    side = Side.HOLD if side_raw not in {"buy", "sell"} else Side(side_raw)
    try:
        confidence = float(thesis.get("confidence", 0.5))
    except (TypeError, ValueError):
        confidence = 0.5
    confidence = max(0.0, min(1.0, confidence))
    stop_price = thesis.get("stop_price")
    try:
        stop_price = round(float(stop_price), 2) if stop_price is not None else None
    except (TypeError, ValueError):
        stop_price = None

    quantity = 0.0
    if side is not Side.HOLD:
        # Conservative probe sizing: Hermes proposes direction, local sizing
        # keeps the order small and within risk limits.
        quantity = round(50.0 / snapshot.price, 8)

    return TradeIntent(
        symbol=snapshot.symbol,
        side=side,
        quantity=quantity,
        thesis=str(thesis.get("thesis", "")).strip() or "Hermes草拟假设（无摘要）",
        invalidation=str(thesis.get("invalidation", "")).strip() or "无",
        stop_price=stop_price,
        confidence=confidence,
        source="hermes",
    )

"""LLM research layer for the trading control plane.

Hermes-routed model integration per the project charter:

- Model output is a RESEARCH INPUT. It can draft a trade thesis, but the
  thesis must still pass the independent risk review before it becomes a
  decision, and it never places an order.
- Credentials come only from environment variables, never from code or
  audit logs.
- When the API is unavailable, out of budget, or the response cannot be
  parsed, the module degrades to a deterministic fallback instead of
  failing the pipeline (observation mode).

Environment variables (all optional):

- ``LLM_API_KEY`` (falls back to ``DEEPSEEK_API_KEY``)
- ``LLM_BASE_URL``  (default ``https://api.deepseek.com/v1``)
- ``LLM_MODEL``     (default ``deepseek-chat``)

Token usage is recorded into ``artifacts/token_usage.json`` (project-only
scope; never reads Hermes-global usage).
"""

from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import MarketSnapshot, Side, TradeIntent

DEFAULT_BASE_URL = "https://api.deepseek.com/v1"
DEFAULT_MODEL = "deepseek-chat"
REQUEST_TIMEOUT_SECONDS = 30.0

_USAGE_PATH = Path(__file__).resolve().parents[2] / "artifacts" / "token_usage.json"


class LLMUnavailableError(RuntimeError):
    """Raised when the model API cannot be used (no key, network, budget)."""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _env_key() -> str:
    key = os.environ.get("LLM_API_KEY") or os.environ.get("DEEPSEEK_API_KEY")
    return (key or "").strip()


def record_usage(provider: str, model: str, input_tokens: int, output_tokens: int) -> dict[str, Any]:
    """Atomically accumulate project token usage into artifacts/token_usage.json."""
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


def chat_json(
    messages: list[dict[str, str]],
    *,
    temperature: float = 0.2,
    max_tokens: int = 800,
) -> dict[str, Any]:
    """Call an OpenAI-compatible chat completions endpoint and return parsed JSON.

    Raises LLMUnavailableError when the model cannot be reached or the
    response is not valid JSON.
    """
    api_key = _env_key()
    if not api_key:
        raise LLMUnavailableError("LLM_API_KEY / DEEPSEEK_API_KEY not set; degraded to deterministic mode")
    base_url = (os.environ.get("LLM_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
    model = os.environ.get("LLM_MODEL") or DEFAULT_MODEL

    body = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
    }
    request = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise LLMUnavailableError(f"model call failed: {exc}") from exc

    usage = payload.get("usage") or {}
    record_usage(provider="deepseek" if "deepseek" in base_url else "llm", model=model,
                 input_tokens=int(usage.get("prompt_tokens", 0) or 0),
                 output_tokens=int(usage.get("completion_tokens", 0) or 0))

    try:
        content = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMUnavailableError(f"unexpected model response shape: {exc}") from exc
    if not isinstance(content, str) or not content.strip():
        raise LLMUnavailableError("empty model response")
    try:
        return json.loads(content)
    except ValueError as exc:
        raise LLMUnavailableError(f"model response is not valid JSON: {exc}") from exc


def deterministic_fallback(snapshot: MarketSnapshot) -> TradeIntent:
    """Deterministic observation-mode thesis when the model is unavailable."""
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


def draft_thesis(
    snapshot: MarketSnapshot,
    market_state: str,
    news_brief: str = "",
    *,
    use_llm: bool = True,
) -> tuple[TradeIntent, dict[str, Any]]:
    """Draft a trade thesis from the market snapshot.

    Returns ``(intent, meta)`` where ``meta`` carries ``degraded``,
    ``provider`` and ``model`` so the caller can audit how the thesis was
    produced. The returned intent has source ``llm_draft`` or
    ``deterministic_fallback`` and still must pass risk review.
    """
    if not use_llm:
        intent = deterministic_fallback(snapshot)
        return intent, {"degraded": True, "provider": None, "model": None, "reason": "llm disabled"}

    prompt = (
        "你是AI交易事业部的研究员。基于给定市场快照、市场状态与新闻简报，"
        "草拟一个交易假设。只输出JSON，不要其他文字。JSON结构：\n"
        "{\n"
        '  "side": "buy" 或 "sell" 或 "hold",\n'
        '  "thesis": "为什么价格可能继续走（含证据与预期差）",\n'
        '  "invalidation": "什么证据会推翻这个判断",\n'
        '  "stop_price": 数字或 null,\n'
        '  "confidence": 0到1之间的小数\n'
        "}\n"
        "约束：不编造消息；证据不足时 side 为 hold；"
        "置信度反映证据强度而非意愿。"
    )
    user_content = (
        f"市场快照: {json.dumps(asdict(snapshot), ensure_ascii=False, default=str)}\n"
        f"市场状态: {market_state}\n"
        f"新闻简报: {news_brief or '（无）'}\n"
        f"风险边界: 单笔模拟订单上限由独立风控审核，草拟时按保守小仓估算。"
    )
    try:
        result = chat_json(
            [
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_content},
            ],
            temperature=0.2,
            max_tokens=800,
        )
    except LLMUnavailableError as exc:
        intent = deterministic_fallback(snapshot)
        return intent, {"degraded": True, "provider": None, "model": None, "reason": str(exc)}

    side_raw = str(result.get("side", "hold")).lower()
    side = Side.HOLD if side_raw not in {"buy", "sell"} else Side(side_raw)
    confidence = float(result.get("confidence", 0.5))
    confidence = max(0.0, min(1.0, confidence))
    stop_price = result.get("stop_price")
    stop_price = round(float(stop_price), 2) if isinstance(stop_price, (int, float)) else None
    quantity = 0.0
    if side is not Side.HOLD:
        # Conservative probe sizing: model proposes direction, local sizing
        # keeps the order small and within risk limits.
        quantity = round(50.0 / snapshot.price, 8)

    intent = TradeIntent(
        symbol=snapshot.symbol,
        side=side,
        quantity=quantity,
        thesis=str(result.get("thesis", "")).strip() or "LLM草拟假设（无摘要）",
        invalidation=str(result.get("invalidation", "")).strip() or "无",
        stop_price=stop_price,
        confidence=confidence,
        source="llm_draft",
    )
    return intent, {
        "degraded": False,
        "provider": "deepseek" if "deepseek" in (os.environ.get("LLM_BASE_URL") or DEFAULT_BASE_URL) else "llm",
        "model": os.environ.get("LLM_MODEL") or DEFAULT_MODEL,
    }

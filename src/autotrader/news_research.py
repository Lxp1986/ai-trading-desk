"""宏观与新闻研究员（落地：事件分级 + 落盘）。

新闻抓取由 CEO（Hermes）联网执行后调用本模块记录与分级；本模块提供：
- ``grade_event`` 事件分级（A/B/C）；
- ``record_event`` 写入 artifacts/events.jsonl；
- ``load_events`` 读取（供策略引擎 event_driven 使用）。

分级规则（研讨纪要 §3.11 摘要）：
- A：官方公告/宏观数据/监管定调等已验证、影响持续、预期差明确的重大事件；
- B：可靠媒体报道/行业事件，影响待确认；
- C：传闻/未验证消息/名人观点，只观察。
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

EVENTS_PATH = Path(__file__).resolve().parents[2] / "artifacts" / "events.jsonl"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def grade_event(*, verified: bool, official: bool, expected_gap: bool,
                persistence: bool, source_quality: str) -> str:
    """按事件特征分级。"""
    if verified and official and expected_gap and persistence:
        return "A"
    if source_quality in ("official", "reliable") and verified:
        return "A" if expected_gap else "B"
    return "B" if verified else "C"


def record_event(*, title: str, impact: str, assets: list[str],
                 grade: str, bias: str | None = None,
                 source: str = "", details: str = "") -> dict[str, Any]:
    """记录一条事件到 events.jsonl，返回事件字典。"""
    event = {
        "id": uuid.uuid4().hex[:12],
        "time": now_iso(),
        "title": title,
        "impact": impact,
        "assets": assets,
        "grade": grade,
        "bias": bias,
        "source": source,
        "details": details,
    }
    EVENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with EVENTS_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")
    return event


def load_events(limit: int = 50) -> list[dict[str, Any]]:
    if not EVENTS_PATH.exists():
        return []
    events: list[dict[str, Any]] = []
    with EVENTS_PATH.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return events[-limit:]

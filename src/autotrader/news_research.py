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


# ---------------------------------------------------------------- 确定性新闻采集
# 免费公开 RSS 源（stdlib urllib + xml，零 Token）。抓取 → 关键词分级 → 落盘。
# 供"宏观与新闻研究员"每轮主动履职，不依赖 Hermes 介入。

NEWS_SOURCES = [
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://cointelegraph.com/rss",
]

# 关键词 → 级别 / 方向（标题通常为英文）
GRADE_A_KEYWORDS = (
    "sec", "etf", "fed", "federal reserve", "rate cut", "rate hike", "halving",
    "congress", "senate", "regulation", "lawsuit", "arrest", "hack", "exploit",
    "bankruptcy", "cpi", "inflation", "crackdown", "ban", "sanction",
)
GRADE_B_KEYWORDS = (
    "whale", "listing", "delisting", "upgrade", "partnership", "investment",
    "acquisition", "funding", "launch", "mainnet", "airdrop", "unlock",
    "inflow", "outflow", "spot", "stablecoin", "ethereum", "bitcoin spot",
)
BULL_KEYWORDS = (
    "approve", "launch", "surge", "rally", "gain", "partnership", "adoption",
    "inflow", "upgrade", "record", "all-time", "breakout", "buy",
)
BEAR_KEYWORDS = (
    "hack", "exploit", "ban", "lawsuit", "crash", "drop", "outflow",
    "reject", "delay", "inflation", "crackdown", "arrest", "bankruptcy",
    "sue", "charge", "fraud", "sell", "liquidation",
)


def _fetch_rss(url: str, timeout: int = 10) -> list[dict[str, Any]]:
    """抓取一个 RSS 源，返回 [{title, link, pub_date}]。"""
    import urllib.request
    from xml.etree import ElementTree

    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (autotrader-research)"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read(300_000)
    root = ElementTree.fromstring(body)
    items: list[dict[str, Any]] = []
    for item in root.iter("item"):
        title_el = item.find("title")
        link_el = item.find("link")
        pub_el = item.find("pubDate")
        title = (title_el.text or "").strip() if title_el is not None else ""
        if not title:
            continue
        items.append({
            "title": title[:220],
            "link": (link_el.text or "").strip() if link_el is not None else "",
            "pub_date": (pub_el.text or "").strip() if pub_el is not None else "",
        })
    return items


def keyword_grade(title: str) -> tuple[str, str | None]:
    """关键词规则分级：返回 (级别 A/B/C, 方向 bull/bear/None)。"""
    t = title.lower()
    bias: str | None = None
    bull_hits = sum(1 for k in BULL_KEYWORDS if k in t)
    bear_hits = sum(1 for k in BEAR_KEYWORDS if k in t)
    if bull_hits > bear_hits:
        bias = "bull"
    elif bear_hits > bull_hits:
        bias = "bear"
    grade = "C"
    if any(k in t for k in GRADE_A_KEYWORDS):
        grade = "A"
    elif any(k in t for k in GRADE_B_KEYWORDS):
        grade = "B"
    return grade, bias


def scan_news(max_items: int = 60) -> dict[str, Any]:
    """新闻研究员主动履职：抓取全部源 → 关键词分级 → A/B 级事件落盘。

    去重：与 events.jsonl 已有标题（前 60 字）相同则跳过。
    返回统计（供 Dashboard 展示当日产出）。
    """
    import urllib.error
    from xml.etree import ElementTree as _ET

    seen = {e.get("title", "")[:60] for e in load_events(500)}
    fresh: list[dict[str, Any]] = []
    a_events: list[dict[str, Any]] = []
    errors: list[str] = []
    for url in NEWS_SOURCES:
        try:
            fresh.extend(_fetch_rss(url))
        except (urllib.error.URLError, OSError, _ET.ParseError) as exc:
            errors.append(f"{url.split('/')[2]}: {type(exc).__name__}")

    for item in fresh[:max_items]:
        if item["title"][:60] in seen:
            continue
        seen.add(item["title"][:60])
        grade, bias = keyword_grade(item["title"])
        if grade in ("A", "B"):
            event = record_event(
                title=item["title"], impact="unknown", assets=["BTC"],
                grade=grade, bias=bias,
                source="rss/" + item.get("link", "")[:80] or "rss",
                details=f"自动抓取 {item.get('pub_date', '')}",
            )
            a_events.append(event)

    return {
        "fetched": len(fresh),
        "recorded": len(a_events),
        "a_grade": sum(1 for e in a_events if e["grade"] == "A"),
        "b_grade": sum(1 for e in a_events if e["grade"] == "B"),
        "errors": errors,
    }

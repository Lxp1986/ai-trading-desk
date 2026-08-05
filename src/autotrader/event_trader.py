"""事件交易员（落地：五阶段事件交易流程框架）。

研讨纪要 §3.17：只在重大事件有明确预期差时行动，区分五阶段：
event_pre（事件前）/ confirmation（确认）/ first_wave（第一波冲击）/
diffusion（扩散追涨）/ distribution（派发反转）。

本模块提供：
- ``phase_of`` 按事件时间与价格反应判定阶段；
- ``checklist`` 每个阶段必须满足的确认条件（未满足→等待）；
- ``plan`` 生成事件交易计划草案（方向/分批/失效位由 CEO 复核后执行）。
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

# 事件后各阶段典型时间窗（分钟）
_PHASE_WINDOWS = [
    ("event_pre", None, 0),
    ("confirmation", 0, 30),
    ("first_wave", 30, 180),
    ("diffusion", 180, 24 * 60),
    ("distribution", 24 * 60, None),
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def phase_of(event_time: str, now: str | None = None) -> str:
    """按事件发生到现在的时间判定阶段。event_time/now 为 ISO 字符串。"""
    if not event_time:
        return "confirmation"
    try:
        start = datetime.fromisoformat(event_time.replace("Z", "+00:00"))
        current = datetime.fromisoformat((now or now_iso()).replace("Z", "+00:00"))
        minutes = (current - start).total_seconds() / 60
    except (ValueError, TypeError):
        return "confirmation"
    for name, begin, end in _PHASE_WINDOWS:
        if begin is None or minutes >= begin:
            if end is None or minutes < end:
                return name
    return "distribution"


@dataclass
class EventTradePlan:
    event_id: str
    title: str
    phase: str
    direction: str            # buy / sell / wait
    size_plan: str            # 分批计划（如 "1/3, 1/3, 1/3"）
    invalid_conditions: list[str] = field(default_factory=list)  # 失效位
    exit_plan: str = ""       # 分段退出

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def checklist(phase: str) -> list[str]:
    """各阶段必须满足的确认条件。"""
    return {
        "event_pre": ["事件已定档但未发生，不开仓", "仅观察与预演计划"],
        "confirmation": ["官方/可靠源确认事件真实性", "预期差方向明确", "价格尚未完全定价"],
        "first_wave": ["第一波方向与预期一致", "成交量确认（量比≥1.5）", "分批建仓，不一次性满仓"],
        "diffusion": ["扩散追涨只做小仓（≤1/3）", "禁止追高超过 +3% 后入场", "关注派发信号"],
        "distribution": ["派发迹象（量增价滞/冲高回落）→ 分段退出", "不可恋战"],
    }.get(phase, ["等待确认"])


def plan(event: dict[str, Any], price_change_pct: float | None = None) -> EventTradePlan:
    """生成事件交易计划草案（CEO 复核后才可执行）。"""
    phase = phase_of(event.get("time", ""))
    bias = event.get("bias")
    direction = "wait"
    if bias in ("bull", "bear") and phase in ("confirmation", "first_wave"):
        direction = bias
    size_plan = "1/3 分批"
    if phase == "diffusion":
        size_plan = "≤1/3 小仓"
    invalid: list[str] = ["事件被证伪", "方向与预期相反且突破失效位"]
    if price_change_pct is not None and abs(price_change_pct) > 3 and phase == "diffusion":
        invalid.append("已追高超过 3%，暂停入场")
    return EventTradePlan(
        event_id=event.get("id", ""),
        title=event.get("title", ""),
        phase=phase,
        direction=direction,
        size_plan=size_plan,
        invalid_conditions=invalid,
        exit_plan="分段退出：+2ATR 减 1/3，冲高回落破 EMA20 清仓" if direction != "wait" else "无",
    )

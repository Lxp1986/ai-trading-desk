from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .models import Decision, MarketSnapshot, RiskLimits, TradeIntent
from .risk import review


class DecisionEngine:
    """CEO decision boundary for research/simulation; never talks to an exchange."""

    def __init__(self, limits: RiskLimits, audit_path: Path | None = None) -> None:
        self.limits = limits
        self.audit_path = audit_path

    def evaluate(self, snapshot: MarketSnapshot, intent: TradeIntent) -> Decision:
        approved, reasons = review(snapshot, intent, self.limits)
        decision = Decision(
            intent=intent,
            approved=approved,
            reasons=reasons,
            simulated_value=intent.quantity * snapshot.price,
        )
        self._audit(snapshot, decision)
        return decision

    def _audit(self, snapshot: MarketSnapshot, decision: Decision) -> None:
        if self.audit_path is None:
            return
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)
        record = {"snapshot": asdict(snapshot), "decision": asdict(decision)}
        with self.audit_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")

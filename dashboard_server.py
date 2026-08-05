from __future__ import annotations

import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
ROOT = Path(__file__).resolve().parent
AUDIT = ROOT / "artifacts" / "audit.jsonl"
TOKEN_USAGE = ROOT / "artifacts" / "token_usage.json"
STATE = ROOT / "artifacts" / "state.json"
SIGNALS = ROOT / "artifacts" / "signals.jsonl"
WEIGHTS = ROOT / "artifacts" / "strategy_weights.json"
EVENTS = ROOT / "artifacts" / "events.jsonl"
STARTING_CAPITAL_USDT = 80000.0  # OKX 模拟盘重置后总权益

import sys
sys.path.insert(0, str(ROOT / "src"))
from autotrader.team import counts, research_team, snapshot

# 策略清单（真实运行状态由权重文件 + 信号记录决定）
STRATEGY_META = [
    ("trend_breakout", "趋势突破", "顺势 + 量能确认"),
    ("pullback_rebound", "回撤反弹", "趋势中回踩均线 + RSI 修复"),
    ("range_reversion", "震荡高抛低吸", "震荡市 RSI 边界反转"),
    ("defensive", "防守", "波动异常 → 观望降频"),
    ("event_driven", "事件驱动", "A级事件 + 明确预期差"),
]


def _strategies_status() -> list[dict]:
    """策略真实状态：权重（启用/降权/停用）+ 最近触发时间。"""
    weights: dict = {}
    if WEIGHTS.exists():
        try:
            weights = json.loads(WEIGHTS.read_text(encoding="utf-8")).get("weights", {})
        except (OSError, ValueError):
            weights = {}
    last_trigger: dict[str, str] = {}
    if SIGNALS.exists():
        try:
            lines = SIGNALS.read_text(encoding="utf-8").strip().splitlines()[-50:]
            for line in lines:
                if not line:
                    continue
                record = json.loads(line)
                for signal in record.get("signals", []):
                    last_trigger.setdefault(signal.get("strategy"), record.get("time", ""))
        except (OSError, ValueError):
            pass
    result = []
    for key, label, desc in STRATEGY_META:
        weight = weights.get(key, 1.0)
        if weight <= 0:
            status, badge = "已停用", "gray"
        elif weight < 1.0:
            status, badge = f"降权({weight})", "amber"
        else:
            status, badge = "启用", ""
        result.append({
            "key": key, "label": label, "description": desc,
            "status": status, "badge": badge, "weight": weight,
            "last_trigger": last_trigger.get(key, ""),
        })
    return result


class DashboardHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_GET(self):
        if urlparse(self.path).path == "/api/status":
            self._json(self._status())
            return
        super().do_GET()


    def _live_prices(self):
        """实时价格看板数据（guardian 每分钟更新）。"""
        try:
            from autotrader.live_prices import load_live_prices
            return load_live_prices()
        except Exception:
            return {"prices": {}, "source": "error", "updated_at": None}

    def _status(self):
        decisions = []
        if AUDIT.exists():
            for line in AUDIT.read_text(encoding="utf-8").splitlines()[-20:]:
                try:
                    decisions.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        token_usage = {
            "project": "AI自主交易事业部",
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "api_calls": 0,
            "updated_at": None,
            "scope": "project_only",
            "provider": "Hermes routed model",
        }
        if TOKEN_USAGE.exists():
            try:
                token_usage.update(json.loads(TOKEN_USAGE.read_text(encoding="utf-8")))
            except (OSError, json.JSONDecodeError):
                token_usage["status"] = "usage file unreadable"

        # 运行循环最新状态（runner.py 写入；缺失时退回写死初始值）
        state: dict = {}
        if STATE.exists():
            try:
                state = json.loads(STATE.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                state = {}
        portfolio = state.get("portfolio", {}) or {}
        market = state.get("snapshot", {}) or {}
        indicators = state.get("indicators", {}) or {}
        risk = state.get("risk", {}) or {}
        agents = state.get("agents", {}) or {}

        # 策略真实状态（权重 + 最近触发）
        strategies = _strategies_status()

        # 事件记录（事件中心页）
        events = []
        if EVENTS.exists():
            try:
                for line in EVENTS.read_text(encoding="utf-8").splitlines()[-30:]:
                    if line.strip():
                        events.append(json.loads(line))
            except (OSError, json.JSONDecodeError):
                pass

        # 最近交易假设（经营总览 / 持仓页共用）
        recent_decisions = [
            {
                "time": (d.get("decision") or {}).get("decided_at") or d.get("decided_at") or d.get("time", ""),
                "symbol": (d.get("decision") or {}).get("intent", {}).get("symbol", "—"),
                "side": (d.get("decision") or {}).get("intent", {}).get("side", "hold"),
                "value": (d.get("decision") or {}).get("simulated_value", 0),
                "confidence": (d.get("decision") or {}).get("intent", {}).get("confidence", 0),
                "approved": (d.get("decision") or {}).get("approved", False),
                "reasons": list((d.get("decision") or {}).get("reasons", [])),
            }
            for d in decisions[-8:]
        ]

        staff_active = sum(1 for e in snapshot() if e["status"] == "active")

        # 多标的主动机会榜（策略研究员）
        try:
            from autotrader.opportunities import load_opportunities
            opportunities = load_opportunities()
        except Exception:
            opportunities = {"ranked": [], "opportunities": [], "scanned": 0, "updated_at": ""}

        # 持仓实时监控（guardian 每 30s 写入 positions.json）
        positions_monitor = {"count": 0, "positions": {}, "updated_at": ""}
        try:
            pos_path = ROOT / "artifacts" / "positions.json"
            if pos_path.exists():
                positions_monitor = json.loads(
                    pos_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass

        return {
            "mode": "simulation",
            "network": "OKX Demo Trading（模拟盘）",
            "currency": "USDT",
            "starting_capital": STARTING_CAPITAL_USDT,
            "okx_account": state.get("okx_account", {}),
            "base_cash": state.get("base_cash"),
            "nav": portfolio.get("equity", STARTING_CAPITAL_USDT),
            "cash": portfolio.get("cash", STARTING_CAPITAL_USDT),
            "positions": portfolio.get("positions", {}),
            "position_value": portfolio.get("position_value", 0.0),
            "realized_pnl": portfolio.get("realized_pnl", 0.0),
            "unrealized_pnl": portfolio.get("unrealized_pnl", 0.0),
            "max_drawdown_pct": portfolio.get("max_drawdown_pct", 0.0),
            "positions_monitor": positions_monitor,
            "market": {
                "symbol": market.get("symbol", "BTC/USDT"),
                "price": market.get("price"),
                "trend": market.get("trend", "unknown"),
                "volume_ratio": market.get("volume_ratio"),
                "liquidity_ok": market.get("liquidity_ok"),
                "rsi14": indicators.get("rsi14"),
                "atr14": indicators.get("atr14"),
                "change_24h_pct": indicators.get("change_24h_pct"),
            },
            "risk": risk,
            "state_updated_at": state.get("updated_at"),
            "local_only": True,
            "audit_records": len(decisions),
            "latest_decision": decisions[-1] if decisions else None,
            "employees": snapshot(),
            "research_team": research_team(),
            "employee_counts": counts(),
            "agents_work": agents,
            "strategies": strategies,
            "events": events,
            "recent_decisions": recent_decisions,
            "staff_active": staff_active,
            "liquidity_ok": market.get("liquidity_ok"),
            "token_usage": token_usage,
            "opportunities": opportunities,
            "live_prices": self._live_prices(),
        }

    def _json(self, payload):
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format, *args):
        print(format % args)


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 8765), DashboardHandler)
    print("AI trading dashboard: http://127.0.0.1:8765/dashboard.html", flush=True)
    print("API: http://127.0.0.1:8765/api/status", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

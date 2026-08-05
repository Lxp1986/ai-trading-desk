from __future__ import annotations

import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
ROOT = Path(__file__).resolve().parent
AUDIT = ROOT / "artifacts" / "audit.jsonl"
TOKEN_USAGE = ROOT / "artifacts" / "token_usage.json"
STATE = ROOT / "artifacts" / "state.json"
STARTING_CAPITAL_USDT = 277.0

import sys
sys.path.insert(0, str(ROOT / "src"))
from autotrader.team import counts, research_team, snapshot


class DashboardHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_GET(self):
        if urlparse(self.path).path == "/api/status":
            self._json(self._status())
            return
        super().do_GET()

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

        return {
            "mode": "simulation",
            "network": "Binance Spot Testnet",
            "currency": "USDT",
            "starting_capital": STARTING_CAPITAL_USDT,
            "nav": portfolio.get("equity", STARTING_CAPITAL_USDT),
            "cash": portfolio.get("cash", STARTING_CAPITAL_USDT),
            "positions": portfolio.get("positions", {}),
            "position_value": portfolio.get("position_value", 0.0),
            "realized_pnl": portfolio.get("realized_pnl", 0.0),
            "unrealized_pnl": portfolio.get("unrealized_pnl", 0.0),
            "max_drawdown_pct": portfolio.get("max_drawdown_pct", 0.0),
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
            "token_usage": token_usage,
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

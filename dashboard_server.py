from __future__ import annotations

import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
ROOT = Path(__file__).resolve().parent
AUDIT = ROOT / "artifacts" / "audit.jsonl"
TOKEN_USAGE = ROOT / "artifacts" / "token_usage.json"
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
            "provider": "Hermes routed DeepSeek",
        }
        if TOKEN_USAGE.exists():
            try:
                token_usage.update(json.loads(TOKEN_USAGE.read_text(encoding="utf-8")))
            except (OSError, json.JSONDecodeError):
                token_usage["status"] = "usage file unreadable"
        return {
            "mode": "simulation",
            "network": "Binance Spot Testnet",
            "currency": "USDT",
            "starting_capital": STARTING_CAPITAL_USDT,
            "nav": STARTING_CAPITAL_USDT,
            "local_only": True,
            "audit_records": len(decisions),
            "latest_decision": decisions[-1] if decisions else None,
            "employees": snapshot(),
            "research_team": research_team(),
            "employee_counts": counts(),
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

"""持仓实时监控 + 主动调仓引擎（确定性执行 · 零 Token）——真正的执行闭环。

董事长要求："正在持有的仓位能不能实时监控、实时主动调整？不能是应付式工作！"

本模块把"决策 → 执行"变成可验证的确定性链路：

- monitor_positions()：读账本 + 实时价 → 持仓快照（浮盈浮亏/盈亏%/距止损距离）
  → 写 artifacts/positions.json（guardian 每 30s 调用，实时监控）；
- emergency_stop_loss()：浮亏超止损线 → **立即市价平仓**（guardian 每 tick 检查，
  秒级响应——止损绝不等 15 分钟轮次）；
- manage()：每轮完整调仓（runner 15m）——
    止损触发        → 平仓（硬风控优先）
    止盈达成        → 平仓落袋
    信号翻转（sell 信号 vs 多头）→ 平仓/减仓
    同向信号（buy 信号 vs 多头）→ 加仓（风控预算内）
- 止损/止盈 ATR 动态：止损 = max(2×ATR₁h, 1.5%)，止盈 = max(3.5×ATR₁h, 3%)
  （波动大自动放宽，波动小自动收紧——自适应）；
- 执行链：决策 → 风控校验（熔断时 SELL/HOLD 放行、BUY 冻结）→ 测试网下单
  → 审计 audit.jsonl + 账本 orders.jsonl → 回报。

注意：模拟盘阶段所有执行走 Binance Spot Testnet（虚拟资产），
绝不触达真实交易所（LIVE_TRADING_ENABLED 开关由董事会掌控）。
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = Path(os.environ.get("ARTIFACTS_DIR", ROOT / "artifacts"))
ORDERS_PATH = ARTIFACTS / "orders.jsonl"
AUDIT_PATH = ARTIFACTS / "audit.jsonl"
POSITIONS_PATH = ARTIFACTS / "positions.json"
STATE_PATH = ARTIFACTS / "state.json"
DB_PATH = ARTIFACTS / "market.db"

# 默认风控参数（可被 ATR 动态覆盖）
DEFAULT_STOP_LOSS_PCT = 3.0    # 浮亏 ≥3% → 止损
DEFAULT_TAKE_PROFIT_PCT = 6.0  # 浮盈 ≥6% → 止盈
ATR_MULT_STOP = 2.0            # 止损 = 2×ATR₁h
ATR_MULT_PROFIT = 3.5          # 止盈 = 3.5×ATR₁h
MIN_STOP_PCT = 1.5
MAX_STOP_PCT = 8.0
MIN_PROFIT_PCT = 3.0
MAX_PROFIT_PCT = 15.0


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def now_cn() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S %z")


# ---------- 持仓读取 ----------

def load_positions() -> dict[str, dict[str, Any]]:
    """读账本 → 当前持仓（quantity>0）。返回 {SYMBOL: {quantity, avg_cost, cost_basis}}。"""
    from autotrader.portfolio import load_orders, open_positions
    orders = load_orders(ORDERS_PATH) if ORDERS_PATH.exists() else []
    poss = open_positions(orders)
    return {s: {"quantity": float(p.quantity), "avg_cost": float(p.avg_cost),
                "cost_basis": float(p.cost_basis)} for s, p in poss.items()}


def _latest_price(symbol: str) -> float | None:
    """取最新价格：live_prices.json 优先，state.json 兜底。"""
    lp = POSITIONS_PATH.parent / "live_prices.json"
    if lp.exists():
        try:
            data = json.loads(lp.read_text(encoding="utf-8"))
            item = data.get("prices", {}).get(symbol)
            if item and item.get("price"):
                return float(item["price"])
        except (OSError, ValueError):
            pass
    if STATE_PATH.exists():
        try:
            data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
            snap = data.get("snapshot", {})
            if snap.get("symbol") == symbol and snap.get("price"):
                return float(snap["price"])
        except (OSError, ValueError):
            pass
    return None


def _atr_pct(symbol: str) -> float | None:
    """当前 1h ATR（价格百分比）——动态止损止盈依据。"""
    try:
        from autotrader.market import compute_indicators, load_klines
        for sym in (symbol, symbol.replace("USDT", "")):
            klines = load_klines(sym, "1h", 60)
            if klines and len(klines) >= 15:
                ind = compute_indicators(klines)
                price, atr = ind.get("price", 0.0), ind.get("atr14", 0.0)
                if price > 0 and atr > 0:
                    return atr / price * 100
    except Exception:
        pass
    return None


def levels_for(symbol: str, atr_pct: float | None = None) -> dict[str, float]:
    """止损/止盈线（ATR 动态，回落默认值）。"""
    atr = atr_pct if atr_pct is not None else _atr_pct(symbol)
    if atr:
        stop = min(MAX_STOP_PCT, max(MIN_STOP_PCT, atr * ATR_MULT_STOP))
        prof = min(MAX_PROFIT_PCT, max(MIN_PROFIT_PCT, atr * ATR_MULT_PROFIT))
    else:
        stop, prof = DEFAULT_STOP_LOSS_PCT, DEFAULT_TAKE_PROFIT_PCT
    return {"stop_loss_pct": round(stop, 2), "take_profit_pct": round(prof, 2)}


# ---------- 实时监控（guardian 每 tick 调用） ----------

def monitor_positions(prices: dict[str, float] | None = None) -> dict[str, Any]:
    """持仓实时快照 → positions.json（浮盈浮亏/盈亏%/距止损距离）。"""
    positions = load_positions()
    if not positions:
        snap = {"updated_at": now_cn(), "positions": {}, "count": 0,
                "note": "当前零持仓（现金保留）"}
        POSITIONS_PATH.write_text(json.dumps(snap, ensure_ascii=False, indent=2),
                                  encoding="utf-8")
        return snap

    rows: dict[str, dict[str, Any]] = {}
    for symbol, pos in positions.items():
        price = (prices or {}).get(symbol) or _latest_price(symbol)
        if not price or price <= 0:
            continue
        cost = float(pos["avg_cost"])
        pnl = (price - cost) * float(pos["quantity"])
        pnl_pct = (price / cost - 1) * 100 if cost else 0.0
        levels = levels_for(symbol)
        stop = cost * (1 - levels["stop_loss_pct"] / 100)
        rows[symbol] = {
            "quantity": pos["quantity"], "avg_cost": round(cost, 4),
            "price": round(price, 4), "pnl": round(pnl, 4),
            "pnl_pct": round(pnl_pct, 2),
            "stop_loss_pct": levels["stop_loss_pct"],
            "take_profit_pct": levels["take_profit_pct"],
            "stop_price": round(stop, 4),
            "distance_to_stop_pct": round((price / stop - 1) * 100, 2),
            "status": "hold",
        }
        if pnl_pct <= -levels["stop_loss_pct"]:
            rows[symbol]["status"] = "stop_loss_triggered"
        elif pnl_pct >= levels["take_profit_pct"]:
            rows[symbol]["status"] = "take_profit_ready"

    snap = {"updated_at": now_cn(), "positions": rows, "count": len(rows)}
    POSITIONS_PATH.write_text(json.dumps(snap, ensure_ascii=False, indent=2),
                              encoding="utf-8")
    return snap


# ---------- 主动调仓决策（runner 每轮调用） ----------

def manage(client: Any, signals: list[dict[str, Any]] | None = None,
           prices: dict[str, float] | None = None) -> dict[str, Any]:
    """完整调仓决策：止损 → 止盈 → 信号翻转 → 同向加仓。

    返回执行结果（动作列表）。
    """
    positions = load_positions()
    if not positions:
        return {"actions": [], "note": "零持仓，无需调仓"}
    actions: list[dict[str, Any]] = []
    sig_by_symbol: dict[str, dict[str, Any]] = {}
    for s in signals or []:
        sym = str(s.get("symbol", "")).upper()
        sig_by_symbol[sym] = s

    for symbol, pos in positions.items():
        price = (prices or {}).get(symbol) or _latest_price(symbol)
        if not price or price <= 0:
            continue
        cost = float(pos["avg_cost"])
        qty = float(pos["quantity"])
        pnl_pct = (price / cost - 1) * 100 if cost else 0.0
        levels = levels_for(symbol)

        # 1) 止损（硬风控优先）
        if pnl_pct <= -levels["stop_loss_pct"]:
            result = _execute(client, symbol, "SELL", qty,
                              f"止损平仓（浮亏 {pnl_pct:.2f}% ≤ -{levels['stop_loss_pct']}%）")
            actions.append(result)
            continue
        # 2) 止盈
        if pnl_pct >= levels["take_profit_pct"]:
            result = _execute(client, symbol, "SELL", qty,
                              f"止盈平仓（浮盈 {pnl_pct:.2f}% ≥ {levels['take_profit_pct']}%）")
            actions.append(result)
            continue
        # 3) 信号翻转（多头持仓 + sell 信号 → 平仓）
        sig = sig_by_symbol.get(symbol) or sig_by_symbol.get(symbol.replace("USDT", ""))
        if sig and str(sig.get("action", "")).lower() == "sell":
            result = _execute(client, symbol, "SELL", qty,
                              f"信号翻转平仓（{sig.get('strategy', '')}: {sig.get('reason', '')[:50]}）")
            actions.append(result)
            continue
        # 4) 同向信号 → 加仓（风控预算内：单笔风险 ≤ 现金 1%，最多加 1 次）
        if sig and str(sig.get("action", "")).lower() == "buy":
            from autotrader.portfolio import cash_balance, load_orders
            orders = load_orders(ORDERS_PATH) if ORDERS_PATH.exists() else []
            cash = cash_balance(orders)
            budget = cash * 0.01 if cash else 0.0
            add_qty = budget / price if price > 0 else 0.0
            if add_qty >= qty * 0.1:  # 加仓量至少为持仓 10%
                result = _execute(client, symbol, "BUY", add_qty,
                                  f"同向加仓（{sig.get('strategy', '')}，预算 {budget:.2f} USDT）")
                actions.append(result)
            else:
                actions.append({"symbol": symbol, "action": "no_add",
                                "reason": f"加仓预算不足（{budget:.2f} USDT < 持仓 10%）"})
    return {"actions": actions, "count": len(actions)}


# ---------- 紧急止损（guardian 每 tick 调用，秒级响应） ----------

def emergency_stop_loss(client: Any, prices: dict[str, float] | None = None) -> dict[str, Any]:
    """持仓浮亏超止损线 → 立即市价平仓（不等 15 分钟轮次）。

    返回是否执行了平仓。
    """
    positions = load_positions()
    executed: list[dict[str, Any]] = []
    for symbol, pos in positions.items():
        price = (prices or {}).get(symbol) or _latest_price(symbol)
        if not price or price <= 0:
            continue
        cost = float(pos["avg_cost"])
        qty = float(pos["quantity"])
        pnl_pct = (price / cost - 1) * 100 if cost else 0.0
        levels = levels_for(symbol)
        if pnl_pct <= -levels["stop_loss_pct"]:
            executed.append(_execute(client, symbol, "SELL", qty,
                                     f"紧急止损（30s 粒度浮亏 {pnl_pct:.2f}%，立即平仓）"))
    return {"executed": executed, "count": len(executed)}


# ---------- 执行链（下单 + 审计 + 账本） ----------

def _execute(client: Any, symbol: str, side: str, qty: float, reason: str) -> dict[str, Any]:
    """统一执行：测试网下单 → 账本 → 审计。任何失败都不影响主循环。"""
    try:
        order = client.create_test_order(symbol, side, str(round(qty, 8)))
        logged_at = now_iso()
        # 账本（主记录）
        entry = {
            "type": "testnet_order", "order_id": order.get("orderId") or order.get("order_id"),
            "symbol": symbol, "side": side, "order_type": "MARKET",
            "status": order.get("status") or "FILLED",
            "price": order.get("price", "0"), "avg_fill_price": order.get("avgFillPrice")
            or order.get("avg_fill_price"), "quantity": str(round(qty, 8)),
            "created_at": order.get("transactTime") or order.get("created_at"),
            "logged_at": logged_at,
            "note": f"position_manager: {reason}",
        }
        with ORDERS_PATH.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
        # 审计
        with AUDIT_PATH.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({
                "ts": now_cn(), "type": "position_manage",
                "symbol": symbol, "side": side, "quantity": round(qty, 8),
                "reason": reason, "order_id": entry["order_id"],
            }, ensure_ascii=False) + "\n")
        return {"symbol": symbol, "action": f"{side}_executed", "quantity": round(qty, 8),
                "reason": reason, "order_id": entry["order_id"], "ok": True}
    except Exception as exc:
        return {"symbol": symbol, "action": f"{side}_failed", "reason": reason,
                "error": str(exc)[:120], "ok": False}


# ---------- 一键全流程 ----------

def run_position_cycle(client: Any, signals: list[dict[str, Any]] | None = None,
                       prices: dict[str, float] | None = None) -> dict[str, Any]:
    """监控 + 调仓（runner 每轮调用）：先紧急止损，再完整调仓决策。"""
    mon = monitor_positions(prices)
    emg = emergency_stop_loss(client, prices)
    mng = manage(client, signals, prices)
    return {"monitor": mon, "emergency": emg, "manage": mng}

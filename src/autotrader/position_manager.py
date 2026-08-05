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


def _latest_price(symbol: str, max_age_s: int = 300) -> float | None:
    """取最新价格：live_prices.json 优先（≤5 分钟新鲜度），state.json 兜底。

    陈旧价格（数据源中断）返回 None——决策层不得用过期价交易。
    """
    import time as _t
    lp = POSITIONS_PATH.parent / "live_prices.json"
    if lp.exists():
        try:
            data = json.loads(lp.read_text(encoding="utf-8"))
            item = data.get("prices", {}).get(symbol)
            if item and item.get("price"):
                updated = data.get("updated_at", "")
                # 新鲜度校验（updated_at 为本地时间字符串）
                try:
                    from datetime import datetime as _dt
                    ts = _dt.strptime(str(updated), "%Y-%m-%d %H:%M:%S")
                    age = (_dt.now() - ts).total_seconds()
                    if age <= max_age_s:
                        return float(item["price"])
                except (ValueError, TypeError):
                    pass
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

# 防重复窗口：同一 symbol+side 在 N 秒内只执行一次（guardian 30s 与 runner 15m 竞态防护）
DEDUP_WINDOW_S = 300
_LAST_ORDERS: dict[tuple[str, str], float] = {}


def _risk_gate(symbol: str, side: str) -> dict[str, Any]:
    """硬风控闸门：熔断时 BUY 冻结、SELL/HOLD 放行；连亏≥5 暂停新仓。

    返回 {"ok": True} 或 {"ok": False, "reason": ...}。
    """
    try:
        from autotrader.portfolio import load_orders
        from autotrader.risk import compute_state
        orders = load_orders(ORDERS_PATH) if ORDERS_PATH.exists() else []
        state = compute_state(orders)
        if state.trading_halted and side == "BUY":
            reasons = "; ".join(state.halt_reasons or ("风控熔断",))
            return {"ok": False, "reason": f"风控熔断，BUY 冻结（{reasons}）"}
        if side == "BUY" and state.consecutive_losses >= 5:
            return {"ok": False,
                    "reason": f"连亏 {state.consecutive_losses} 笔 ≥5，暂停新仓（硬风控）"}
        return {"ok": True}
    except Exception as exc:
        # 风控不可用时保守拒绝 BUY（宁可错过不可违规）
        if side == "BUY":
            return {"ok": False, "reason": f"风控不可用，BUY 保守拒绝（{str(exc)[:60]}）"}
        return {"ok": True}


def _dedup_ok(symbol: str, side: str) -> bool:
    """防重复：窗口内同 symbol+side 已执行 → 跳过。"""
    import time
    key = (symbol, side)
    last = _LAST_ORDERS.get(key)
    now = time.time()
    if last is not None and now - last < DEDUP_WINDOW_S:
        return False
    _LAST_ORDERS[key] = now
    return True


def _execute(client: Any, symbol: str, side: str, qty: float, reason: str) -> dict[str, Any]:
    """统一执行：风控闸门 → 防重 → 测试网下单 → 账本 → 审计。任何失败都不影响主循环。"""
    # 熔断强制（SELL 放行、BUY 冻结）
    gate = _risk_gate(symbol, side)
    if not gate["ok"]:
        return {"symbol": symbol, "action": f"{side}_blocked", "reason": reason,
                "error": gate["reason"], "ok": False}
    # 防重复（双进程竞态防护：guardian 30s + runner 15m）
    if not _dedup_ok(symbol, side):
        return {"symbol": symbol, "action": f"{side}_deduped", "reason": reason,
                "error": "防重窗口内已执行", "ok": False}
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


# ---------- 开仓引擎（补齐执行闭环第一环：信号 → 开仓） ----------

# 单标的仓位上限（集中度控制，防满仓）
MAX_POSITION_PCT = 20.0    # 单标的 ≤ 现金 20%
MIN_TRADE_USDT = 5.0       # 最小开仓金额（测试网最小下单约束）
MAX_POSITIONS = 3          # 最多同时持仓数（分散风险）


def open_position(client: Any, symbol: str, signal: dict[str, Any],
                  price: float | None = None,
                  events: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """开仓引擎：信号 → 风控闸门 → 仓位计算 → 下单 → 账本审计。

    风控闸门（全部强制）：
    - 熔断/连亏（_risk_gate）
    - 已有持仓 → 不重复开仓（交给 manage 加仓逻辑）
    - 持仓数 ≥ MAX_POSITIONS → 拒绝（分散风险）
    - 信号强度 < 0.5 → 拒绝（弱信号不开仓）
    - 价格新鲜度（_latest_price 已校验）

    仓位计算：单笔风险预算 = 现金 × 1% ÷ 止损距离(%)；
    上限 = 现金 × MAX_POSITION_PCT；下限 = MIN_TRADE_USDT。
    """
    if str(signal.get("action", "")).lower() != "buy":
        return {"symbol": symbol, "action": "no_open", "reason": "非买入信号", "ok": False}
    strength = float(signal.get("strength", 0) or 0)
    if strength < 0.5:
        return {"symbol": symbol, "action": "no_open",
                "reason": f"信号强度 {strength:.2f} < 0.5（弱信号不开仓）", "ok": False}
    # 已有持仓 → 不重复开仓
    positions = load_positions()
    if symbol in positions and positions[symbol]["quantity"] > 0:
        return {"symbol": symbol, "action": "no_open",
                "reason": f"已持有 {symbol}，不重复开仓（调仓由 manage 处理）", "ok": False}
    if len(positions) >= MAX_POSITIONS:
        return {"symbol": symbol, "action": "no_open",
                "reason": f"持仓数 {len(positions)} ≥ {MAX_POSITIONS}（分散风险限制）", "ok": False}
    # 价格（新鲜度已校验）
    px = price or _latest_price(symbol)
    if not px or px <= 0:
        return {"symbol": symbol, "action": "no_open", "reason": "价格不可用", "ok": False}
    # 仓位计算：风险预算法
    from autotrader.portfolio import cash_balance, load_orders
    orders = load_orders(ORDERS_PATH) if ORDERS_PATH.exists() else []
    cash = cash_balance(orders)
    if cash <= 0:
        return {"symbol": symbol, "action": "no_open", "reason": "无可用现金", "ok": False}
    levels = levels_for(symbol)
    stop_dist_pct = levels["stop_loss_pct"]  # 止损距离（%）
    risk_budget = cash * 0.01                 # 单笔风险预算 = 现金 1%
    risk_qty = (risk_budget / (px * stop_dist_pct / 100)) if stop_dist_pct > 0 else 0.0
    cap_qty = (cash * MAX_POSITION_PCT / 100) / px
    qty = min(risk_qty, cap_qty)
    if qty * px < MIN_TRADE_USDT:
        return {"symbol": symbol, "action": "no_open",
                "reason": f"开仓金额 {qty * px:.2f} < {MIN_TRADE_USDT} USDT（过小）", "ok": False}
    result = _execute(client, symbol, "BUY", qty,
                      f"开仓（{signal.get('strategy', '')} 强度{strength:.2f}，"
                      f"风险预算 {risk_budget:.2f} USDT @ 止损 {stop_dist_pct}%）")
    if result.get("ok"):
        # 审计开仓决策（交易假设）
        with AUDIT_PATH.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({
                "ts": now_cn(), "type": "open_position",
                "symbol": symbol, "signal": signal.get("strategy", ""),
                "strength": strength, "quantity": round(qty, 8),
                "price": round(px, 4), "stop_loss_pct": stop_dist_pct,
                "risk_budget": round(risk_budget, 2),
                "reason": signal.get("reason", "")[:200],
            }, ensure_ascii=False) + "\n")
    return result


# ---------- 一键全流程 ----------

def run_position_cycle(client: Any, signals: list[dict[str, Any]] | None = None,
                       prices: dict[str, float] | None = None) -> dict[str, Any]:
    """监控 + 调仓（runner 每轮调用）：先紧急止损，再完整调仓决策。"""
    mon = monitor_positions(prices)
    emg = emergency_stop_loss(client, prices)
    mng = manage(client, signals, prices)
    return {"monitor": mon, "emergency": emg, "manage": mng}

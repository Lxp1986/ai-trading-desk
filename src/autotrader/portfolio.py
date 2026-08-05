"""本地账本与持仓模块（审计员/经营报告员/组合经理落地）。

从 ``artifacts/orders.jsonl``（Binance 测试网虚拟订单的本地主记录）计算：

- 当前持仓（按 symbol 聚合，含平均成本）；
- 现金余额（起始资金 − 买入 + 卖出）；
- 已实现盈亏（卖出结算）；
- 浮动盈亏与净值（按给定当前价逐日盯市）；
- 最大回撤（基于账本权益序列）。

口径说明：本地账本以 ``STARTING_CASH_USDT``（277.0，Dashboard 既有口径）
为起始资金，测试网虚拟资产仅作执行环境；测试网每月重置不影响本地账本。
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ORDERS_PATH = Path(__file__).resolve().parents[2] / "artifacts" / "orders.jsonl"
STARTING_CASH_USDT = 277.0


def load_orders(path: Path = ORDERS_PATH) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records


def _qty(order: dict[str, Any]) -> float:
    return float(order.get("quantity") or order.get("executedQty") or 0.0)


def _quote_qty(order: dict[str, Any]) -> float:
    return float(order.get("quote_qty") or order.get("cummulativeQuoteQty") or 0.0)


def _fee(order: dict[str, Any]) -> float:
    return float(order.get("fee") or 0.0)


@dataclass
class Position:
    symbol: str
    quantity: float
    avg_cost: float
    cost_basis: float
    realized_pnl: float = 0.0


def positions(orders: list[dict[str, Any]]) -> dict[str, Position]:
    """Aggregate orders into per-symbol positions (keeps closed symbols with qty=0)."""
    result: dict[str, Position] = {}
    for order in orders:
        if order.get("status") not in (None, "FILLED", "filled"):
            continue  # 只统计已成交订单
        symbol = order.get("symbol", "")
        if not symbol:
            continue
        pos = result.setdefault(symbol, Position(symbol, 0.0, 0.0, 0.0))
        qty, quote = _qty(order), _quote_qty(order)
        side = str(order.get("side", "")).upper()
        if side == "BUY":
            new_qty = pos.quantity + qty
            pos.cost_basis = pos.cost_basis + quote + _fee(order)
            pos.avg_cost = pos.cost_basis / new_qty if new_qty else 0.0
            pos.quantity = new_qty
        elif side == "SELL":
            # 已实现盈亏 = 卖出所得 − 卖出数量 × 平均成本 − 费用
            if pos.quantity > 0:
                portion = min(qty, pos.quantity)
                pos.realized_pnl += (quote - _fee(order)) - portion * pos.avg_cost
                pos.quantity = max(0.0, pos.quantity - portion)
    return result


def open_positions(orders: list[dict[str, Any]]) -> dict[str, Position]:
    """Only positions with remaining quantity."""
    return {k: v for k, v in positions(orders).items() if v.quantity > 0}


def _match_price(prices: dict[str, float], symbol: str) -> float | None:
    """Match a price by symbol, tolerant of BTCUSDT vs BTC/USDT formats."""
    if symbol in prices:
        return prices[symbol]
    normalized = symbol.replace("/", "")
    for key, value in prices.items():
        if key.replace("/", "") == normalized:
            return value
    return None


def cash_balance(orders: list[dict[str, Any]], start_cash: float = STARTING_CASH_USDT) -> float:
    cash = start_cash
    for order in orders:
        if order.get("status") not in (None, "FILLED", "filled"):
            continue
        side = str(order.get("side", "")).upper()
        if side == "BUY":
            cash -= _quote_qty(order) + _fee(order)
        elif side == "SELL":
            cash += _quote_qty(order) - _fee(order)
    return round(cash, 8)


def realized_pnl(orders: list[dict[str, Any]]) -> float:
    """Sum of realized PnL across all symbols (including closed ones)."""
    return round(sum(p.realized_pnl for p in positions(orders).values()), 8)


def equity(orders: list[dict[str, Any]], prices: dict[str, float], start_cash: float = STARTING_CASH_USDT) -> float:
    """净值 = 现金 + Σ(持仓 × 当前价)。"""
    cash = cash_balance(orders, start_cash)
    pos_value = 0.0
    for p in positions(orders).values():
        price = _match_price(prices, p.symbol) or p.avg_cost
        pos_value += p.quantity * price
    return round(cash + pos_value, 8)


def unrealized_pnl(orders: list[dict[str, Any]], prices: dict[str, float]) -> float:
    pos_value = 0.0
    cost = 0.0
    for p in positions(orders).values():
        price = _match_price(prices, p.symbol) or p.avg_cost
        pos_value += p.quantity * price
        cost += p.cost_basis
    return round(pos_value - cost, 8)


def max_drawdown(orders: list[dict[str, Any]], prices: dict[str, float], start_cash: float = STARTING_CASH_USDT) -> float:
    """基于逐笔订单后的权益序列计算最大回撤（百分比）。"""
    eq_series = [start_cash]  # 初始权益点
    for i in range(1, len(orders) + 1):
        eq_series.append(equity(orders[:i], prices, start_cash))
    peak, max_dd = eq_series[0], 0.0
    for eq in eq_series:
        peak = max(peak, eq)
        if peak > 0:
            max_dd = max(max_dd, (peak - eq) / peak)
    return round(max_dd * 100, 2)


def portfolio_snapshot(orders: list[dict[str, Any]], prices: dict[str, float], start_cash: float = STARTING_CASH_USDT) -> dict[str, Any]:
    """完整账本快照（供 Dashboard / 经营报告使用）。"""
    pos = open_positions(orders)
    return {
        "starting_cash": start_cash,
        "cash": cash_balance(orders, start_cash),
        "positions": {k: {"quantity": v.quantity, "avg_cost": v.avg_cost, "cost_basis": v.cost_basis} for k, v in pos.items()},
        "position_value": round(sum(v.quantity * (_match_price(prices, k) or v.avg_cost) for k, v in pos.items()), 8),
        "realized_pnl": realized_pnl(orders),
        "unrealized_pnl": unrealized_pnl(orders, prices),
        "equity": equity(orders, prices, start_cash),
        "max_drawdown_pct": max_drawdown(orders, prices, start_cash),
    }

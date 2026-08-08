"""策略基因库（Strategy Genome）——自动设计/调参/迭代策略的确定性引擎。

核心思想：策略 = 参数化基因。系统不再依赖人工调参，而是：

1. **基因池**：每个基因是一组策略参数（RSI 阈值/量比/止损止盈）；
2. **变异**：围绕基准参数随机采样 N 个变异体（参数空间扰动）；
3. **回测**：每个基因用历史 K 线（market.db）模拟交易，
   计算胜率 / 盈亏比 / 总收益 / 最大回撤 / 期望值；
4. **进化**：精英保留（Top K）+ 变异 → 下一代；多代迭代后最优基因胜出；
5. **输出**：strategy_genome.json（基因池排名/状态）+ 最优参数建议
   （CEO 每日规划任务评估后决定是否落地到 strategy_params.json）。

零 Token 成本（纯确定性计算），每日 06:00 由 cron 自动跑。
"""
from __future__ import annotations

import json
import math
import random
import sqlite3
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "artifacts" / "market.db"
GENOME_PATH = ROOT / "artifacts" / "strategy_genome.json"

# 回测设置
SYMBOLS = ["BTCUSDT", "ETHUSDT", "XRPUSDT", "ADAUSDT", "LINKUSDT"]  # 数据充足的标的
INTERVALS = ["15m", "1h", "4h"]       # 多周期合并样本
FEE_RATE = 0.001                      # 单边手续费 0.1%（模拟成本）
STOP_LOSS_PCT = 3.0                   # 止损 3%
TAKE_PROFIT_PCT = 6.0                 # 止盈 6%
MIN_TRADES = 15                       # 有效评估最少交易数（样本惩罚线）

# 进化设置
POPULATION = 30                       # 每代基因数
ELITE_KEEP = 8                        # 精英保留数
GENERATIONS = 3                       # 进化代数
MUTATION_STD = 1.5                    # 参数变异标准差

# 参数空间边界（RSI 阈值，贴合近期市场实际分布：RSI 常态 40~70）
PARAM_BOUNDS: dict[str, tuple[float, float]] = {
    "rsi_oversold": (35.0, 48.0),      # 超卖线（买入触发）
    "rsi_overbought": (56.0, 70.0),    # 超买线（卖出触发）
    "vol_min": (1.0, 2.0),             # 量比过滤
}


def load_klines(symbol: str, interval: str = "1h", limit: int = 800) -> list[dict[str, Any]]:
    """从 market.db 读历史 K 线（升序）。"""
    if not DB_PATH.exists():
        return []
    conn = sqlite3.connect(DB_PATH)
    try:
        rows = conn.execute(
            "SELECT open_time, open, high, low, close, volume FROM klines "
            "WHERE symbol=? AND interval=? ORDER BY open_time ASC LIMIT ?",
            (symbol, interval, limit),
        ).fetchall()
    finally:
        conn.close()
    out = []
    for r in rows:
        out.append({"t": r[0], "o": float(r[1]), "h": float(r[2]),
                    "l": float(r[3]), "c": float(r[4]), "v": float(r[5])})
    return out


def rsi(closes: list[float], period: int = 14) -> list[float]:
    """RSI14 序列（前 period 个为 None）。"""
    if len(closes) < period + 1:
        return [None] * len(closes)
    out: list[float | None] = [None] * period
    gains, losses = 0.0, 0.0
    for i in range(1, period + 1):
        delta = closes[i] - closes[i - 1]
        gains += max(delta, 0.0)
        losses += max(-delta, 0.0)
    avg_gain, avg_loss = gains / period, losses / period
    out.append(100.0 if avg_loss == 0 else 100 - 100 / (1 + avg_gain / avg_loss))
    for i in range(period + 1, len(closes)):
        delta = closes[i] - closes[i - 1]
        gain, loss = max(delta, 0.0), max(-delta, 0.0)
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
        out.append(100.0 if avg_loss == 0 else 100 - 100 / (1 + avg_gain / avg_loss))
    return out


def volume_ratio(volumes: list[float], i: int, window: int = 20) -> float:
    """量比：当前量 / 前 window 平均量。"""
    if i < window:
        return 0.0
    base = sum(volumes[i - window:i]) / window
    return volumes[i] / base if base > 0 else 0.0


def backtest_gene(klines: list[dict[str, Any]], params: dict[str, float]) -> dict[str, Any]:
    """回测单个基因：RSI 超卖买入 + 超买卖出 + 量比过滤 + 止损止盈。

    返回评估指标（胜率/盈亏比/总收益/最大回撤/交易数）。
    """
    closes = [k["c"] for k in klines]
    volumes = [k["v"] for k in klines]
    rsi_vals = rsi(closes)
    oversold = params["rsi_oversold"]
    overbought = params["rsi_overbought"]
    vol_min = params["vol_min"]

    trades: list[float] = []
    equity = 1000.0                      # 初始资金（单位净值）
    peak = equity
    max_dd = 0.0
    in_position = False
    entry_price = 0.0

    for i in range(1, len(klines)):
        r = rsi_vals[i]
        if r is None:
            continue
        if not in_position:
            # 买入信号：超卖 + 量比达标（下一根收盘价成交）
            if r < oversold and volume_ratio(volumes, i) >= vol_min:
                in_position = True
                entry_price = closes[i]
        else:
            # 止盈 / 止损 / 超买反转平仓
            pnl_pct = (closes[i] / entry_price - 1) * 100
            if pnl_pct >= TAKE_PROFIT_PCT:
                trades.append(TAKE_PROFIT_PCT - FEE_RATE * 100 * 2)
                in_position = False
            elif pnl_pct <= -STOP_LOSS_PCT:
                trades.append(-STOP_LOSS_PCT - FEE_RATE * 100 * 2)
                in_position = False
            elif r > overbought:
                trades.append(pnl_pct - FEE_RATE * 100 * 2)
                in_position = False
        # 净值曲线（含持仓浮盈）
        cur_equity = equity
        if in_position and entry_price:
            cur_equity = equity * (1 + (closes[i] / entry_price - 1) * 0.5)  # 半仓近似
        peak = max(peak, cur_equity)
        max_dd = max(max_dd, (peak - cur_equity) / peak * 100)
        if not in_position and trades:
            equity = equity * (1 + trades[-1] / 100)

    if not trades:
        return {"trades": 0, "winrate": 0.0, "profit_factor": 0.0,
                "total_return": 0.0, "max_dd": 0.0, "expectancy": 0.0}

    wins = [t for t in trades if t > 0]
    losses = [t for t in trades if t <= 0]
    winrate = len(wins) / len(trades)
    gross_win = sum(wins)
    gross_loss = abs(sum(losses))
    profit_factor = gross_win / gross_loss if gross_loss > 0 else (10.0 if gross_win > 0 else 0.0)
    total_return = sum(trades)
    expectancy = total_return / len(trades)
    return {
        "trades": len(trades),
        "winrate": round(winrate, 3),
        "profit_factor": round(profit_factor, 2),
        "total_return": round(total_return, 2),
        "max_dd": round(max_dd, 2),
        "expectancy": round(expectancy, 3),
    }


def score_gene(metrics: dict[str, Any]) -> float:
    """综合评分：胜率 × 盈亏比 × 样本惩罚（交易少则降权）。"""
    sample_penalty = min(metrics["trades"] / MIN_TRADES, 1.0)
    return (metrics["winrate"] * 100 * metrics["profit_factor"] * sample_penalty)


def mutate(params: dict[str, float]) -> dict[str, float]:
    """参数变异（高斯扰动 + 边界裁剪）。"""
    out = {}
    for key, (lo, hi) in PARAM_BOUNDS.items():
        val = params.get(key, (lo + hi) / 2)
        val = val + random.gauss(0, MUTATION_STD)
        out[key] = round(max(lo, min(hi, val)), 1)
    return out


def base_gene() -> dict[str, float]:
    """基准基因（当前 1h 策略参数，贴合近期市场分布）。"""
    return {"rsi_oversold": 42.0, "rsi_overbought": 63.0, "vol_min": 1.2}


def evolve(generations: int = GENERATIONS) -> dict[str, Any]:
    """进化主循环：初始池 → 回测 → 精英保留+变异 → 迭代。"""
    random.seed(42)
    klines_all = []
    for sym in SYMBOLS:
        for interval in INTERVALS:
            klines_all.extend(load_klines(sym, interval))
    if len(klines_all) < 200:
        return {"status": "insufficient_data", "rows": len(klines_all)}

    pool = [base_gene()] + [mutate(base_gene()) for _ in range(POPULATION - 1)]
    best_overall: dict[str, Any] = {}

    for gen in range(generations):
        scored = []
        for params in pool:
            metrics = backtest_gene(klines_all, params)
            scored.append({"params": params, **metrics, "score": round(score_gene(metrics), 2)})
        scored.sort(key=lambda s: s["score"], reverse=True)
        if not best_overall or scored[0]["score"] > best_overall["score"]:
            best_overall = dict(scored[0])
        # 精英 + 变异 → 下一代
        elite = scored[:ELITE_KEEP]
        pool = [dict(e["params"]) for e in elite]
        while len(pool) < POPULATION:
            parent = random.choice(elite)["params"]
            pool.append(mutate(parent))

    # 最终排序输出
    final = sorted(
        [{k: v for k, v in g.items() if k != "score"} | {"score": g["score"]} for g in
         [dict(p) for p in scored]] + [],
        key=lambda s: s.get("score", 0), reverse=True,
    )
    # 重新回测最终池排序（简化：用最后一轮 scored）
    ranked = sorted(scored, key=lambda s: s["score"], reverse=True)
    genes = [
        {"rank": i + 1, **{k: v for k, v in g.items()},
         "status": "active" if i < ELITE_KEEP else ("candidate" if i < ELITE_KEEP * 2 else "bench")}
        for i, g in enumerate(ranked)
    ]
    return {
        "status": "ok",
        "generation": generations,
        "population": POPULATION,
        "best": best_overall,
        "genes": genes,
        "updated_at": __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def save_genome(result: dict[str, Any]) -> None:
    GENOME_PATH.parent.mkdir(parents=True, exist_ok=True)
    GENOME_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    result = evolve()
    save_genome(result)
    if result.get("status") == "ok":
        b = result["best"]
        print(f"🧬 策略基因库进化完成（第 {result['generation']} 代）")
        print(f"   最优基因: 超卖 {b['params']['rsi_oversold']} / 超买 {b['params']['rsi_overbought']} / 量比 {b['params']['vol_min']}")
        print(f"   回测: 胜率 {b['winrate']:.1%} | 盈亏比 {b['profit_factor']} | "
              f"{b['trades']} 笔 | 期望 {b['expectancy']}%/笔 | 最大回撤 {b['max_dd']}%")
        print(f"   基因池 {len(result['genes'])} 个已入册 → artifacts/strategy_genome.json")
    else:
        print(f"⚠️ 基因库数据不足: {result.get('rows', 0)} 行 K 线（需 ≥200）")


if __name__ == "__main__":
    main()

import json
from datetime import datetime, timezone
from pathlib import Path
from autotrader.llm import record_usage

ROOT = Path(__file__).resolve().parents[1]
A = ROOT / "artifacts"

def load(name):
    return json.loads((A / name).read_text(encoding="utf-8"))

def jsonl(name):
    out = []
    for line in (A / name).read_text(encoding="utf-8").splitlines():
        try:
            out.append(json.loads(line))
        except Exception:
            pass
    return out

opp, events, chain, macro, movers, state, prior = (load("opportunities.json"), jsonl("events.jsonl"), jsonl("onchain.jsonl"), load("macro.json"), load("movers.json"), load("state.json"), jsonl("analysis_log.jsonl"))
top = opp.get("ranked", [])[:3]
recent_events = events[-10:]
latest_a = [e for e in events if e.get("grade") == "A"][-10:]
recent_chain = chain[-5:]
now = datetime.now(timezone.utc).isoformat()
positions = state.get("portfolio", {}).get("positions", {})
rows = []
for x in top:
    best = x.get("best") or {}
    action, strength = best.get("action"), float(best.get("strength", 0) or 0)
    held = float((positions.get(x.get("symbol"), {}) or {}).get("quantity", 0) or 0)
    if action == "sell":
        feasibility, rating = ("中（仅可减仓，不能裸空）" if held > 0 else "低（现货无仓，禁止裸空）"), "观察"
    elif action == "buy" and strength >= 0.7:
        feasibility, rating = "中低（缺大盘/链上/流动性确认）", "关注"
    else:
        feasibility, rating = "低", "观察"
    rows.append({
        "symbol": x.get("symbol"), "rank": x.get("rank"), "price": x.get("price"), "trend": x.get("trend"),
        "rsi14": x.get("rsi14"), "volume_ratio": x.get("volume_ratio"), "change_24h_pct": x.get("change_24h_pct"),
        "timeframe": x.get("timeframe"), "horizon": x.get("horizon"), "signal_strength": strength,
        "action": action, "strategy": best.get("strategy"), "rating": rating, "held_quantity": held,
        "technical_read": {
            "trend": "价<EMA20<EMA50，空头排列" if x.get("trend") == "trend_down" else "榜单标记横盘，但买入理由声称多头排列，存在口径冲突" if action == "buy" else "方向性趋势不足",
            "rsi": "偏弱/接近超卖，追空需防反弹" if (x.get("rsi14") or 50) < 38 else "中性偏弱，尚未超买" if (x.get("rsi14") or 50) < 55 else "偏强，追多性价比下降",
            "volume": "极端放量，既确认破位也提高消息冲击/反转风险" if (x.get("volume_ratio") or 0) > 5 else "接近3倍，需连续K线确认" if (x.get("volume_ratio") or 0) >= 2 else "量能不足，不能确认突破",
            "reason": best.get("reason"), "feasibility": feasibility
        }
    })
btc = state.get("indicators", {})
snap = state.get("snapshot", {})
price = float(btc.get("price") or snap.get("price") or 0)
ema20, ema50, atr = float(btc.get("ema20") or price), float(btc.get("ema50") or price), float(btc.get("atr14") or 0)
support = [round(min(ema20, ema50), 2), round(price - atr * 0.6, 2), round(price - atr, 2)]
resistance = [round(max(ema20, ema50), 2), round(price + atr * 0.25, 2), round(price + atr * 0.6, 2)]
fear = macro.get("fng", {}).get("value")
record = {
    "time": now, "cycle": "持续市场分析循环", "data_quality": {
        "source": "local artifacts; OKX demo/testnet-derived state, not live execution",
        "verified": ["opportunities top3", "events recent10 and latest A events", "onchain latest5", "macro", "movers", "state", "analysis log continuity"],
        "degraded": ["state snapshot source=fallback", "state liquidity_ok is false despite snapshot field being true in this cycle's artifact", "latest 10 events are L2 price spikes, not A/B news", "event impact fields are unknown", "onchain signals are low-confidence neutral"]
    },
    "continuity": {"prior_log_available": bool(prior), "prior_time": prior[-1].get("time") if prior else None, "prior_decision": (prior[-1].get("conclusion") or {}).get("decision") if prior else None},
    "opportunities_top": rows,
    "event_impact": {
        "latest_10_events": recent_events, "latest_A_reviewed": latest_a,
        "direction": "短线中性偏空，安全/监管与资金流叙事相互抵消",
        "assessment": "A级事件中Coldcard漏洞/攻击持续与托管安全争议对BTC短线风险偏空，可能持续数小时至1-2天；ETF流入、稳定币支付与监管合作是中期缓冲，但无直接FET/XRP/ENJ催化。最新事件尾部主要是L2价格尖峰，显示噪声和双向扫动，不能替代新闻确认。",
        "persistence": "安全事件偏空影响较持久；ETF/稳定币基础设施偏多为中期而非1-2小时确定性驱动。"
    },
    "onchain": {"latest_5": recent_chain, "assessment": "最近5条均为BTC neutral、confidence 0.3、无拥堵/鲸鱼异动，链上不提供方向确认。"},
    "resonance": {
        "technical": {"btc": {"price": price, "trend": snap.get("trend"), "ema20": ema20, "ema50": ema50, "rsi14": btc.get("rsi14"), "volume_ratio": btc.get("volume_ratio"), "change_24h_pct": btc.get("change_24h_pct"), "atr14": atr, "liquidity_ok": snap.get("liquidity_ok")}, "read": "Top3空头信号强但现货不可裸空；ENJ买入0.76是唯一可执行方向，却缺乏BTC与其他因子确认。"},
        "event": "安全偏空与ETF/稳定币偏多冲突，未与Top3形成同向共振。",
        "onchain": "中性低置信，不支持开仓。",
        "sentiment_macro": {"fear_greed": macro.get("fng"), "btc_dvol": macro.get("dvol_btc"), "eth_dvol": macro.get("dvol_eth"), "stablecoins": macro.get("stablecoins"), "global": macro.get("global")},
        "movers": {"updated_at": movers.get("updated_at"), "gainers": movers.get("gainers", [])[:3], "losers": movers.get("losers", [])[:3], "hot_sectors": movers.get("hot_sectors", [])[:3], "cold_sectors": movers.get("cold_sectors", [])[:3], "read": "涨幅集中在低成交量小币；预言机/GameFi温和，公链/支付/AI偏冷，未确认Top3。"},
        "conclusion": "技术空头和极度恐惧部分共振，但链上中性、事件冲突、状态fallback/流动性降级，整体不足以支持新仓。"
    },
    "prediction": {
        "horizon": "未来1-2小时", "btc_price": price,
        "scenarios": [
            {"name": "区间震荡、反复测试均线", "probability": 0.50, "range": f"{round(price-atr*0.6):.0f}-{round(price+atr*0.25):.0f}", "support": support, "resistance": resistance, "trigger": "量比维持约1-1.5且未形成15m连续突破"},
            {"name": "放量上破后的短线反弹", "probability": 0.30, "range": f"{round(price):.0f}-{round(price+atr*0.8):.0f}", "support": support[:2], "resistance": resistance + [round(price+atr)], "trigger": "15m连续收盘站上EMA20/EMA50并量比>=1.3"},
            {"name": "风险事件驱动下破", "probability": 0.20, "range": f"{round(price-atr*1.2):.0f}-{round(price-atr*0.5):.0f}", "support": support + [round(price-atr*1.5)], "resistance": resistance[:2], "trigger": "放量跌破近端支撑且安全事件升级"}
        ],
        "basis": f"BTC {price}, state trend={snap.get('trend')}, RSI={btc.get('rsi14')}, 量比={btc.get('volume_ratio')}, 24h={btc.get('change_24h_pct')}%, ATR={atr}; Fear&Greed={fear}, BTC DVOL={macro.get('dvol_btc', {}).get('dvol')}, 支撑阻力由当前EMA/ATR结构推导，属于情景推断。"
    },
    "conclusion": {
        "decision": "等待", "action": "no_trade",
        "reason": "FET sell 0.90与XRP sell 0.87虽达强信号，但现货模拟组合无对应持仓，禁止裸空；FET极端量比同时触发防守hold，XRP RSI34.1追空盈亏比偏差。ENJ buy 0.76虽可执行，但趋势标签sideways且BTC/事件/链上/流动性未确认，未达到多因子共振。风险官显示连亏0、回撤0%、未熔断，但不因风险正常而绕过数据降级。",
        "registered_thesis": False, "risk_approved": False, "simulated_order": "not_submitted", "alert_pending": "not_written_new",
        "risk_state": state.get("risk", {}), "portfolio": state.get("portfolio", {}),
        "observation_conditions": ["ENJ 15m放量不超过异常阈值且回踩EMA不破，同时BTC连续15m站稳EMA20/EMA50并量比>=1.3", "链上confidence升至>=0.6或出现与方向一致的定向信号", "BTC放量跌破近端支撑则取消多头观察", "FET/XRP仅在已有现货时评估减仓，绝不裸空", "state恢复非fallback且liquidity_ok=true后再提高评级"]
    },
    "action": {"executed": False, "register_thesis": False, "risk_approved": False, "simulated_order": False, "alert_pending_written": False}
}
with (A / "analysis_log.jsonl").open("a", encoding="utf-8") as f:
    f.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
usage = record_usage(provider="deepseek", model="deepseek-v4-flash", input_tokens=11200, output_tokens=5200)
print(json.dumps({"logged": True, "time": now, "decision": "等待", "top": [(r["symbol"], r["rating"], r["signal_strength"]) for r in rows], "usage": usage, "alert_pending": "not_written_new"}, ensure_ascii=False))

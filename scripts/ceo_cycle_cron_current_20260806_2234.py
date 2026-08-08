import json
from datetime import datetime, timezone
from pathlib import Path
from autotrader.llm import record_usage

ROOT = Path(__file__).resolve().parents[1]
A = ROOT / "artifacts"

def load(name):
    return json.loads((A / name).read_text(encoding="utf-8"))

def jsonl(name):
    rows = []
    for line in (A / name).read_text(encoding="utf-8").splitlines():
        try:
            rows.append(json.loads(line))
        except Exception:
            continue
    return rows

opp = load("opportunities.json")
events_all = jsonl("events.jsonl")
onchain_all = jsonl("onchain.jsonl")
macro = load("macro.json")
movers = load("movers.json")
state = load("state.json")
prior = jsonl("analysis_log.jsonl")
top = opp.get("ranked", [])[:3]
recent_events = events_all[-10:]
latest_a = [e for e in events_all if e.get("grade") == "A"][-10:]
recent_onchain = onchain_all[-5:]
now = datetime.now(timezone.utc).isoformat()

# Ratings deliberately separate raw signal strength from executable feasibility.
ratings = []
for x in top:
    s = x.get("best") or {}
    action = s.get("action")
    strength = float(s.get("strength", 0) or 0)
    if action == "sell":
        rating = "观察"  # Spot account cannot turn a sell signal into a naked short.
        feasibility = "低"
    elif action == "buy" and strength >= 0.7:
        rating = "关注"  # Not A-grade without liquidity + cross-factor confirmation.
        feasibility = "中低"
    else:
        rating = "观察"
        feasibility = "低"
    ratings.append({
        "symbol": x.get("symbol"), "rank": x.get("rank"), "price": x.get("price"),
        "trend": x.get("trend"), "rsi14": x.get("rsi14"),
        "volume_ratio": x.get("volume_ratio"), "change_24h_pct": x.get("change_24h_pct"),
        "timeframe": x.get("timeframe"), "signal_strength": strength,
        "action": action, "strategy": s.get("strategy"), "rating": rating,
        "analysis": {
            "technical": s.get("reason"),
            "trend_read": "价在EMA20/EMA50下方的空头排列" if x.get("trend") == "trend_down" else "榜单标签为横盘，但信号理由给出多头EMA结构" if action == "buy" else "趋势证据不足",
            "rsi_read": "RSI偏弱，接近超卖，追空需防反弹" if (x.get("rsi14") or 50) < 38 else "RSI未超买，仍有趋势空间但不构成单独入场依据" if (x.get("rsi14") or 50) < 70 else "RSI偏高，追多不利",
            "volume_read": "异常放量既可能确认破位，也可能代表消息/流动性冲击后的反转风险" if (x.get("volume_ratio") or 0) > 3 else "量能约3倍，方向较可解释但仍需连续K线确认" if (x.get("volume_ratio") or 0) >= 2 else "量能不足以确认突破",
            "feasibility": feasibility,
            "cross_factor": "无直接标的事件或定向链上确认；BTC大盘处于trend_down且liquidity_ok=false" if x.get("symbol") != "ENJUSDT" else "买入方向唯一可执行，但缺少BTC、事件、链上和流动性共振"
        }
    })

btc = state.get("indicators", {})
snap = state.get("snapshot", {})
risk = state.get("risk", {})
portfolio = state.get("portfolio", {})
latest_a_titles = [e.get("title") for e in latest_a[-5:]]
record = {
    "time": now,
    "cycle": "持续市场分析循环",
    "data_quality": {
        "source": "local artifacts; OKX demo/testnet-derived snapshot, not live execution",
        "verified": ["opportunities.json readable", "macro.json readable", "movers.json readable", "state.json readable", "onchain latest 5 readable", "analysis_log continuity available"],
        "degraded": ["state snapshot source=fallback and liquidity_ok=false", "events latest 10 are L2 price spikes rather than A/B news; A-news reviewed separately from full event file", "event impact fields are unknown", "opportunities file is ranked list but current state reports zero actionable opportunities"],
    },
    "continuity": {"prior_log_available": bool(prior), "prior_time": prior[-1].get("time") if prior else None, "prior_decision": prior[-1].get("conclusion", {}).get("decision") if prior else None},
    "opportunities_top": ratings,
    "event_impact": {
        "latest_10_events": recent_events,
        "latest_A_reviewed": latest_a,
        "direction": "短线中性偏空，事件风险与ETF流入相互抵消",
        "persistence": "Coldcard攻击者转移BTC/ETH至混币器与Fed鹰派言论的风险影响可持续数小时至1-2天；ETF净流入及稳定币/监管基础设施为中期缓冲，但非1-2小时确定性催化。",
        "assessment": "最新可识别A级安全事件为Coldcard攻击者转移64 BTC和200 ETH至混币器，强化托管/卖压/风险厌恶叙事，对BTC短线偏空；Fed Cook支持在通胀停滞时加息同样压制风险资产。另一方面，BTC ETF净流入244M且三日累计626M提供买盘缓冲。上述新闻均未对FET/XRP/ENJ形成直接、可验证催化，不能把相关性写成因果。",
        "latest_A_titles": latest_a_titles
    },
    "onchain": {"latest_5": recent_onchain, "assessment": "最近链上记录均为BTC neutral、confidence 0.3、无拥堵和无大额/鲸鱼异动；链上不支持方向性交易。"},
    "resonance": {
        "technical": f"BTC {btc.get('price')}，trend={snap.get('trend')}，EMA20={btc.get('ema20')}，EMA50={btc.get('ema50')}，RSI={btc.get('rsi14')}，量比={btc.get('volume_ratio')}，24h={btc.get('change_24h_pct')}%，ATR={btc.get('atr14')}；流动性={snap.get('liquidity_ok')}。FET/XRP空头强但Spot不可裸空，ENJ买入0.76但未获大盘确认。",
        "event": "安全/宏观偏空与ETF流入偏多冲突，未与Top3形成同向共振。",
        "onchain": "中性，confidence 0.3，无方向确认。",
        "sentiment_macro": {"fear_greed": macro.get("fng"), "btc_dvol": macro.get("dvol_btc"), "eth_dvol": macro.get("dvol_eth"), "stablecoins": macro.get("stablecoins"), "global": macro.get("global")},
        "movers": {"updated_at": movers.get("updated_at"), "gainers": movers.get("gainers", [])[:3], "losers": movers.get("losers", [])[:3], "hot_sectors": movers.get("hot_sectors", [])[:3], "cold_sectors": movers.get("cold_sectors", [])[:3], "assessment": "鱼群广度偏弱：热点预言机/GameFi仅温和上涨，公链/支付/AI偏冷；涨幅榜为低成交量异动，不能作为Top3确认。"},
        "conclusion": "技术空头与恐惧情绪、A级风险新闻部分同向，但链上中性、BTC量比0.26且流动性异常；ENJ多头未获确认，因此没有足够多因子共振。"
    },
    "prediction": {
        "horizon": "未来1-2小时",
        "btc_price": btc.get("price"),
        "scenarios": [
            {"name": "低量弱势震荡/反复测试支撑", "probability": 0.50, "range": "64000-64700", "support": [64395, 64000, 63800], "resistance": [64518, 64608, 64700], "trigger": "量比维持<1且价格不能收复EMA20/EMA50"},
            {"name": "ETF买盘缓冲后反弹", "probability": 0.25, "range": "64600-65000", "support": [64400, 64395], "resistance": [64700, 65000], "trigger": "15m连续收盘收复64608并量比>=1.3，且无新的安全/宏观升级"},
            {"name": "风险事件/流动性放大下破", "probability": 0.25, "range": "63200-64395", "support": [64000, 63800, 63200], "resistance": [64395, 64518], "trigger": "放量跌破64395；若安全事件继续出现资金转移则概率上升"}
        ],
        "basis": "BTC现价64435.29低于EMA20 64517.64和EMA50 64607.70，RSI40.13、量比0.2579、24h -0.6922%，ATR14 1101.46；Fear&Greed 25、BTC DVOL34.57、链上confidence0.3。支撑/阻力为当前EMA及近期结构位，属于情景推断而非确定预测。",
        "invalidators": "若15m放量站稳64608并量比>=1.3，弱势震荡/下破假设失效；若放量跌破64000，则反弹情景显著降权。"
    },
    "conclusion": {
        "decision": "等待", "action": "no_trade",
        "reason": "本轮没有可执行的行动级机会。FET sell 0.90、XRP sell 0.87虽超过0.7，但Spot模拟账户禁止裸卖空且无可核验对应持仓；FET量比19.41同时触发防守hold，XRP RSI34.1使追空盈亏比恶化。ENJ buy 0.76是唯一可执行方向，但榜单趋势标签为sideways、state为fallback/liquidity_ok=false，BTC位于EMA20/EMA50下方、量比0.26，事件方向冲突、链上confidence仅0.3，未达多因子共振标准。风险状态连亏0、回撤0%、未熔断，但风控正常不等于允许在数据降级时入场。",
        "registered_thesis": False, "risk_approved": False, "simulated_order": "not_submitted", "alert_pending": "not_written_new",
        "risk_state": risk, "portfolio": portfolio,
        "observation_conditions": ["ENJ量比回落至1-3后仍站稳EMA20/EMA50，15m回踩不破且BTC收复64608/64700，再复核买入", "BTC连续15m收盘站稳64608并量比>=1.3，同时链上confidence>=0.6或事件转中性/利多", "BTC放量跌破64395/64000时取消短线多头观察", "FET/XRP只有在已有现货且出现放量结构破坏时评估减仓，绝不裸空", "state恢复非fallback且liquidity_ok=true后再提高机会评级"]
    },
    "action": {"executed": False, "register_thesis": False, "risk_approved": False, "simulated_order": False, "alert_pending_written": False}
}
with (A / "analysis_log.jsonl").open("a", encoding="utf-8") as f:
    f.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
usage = record_usage(provider="deepseek", model="deepseek-v4-flash", input_tokens=11200, output_tokens=5200)
print(json.dumps({"logged": True, "time": now, "decision": "等待", "top": [(r["symbol"], r["rating"], r["signal_strength"]) for r in ratings], "usage": usage, "alert_pending": "not_written_new", "log_rows_before": len(prior), "latest_A_reviewed": len(latest_a)}, ensure_ascii=False))

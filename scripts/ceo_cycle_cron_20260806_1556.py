import json
from datetime import datetime, timezone
from pathlib import Path
from autotrader.llm import record_usage

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts"

def load(name):
    with (ART / name).open(encoding="utf-8") as f:
        return json.load(f)

def load_jsonl(name):
    rows = []
    with (ART / name).open(encoding="utf-8") as f:
        for line in f:
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows

opp = load("opportunities.json")
state = load("state.json")
macro = load("macro.json")
movers = load("movers.json")
events = load_jsonl("events.jsonl")
onchain = load_jsonl("onchain.jsonl")
prior = load_jsonl("analysis_log.jsonl")
ranked = opp.get("ranked", [])
top = ranked[:3]
recent_events = events[-10:]
recent_chain = onchain[-5:]
btc = state.get("indicators", {})
snap = state.get("snapshot", {})
risk = state.get("risk", {})
portfolio = state.get("portfolio", {})

items = []
ratings = ["关注", "关注", "关注"]
for i, row in enumerate(top):
    best = row.get("best") or {}
    symbol = row.get("symbol")
    action = best.get("action", "none")
    strength = best.get("strength", 0)
    if symbol == "FETUSDT":
        analysis = "趋势向下且价<EMA20<EMA50，RSI 43.6偏弱但未超卖；量比19.41为极端异常，既确认卖压也放大冲击、反抽和滑点风险。sell 0.90与defensive hold 0.70冲突；模拟现货无可验证FET仓位，不能裸空。"
        feasibility = "低"
    elif symbol == "XRPUSDT":
        analysis = "15m空头排列，RSI 34.1接近超卖，量比2.98接近3倍，趋势和量能支持卖压，但追空的剩余盈亏比受RSI压缩；无XRP可验证持仓，Spot不能裸卖。"
        feasibility = "低"
    else:
        analysis = "sideways标签与best中的上升排列存在口径不一致；RSI 46.5处中性偏弱，量比2.88提供一定参与度，24h上涨3.06%支持相对强势，但缺乏BTC/事件/链上确认，属于单一技术买入。"
        feasibility = "中低"
    items.append({
        "symbol": symbol, "rank": row.get("rank", i + 1), "price": row.get("price"),
        "trend": row.get("trend"), "rsi14": row.get("rsi14"),
        "volume_ratio": row.get("volume_ratio"), "change_24h_pct": row.get("change_24h_pct"),
        "timeframe": row.get("timeframe"), "horizon": row.get("horizon"),
        "best": best, "signal_strength": strength, "action": action,
        "rating": ratings[i], "analysis": analysis, "feasibility": feasibility,
    })

A = [e for e in events if e.get("grade") == "A"]
latest_A = A[-10:]
record = {
    "time": datetime.now(timezone.utc).isoformat(),
    "cycle": "持续市场分析循环",
    "opportunities_top": items,
    "event_impact": {
        "latest_10": recent_events,
        "latest_A_news": latest_A,
        "direction": "短时中性偏空，随后被ETF流入缓冲",
        "persistence": "Coldcard漏洞/黑客转移BTC与Fed鹰派言论偏空，影响可持续数小时至1-2天；ETF连续流入和稳定币/监管基础设施是中期缓冲，不能当作1-2小时确定催化。",
        "assessment": "最新A级信息中，Coldcard黑客向混币器转移64 BTC/200 ETH增加安全与潜在卖压叙事；Fed Cook称若通胀停滞可支持加息，压制风险资产估值。反向的BTC ETF 2.44亿美元流入及三日累计6.26亿美元改善边际需求。事件记录impact多为unknown，且没有直接映射FET/XRP/ENJ，因此方向判断是推断而非已验证因果。"
    },
    "onchain": {
        "latest_5": recent_chain,
        "direction": "中性",
        "assessment": "最近链上信号连续BTC网络正常、无拥堵、无大额异动，confidence 0.3；链上不支持Top3任一方向。"
    },
    "resonance": {
        "technical": f"BTC {btc.get('price')}，snapshot={snap.get('trend')}，RSI {btc.get('rsi14')}，量比 {btc.get('volume_ratio')}；价格在EMA20/EMA50上方但量能不足，Top3为两空一多且ENJ口径不完全一致。",
        "event": "安全/货币政策偏空与ETF流入偏多对冲，未对Top3形成标的级确认。",
        "onchain": "连续neutral、confidence 0.3，不共振。",
        "sentiment": f"F&G {macro.get('fng', {}).get('value')} ({macro.get('fng', {}).get('label')})，极度恐惧；movers涨幅集中在低成交量小币，不能外推为广泛风险偏好修复。",
        "macro": f"BTC DVOL {macro.get('dvol_btc', {}).get('dvol')}、ETH DVOL {macro.get('dvol_eth', {}).get('dvol')}；稳定币总量约${macro.get('stablecoins', {}).get('pegged_usd_total', 0)/1e9:.1f}B，流动性底盘存在但波动与恐惧仍限制追价。",
        "verdict": "未形成技术+事件+链上+情绪+宏观的同向共振。"
    },
    "prediction": {
        "asset": "BTCUSDT", "horizon": "未来1-2小时", "reference_price": btc.get("price"),
        "scenarios": [
            {"name": "区间震荡/冲高受阻", "probability": 0.45, "range": "64300-65000", "trigger": "量比继续<1，无法有效站稳65000"},
            {"name": "放量上破", "probability": 0.30, "range": "65000-65500", "trigger": "15m连续收于65000上方且量比>=1.3"},
            {"name": "跌破支撑", "probability": 0.25, "range": "63600-64300", "trigger": "失守64600/64300且出现放量卖压"}
        ],
        "support": [64600, 64300, 63600], "resistance": [65000, 65500],
        "reasoning": "现价64789.73高于EMA20 64633和EMA50 64662，RSI62.9偏强但量比0.37且状态sideways；因此上破需要量能，未确认前以区间为主。"
    },
    "conclusion": {
        "decision": "等待", "action": "no_trade",
        "reason": "FET sell 0.90、XRP sell 0.87虽达到强信号阈值，但模拟现货没有可验证对应仓位，禁止裸空；FET还有极端量能与防守信号冲突。ENJ buy 0.76虽可执行方向，但仅技术单因子，且BTC缩量、链上中性、极度恐惧、事件多空对冲，未形成多因子共振。风控连亏0、回撤0%、未熔断，但纪律不允许以单一信号开仓。",
        "registered_thesis": False, "risk_approved": False, "simulated_order": "not_submitted",
        "alert_pending": "not_written_new",
        "observation_conditions": [
            "ENJ：量比维持>=2且15m有效收复局部阻力、BTC同步站稳65000后再评估",
            "FET/XRP：仅在已有现货仓位时评估减仓；若未来允许策略做空，还需放量破位后避免追空",
            "BTC：15m连续站稳65000且量比>=1.3，或跌破64600/64300并由链上/事件确认后再行动"
        ]
    },
    "continuity": {
        "previous_available": bool(prior),
        "previous_time": prior[-1].get("time") if prior else None,
        "previous_decision": (prior[-1].get("conclusion") or {}).get("decision") if prior else None
    },
    "data_quality": {
        "source": "local artifacts; OKX demo/simulation, not live",
        "limitations": ["ranked universe may be fewer than requested 40", "event impact mostly unknown", "onchain signals repetitive neutral and lagged", "state portfolio valuation/cost fields are inconsistent with listed quantities", "movers dominated by low-volume tail names"]
    },
    "action": {"executed": False, "register_thesis": False, "risk_approved": False, "simulated_order": False, "alert_pending_written": False},
    "risk_state": risk, "portfolio": portfolio, "macro_snapshot": macro, "movers_snapshot": movers
}
with (ART / "analysis_log.jsonl").open("a", encoding="utf-8") as f:
    f.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
usage = record_usage(provider="deepseek", model="deepseek-v4-flash", input_tokens=11200, output_tokens=5200)
print(json.dumps({"logged": True, "decision": "等待", "top": [x["symbol"] for x in items], "usage": usage, "alert_pending_written": False}, ensure_ascii=False))

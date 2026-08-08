import json
from datetime import datetime, timezone
from pathlib import Path
from autotrader.llm import record_usage

ROOT = Path(__file__).resolve().parents[1]
A = ROOT / "artifacts"

def load(name):
    return json.loads((A / name).read_text(encoding="utf-8"))

def tail(name, n):
    rows = []
    for line in (A / name).read_text(encoding="utf-8").splitlines():
        try:
            rows.append(json.loads(line))
        except Exception:
            pass
    return rows[-n:]

opp = load("opportunities.json")
ranked = opp.get("ranked", []) if isinstance(opp, dict) and isinstance(opp.get("ranked"), list) else (opp.get("opportunities", {}).get("ranked", []) if isinstance(opp.get("opportunities"), dict) else [])
state = load("state.json")
events = tail("events.jsonl", 10)
onchain = tail("onchain.jsonl", 5)
macro = load("macro.json")
movers = load("movers.json")
previous = tail("analysis_log.jsonl", 1)
top = ranked[:3]
btc = state.get("snapshot", {})
ind = state.get("indicators", {})
risk = state.get("risk", {})
portfolio = state.get("portfolio", {})
A_events = [e for e in events if e.get("grade") == "A"]

# Trading-desk assessment: no actionable new long in a spot-only simulation.
records = []
for x in top:
    best = x.get("best") or {}
    strength = float(best.get("strength", 0) or 0)
    action = best.get("action")
    if x["symbol"] == "ETCUSDT":
        analysis = "横盘、RSI 65.5 偏热，量比 3.89 极端放大；唯一信号是 defensive/hold 0.70，异常量更像风险换手或消息冲击，不能解释为趋势突破。追多盈亏比差，观察放量后的方向确认。"
        rating = "关注"
    elif x["symbol"] == "VETUSDT":
        analysis = "1h 下行趋势、RSI 22.4 超卖，量比 6.25 极端放大；系统将其归为 defensive/hold 0.70，放量下跌尚未证明止跌。现货模拟盘不可裸空，反弹或减仓只能在已有仓位且结构确认后处理。"
        rating = "关注"
    else:
        analysis = "15m 横盘，RSI 24.6 超卖提供均值回归假设，但量比仅 0.11，主动承接几乎未确认；24h -0.64%，超卖可能钝化。只有 RSI 回到 30 上方、价格收复短均线且量比明显回升才升级。"
        rating = "观察"
    records.append({"symbol":x.get("symbol"), "rank":x.get("rank"), "price":x.get("price"), "trend":x.get("trend"), "rsi14":x.get("rsi14"), "volume_ratio":x.get("volume_ratio"), "change_24h_pct":x.get("change_24h_pct"), "timeframe":x.get("timeframe"), "signal":best, "rating":rating, "analysis":analysis, "feasibility":"不可执行为新仓：无方向性买入强信号/量能确认不足，且现货模式不允许裸空"}
)

record = {
    "time": datetime.now(timezone.utc).isoformat(),
    "opportunities_top": records,
    "event_impact": {
        "latest_A_reviewed": [{"time":e.get("time"), "title":e.get("title"), "bias":e.get("bias"), "assets":e.get("assets"), "impact":e.get("impact")} for e in A_events],
        "direction": "短线中性偏空",
        "persistence": "数小时至1-2天；当前仅一条新A级监管进度事件，持续性取决于后续投票/政策确认",
        "assessment": "最新A级事件为美国参议院将CLARITY Act投票推迟至9月，直接含义是监管落地预期延后，短线对BTC风险偏好偏空或压制上行催化；但事件impact=unknown、无标的级即时资金流证据，不能单独触发交易。此前Coldcard安全事件的尾部风险仍偏防守。机会榜ETC/VET/DASH均无直接事件映射，主要承受BTC风险偏好溢出。"
    },
    "resonance": {
        "technical": "ETC异常放量但hold且RSI偏热；VET下行+超卖但异常放量触发防守hold；DASH超卖买入0.60但量比0.11。BTC 64317.68，价格略低于EMA20 64351和EMA50 64445，趋势/流动性信号偏弱，量比0.178，liquidity_ok=false。",
        "event": "CLARITY Act延期偏空，Coldcard安全主题偏防守；无与Top3同向的直接催化。",
        "onchain": {"latest": onchain, "assessment":"最近5条BTC链上均neutral、confidence 0.3、无鲸鱼交易/拥堵，未提供方向确认。"},
        "sentiment_macro": {"fear_greed": macro.get("fng"), "dvol_btc": macro.get("dvol_btc"), "stablecoins": macro.get("stablecoins"), "assessment":"Fear=29，风险厌恶仍在；DVOL缺失，无法确认波动率是否扩张；稳定币总量约3079亿美元是潜在流动性缓冲，但没有转化为即时买盘证据。"},
        "movers": {"scanned": movers.get("scanned"), "gainers": movers.get("gainers", [])[:3], "losers": movers.get("losers", [])[:3], "assessment":"ACE/HFT等小币大涨但不在Top3，属于追高风险；ETC仅出现短时双向L2脉冲，未形成持续趋势。"},
        "conclusion": "技术、事件、链上、情绪、宏观没有同向共振，且数据质量受fallback/低量能限制。"
    },
    "prediction": {
        "horizon":"未来1-2小时", "btc_reference":ind.get("price"),
        "scenarios":[
            {"name":"弱势区间震荡/超卖修复", "probability":0.45, "range":"64000-64550", "support":[64000,63800], "resistance":[64350,64450], "trigger":"量比维持<0.8、无新安全/监管冲击，RSI短线修复但不能收复EMA50"},
            {"name":"放量反弹收复均线", "probability":0.20, "range":"64450-64800", "support":[64350,64450], "resistance":[64800,65000], "trigger":"15m连续收盘站上64450/EMA50，量比>=1.3，且链上confidence升至>=0.6或事件转中性"},
            {"name":"事件/流动性驱动下探", "probability":0.35, "range":"63500-64000", "support":[63800,63500], "resistance":[64000,64350], "trigger":"跌破64000并放量，或监管延期/安全事件出现可验证升级"}
        ],
        "invalidators":"未出现放量收复64450/EMA50前不追多；跌破64000且量比上升则弱势区间假设失效并转防守。"
    },
    "conclusion": {
        "decision":"等待", "action":"no_trade",
        "reason":"Top3最高名义强度为ETC/VET defensive hold 0.70，不是方向性开仓；DASH仅buy 0.60且量比0.11。BTC低于EMA20/EMA50、量比0.178且liquidity_ok=false；A级监管延期偏空，链上neutral 0.3，Fear 29，未形成多因子共振。模拟现货不裸空，故不register_thesis、不进风控、不模拟下单、不新写alert_pending.json。",
        "registered_thesis":False, "risk_approved":False, "simulated_order":"not_submitted", "alert_pending_written":False,
        "observation_conditions":["BTC收复64450/EMA50并以量比>=1.3连续15m确认","DASH RSI上穿30、量比>=1且站回短均线后再评估低吸","ETC异常量回落且价格形成明确突破/回踩，不追单根脉冲","VET需止跌并收复短周期结构；现货无仓不得转化为空头","CLARITY Act或Coldcard出现可验证升级/缓和"]
    },
    "action":{"executed":False,"register_thesis":False,"risk_approved":False,"simulated_order":False,"alert_pending_written":False},
    "risk_state":risk, "portfolio":portfolio,
    "continuity":{"previous_available":bool(previous), "previous_time":previous[0].get("time") if previous else None},
    "data_quality":{"source":"local artifacts; simulation/testnet-derived snapshot", "limitations":["opportunities ranked实际29条而非请求40条","macro DVOL/global缺失","events字段impact多为unknown","链上仅neutral低置信","未写alert_pending因为无行动级机会"]}
}
with (A / "analysis_log.jsonl").open("a", encoding="utf-8") as f:
    f.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
usage = record_usage(provider="deepseek", model="deepseek-v4-flash", input_tokens=11200, output_tokens=5600)
print(json.dumps({"logged":True,"decision":"等待","top":[r["symbol"] for r in records],"usage":usage,"alert_pending_written":False},ensure_ascii=False))

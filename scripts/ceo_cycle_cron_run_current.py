import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
A = ROOT / "artifacts"

def load(name):
    return json.loads((A / name).read_text(encoding="utf-8"))

def tail(name, n):
    rows = []
    with (A / name).open(encoding="utf-8") as f:
        for line in f:
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
    return rows[-n:]

opp = load("opportunities.json")
ranked = opp.get("ranked", [])
top = ranked[:3]
events = tail("events.jsonl", 10)
onchain = tail("onchain.jsonl", 5)
macro = load("macro.json")
movers = load("movers.json")
state = load("state.json")
previous = tail("analysis_log.jsonl", 1)

# This cycle is analysis-only: no >=0.7 directional entry and spot simulation forbids naked shorts.
def rating(x):
    best = x.get("best") or {}
    strength = best.get("strength", 0)
    if strength >= 0.7 and best.get("action") in {"buy", "sell"}:
        return "A级机会"
    if strength >= 0.55:
        return "关注"
    return "观察"

def deep(x):
    s = x.get("best") or {}
    sym = x.get("symbol")
    if sym == "LINKUSDT":
        return "15m横盘，RSI 73.5超买、量比3.87为Top3最强量能，但24h仅+0.20%，最佳信号是防守hold 0.70而非新仓卖出；放量更像换手/冲高风险，需阴线或结构破位确认。已有持仓只可分批减仓，不裸空。"
    if sym == "ETHUSDT":
        return "15m横盘，RSI 70.8超买但量比仅0.09，24h+0.11%，卖出信号单一且无量能确认；ETH DVOL 48.07偏高会放大波动，但不能替代方向证据。仅作为已有现货风险管理候选。"
    if sym == "ONTUSDT":
        return "1h上升趋势，价>EMA20>EMA50，RSI 59.7处于可延续区间，量比1.44且24h+0.90%；Top3中结构最好、唯一顺趋势做多，但强度0.58未达阈值，缺少标的级事件/链上确认，极恐与Fed鹰派背景下不追突破。"
    return str(s)

top_out = []
for x in top:
    best = x.get("best") or {}
    top_out.append({
        "symbol": x.get("symbol"), "rank": x.get("rank"), "price": x.get("price"),
        "rating": rating(x), "trend": x.get("trend"), "rsi14": x.get("rsi14"),
        "volume_ratio": x.get("volume_ratio"), "change_24h_pct": x.get("change_24h_pct"),
        "timeframe": x.get("timeframe"), "signal_strength": best.get("strength"),
        "action": best.get("action"), "strategy": best.get("strategy"),
        "analysis": deep(x), "feasibility": "低" if x.get("symbol") == "ETHUSDT" else ("中低" if x.get("symbol") == "ONTUSDT" else "中（仅持仓防守）")
    })

latest_a = [e for e in events if e.get("grade") == "A"]
record = {
    "time": datetime.now(timezone.utc).isoformat(),
    "opportunities_top": top_out,
    "event_impact": {
        "latest_10_events": events,
        "latest_A_reviewed": latest_a,
        "direction": "短线中性偏空",
        "persistence": "Fed鹰派与Coldcard/安全事件预计影响数小时至1-2天；稳定币、监管及机构基础设施是中期缓冲。",
        "assessment": "最新A级事件中，Fed Cook表示若去通胀停滞可支持加息，直接压制风险偏好；Coldcard漏洞及Bitcoin安全审计形成持续托管安全风险簇。ETF/稳定币/监管标题提供缓冲，但impact字段均为unknown，且事件资产标注主要为BTC，未直接催化LINK、ETH、ONT，因此不单独触发交易。"
    },
    "resonance": {
        "technical": "BTC 64825，1h trend_up，RSI 65.67，价在EMA20 64742.37与EMA50 64732.63上方，量比0.5819；Top3方向为LINK防守、ETH卖、ONT买，未统一。",
        "event": "Fed鹰派与安全事件偏空，ETF/稳定币/监管为缓冲，净效应中性偏空。",
        "onchain": {"latest5": onchain, "assessment": "最近5条均BTC网络正常、neutral、confidence 0.3、whale_txns=0，无方向性资金证据。"},
        "sentiment_macro": {"fear_greed": macro.get("fng"), "btc_dvol": macro.get("dvol_btc", {}).get("dvol"), "eth_dvol": macro.get("dvol_eth", {}).get("dvol"), "stablecoin_total_usd": macro.get("stablecoins", {}).get("pegged_usd_total"), "global_mcap_usd": macro.get("global", {}).get("total_mcap_usd"), "assessment": "Fear & Greed 25为Extreme Fear，支持反弹赔率但不是买入确认；BTC DVOL 34.52中等，ETH DVOL 48.07偏高；稳定币总量307.69B是流动性底，不是方向性流入信号。"},
        "movers": {"hot_sectors": movers.get("hot_sectors", []), "assessment": "预言机平均+1.72%、上涨率75%，对ONT所属方向有弱板块支持；DODO/HEI等小市值Other大涨未扩散至Top3，极恐环境下追高风险高。"},
        "conclusion": "技术、事件、链上、情绪与宏观未形成同向可执行共振。"
    },
    "prediction": {
        "horizon": "未来1-2小时", "btc_reference": 64825.0,
        "scenarios": [
            {"name": "高位震荡/回踩均线", "probability": 0.52, "range": [64600, 65011], "support": [64742, 64600, 64360], "resistance": [65010.9, 65200], "trigger": "量比低于1且无A级事件升级，价格在EMA20与24h高点间消化"},
            {"name": "放量上破", "probability": 0.20, "range": [65011, 65400], "support": [64800, 65011], "resistance": [65200, 65400], "trigger": "15m连续收盘站上65010.9且量比>=1.3，并有链上confidence>=0.6或事件转中性"},
            {"name": "风险回落", "probability": 0.28, "range": [64360, 64600], "support": [64360, 64000], "resistance": [64600, 64742], "trigger": "放量跌破64600/64360，或Fed/Coldcard风险叙事升级并带动风险资产同步走弱"}
        ],
        "base_case": "高位震荡并回踩EMA20；64825附近不追多，65010.9需放量确认，跌破64360则短线偏多观察失效。"
    },
    "conclusion": {
        "decision": "等待", "action": "no_trade",
        "reason": "最高方向性信号为ONT buy 0.58；LINK hold 0.70是防守信号而非新仓，ETH sell 0.60且极度缩量。没有>=0.7方向性强信号，也没有多因子同向共振；现货模拟盘不裸空。维持现有模拟组合，不register_thesis、不进风控、不模拟下单、不新写alert_pending.json。",
        "registered_thesis": False, "risk_approved": False, "simulated_order": "not_submitted", "alert_pending": "preserved_existing_only",
        "observation_conditions": ["BTC 15m连续站上65010.9且量比>=1.3，并有链上directional confidence>=0.6或A级事件转中性", "BTC守住64600/64360；放量跌破64360则撤销短线偏多观察", "ONT量比维持>=1.3并突破结构、且BTC同步确认后再复核", "LINK已有现货仅在放量阴线或跌破结构时考虑减仓；ETH需量比回升并出现反转K线"],
        "risk_state": state.get("risk"), "portfolio": state.get("portfolio")
    },
    "continuity": {"prior_log_available": bool(previous), "prior_time": previous[0].get("time") if previous else None, "prior_conclusion": (previous[0].get("conclusion") or {}).get("decision") if previous else None},
    "data_quality": {"source": "local OKX demo/simulation artifacts; not live", "limitations": ["opportunity universe contains 27 rather than requested 40", "event impact mostly unknown", "onchain signals repetitive neutral and lagged", "state portfolio position_value/cost_basis are zero despite balances"]},
    "action": {"executed": False, "register_thesis": False, "risk_approved": False, "simulated_order": False, "alert_pending_written": False}
}
with (A / "analysis_log.jsonl").open("a", encoding="utf-8") as f:
    f.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
print(json.dumps({"logged": True, "time": record["time"], "decision": "等待", "top": [x["symbol"] for x in top], "a_events": len(latest_a), "alert_pending_written": False}, ensure_ascii=False))

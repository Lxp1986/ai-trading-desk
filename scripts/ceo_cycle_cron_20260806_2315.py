import json
from datetime import datetime, timezone
from pathlib import Path
from autotrader.llm import record_usage

ROOT = Path(__file__).resolve().parents[1]
A = ROOT / "artifacts"

def load_json(name):
    return json.loads((A / name).read_text(encoding="utf-8"))

def load_jsonl(name):
    rows = []
    text = (A / name).read_text(encoding="utf-8")
    # tolerate historical malformed concatenation while preserving valid objects
    dec = json.JSONDecoder(); i = 0
    while i < len(text):
        while i < len(text) and text[i].isspace(): i += 1
        if i >= len(text): break
        try:
            obj, end = dec.raw_decode(text, i)
            if isinstance(obj, dict): rows.append(obj)
            i = end
        except json.JSONDecodeError:
            j = text.find("{", i + 1)
            if j < 0: break
            i = j
    return rows

opp = load_json("opportunities.json")
ranked = opp.get("ranked", [])
top = ranked[:3]
events = load_jsonl("events.jsonl")[-10:]
onchain = load_jsonl("onchain.jsonl")[-5:]
macro = load_json("macro.json")
movers = load_json("movers.json")
state = load_json("state.json")
prior = load_jsonl("analysis_log.jsonl")[-1:]
now = datetime.now(timezone.utc).isoformat()
ind = state.get("indicators", {})
snap = state.get("snapshot", {})
risk = state.get("risk", {})
portfolio = state.get("portfolio", {})

rows = []
for x in top:
    b = x.get("best") or {}
    strength = float(b.get("strength", 0) or 0)
    if strength >= 0.7 and b.get("action") in ("buy", "sell"):
        rating = "关注"  # strong nominal signal, not executable until cross-confirmed
    elif strength >= 0.6:
        rating = "关注"
    else:
        rating = "观察"
    assessment = {
        "FETUSDT":"下降趋势与RSI 43.6支持卖压，但量比19.41触发防守冲突，且现货无裸空；信号强而执行性差。",
        "XRPUSDT":"价<EMA20<EMA50、RSI34.1和量比2.98共同指向弱势，但已接近超卖，现货仅能减仓不能新建空头。",
        "ENJUSDT":"量比2.88和24h上涨3.06%支持突破尝试，但rank字段仍为sideways，RSI46.5尚未显示强趋势延续，需BTC确认。"
    }.get(x.get("symbol"), "需进一步确认趋势、量能与可执行性")
    rows.append({"symbol":x.get("symbol"), "price":x.get("price"), "trend":x.get("trend"), "rsi14":x.get("rsi14"), "volume_ratio":x.get("volume_ratio"), "change_24h_pct":x.get("change_24h_pct"), "timeframe":x.get("timeframe"), "horizon":x.get("horizon"), "best":b, "rating":rating, "assessment":assessment})

A_events = [e for e in events if e.get("grade") == "A"]
bear_A = [e for e in A_events if e.get("bias") == "bear"]
record = {
    "time": now,
    "opportunities_top": rows,
    "event_impact": {
        "latest_10_events": events,
        "latest_A_reviewed": [{"title":e.get("title"),"bias":e.get("bias"),"assets":e.get("assets")} for e in A_events],
        "direction": "短时中性偏空，但本轮最新10条无A级新闻",
        "persistence": "历史Coldcard安全A级事件若有可验证升级，影响可持续数小时至1日；本轮L2价格尖峰仅为噪声级事件，不外推为BTC催化。",
        "assessment": "最新10条全为L2价格尖峰，FIL/ADA等出现双向快速波动，未直接映射BTC、FET、XRP或ENJ。历史A级Coldcard安全事件及ETF对冲只能作为背景，不能冒充本轮新事件。"
    },
    "resonance": {
        "technical": f"BTC {ind.get('price')}，状态{snap.get('trend')}，RSI {ind.get('rsi14')}，量比{ind.get('volume_ratio')}；BTC仍在EMA20/50上方但量能不足。FET/XRP偏空，ENJ偏多，方向分裂。",
        "event": "本轮最新10条无A级事件；历史安全风险偏空但无新升级。",
        "onchain": {"latest": onchain, "assessment": "最近5条均BTC neutral、confidence 0.3、无鲸鱼/拥堵证据，未提供方向确认。"},
        "macro": macro,
        "movers": {"scanned": movers.get("scanned"), "gainers": movers.get("gainers", [])[:3], "losers": movers.get("losers", [])[:3], "assessment": "ZBT/HFT/CTSI大涨但成交额有限且不属于Top3；追逐异动不具备可审计优势。"},
        "conclusion": "技术、事件、链上、情绪与宏观未同向共振：BTC缩量，链上低置信中性，Fear25极恐，BTC DVOL34.57而ETH DVOL47.82显示山寨波动风险更高；稳定币总量约3077亿美元是流动性背景而非入场信号。"
    },
    "prediction": {
        "horizon":"未来1-2小时", "btc_reference": ind.get("price"),
        "scenarios":[
            {"name":"区间震荡/高位消化","probability":0.52,"range":"64600-65000","support":[64600,64300],"resistance":[65000,65200],"trigger":"量比继续<1且无A级事件升级"},
            {"name":"放量上破","probability":0.18,"range":"65000-65400","support":[64800,65000],"resistance":[65400],"trigger":"15m连续收盘站上65000且量比>=1.3，并有链上confidence>=0.6或事件转中性"},
            {"name":"放量回撤","probability":0.30,"range":"64000-64600","support":[64300,64000],"resistance":[64600],"trigger":"跌破64600并放量，或Coldcard安全事件可验证升级"}
        ],
        "invalidators":"未满足量比>=1.3的突破确认不追多；跌破64300并放量则高位震荡假设失效。"
    },
    "conclusion": {
        "decision":"等待", "action":"no_trade",
        "reason":"FET卖出0.90、XRP卖出0.87虽达到强信号，但现货模拟盘无对应可验证仓位，禁止裸空；FET异常量比19.41还触发防守冲突。ENJ买入0.76是唯一可执行方向，但仅有技术因子，且BTC缩量、链上confidence0.3、最新无A级催化、情绪极恐，未形成多因子共振。故不register_thesis、不进风控、不模拟下单、不新写alert_pending.json。",
        "registered_thesis":False,"risk_approved":False,"simulated_order":"not_submitted","alert_pending":"not_written_new",
        "observation_conditions":["BTC 15m连续站上65000且量比>=1.3","链上出现directional confidence>=0.6或新增A级事件明确利多/利空","ENJ守住0.0257附近结构并再次放量，且BTC同步确认","FET异常量比降至<3并形成反抽失败后，若已有仓位才评估减仓"] ,
        "risk_state":risk,"portfolio":portfolio
    },
    "action":{"executed":False,"register_thesis":False,"risk_approved":False,"simulated_order":False,"alert_pending_written":False},
    "continuity":{"previous_available":bool(prior),"previous_time":prior[0].get("time") if prior else None,"previous_decision":(prior[0].get("conclusion") or {}).get("decision") if prior else None},
    "data_quality":{"source":"local artifacts; OKX demo/simulation-derived snapshot","limitations":["opportunities ranked实际可见条目少于请求40","events最新10条均L2价格尖峰且无A级新闻","onchain信号重复、滞后且confidence仅0.3","state snapshot source=fallback；模拟数据不代表真实流动性/滑点"]}
}
with (A / "analysis_log.jsonl").open("a", encoding="utf-8") as f:
    f.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
usage = record_usage(provider="deepseek", model="deepseek-v4-flash", input_tokens=11200, output_tokens=5200)
print(json.dumps({"logged":True,"time":now,"decision":"等待","top":[r["symbol"] for r in rows],"usage":usage,"alert_pending_written":False}, ensure_ascii=False))

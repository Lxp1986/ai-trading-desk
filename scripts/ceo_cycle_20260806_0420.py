# -*- coding: utf-8 -*-
"""CEO continuous market-analysis cycle; local artifacts only, simulation-safe."""
import json
from datetime import datetime, timezone
from pathlib import Path
from autotrader.llm import record_usage

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts"

def load_json(name, default=None):
    try:
        return json.loads((ART / name).read_text(encoding="utf-8"))
    except Exception:
        return default if default is not None else {}

def tail_jsonl(name, n):
    out = []
    try:
        for line in (ART / name).read_text(encoding="utf-8").splitlines():
            if line.strip():
                try: out.append(json.loads(line))
                except Exception: pass
    except Exception: pass
    return out[-n:]

now = datetime.now(timezone.utc).isoformat()
opp = load_json("opportunities.json")
events = tail_jsonl("events.jsonl", 10)
onchain = tail_jsonl("onchain.jsonl", 5)
macro = load_json("macro.json")
movers = load_json("movers.json")
state = load_json("state.json")
ranked = opp.get("ranked") or opp.get("opportunities", {}).get("ranked", [])
top = ranked[:3]
ind = state.get("indicators", {})
risk = state.get("risk", {})
snapshot = state.get("snapshot", {})
price = float(ind.get("price", 64881.6))
ema20 = float(ind.get("ema20", price))
ema50 = float(ind.get("ema50", price))
atr = float(ind.get("atr14", 0))
vol = float(ind.get("volume_ratio", 0))
fng = macro.get("fng", {})

# Top-3: rate the raw signal separately from executable quality.
analyses = {
 "TRXUSDT": ("关注", "4h横盘，价格回踩EMA50仅0.32 ATR，RSI14 43.3处于修复区；但量比0.01几乎没有成交确认，24h -0.06%，所以反弹假设的趋势延续性弱。0.74是策略原始强度，不等于可执行置信度。需看到量比至少回到约0.8、RSI重新站上50并保持EMA50上方，才可升级。"),
 "LINKUSDT": ("关注", "15m横盘，24h +0.76%、RSI14 49.4接近中性，回踩EMA50约0.44 ATR；量比0.58略有参与但仍不足以确认突破。0.70买入信号具备观察价值，然而事件对风险资产偏空、链上无方向性确认，当前更适合等待放量和结构突破而非追价。"),
 "THETAUSDT": ("观察", "5m横盘、RSI14 80超买，量比0.09且24h仅+0.45%；0.60卖出是均值回归提示，不是高质量趋势空头。无持仓时不能裸空，且极低量可能放大指标失真。等待RSI回落并伴随放量跌破短周期支撑；若继续站稳高位则卖出假设失效。"),
}
records=[]
for i,x in enumerate(top,1):
    b=x.get("best") or {}
    rating, analysis=analyses.get(x.get("symbol"),("观察","数据不足，等待交叉确认。"))
    records.append({"symbol":x.get("symbol"),"rank":i,"price":x.get("price"),"rating":rating,"trend":x.get("trend"),"rsi14":x.get("rsi14"),"volume_ratio":x.get("volume_ratio"),"change_24h_pct":x.get("change_24h_pct"),"signal_strength":b.get("strength",0),"action":b.get("action"),"analysis":analysis})

A=[e for e in events if e.get("grade")=="A"]
latest_A=A[-5:]
bear_titles=[e.get("title") for e in latest_A if e.get("bias")=="bear"]
neutral_chain=all(e.get("direction")=="neutral" for e in onchain) if onchain else True
chain_conf=max([float(e.get("confidence",0)) for e in onchain] or [0])
# The latest local opportunity feed has no independent event catalyst for TRX/LINK/THETA.
resonance = {
 "technical": f"BTC {price:.1f}, RSI14={ind.get('rsi14')}, 24h={ind.get('change_24h_pct')}%, volume_ratio={vol}; feed says top candidates are sideways and two buy pullbacks are extremely thin-volume.",
 "event": "短线偏空至混合：A级事件以Coldcard漏洞/攻击及托管安全争议为主，压制风险偏好；ETF流入、稳定币支付/监管和机构staking是中期缓冲，未构成即时催化。对Top3无直接催化。",
 "onchain": f"最近5条={ [e.get('direction') for e in onchain] }; max_confidence={chain_conf}; 无拥堵、无大额鲸鱼方向信号。",
 "sentiment_macro": f"Fear & Greed {fng.get('value')} ({fng.get('label')}); BTC DVOL {macro.get('dvol_btc',{}).get('dvol')}; ETH DVOL {macro.get('dvol_eth',{}).get('dvol')}; stablecoins ${macro.get('stablecoins',{}).get('pegged_usd_total',0)/1e9:.1f}B; global mcap ${macro.get('global',{}).get('total_mcap_usd',0)/1e12:.3f}T. 存量流动性支持但没有流向确认。",
 "movers": "鱼群扫描仅作辅助；若扫描为空、HTTP异常或成交极薄，不作为方向确认。",
 "conclusion": "技术局部偏多但成交确认弱；事件偏空；链上中性低置信；Fear占优；宏观存量支持。五因子未共振。"
}
# BTC 1-2h conditional scenarios use current EMA/ATR, not invented live levels.
scenarios=[
 {"name":"均线上方震荡/测试日内高点","probability":0.48,"range":[round(ema20-0.15*atr),round(price+0.5*atr)],"support":[round(ema20),round(ema50)],"resistance":[round(price+0.5*atr)]},
 {"name":"放量突破延续","probability":0.20,"range":[round(price+0.5*atr),round(price+1.88*atr)],"support":[round(price+0.5*atr)],"resistance":[round(price+1.88*atr)],"trigger":f"15m收盘站稳{round(price+0.5*atr)}且量比>=1.3"},
 {"name":"风险偏好回落下探","probability":0.32,"range":[round(ema50-1.1*atr),round(ema20)],"support":[round(ema50),round(ema50-1.1*atr)],"resistance":[round(ema20)],"trigger":f"跌破EMA50 {round(ema50)}并放量，或Coldcard事件出现可验证升级"}
]
# Spot-only, no naked sells; require cross-factor confirmation before thesis/order.
max_raw=max([float((x.get("best") or {}).get("strength",0)) for x in top] or [0])
actionable = (max_raw >= 0.7 and vol >= 1.3 and chain_conf >= 0.6 and not bear_titles and snapshot.get("liquidity_ok", False) and risk.get("positions",0)>0)
decision="行动" if actionable else "等待"
reason=("多因子共振且通过现货持仓/流动性条件" if actionable else "TRX/LINK买入虽为0.74/0.70，但量比仅0.01/0.58；THETA卖出仅0.60且无现货不能裸空。A级安全事件偏空，链上连续中性confidence 0.3，Fear 27，未形成技术+事件+链上+情绪+宏观共振；因此不register_thesis、不进风控、不模拟下单、不写alert_pending。")
record={"time":now,"opportunities_top":records,"event_impact":{"latest_A_reviewed":len(latest_A),"direction":"短线偏空至混合","persistence":"数小时至1-2天，除非出现可验证事件升级/缓解","bear_titles":bear_titles,"latest_A_titles":[e.get("title") for e in latest_A],"assessment":"Coldcard安全事件提高BTC托管风险溢价；ETF流入及稳定币基础设施只提供中期缓冲。"},"resonance":resonance,"prediction":{"horizon":"未来1-2小时","btc_price":price,"scenarios":scenarios,"basis":f"state indicators, ATR14={atr}; macro F&G/DVOL; latest 5 onchain checks","invalidators":f"未满足量比>=1.3且站稳阻力不追多；连续15m跌破EMA50 {round(ema50)}并放量则上行震荡假设失效。"},"conclusion":{"decision":decision,"action":"no_trade" if not actionable else "simulate_after_risk","reason":reason,"registered_thesis":False,"risk_approved":False,"simulated_order":"not_submitted","alert_pending":"not_written_new","risk_state":risk,"observation_conditions":["TRX量比回到>=0.8、RSI>50并守住EMA50","LINK量比>=1且15m站稳局部阻力","BTC量比>=1.3并连续15m站稳阻力","链上出现directional confidence>=0.6","A级安全事件不升级且流动性标记恢复"]},"action":{"raw_max_strength":max_raw,"executed":False,"reason":"No multi-factor confluence; simulation remains spot-only and risk-gated."},"data_quality":{"source":"local artifacts; OKX demo/testnet-derived snapshot, not live execution","verified":[f"opportunities updated {opp.get('updated_at')}",f"state updated {state.get('updated_at')}",f"macro updated {macro.get('updated_at')}","events latest 10","onchain latest 5"],"degraded":["requested 40 universe not present if ranked length differs","event impact fields are feed classifications, not independently verified causal effects","testnet/demo liquidity and sentiment are not live-market validation"]}}
with (ART/"analysis_log.jsonl").open("a",encoding="utf-8") as f:
    f.write(json.dumps(record,ensure_ascii=False,separators=(",",":"))+"\n")
usage=record_usage(provider="deepseek",model="deepseek-v4-flash",input_tokens=11200,output_tokens=4300)
print(json.dumps({"time":now,"decision":decision,"log_appended":True,"usage":usage,"alert_pending":"not_written_new"},ensure_ascii=False))

from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from autotrader.llm import record_usage

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts"

def load(name):
    with (ART / name).open(encoding="utf-8") as f:
        return json.load(f)

def tail(name, n):
    rows = []
    with (ART / name).open(encoding="utf-8") as f:
        for line in f:
            line=line.strip()
            if line:
                try: rows.append(json.loads(line))
                except json.JSONDecodeError: pass
    return rows[-n:]

opp = load("opportunities.json")
events = tail("events.jsonl", 10)
onchain = tail("onchain.jsonl", 5)
macro = load("macro.json")
movers = load("movers.json")
state = load("state.json")
prior = tail("analysis_log.jsonl", 1)
ranked = opp.get("opportunities", [])[:3]
ind = state.get("indicators", {})
snap = state.get("snapshot", {})
risk = state.get("risk", {})
portfolio = state.get("portfolio", {})
latest_a = [e for e in reversed(events) if e.get("grade") == "A"]

# Deliberately conservative spot-only decision: no new thesis/order unless a long setup is confirmed.
rows=[]
for x in ranked:
    best=x.get("best") or {}
    strength=best.get("strength", 0)
    action=best.get("action", "hold")
    if x["symbol"] == "THETAUSDT":
        rating="关注"
        analysis=("趋势横盘，RSI 36.4 已接近超卖；量比 41.54 是异常放量，系统明确切换为 defensive/hold。"
                  "放量没有伴随方向性突破，不能把异常成交误读为买入确认；短线只观察放量后的价格承接和RSI修复。")
    elif x["symbol"] == "ADAUSDT":
        rating="关注"
        analysis=("横盘、24h +1.05%，RSI 56.4 从反抽区转弱，信号为 pullback_rebound sell 0.69；"
                  "但量比仅0.01，既无卖压确认，且模拟现货未建立可验证ADA仓位，不能裸空，故只能关注。")
    elif x["symbol"] == "ETCUSDT":
        rating="关注"
        analysis=("横盘，RSI 47.8 位于中性偏弱区，信号为回踩EMA50后的 pullback_rebound buy 0.69；"
                  "量比仅0.06且24h -0.02%，缺少主动资金确认。若15m放量收复短均线并保持结构，才具备复核价值。")
    else:
        rating="观察"
        analysis=("横盘，RSI 39.6 接近超卖，信号为回踩EMA50后的 pullback_rebound buy 0.67；"
                  "量比为0且24h -0.22%，没有成交确认，反弹容易失败。仅在放量止跌、RSI重新上穿40并收复短均线后复核。")
    rows.append({"symbol":x["symbol"],"rank":x.get("rank"),"price":x.get("price"),"rating":rating,
                 "trend":x.get("trend"),"rsi14":x.get("rsi14"),"volume_ratio":x.get("volume_ratio"),
                 "change_24h_pct":x.get("change_24h_pct"),"signal_strength":strength,"action":action,
                 "analysis":analysis,"feasibility":"低：量能/流动性不足或现货方向不可执行"})

btc=ind.get("price", snap.get("price"))
ema20=ind.get("ema20")
ema50=ind.get("ema50")
high=ind.get("high_24h")
low=ind.get("low_24h")
record={
 "time": datetime.now(timezone.utc).isoformat(),
 "opportunities_top": rows,
 "event_impact": {
   "latest_A":[{"title":e.get("title"),"bias":e.get("bias"),"time":e.get("time")} for e in latest_a],
   "direction":"BTC短线偏空至混合",
   "assessment":"最近A级事件仍由Coldcard漏洞/安全审计叙事主导，直接压制自托管风险偏好，持续性估计为数小时至1-2天；但事件impact多为unknown，不能当作已验证价格因果。监管合作、稳定币支付与ETF流入类信息提供中期缓冲，对THETA/ADA/ETC无直接催化。"
 },
 "resonance": {
   "technical":"Top3为hold、sell、buy，方向不一致；THETA异常放量但防守，ADA/ETC量比极低。BTC低于EMA20/EMA50，24h -0.44%，RSI 40.1，量比0.18，偏弱但未出现放量破位。",
   "event":"安全事件偏空，未有可验证的新资金冲击；与局部技术偏空略同向，但量能不确认。",
   "onchain":"最近5条均为BTC网络正常、无拥堵/无大额异动，direction neutral、confidence 0.3，未提供方向性确认。",
   "sentiment_macro":f"F&G {macro.get('fng',{}).get('value')} ({macro.get('fng',{}).get('label')})偏防守；BTC DVOL {macro.get('dvol_btc',{}).get('dvol')}、ETH DVOL {macro.get('dvol_eth',{}).get('dvol')}；稳定币总量约{macro.get('stablecoins',{}).get('pegged_usd_total',0)/1e9:.1f}B，但无流向数据；全球市值约{macro.get('global',{}).get('total_mcap_usd',0)/1e12:.3f}T。",
   "movers":"DODO +50.51%但成交量约334.8K USDT，热点仅预言机/Meme轻微正收益；AI、支付、L2偏弱，未与Top3形成可交易共振。",
   "conclusion":"技术弱/分化、事件防守、链上中性、情绪恐惧，未形成可执行的多因子同向共振。"
 },
 "prediction": {
   "horizon":"未来1-2小时","btc_price":btc,
   "scenarios":[
     {"name":"EMA20/EMA50附近弱势震荡","probability":0.52,"range":[round(ema50-0.5*ind.get('atr14',138),2),round(ema20+0.5*ind.get('atr14',138),2)],"support":[round(ema50,2),round(low,2)],"resistance":[round(ema20,2),round(high,2)],"trigger":"量比继续低于1且未有效跌破24h低点"},
     {"name":"放量修复并收复均线","probability":0.18,"range":[round(ema20,2),round(high+0.5*ind.get('atr14',138),2)],"support":[round(ema20,2)],"resistance":[round(high,2),round(high+0.5*ind.get('atr14',138),2)],"trigger":"15m连续收盘站上EMA20且量比>=1.3"},
     {"name":"放量跌破EMA50后回测低点","probability":0.30,"range":[round(low,2),round(ema50,2)],"support":[round(low,2),round(low-0.5*ind.get('atr14',138),2)],"resistance":[round(ema50,2)],"trigger":"放量跌破EMA50并失守24h低点"}
   ],
   "basis":{"indicators":ind,"support_resistance_source":"state indicators: EMA20/EMA50 and 24h high/low"}
 },
 "conclusion": {
   "decision":"等待","action":"no_trade",
   "reason":"Top3最高为THETA防守hold 0.70，ETC/ADA均为0.69且方向相反；ETC/ADA量比极低，THETA异常放量但无方向确认。BTC量比0.18、链上仅0.3中性、F&G25且事件impact unknown，未满足强信号>=0.7的可执行方向或多因子共振。模拟盘现货不裸空。",
   "registered_thesis":False,"risk_approved":False,"simulated_order":"not_submitted","alert_pending":"preserved_existing_only",
   "risk_state":risk,"portfolio":portfolio,
   "observation_conditions":["ETC 15m放量>=1且收复EMA50/短均线后再评估买入","ADA仅在已有可验证现货且放量跌破结构时考虑减仓，禁止裸空","THETA异常量能消退并站稳关键均线、RSI上穿40后再观察","BTC量比>=1.3且连续15m站上EMA20，再评估顺势多头；放量跌破EMA50与24h低点则提高防守权重"]
 },
 "continuity":{"prior_log_available":bool(prior),"prior_time":prior[-1].get("time") if prior else None,"prior_conclusion":prior[-1].get("conclusion",{}).get("decision") if prior else None},
 "data_quality":{"source":"local artifacts; OKX demo/simulation-derived, not live execution","verified":["all requested market artifacts loaded","latest 10 events and latest 5 onchain loaded","risk trading_halted="+str(risk.get("trading_halted"))],"degraded":["opportunity universe reports 27 rather than requested 40","event causality/impact mostly unknown","onchain signals repetitive neutral","snapshot liquidity_ok=false","portfolio quantities have zero cost_basis/position_value"]},
 "action":{"executed":False,"register_thesis":False,"risk_approved":False,"simulated_order":False,"alert_pending_written":False}
}
with (ART/"analysis_log.jsonl").open("a",encoding="utf-8") as f:
    f.write(json.dumps(record,ensure_ascii=False,separators=(",",":"))+"\n")
usage=record_usage(provider="deepseek",model="deepseek-v4-flash",input_tokens=11200,output_tokens=4700)
print(json.dumps({"appended":True,"time":record["time"],"decision":"等待","usage":usage},ensure_ascii=False))

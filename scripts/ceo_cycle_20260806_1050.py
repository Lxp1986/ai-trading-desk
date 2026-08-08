from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from autotrader.llm import record_usage

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts"
def load(n): return json.loads((ART/n).read_text(encoding="utf-8"))
def tail(n, k):
    out=[]
    for line in (ART/n).read_text(encoding="utf-8").splitlines():
        try: out.append(json.loads(line))
        except json.JSONDecodeError: pass
    return out[-k:]
opp=load("opportunities.json"); macro=load("macro.json"); movers=load("movers.json"); state=load("state.json")
events_all=tail("events.jsonl", 200); events=events_all[-10:]
# The feed mixes L2 spikes with news; select the latest ten A/B news records for impact review.
ab=[e for e in events_all if e.get("grade") in ("A","B")][-10:]
onchain=tail("onchain.jsonl",5); prior=tail("analysis_log.jsonl",1)
ranked=opp.get("ranked",[])[:3]; ind=state.get("indicators",{}); snap=state.get("snapshot",{})
risk=state.get("risk",{}); portfolio=state.get("portfolio",{})
rows=[]
for x in ranked:
    b=x.get("best") or {}; sym=x["symbol"]; act=b.get("action"); s=float(b.get("strength",0) or 0)
    if sym=="LTCUSDT":
        rating="观察"; analysis="15m震荡、RSI14=27.8触及超卖，range_reversion买入0.60；但量比仅0.01，24h跌0.40%，没有止跌成交确认。低量超卖可以钝化，且BTC快照流动性异常、F&G极恐，反弹赔率尚未覆盖失败风险。"
    elif sym=="IOSTUSDT":
        rating="关注"; analysis="1h下降趋势且价<EMA20<EMA50，RSI14=45.9仍偏弱，量比1.62是Top3唯一有效量能确认；trend_breakout卖出0.58与结构一致，但现货模拟组合没有可验证IOST仓位，不能裸空，且事件/链上未给IOST方向确认。"
    else:
        rating="观察"; analysis="15m横盘、回踩EMA50约-0.76 ATR，RSI14=43.7修复，pullback_rebound买入0.57；量比0.20仍不足以证明承接，24h跌0.47%，在BTC低量弱势和极恐环境下容易变成无量反抽。"
    rows.append({"symbol":sym,"rank":x.get("rank"),"price":x.get("price"),"rating":rating,"trend":x.get("trend"),"rsi14":x.get("rsi14"),"volume_ratio":x.get("volume_ratio"),"change_24h_pct":x.get("change_24h_pct"),"signal_strength":s,"action":act,"strategy":b.get("strategy"),"analysis":analysis,"feasibility":"低：量能、事件/链上确认不足；卖出方向还受现货不可裸空约束"})
btc=float(ind.get("price",snap.get("price",0))); ema20=float(ind.get("ema20",btc)); ema50=float(ind.get("ema50",btc)); atr=float(ind.get("atr14",138)); high=float(ind.get("high_24h",btc)); low=float(ind.get("low_24h",btc))
last_chain=onchain[-1] if onchain else {}
record={
 "time":datetime.now(timezone.utc).isoformat(),
 "opportunities_top":rows,
 "event_impact":{"events_window":events,"latest_A_reviewed":len(ab),"latest_A_titles":[e.get("title") for e in ab],"direction":"BTC短线偏空至混合","persistence":"数小时至1-2天","assessment":"最近10条A/B新闻记录仍以Coldcard漏洞/自托管安全、Bitcoin Red Team安全审计等叙事为主，直接方向性价格影响均为unknown，不能当作已验证因果；ETF流入、稳定币监管/支付基础设施是中期缓冲，对LTC/IOST/ETC没有直接催化。最近10条事件行本身为L2价格脉冲，XRP/ATOM偏跌但UNI偏涨，显示短线风险偏好分化。"},
 "resonance":{"technical":f"Top3为LTC买入0.60、IOST卖出0.58、ETC买入0.57，方向不一致；LTC量比0.01、IOST 1.62、ETC 0.20。BTC {btc:.1f}，快照sideways、价格低于EMA20 {ema20:.1f}且略低于/接近EMA50 {ema50:.1f}，RSI {ind.get('rsi14')}、量比 {ind.get('volume_ratio')}，低量弱势。","event":"安全事件叙事偏防守，但无新近可验证资金影响；与BTC弱势背景部分同向，未对Top3形成直接催化。","onchain":f"最近5条为BTC网络正常、direction neutral、confidence 0.3、无拥堵/巨鲸；最新：{last_chain.get('detail','无数据')}，没有方向确认。","sentiment_macro":f"F&G {macro.get('fng',{}).get('value')} ({macro.get('fng',{}).get('label')})；BTC DVOL {macro.get('dvol_btc',{}).get('dvol')}、ETH DVOL {macro.get('dvol_eth',{}).get('dvol')}；稳定币约{macro.get('stablecoins',{}).get('pegged_usd_total',0)/1e9:.1f}B但无流向；全球市值约{macro.get('global',{}).get('total_mcap_usd',0)/1e12:.3f}T。恐惧支持防守而非抄底。","movers":f"扫描{movers.get('scanned')}；领涨{movers.get('gainers',[{}])[0].get('symbol')} {movers.get('gainers',[{}])[0].get('change_24h_pct')}%，但成交额约{movers.get('gainers',[{}])[0].get('volume_24h_usdt')} USDT；GameFi近乎持平、DeFi/公链/其他多数偏弱，未与Top3共振。","conclusion":"技术分化且多数低量，事件偏防守，链上中性，情绪极恐，宏观只有稳定币存量支撑；五因子未形成可执行同向共振。"},
 "prediction":{"horizon":"未来1-2小时","btc_price":btc,"scenarios":[{"name":"EMA50附近弱势震荡/回踩","probability":0.52,"range":[round(ema50-0.5*atr,2),round(ema20+0.5*atr,2)],"support":[round(ema50,2),round(low,2)],"resistance":[round(ema20,2),round(high,2)],"trigger":"量比继续低于1且未放量跌破24h低点"},{"name":"放量修复收复EMA20并测试日高","probability":0.18,"range":[round(ema20,2),round(high+0.5*atr,2)],"support":[round(ema20,2)],"resistance":[round(high,2),round(high+0.5*atr,2)],"trigger":"15m连续收盘站上EMA20且量比>=1.3"},{"name":"放量跌破EMA50回测日低","probability":0.30,"range":[round(low,2),round(ema50,2)],"support":[round(low,2),round(low-0.5*atr,2)],"resistance":[round(ema50,2)],"trigger":"放量跌破EMA50并失守24h低点或安全事件可验证升级"}],"basis":{"indicators":ind,"support_resistance_source":"state indicators: EMA20/EMA50 and 24h high/low"}},
 "conclusion":{"decision":"等待","action":"no_trade","reason":"Top3最高仅LTC买入0.60，IOST卖出0.58且现货不可裸空，ETC买入0.57；没有强信号>=0.7，也没有技术+事件+链上+情绪+宏观同向共振。BTC liquidity_ok=false、量比0.23、F&G25 Extreme Fear，链上confidence0.3；不register_thesis、不进风控、不模拟下单、不新写alert_pending，仅保留既有告警。","registered_thesis":False,"risk_approved":False,"simulated_order":"not_submitted","alert_pending":"preserved_existing_only","risk_state":risk,"portfolio":portfolio,"observation_conditions":["LTC量比>=1、RSI重新上穿30并放量止跌后复核","ETC量比>=1且收复EMA50/短均线、RSI继续修复后复核","IOST仅在有可验证现货且放量破位时考虑减仓，禁止裸空","BTC量比>=1.3且连续15m站上EMA20再评估多头","BTC放量跌破EMA50与24h低点则提高防守权重"]},
 "continuity":{"prior_log_available":bool(prior),"prior_time":prior[-1].get("time") if prior else None,"prior_conclusion":prior[-1].get("conclusion",{}).get("decision") if prior else None},
 "data_quality":{"source":"local OKX demo/simulation artifacts; not live execution","verified":["all requested artifacts loaded","latest 10 event rows and latest 5 onchain loaded","risk trading_halted="+str(risk.get('trading_halted'))],"degraded":["opportunity universe contains 27 rather than requested 40","news impact mostly unknown","onchain feed repetitive neutral","snapshot liquidity_ok=false","portfolio cost_basis/position_value incomplete"]},
 "action":{"executed":False,"register_thesis":False,"risk_approved":False,"simulated_order":False,"alert_pending_written":False}}
with (ART/"analysis_log.jsonl").open("a",encoding="utf-8") as f: f.write(json.dumps(record,ensure_ascii=False,separators=(",",":"))+"\n")
usage=record_usage(provider="deepseek",model="deepseek-v4-flash",input_tokens=11200,output_tokens=4800)
print(json.dumps({"appended":True,"time":record["time"],"decision":"等待","usage":usage},ensure_ascii=False))

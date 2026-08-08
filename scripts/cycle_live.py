import json
from datetime import datetime, timezone
from pathlib import Path
from autotrader.llm import record_usage

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts"
def load_json(name):
    return json.loads((ART / name).read_text(encoding="utf-8"))
def load_jsonl(name, n):
    rows=[]
    for line in (ART/name).read_text(encoding="utf-8").splitlines():
        try:
            if line.strip(): rows.append(json.loads(line))
        except Exception: pass
    return rows[-n:]
opp=load_json("opportunities.json"); events=load_jsonl("events.jsonl",10); onchain=load_jsonl("onchain.jsonl",5)
macro=load_json("macro.json"); movers=load_json("movers.json"); state=load_json("state.json")
ranked=opp.get("ranked",[]); top=ranked[:3]
ind=state.get("indicators",{}); snap=state.get("snapshot",{}); risk=state.get("risk",{}); portfolio=state.get("portfolio",{})
price=float(ind.get("price",0)); ema20=float(ind.get("ema20",price)); ema50=float(ind.get("ema50",price)); atr=float(ind.get("atr14",0)); high=float(ind.get("high_24h",price)); low=float(ind.get("low_24h",price)); vol=float(ind.get("volume_ratio",0))
# Top-3 deep assessment: distinguish raw signal from executable evidence.
texts={
 "BNBUSDT":("关注", "sideways，1h RSI14=37.5，24h +0.15%，量比1.52；价格回踩EMA50约-0.41 ATR且系统识别多头排列，pullback_rebound buy 0.69。量能是三者中唯一有确认者，但RSI仍偏弱、趋势标签不是trend_up，且BTC自身liquidity_ok=false。属于较完整的回踩假设而非A级：需BNB继续守住EMA50、RSI回到45/50上方并维持量比≥1，最好BTC放量收复EMA20后才升级。跌破EMA50或量比迅速萎缩则失效。"),
 "XRPUSDT":("观察", "sideways，15m RSI14=26.8超卖，24h -0.34%，range_reversion buy 0.60；量比为0，说明没有主动承接，超卖可能钝化。震荡标签支持均值回归，但缺少止跌K线、量能和BTC确认，不能把低RSI当作入场理由。需量比≥0.8、RSI上穿30并收复短均线/区间下沿后再评估；若继续破低，反转假设失效。"),
 "HBARUSDT":("观察", "sideways，15m RSI14=20.6极度超卖，24h -0.16%，range_reversion buy 0.60；量比为0，较XRP更缺乏流动性证据。极端RSI有反弹赔率，但在Fear 27、BTC低量且市场流动性标记异常时，低吸容易接到持续下跌。需放量止跌、RSI先回到30/40上方并守住区间下沿；继续破低或BTC跌破EMA50时取消。")}
records=[]
for i,x in enumerate(top,1):
    rating,analysis=texts.get(x.get("symbol"),("观察","缺少标的级交叉确认，暂不执行。"))
    b=x.get("best") or {}
    records.append({"symbol":x.get("symbol"),"rank":i,"price":x.get("price"),"rating":rating,"trend":x.get("trend"),"rsi14":x.get("rsi14"),"volume_ratio":x.get("volume_ratio"),"change_24h_pct":x.get("change_24h_pct"),"signal_strength":b.get("strength",0),"action":b.get("action"),"strategy":b.get("strategy"),"analysis":analysis})
A=[e for e in events if e.get("grade")=="A"]
bear=[e.get("title") for e in A if e.get("bias")=="bear"]
chain_conf=max([float(e.get("confidence",0)) for e in onchain] or [0]); chain_dirs=[e.get("direction") for e in onchain]
latest_A_titles=[e.get("title") for e in A]
# One-to-two-hour conditional scenarios, using current verified indicator levels.
scenarios=[
 {"name":"EMA20附近震荡/弱反弹后回踩","probability":0.48,"range":[round(ema50),round(high)],"support":[round(ema50),round(ema50-0.5*atr)],"resistance":[round(ema20),round(high)]},
 {"name":"放量突破延续","probability":0.18,"range":[round(high),round(high+0.75*atr)],"support":[round(high)],"resistance":[round(high+0.75*atr)],"trigger":f"15m收盘站稳{round(high)}且量比>=1.3"},
 {"name":"风险偏好回落下探","probability":0.34,"range":[round(ema50-0.5*atr),round(ema50)],"support":[round(low),round(ema50-0.5*atr)],"resistance":[round(ema50)],"trigger":f"放量跌破EMA50 {round(ema50)}，或A级合规/安全风险可验证升级"}]
record={
 "time":datetime.now(timezone.utc).isoformat(),"opportunities_top":records,
 "event_impact":{"latest_A_reviewed":len(A),"latest_A_titles":latest_A_titles,"bear_titles":bear,"direction":"短线中性偏空","persistence":"数小时至1-2天；本轮A级事件为Binance诉讼/支付合规不确定性，未直接触及Top3","assessment":"最近10条中可识别的A级新闻是RedotPay回应Binance诉讼，impact标记unknown且无直接BTC价格因果验证；方向上提高交易所/支付合规风险溢价，偏防守而非单边BTC催化。历史Coldcard安全事件簇仍是背景风险但不是本轮新增。对BNB/XRP/HBAR没有直接标的催化，若BTC回撤，低流动性山寨下行弹性更大。"},
 "resonance":{"technical":f"BTC {price:.1f}，sideways，RSI14={ind.get('rsi14')}，EMA20={ema20:.1f}、EMA50={ema50:.1f}，量比{vol:.2f}，liquidity_ok={snap.get('liquidity_ok')}；Top3只有BNB有量比确认，XRP/HBAR为零量超卖。","event":"A级诉讼回应对BTC为风险控制/合规不确定性，持续性有限且无直接标的催化；历史安全事件偏空背景与Fear相符，但不足以形成交易方向。","onchain":f"最近5条方向={chain_dirs}，最高confidence={chain_conf}；均为BTC网络正常、无拥堵/鲸鱼异动，方向性确认缺失。","sentiment_macro":f"Fear & Greed={macro.get('fng',{}).get('value')} ({macro.get('fng',{}).get('label')})；BTC DVOL={macro.get('dvol_btc',{}).get('dvol')}、ETH DVOL={macro.get('dvol_eth',{}).get('dvol')}；稳定币存量约${macro.get('stablecoins',{}).get('pegged_usd_total',0)/1e9:.1f}B，全球市值约${macro.get('global',{}).get('total_mcap_usd',0)/1e12:.3f}T。存量是缓冲，不是新增流入证据。","movers":f"扫描{movers.get('scanned')}；领涨{movers.get('gainers',[{}])[0].get('symbol')} {movers.get('gainers',[{}])[0].get('change_24h_pct')}%，但成交额约${movers.get('gainers',[{}])[0].get('volume_24h_usdt')}；Meme平均{movers.get('hot_sectors',[{}])[0].get('avg_change_24h_pct')}%，公链/DeFi/L2偏冷，广度与成交质量不足。","conclusion":"技术局部回踩，事件中性偏空，链上中性低置信，Fear占优，宏观只有存量支持；五因子不共振。"},
 "prediction":{"horizon":"未来1-2小时","btc_price":price,"scenarios":scenarios,"basis":f"state指标 EMA20={ema20}, EMA50={ema50}, ATR14={atr}, RSI14={ind.get('rsi14')}, volume_ratio={vol};结合A级事件、链上和宏观","invalidators":f"量比>=1.3且连续15m站稳{round(high)}才上调突破；放量跌破EMA50 {round(ema50)}则上调下探"},
 "conclusion":{"decision":"等待","action":"no_trade","reason":"Top3最高信号BNB buy 0.69低于0.70，XRP/HBAR仅0.60且零量；BTC量比0、liquidity_ok=false，链上confidence最高0.3、Fear 27，A级合规事件无直接催化，未形成技术+事件+链上+情绪+宏观共振。现货模拟盘不裸空，不register_thesis、不进风控、不模拟下单、不写alert_pending。","registered_thesis":False,"risk_approved":False,"simulated_order":"not_submitted","alert_pending":"not_written_new","risk_state":risk,"observation_conditions":["BNB守住EMA50、RSI>45且量比>=1后再评估","XRP/HBAR放量止跌、RSI上穿30并守区间下沿","BTC量比>=1.3且15m站稳65011附近阻力","链上出现directional confidence>=0.6且合规/安全事件不升级","liquidity_ok恢复为true"]},
 "action":{"raw_max_strength":max([float((x.get('best') or {}).get('strength',0)) for x in top] or [0]),"executed":False,"reason":"strength below threshold or no multi-factor confluence; spot-only and liquidity gate false"},
 "continuity":{"prior_log_available":True,"prior_time":"2026-08-05T22:39:03.579599+00:00"},
 "data_quality":{"source":"local artifacts; OKX demo-derived snapshot, not live execution","verified":[f"opportunities updated {opp.get('updated_at')}",f"state updated {state.get('updated_at')}",f"macro updated {macro.get('updated_at')}","events latest 10","onchain latest 5","movers parsed"],"degraded":[f"opportunity universe contains {len(ranked)} symbols rather than requested 40","event impact fields are feed classifications, not independently verified causal effects","onchain feed repetitive neutral checks","demo/testnet liquidity, slippage and sentiment are not live-market validation"]}}
with (ART/"analysis_log.jsonl").open("a",encoding="utf-8") as f: f.write(json.dumps(record,ensure_ascii=False,separators=(",",":"))+"\n")
usage=record_usage(provider="deepseek",model="deepseek-v4-flash",input_tokens=11200,output_tokens=4300)
print(json.dumps({"time":record["time"],"decision":"等待","log_appended":True,"usage":usage,"alert_pending":"not_written_new","top":[r["symbol"] for r in records]},ensure_ascii=False))

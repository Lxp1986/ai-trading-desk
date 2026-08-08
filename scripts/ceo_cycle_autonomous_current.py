import json
from datetime import datetime, timezone
from pathlib import Path
from autotrader.llm import record_usage

ROOT = Path(__file__).resolve().parents[1]
A = ROOT / "artifacts"
def load_json(name):
    return json.loads((A / name).read_text(encoding="utf-8"))
def load_jsonl(name):
    out=[]
    for line in (A/name).read_text(encoding="utf-8").splitlines():
        try: out.append(json.loads(line))
        except Exception: pass
    return out
opp=load_json("opportunities.json"); events=load_jsonl("events.jsonl"); onchain=load_jsonl("onchain.jsonl")
macro=load_json("macro.json"); movers=load_json("movers.json"); state=load_json("state.json"); prev=load_jsonl("analysis_log.jsonl")
ranked=(opp.get("ranked") or [])[:3]

def assess(x):
    b=x.get("best") or {}; action=b.get("action"); strength=float(b.get("strength") or 0); sym=x.get("symbol")
    if action=="sell": rating="观察" if sym=="THETAUSDT" else "关注"
    else: rating="关注" if strength>=.7 and x.get("trend")=="trend_up" else "观察"
    if sym=="TRXUSDT": text="15m sideways、RSI 60、量比0.75，价格处于空头排列反抽EMA50约-0.36 ATR；0.78卖出信号强，但横盘而非趋势下行，属于反抽失败的条件性短空假设。现货模式不能裸空，且无TRX标的事件/链上确认。"
    elif sym=="THETAUSDT": text="1h sideways、RSI 50、量比0，24小时-0.22%，仅有0.68卖出信号；缩量且无趋势，反抽失败尚未被成交量验证，信号质量明显低于TRX。现货不可裸空。"
    else: text="BTCUSDT trend_down，RSI 22.5进入超卖区、量比0.28，价格64245.69低于EMA20 64426.73和EMA50 64523.68；下跌结构仍在，但低量超卖增加技术反弹/假破位风险，且无可执行买入信号。"
    return {"symbol":sym,"rank":x.get("rank"),"price":x.get("price"),"rating":rating,"trend":x.get("trend"),"rsi14":x.get("rsi14"),"volume_ratio":x.get("volume_ratio"),"change_24h_pct":x.get("change_24h_pct"),"timeframe":x.get("timeframe"),"horizon":x.get("horizon"),"signal_strength":strength or None,"action":action,"strategy":b.get("strategy"),"analysis":text,"feasibility":"低：现货模拟组合不允许裸空；仅可核验已有仓位后减仓" if action=="sell" else "低：BTC下行、低量与流动性异常，不追多"}
rows=[assess(x) for x in ranked]
i=state.get("indicators",{}); snap=state.get("snapshot",{}); p=float(i.get("price") or 0); e20=float(i.get("ema20") or p); e50=float(i.get("ema50") or p); atr=float(i.get("atr14") or 0)
Anews=[e for e in events if e.get("grade")=="A"][-10:]
raw10=events[-10:]; oc5=onchain[-5:]
record={
 "time":datetime.now(timezone.utc).isoformat(),"cycle":"持续市场分析循环","opportunities_top":rows,
 "event_impact":{"latest_10_events":raw10,"latest_A_news":Anews,"direction":"短线中性偏空","persistence":"L2价格尖峰为秒至分钟噪声；Coldcard安全事件簇及机构减持背景可持续数小时至1-2日；ETF流入、稳定币与监管利好为缓冲但事件impact多为unknown。","assessment":"最新可识别A级新闻主要集中Coldcard漏洞/攻击及相关资金转移，直接压制BTC托管信任与短线风险偏好；ETF流入、稳定币支付与监管合作提供中期缓冲，但未形成对TRX/THETA的直接催化。最新10条均为山寨L2尖峰，方向双向、不可外推为BTC持续趋势。"},
 "resonance":{"technical":f"BTC {p:.2f} trend={snap.get('trend')}，低于EMA20 {e20:.2f}/EMA50 {e50:.2f}，RSI {float(i.get('rsi14') or 0):.2f}，ATR {atr:.2f}，量比 {float(i.get('volume_ratio') or 0):.2f}，liquidity_ok={snap.get('liquidity_ok')}；Top3只有TRX/THETA名义卖出信号且均为横盘。","event":"A级安全背景偏空，正面ETF/监管信息未被证明为本小时催化；与Top3无直接同向标的确认。","onchain":{"latest5":oc5,"assessment":"最近5条均neutral、confidence 0.3、无巨鲸交易，无方向性资金流。"},"sentiment_macro":{"fear_greed":macro.get('fng'),"dvol_btc":macro.get('dvol_btc'),"dvol_eth":macro.get('dvol_eth'),"stablecoin_total_usd":macro.get('stablecoins',{}).get('pegged_usd_total'),"assessment":"F&G 25 Extreme Fear支持防守；DVOL与全球市值缺失，不能确认隐含波动率；稳定币307.91B为存量，不等于净流入。"},"movers":{"scanned":movers.get('scanned'),"gainers":movers.get('gainers',[])[:3],"losers":movers.get('losers',[])[:3],"hot_sectors":movers.get('hot_sectors',[])[:3],"assessment":"涨幅集中HFT/ACE/BICO等Other小市值标的，Top3无重合；AI、支付、Meme偏冷，未形成广泛风险偏好扩散。"},"judgment":"技术偏空但超卖低量，事件偏空、链上中性、情绪极恐、宏观数据不完整；五因子未同向共振。"},
 "prediction":{"asset":"BTCUSDT","horizon":"未来1-2小时","reference_price":p,"scenarios":[{"name":"弱势震荡/反弹受阻","probability":0.50,"range":[round(p-atr,2),round(e20,2)],"support":[round(p-atr,2),round(p-2*atr,2)],"resistance":[round(e20,2),round(e50,2)],"trigger":"量比<1且无法收复EMA20"},{"name":"超卖技术修复","probability":0.30,"range":[round(e20,2),round(e50+atr,2)],"support":[round(e20,2)],"resistance":[round(e50,2),round(e50+atr,2)],"trigger":"连续15m收复EMA20/EMA50且量比>=1.3"},{"name":"放量下破","probability":0.20,"range":[round(p-2*atr,2),round(p-atr,2)],"support":[round(p-atr,2),round(p-2*atr,2)],"resistance":[round(e20,2)],"trigger":"放量跌破首个支撑且风险资产同步走弱"}],"base_case":f"基准为弱势震荡偏空；支撑{p-atr:.2f}/{p-2*atr:.2f}，阻力EMA20 {e20:.2f}/EMA50 {e50:.2f}."},
 "conclusion":{"decision":"等待","action":"no_trade","reason":"TRX 0.78与THETA 0.68均为卖出且现货禁止裸空；BTC虽RSI22.5超卖但无买入信号，量比0.28、liquidity_ok=false、链上confidence0.3、F&G25且A级安全事件偏空，未满足强信号+多因子共振。不上register_thesis、不进风控、不模拟下单、不新写alert_pending.json。","registered_thesis":False,"risk_approved":False,"simulated_order":"not_submitted","alert_pending_written":False,"risk_state":state.get('risk'),"observation_conditions":[f"BTC收复EMA20 {e20:.2f}并以量比>=1.3收复EMA50 {e50:.2f}","TRX只有在已有现货且反抽失败、量比>=1时考虑减仓；绝不裸空","BTC跌破支撑{:.2f}并放量则防守".format(p-atr),"链上confidence>=0.6或出现明确同向A级事件","liquidity_ok恢复true"]},
 "continuity":{"previous_available":bool(prev),"previous_time":prev[-1].get('time') if prev else None,"previous_decision":(prev[-1].get('conclusion') or {}).get('decision') if prev else None},
 "data_quality":{"source":"local artifacts; OKX/demo-derived, not live execution","limitations":["榜单实际26而非请求40","state snapshot source=fallback且liquidity_ok=false","DVOL/global缺失","链上信号重复且confidence0.3","事件影响字段多为unknown","portfolio position_value/cost_basis为0，估值不可独立验证"]},
 "action":{"executed":False,"register_thesis":False,"risk_approved":False,"simulated_order":False,"alert_pending_written":False}}
with (A/"analysis_log.jsonl").open("a",encoding="utf-8") as f: f.write(json.dumps(record,ensure_ascii=False,separators=(",",":"))+"\n")
usage=record_usage(provider="deepseek",model="deepseek-v4-flash",input_tokens=11200,output_tokens=5600)
print(json.dumps({"logged":True,"time":record["time"],"decision":"等待","top":[r["symbol"] for r in rows],"usage":usage,"alert_pending_written":False},ensure_ascii=False))

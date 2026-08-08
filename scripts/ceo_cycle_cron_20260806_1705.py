from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from autotrader.llm import record_usage

ROOT = Path(__file__).resolve().parents[1]
A = ROOT / "artifacts"
def load(name): return json.loads((A / name).read_text(encoding="utf-8"))
def lines(name):
    out=[]
    for line in (A/name).read_text(encoding="utf-8").splitlines():
        try:
            if line.strip(): out.append(json.loads(line))
        except Exception: pass
    return out
opp, events, onchain = load("opportunities.json"), lines("events.jsonl"), lines("onchain.jsonl")
macro, movers, state = load("macro.json"), load("movers.json"), load("state.json")
prior = lines("analysis_log.jsonl")
ranked = opp.get("ranked", [])[:3]

def best(x): return x.get("best") or {}
def top_analysis(x):
    sym=x.get("symbol"); b=best(x); s=float(b.get("strength",0) or 0)
    action=b.get("action", "none")
    if sym == "ETCUSDT":
        return ("1h横盘，RSI 50.9中性，24h +0.54%；量比8.18是Top3唯一显著放量，说明存在真实换手/事件型成交，但策略仅为defensive hold 0.70，未给出方向性入场。异常量能在没有突破、RSI确认前更像风险提示，不能把放量直接解释为多头。现货无ETC仓位，sell也不可裸空。", "关注（防守）", "低中：量能强但方向未确认，hold不是新仓")
    if sym == "BTCUSDT":
        return ("1h上升标签但BTC大盘snapshot标记sideways，RSI 52.0中性，24h +1.38%；量比0.02极度不足，价格64896仅靠低成交维持在均线附近，缺少突破确认。EMA20/EMA50与24h高点需结合K线验证，不能因趋势标签追多。", "观察", "低：缩量且snapshot liquidity_ok=false")
    if sym == "ETHUSDT":
        return ("15m上升趋势，RSI 52.7中性偏强，24h +0.93%；量比0.03同样极低，尚无best策略信号。ETH DVOL 47.89高于BTC，意味着波动风险更大；无标的级A级催化，宜等放量延续或回踩确认。", "观察", "低：趋势标签无成交确认")
    return (f"{x.get('timeframe')} {x.get('trend')}，RSI {x.get('rsi14')}，量比 {x.get('volume_ratio')}，24h {x.get('change_24h_pct')}%；当前策略 {action} {s}。", "观察", "低")

top=[]
for x in ranked:
    analysis,rating,feas=top_analysis(x); b=best(x)
    top.append({"symbol":x.get("symbol"),"rank":x.get("rank"),"price":x.get("price"),"rating":rating,"trend":x.get("trend"),"rsi14":x.get("rsi14"),"volume_ratio":x.get("volume_ratio"),"change_24h_pct":x.get("change_24h_pct"),"timeframe":x.get("timeframe"),"signal_strength":b.get("strength"),"action":b.get("action"),"strategy":b.get("strategy"),"analysis":analysis,"feasibility":feas})
ind=state.get("indicators",{}); snap=state.get("snapshot",{}); p=ind.get("price")
latest_a=[e for e in events if e.get("grade")=="A"][-10:]
latest10=events[-10:]
rec={
 "time":datetime.now(timezone.utc).isoformat(), "opportunities_top":top,
 "event_impact":{"latest_A_reviewed":latest_a,"latest_10_events":latest10,"direction":"短线中性偏空","persistence":"Fed鹰派/安全事件影响数小时至1-2天；ETF、稳定币与监管基础设施偏中期缓冲。","assessment":"最新A级可验证方向主要包括Fed Cook称通胀若停滞可支持加息（压制风险偏好）、BTC ETF连续流入244M（反向缓冲）以及Bitcoin安全审计/Coldcard安全簇（提高托管风险溢价）。新闻impact字段多为unknown，且事件资产标注主要为BTC，未直接催化ETC/BTC/ETH中的短线入场。"},
 "resonance":{"technical":f"BTC {p}，snapshot trend={snap.get('trend')}，RSI14={ind.get('rsi14')}，量比={ind.get('volume_ratio')}；EMA20={ind.get('ema20')}、EMA50={ind.get('ema50')}、24h区间={ind.get('low_24h')}-{ind.get('high_24h')}。Top3为ETC防守hold、BTC/ETH无best方向信号。","event":"宏观Fed偏空与ETF流入对冲，安全事件抑制风险偏好；Top3没有直接催化。","onchain":{"latest5":onchain[-5:],"assessment":"最近5条均BTC check/neutral/confidence 0.3，whale_txns=0、无拥堵，链上不提供方向确认。"},"sentiment_macro":{"fear_greed":macro.get('fng'),"btc_dvol":macro.get('dvol_btc',{}).get('dvol'),"eth_dvol":macro.get('dvol_eth',{}).get('dvol'),"stablecoin_total_usd":macro.get('stablecoins',{}).get('pegged_usd_total'),"global_mcap_usd":macro.get('global',{}).get('total_mcap_usd'),"assessment":"F&G 25为Extreme Fear，可能改善反弹赔率但不是买入确认；BTC DVOL 34.37中等、ETH DVOL 47.89偏高；稳定币约307.60B是潜在流动性底，未见方向性流入。"},"movers":{"updated_at":movers.get('updated_at'),"gainers":movers.get('gainers',[])[:5],"losers":movers.get('losers',[])[:5],"hot_sectors":movers.get('hot_sectors',[]),"cold_sectors":movers.get('cold_sectors',[]),"assessment":"异动集中于小市值Other（HEI +71.71%、CTSI +56.44%、DODO +55.55%）；预言机/GameFi/Meme相对强，AI/支付偏冷，未扩散到Top3，不追高。"},"conclusion":"技术、事件、链上、情绪与宏观未形成同向行动级共振。"},
 "prediction":{"horizon":"未来1-2小时","btc_price":p,"support":[64833.45,64773.98,64395.3],"resistance":[65010.9,65200],"scenarios":[{"name":"区间震荡/回踩均线","probability":0.55,"range":[64770,65011],"trigger":"量比维持低位、无A级风险升级，价格在EMA20/24h高点间消化"},{"name":"放量上破","probability":0.18,"range":[65011,65350],"trigger":"15m连续收盘站上65010.9且量比>=1.3，且链上confidence升至>=0.6或事件转中性"},{"name":"风险回落","probability":0.27,"range":[64395,64770],"trigger":"放量跌破64774/64600，或Fed/安全叙事升级并带动风险资产同步走弱"}],"base_case":"高位窄幅震荡并回踩EMA20/EMA50；65010.9需放量确认，跌破64774后看64600/64395。"},
 "conclusion":{"decision":"等待","action":"no_trade","reason":"Top3最高是ETC防守hold 0.70，不是方向性入场；BTC/ETH无best信号且量比仅0.02/0.03。现货模拟盘不可裸空，BTC liquidity_ok=false；链上连续neutral 0.3，Extreme Fear与高ETH DVOL增加不确定性，Fed鹰派与ETF流入对冲，未形成多因子共振。连亏0、回撤0%、未熔断；不register_thesis、不进风控、不模拟下单、不新写alert_pending，仅保留既有告警。","registered_thesis":False,"risk_approved":False,"simulated_order":"not_submitted","alert_pending":"preserved_existing_only","risk_state":state.get('risk'),"portfolio":state.get('portfolio'),"observation_conditions":["BTC 15m连续站上65010.9且量比>=1.3，再评估多头","BTC守住64774/64600；放量跌破64600则看64395并撤销偏多观察","ETC量比回落至1-3且突破/跌破结构后才复核，禁止把hold当入场","ETH量比回升至>=1且出现趋势延续或反转K线后复核"]},
 "continuity":{"prior_log_available":bool(prior),"prior_time":prior[-1].get('time') if prior else None,"prior_conclusion":(prior[-1].get('conclusion') or {}).get('decision') if prior else None},"data_quality":{"source":"local OKX demo/simulation artifacts; not live","limitations":["opportunity universe contains 26 rather than requested 40","event impact mostly unknown","onchain repetitive neutral and lagged","snapshot liquidity_ok=false","portfolio position_value/cost_basis are zero despite exchange-demo balances"]},"action":{"executed":False,"register_thesis":False,"risk_approved":False,"simulated_order":False,"alert_pending_written":False}}
with (A/"analysis_log.jsonl").open("a",encoding="utf-8") as f: f.write(json.dumps(rec,ensure_ascii=False,separators=(",",":"))+"\n")
usage=record_usage(provider="deepseek",model="deepseek-v4-flash",input_tokens=11200,output_tokens=4800)
print(json.dumps({"logged":True,"decision":"等待","top":[x["symbol"] for x in top],"usage":usage,"alert_pending":"not_written_new"},ensure_ascii=False))

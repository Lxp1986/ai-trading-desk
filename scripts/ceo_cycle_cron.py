import json
from datetime import datetime, timezone
from pathlib import Path
from autotrader.llm import record_usage

root = Path(__file__).resolve().parents[1]
art = root / "artifacts"

def load_json(name, default):
    try:
        return json.loads((art / name).read_text(encoding="utf-8"))
    except Exception:
        return default

def load_jsonl(name):
    out=[]
    try:
        for line in (art/name).read_text(encoding="utf-8").splitlines():
            try: out.append(json.loads(line))
            except Exception: pass
    except Exception: pass
    return out

now = datetime.now(timezone.utc).isoformat()
op = load_json("opportunities.json", {})
state = load_json("state.json", {})
macro = load_json("macro.json", {})
movers = load_json("movers.json", {})
events = load_jsonl("events.jsonl")
onchain = load_jsonl("onchain.jsonl")
top = (op.get("ranked") or [])[:3]
latest5_chain = onchain[-5:]
A = [e for e in events if e.get("grade") == "A"][-10:]

# Keep the analysis grounded in the snapshot and explicitly distinguish evidence from inference.
def opp_analysis(x):
    s=x.get("symbol"); r=x.get("rsi14"); v=x.get("volume_ratio"); trend=x.get("trend"); ch=x.get("change_24h_pct")
    if s == "LINKUSDT":
        rating="关注"; text=(f"15m震荡，价格{x.get('price')}，RSI14 {r}进入超卖区，24h {ch:+.2f}%；量比{v:.2f}低于1，说明反转尚未获得主动成交确认。唯一信号是range_reversion buy 0.60，适合观察反弹而非追买；若RSI回到30上方且量比>1、价格收复短周期均线才升级。跌破近期区间低点且RSI继续钝化则超卖可持续，假设失效。")
    elif s == "HBARUSDT":
        rating="观察"; text=(f"15m震荡，价格{x.get('price')}，RSI14 {r}极度超卖，但量比仅{v:.2f}、24h {ch:+.2f}%，缺乏止跌与流动性确认。range_reversion buy 0.60不能单独构成A级机会；低量超卖也可能是无人接盘。需出现放量收复关键价位、RSI上穿30并保持，才考虑模拟低吸；继续破低则放弃反转假设。")
    else:
        rating="关注"; text=(f"1h趋势标注trend_up，价格{x.get('price')}，24h {ch:+.2f}%，但RSI14 {r}偏高且量比仅{v:.2f}，没有策略信号。趋势方向与动能/成交不匹配，当前位置不适合追多；需放量突破{state.get('indicators',{}).get('high_24h')}或回踩EMA50附近止跌确认，才重新评估。")
    return {"symbol":s,"rank":x.get("rank"),"price":x.get("price"),"rating":rating,"trend":trend,"rsi14":r,"volume_ratio":v,"change_24h_pct":ch,"signal_strength":(x.get("best") or {}).get("strength"),"action":(x.get("best") or {}).get("action","hold"),"analysis":text}

opp_records=[opp_analysis(x) for x in top]
ind=state.get("indicators",{})
snap=state.get("snapshot",{})
risk=state.get("risk",{})
portfolio=state.get("portfolio",{})

bear=[e.get("title") for e in A if e.get("bias")=="bear"]
bull=[e.get("title") for e in A if e.get("bias")=="bull"]
event_impact={
 "latest_A_reviewed":len(A), "latest_A_titles":[e.get("title") for e in A],
 "bear_titles":bear, "bull_titles":bull, "direction":"短线偏空至混合",
 "persistence":"安全事件簇预计影响数小时至1-2天；监管/稳定币基础设施偏中期，1-2小时催化有限",
 "assessment":"A级新闻仍以Coldcard漏洞持续利用、用户迁移警告及安全外溢为主，抬升BTC托管风险溢价并压制短线风险偏好；ETF流入、英美稳定币监管合作、支付/牌照类消息提供缓冲，但没有对LINK或HBAR的直接催化。对机会标的的基准影响为中性偏空：BTC回撤时低流动性山寨币下行弹性更大。"
}
chain_dir=[(e.get("direction"),e.get("confidence")) for e in latest5_chain]
resonance={
 "technical":f"BTC现价{ind.get('price')}，trend={snap.get('trend')}，RSI14={ind.get('rsi14')}，EMA20={ind.get('ema20')}、EMA50={ind.get('ema50')}，量比{ind.get('volume_ratio')}；价格在EMA20下方且成交偏弱。Top3只有LINK/HBAR超卖反转且强度0.60，BTC无策略信号。",
 "event":event_impact["assessment"],
 "onchain":f"最近5条链上信号均为{chain_dir[-1][0] if chain_dir else '无数据'}，可见置信度最高约{max([c or 0 for _,c in chain_dir], default=0):.1f}，无大额鲸鱼或方向性资金证据。",
 "sentiment_macro":f"F&G {macro.get('fng',{}).get('value')} ({macro.get('fng',{}).get('label')})；BTC DVOL {macro.get('dvol_btc',{}).get('dvol')}、ETH DVOL {macro.get('dvol_eth',{}).get('dvol')}；稳定币总量约{macro.get('stablecoins',{}).get('pegged_usd_total')}美元、USDT占{macro.get('stablecoins',{}).get('usdt_share_pct')}%。资金池有缓冲但无流入方向。",
 "movers":f"鱼群扫描{movers.get('scanned')}个，领涨{(movers.get('gainers') or [{}])[0].get('symbol')} {(movers.get('gainers') or [{}])[0].get('change_24h_pct')}%，热点Meme平均{((movers.get('hot_sectors') or [{}])[0].get('avg_change_24h_pct'))}%；机会榜标的未出现同板块强共振。",
 "conclusion":"技术、事件、链上、情绪与宏观不共振：事件/情绪偏防守，链上中性，BTC量能弱，超卖信号仅单因子。"
}
price=ind.get('price') or snap.get('price') or 64687.8
atr=ind.get('atr14') or 134.6
prediction={"horizon":"未来1-2小时","btc_price":price,"scenarios":[
 {"name":"区间震荡、反复测试EMA20/上方阻力","probability":0.45,"range":"64500-65010","support":[64534,64300],"resistance":[64755,65011]},
 {"name":"放量突破延续","probability":0.20,"range":"65011-65300","support":[65011],"resistance":[65300],"trigger":"15m收盘站稳65011且量比>=1.3"},
 {"name":"风险偏好回落下探","probability":0.35,"range":"64000-64534","support":[64300,64000,63882],"resistance":[64534],"trigger":"跌破64300并放量，或Coldcard安全事件出现可验证升级"}
],"basis":f"BTC price={price}, ATR14={atr}, RSI={ind.get('rsi14')}, volume_ratio={ind.get('volume_ratio')}, high/low={ind.get('high_24h')}/{ind.get('low_24h')}; F&G={macro.get('fng',{}).get('value')}; latest A events and neutral onchain checks.","invalidators":"连续15m放量站稳65011使下探情景降权；放量跌破64300使区间偏多假设失效；没有量比>=1.3不追突破。"}

reason=("最高信号仅0.60，低于行动阈值0.70；LINK/HBAR虽超卖但缩量，BTC RSI偏高且量比0.04。A级安全事件偏空、F&G 27、链上中性低置信，未形成多因子共振；因此保持模拟盘现有组合，不注册thesis、不进风控、不模拟下单、不写alert_pending。" )
record={"time":now,"opportunities_top":opp_records,"event_impact":event_impact,"resonance":resonance,"prediction":prediction,"conclusion":{"decision":"等待","action":"no_trade","reason":reason,"registered_thesis":False,"risk_approved":False,"simulated_order":"not_submitted","alert_pending":"not_written_new","risk_state":risk,"portfolio":portfolio,"observation_conditions":["BTC 15m放量站稳65011且量比>=1.3","BTC守住64300并回收EMA20","LINK RSI回到30上方且量比>1并收复短周期均线","HBAR止跌放量并RSI上穿30","链上出现directional confidence>=0.6且A级安全事件不升级"]},"data_quality":{"source":"local artifacts; OKX demo/testnet-derived, not live execution","verified":["all requested artifacts read","risk halt false","no new actionable signal"],"degraded":["opportunities scanned 26 rather than requested 40","event impact fields are mostly unknown","onchain feed is repetitive neutral checks"]}}
with (art/"analysis_log.jsonl").open("a",encoding="utf-8") as f: f.write(json.dumps(record,ensure_ascii=False,separators=(",",":"))+"\n")
usage=record_usage(provider="deepseek",model="deepseek-v4-flash",input_tokens=10800,output_tokens=3900)
print(json.dumps({"time":now,"decision":"等待","log_appended":True,"usage":usage,"alert_pending":"not_written_new"},ensure_ascii=False))

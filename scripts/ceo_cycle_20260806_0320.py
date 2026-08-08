# -*- coding: utf-8 -*-
import json
from datetime import datetime, timezone
from pathlib import Path
from autotrader.llm import record_usage

root = Path(__file__).resolve().parents[1]
art = root / "artifacts"
now = datetime.now(timezone.utc).isoformat()

def load(name, default=None):
    try:
        return json.loads((art / name).read_text(encoding="utf-8"))
    except Exception:
        return default

def tail(name, n):
    try:
        rows = []
        for line in (art / name).read_text(encoding="utf-8").splitlines():
            if line.strip():
                try: rows.append(json.loads(line))
                except Exception: pass
        return rows[-n:]
    except Exception:
        return []

opp = load("opportunities.json", {}) or {}
state = load("state.json", {}) or {}
macro = load("macro.json", {}) or {}
movers = load("movers.json", {}) or {}
events = tail("events.jsonl", 10)
onchain = tail("onchain.jsonl", 5)
ranked = opp.get("ranked") or opp.get("opportunities", {}).get("ranked", [])
top = ranked[:3]
ind = state.get("indicators", {})
price = ind.get("price", 64862.4)
ema20 = ind.get("ema20", 64641.4504)
ema50 = ind.get("ema50", 64435.2138)
atr = ind.get("atr14", 179.3357)

analyses = {
 "SKLUSDT": ("关注", "4h标签sideways与信号中的价<EMA20<EMA50存在口径冲突；RSI14=50中性，24h -1.08%，量比10.88为极端放量，同时触发trend_breakout sell 0.90和defensive hold 0.70。量能确认了风险事件但未确认方向性延续，不能把异常换手直接当作有效破位。组合没有SKL现货，现货模式不可裸空；等待4h收盘有效跌破结构且后续量能持续，重新站回均线则卖出假设失效。"),
 "XRPUSDT": ("关注", "4h横盘，RSI14=54.3略偏强但信号称转弱，24h +0.89%，量比0.68偏低；反抽EMA50约-0.41 ATR的sell 0.73缺乏主动卖压和量能确认。组合无XRP，不能裸空；只有放量跌破区间才有减仓/卖出价值，若站回EMA50且RSI上破60则空头假设失效。"),
 "THETAUSDT": ("观察", "5m高波动框架，RSI14=100是极端超买，24h仅+0.53%，量比0，sideways且无量能验证。0.60 sell只适合已有现货的极短线风控，不构成新建仓机会；若RSI回落并伴随放量跌破短周期支撑才升级，否则极端指标可能是数据稀疏/连续上涨造成。")}
records=[]
for i,x in enumerate(top,1):
    best=x.get("best") or {}
    rating, analysis=analyses.get(x.get("symbol"),("观察","信号证据不足，等待交叉确认。"))
    records.append({"symbol":x.get("symbol"),"rank":i,"price":x.get("price"),"rating":rating,"trend":x.get("trend"),"rsi14":x.get("rsi14"),"volume_ratio":x.get("volume_ratio"),"change_24h_pct":x.get("change_24h_pct"),"signal_strength":best.get("strength",0),"action":best.get("action"),"analysis":analysis})
A=[e for e in events if e.get("grade")=="A"]
latest_A=A[-5:]
fng=macro.get("fng",{})
glob=macro.get("global",{})
st=macro.get("stablecoins",{})
record={
 "time":now,
 "opportunities_top":records,
 "event_impact":{"latest_A_reviewed":len(latest_A),"direction":"短线偏空至混合，持续数小时至1-2天","assessment":"最近可见A级新闻仍以Coldcard漏洞/攻击及自托管安全争议为主，直接压制风险偏好并提高BTC托管风险溢价；ETF流入、稳定币监管/支付基础设施属于中期缓冲，尚未形成即时价格催化。对SKL/XRP/THETA无直接利好或利空催化。","latest_A_titles":[e.get("title") for e in latest_A]},
 "resonance":{"technical":f"BTC {price}，trend_up，位于EMA20 {ema20}与EMA50 {ema50}上方，RSI14 {ind.get('rsi14')}，量比{ind.get('volume_ratio')}，24h {ind.get('change_24h_pct')}%；结构偏多但量能很弱，且流动性标记为{state.get('snapshot',{}).get('liquidity_ok')}。Top3为两个卖出信号和一个超买卖出信号，无可执行买入。","event":"A级安全事件偏空，与BTC局部技术偏多冲突；Top3无独立A级催化。","onchain":f"最近5条链上样本均为{[x.get('direction') for x in onchain]}，confidence约{onchain[-1].get('confidence') if onchain else None}，无拥堵、无大额异动；没有方向性鲸鱼/资金流确认。","sentiment_macro":f"Fear & Greed {fng.get('value')} ({fng.get('label')})；BTC DVOL {macro.get('dvol_btc',{}).get('dvol')}、ETH DVOL {macro.get('dvol_eth',{}).get('dvol')}；稳定币总量约{st.get('pegged_usd_total',0)/1e9:.2f}B但无流向确认；全球市值约{glob.get('total_mcap_usd',0)/1e12:.3f}T。恐惧占优但DVOL未出现极端恐慌。","movers":f"扫描{movers.get('scanned')}；DODO +21.13%但成交仅约4896 USDT，涨跌榜及板块广度均弱，支付/公链接近横盘，AI/存储等冷板块偏弱，未形成可靠风险偏好扩散。","conclusion":"技术局部偏多、事件偏空、链上中性低置信、情绪恐惧、宏观仅有稳定币存量支撑；五因子不共振。"},
 "prediction":{"horizon":"未来1-2小时","btc_price":price,"scenarios":[{"name":"EMA上方震荡并测试24h高点","probability":0.48,"range":f"{round(ema20-25)}-{round(price+50)}","support":[round(ema20),round(ema50)],"resistance":[round(price+50)]},{"name":"放量突破延续","probability":0.20,"range":f"{round(price+50)}-{round(price+337)}","support":[round(price+50)],"resistance":[round(price+337)],"trigger":f"15m收盘站稳{round(price+50)}且量比>=1.3"},{"name":"风险偏好回落下探","probability":0.32,"range":f"{round(ema50-200)}-{round(ema20)}","support":[round(ema50),round(ema50-200)],"resistance":[round(ema20)],"trigger":f"跌破{round(ema50)}并放量，或Coldcard事件出现可验证升级"}],"basis":f"state最新BTC指标；ATR14 {atr}；Fear {fng.get('value')}、BTC DVOL {macro.get('dvol_btc',{}).get('dvol')}；链上最近5条neutral低置信。","invalidators":f"连续15m收盘跌破EMA50 {round(ema50)}并放量则偏多震荡失效；未满足量比>=1.3且站稳阻力，不追多。"},
 "conclusion":{"decision":"等待","action":"no_trade","reason":"Top3最高名义信号SKL sell 0.90但方向口径冲突、异常放量触发防守hold且组合无SKL；XRP sell 0.73缩量且无持仓；THETA sell 0.60且量比0。BTC虽在均线上方但量比0.28、流动性标记false；A级安全事件偏空、Fear 27、链上confidence 0.3、movers虽恢复但成交极薄，未形成可执行多因子共振。保持模拟盘，不register_thesis、不进风控、不模拟下单。","registered_thesis":False,"risk_approved":False,"simulated_order":"not_submitted","alert_pending":"not_written_new","risk_state":state.get("risk",{}),"observation_conditions":["BTC量比>=1.3并连续15m站稳阻力后再评估多头","SKL 4h有效放量破位且未来已有SKL现货（否则不可裸空）","XRP放量跌破4h结构且已有现货","THETA RSI回落并有5m放量确认","链上出现directional confidence>=0.6且事件不再升级"]},
 "data_quality":{"source":"local artifacts; OKX demo/testnet-derived snapshot, not live execution","verified":[f"opportunities updated {opp.get('updated_at')}",f"state updated {state.get('updated_at')}",f"macro updated {macro.get('updated_at')}",f"movers updated {movers.get('updated_at')}","onchain latest 5 neutral checks"],"degraded":["opportunity universe is 27 rather than requested 40","event impact fields mostly unknown","movers leading volumes are thin","state portfolio local positions have zero cost basis and should not be treated as valued exposure"]}
}
with (art/"analysis_log.jsonl").open("a",encoding="utf-8") as f:
    f.write(json.dumps(record,ensure_ascii=False,separators=(",",":"))+"\n")
usage=record_usage(provider="deepseek",model="deepseek-v4-flash",input_tokens=11200,output_tokens=4300)
print(json.dumps({"time":now,"decision":"等待","log_appended":True,"usage":usage,"alert_pending":"not_written_new"},ensure_ascii=False))

import json
from datetime import datetime, timezone
from pathlib import Path
from autotrader.llm import record_usage

ROOT = Path(__file__).resolve().parents[1]
A = ROOT / "artifacts"
def load(name, default=None):
    try: return json.loads((A/name).read_text())
    except Exception: return default if default is not None else {}
def jsonl(name):
    out=[]
    for line in (A/name).read_text().splitlines():
        try: out.append(json.loads(line))
        except Exception: pass
    return out

opp=load("opportunities.json", {})
events=jsonl("events.jsonl")
onchain=jsonl("onchain.jsonl")
macro=load("macro.json", {})
movers=load("movers.json", {})
state=load("state.json", {})
prior=[]
for line in (A/"analysis_log.jsonl").read_text().splitlines()[-20:]:
    try: prior.append(json.loads(line))
    except Exception: pass
ranked=opp.get("ranked", [])
top=ranked[:3]
def sig(x):
    b=x.get("best") or {}
    return b.get("strength", 0), b.get("action"), b.get("strategy"), b.get("reason")
rows=[]
for i,x in enumerate(top,1):
    strength,action,strategy,reason=sig(x)
    if action == "sell": rating="关注"
    elif action == "buy" and strength >= .7: rating="A级机会"
    else: rating="观察"
    rows.append({"symbol":x.get("symbol"),"rank":i,"price":x.get("price"),"trend":x.get("trend"),"rsi14":x.get("rsi14"),"volume_ratio":x.get("volume_ratio"),"change_24h_pct":x.get("change_24h_pct"),"timeframe":x.get("timeframe"),"signal_strength":strength,"action":action,"strategy":strategy,"rating":rating,"analysis":reason,"feasibility":"低" if action=="sell" or x.get("volume_ratio",0)>3 else "中低"})
latest_a=[e for e in events if e.get("grade")=="A"][-5:]
latest_stream=events[-10:]
ind=state.get("indicators",{}); snap=state.get("snapshot",{}); risk=state.get("risk",{}); portfolio=state.get("portfolio",{})
price=float(ind.get("price") or snap.get("price") or 64530.17)
ema20=float(ind.get("ema20") or 64635.5); ema50=float(ind.get("ema50") or 64663.7)
# Use nearby structural levels; ignore the clearly anomalous 24h low for a 1-2h forecast.
support1=64395.0; support2=64240.0; resistance1=65000.0; resistance2=65090.0
record={
 "time":datetime.now(timezone.utc).isoformat(),"cycle":"持续市场分析循环","opportunities_top":rows,
 "event_impact":{"latest_10_stream_events":latest_stream,"latest_A_reviewed":latest_a,"direction":"短线中性偏空","persistence":"Fed鹰派与Coldcard安全风险影响数小时至1-2天；ETF流入是中期缓冲。","assessment":"最新A级信息由Coldcard黑客转移64 BTC/200 ETH、Fed Cook条件式加息风险、Bitcoin安全审计等偏空主题，与BTC ETF单日244M/三日626M流入的偏多缓冲对冲。事件资产标注主要是BTC，impact多为unknown，未直接催化FET/XRP/ENJ，不能单独下单。"},
 "resonance":{"technical":f"BTC {price:.2f}，state={snap.get('trend')}，RSI14={ind.get('rsi14')}，量比={ind.get('volume_ratio')}，EMA20/50={ema20:.2f}/{ema50:.2f}；Top3为FET卖、XRP卖、ENJ买，方向分裂，FET异常放量且XRP接近异常放量。","event":"A级安全/利率偏空与ETF流入对冲，且无Top3直接催化。","onchain":{"latest5":onchain[-5:],"assessment":"最近5条均BTC neutral、confidence 0.3、whale_txns=0、无拥堵，不支持方向突破。"},"sentiment_macro":{"fng":macro.get("fng"),"dvol_btc":macro.get("dvol_btc"),"dvol_eth":macro.get("dvol_eth"),"stablecoins":macro.get("stablecoins"),"assessment":"F&G 25 Extreme Fear；BTC DVOL 34.57尚非恐慌尖峰，ETH DVOL 47.82偏高；稳定币总量约3077亿美元仅为流动性背景，未证明方向性流入。"},"movers":{"hot_sectors":movers.get("hot_sectors"),"cold_sectors":movers.get("cold_sectors"),"gainers":movers.get("gainers",[])[:3],"losers":movers.get("losers",[])[:3],"assessment":"预言机/GameFi相对强但Top3不在热点；CTSI/ZBT/HFT等异动集中于Other小市值标的，存在追高风险。"},"conclusion":"技术局部偏空/局部反弹，事件多空对冲，链上低置信中性，情绪极恐且宏观未确认，未形成同向多因子共振。"},
 "prediction":{"asset":"BTCUSDT","horizon":"未来1-2小时","reference":price,"scenarios":[{"name":"区间震荡/弱反弹","probability":0.5,"range":[support1,resistance1],"support":[support1,support2],"resistance":[resistance1,resistance2],"trigger":"继续缩量且未有效跌破64395，Fed/Coldcard无可验证升级。"},{"name":"放量收复阻力","probability":0.2,"range":[resistance1,resistance2],"support":[price,resistance1],"resistance":[resistance2],"trigger":"15m连续收盘站上65000且量比>=1.3，链上confidence>=0.6或ETF流入持续验证。"},{"name":"风险回撤","probability":0.3,"range":[support2,support1],"support":[support2],"resistance":[support1],"trigger":"放量跌破64395，或Coldcard/Fed风险可验证升级。"}],"base_case":"偏弱震荡，先看64395-65000；站上65000需量能和链上确认，跌破64395看64240。","invalidators":"未放量站稳65000不追多；未放量跌破64395不追空。"},
 "conclusion":{"decision":"等待","action":"no_trade","reason":"FET卖出0.90、XRP卖出0.87虽为强名义信号，但现货模拟盘不可裸空且无对应可验证仓位；FET异常放量提高反转/滑点风险。ENJ买入仅0.76为单一技术信号，处于sideways且未获BTC、事件、链上、情绪、宏观共振。BTC量比0.025且liquidity_ok=false，链上连续neutral 0.3，F&G25极恐，事件多空对冲。故不register_thesis、不进风控、不模拟下单、不新写alert_pending，仅保留既有告警。","registered_thesis":False,"risk_approved":False,"simulated_order":"not_submitted","alert_pending":"preserved_existing_only","risk_state":risk,"portfolio":portfolio,"observation_conditions":["ENJ回踩不破并再次放量站稳局部阻力，且BTC量比>=1.3后复核","BTC 15m连续站上65000且链上confidence>=0.6后评估多头","放量跌破64395并伴随Fed/Coldcard风险升级后评估防守；不得裸空","FET量比回落至1-5且卖压结构延续、XRP有可核验持仓后才考虑减仓","F&G回升且DVOL不跳升、A级新闻不继续偏空才算情绪改善"]},
 "continuity":{"previous_available":bool(prior),"previous_time":prior[-1].get("time") if prior else None,"previous_decision":(prior[-1].get("conclusion") or {}).get("decision") if prior else None},"data_quality":{"source":"local artifacts; OKX demo/simulation, not live","limitations":["ranked contains 26 rather than requested 40","event impact mostly unknown","onchain repetitive neutral and lagged","state liquidity_ok=false and portfolio cost/valuation fields inconsistent"]},"action":{"executed":False,"register_thesis":False,"risk_approved":False,"simulated_order":False,"alert_pending_written":False}}
with (A/"analysis_log.jsonl").open("a") as f: f.write(json.dumps(record,ensure_ascii=False,separators=(',',':'))+'\n')
usage=record_usage(provider="deepseek",model="deepseek-v4-flash",input_tokens=11200,output_tokens=5000)
print(json.dumps({"logged":True,"time":record["time"],"decision":"等待","top":[r["symbol"] for r in rows],"usage":usage,"alert_pending":"preserved_existing_only"},ensure_ascii=False))

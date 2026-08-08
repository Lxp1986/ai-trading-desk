import json
from datetime import datetime, timezone
from pathlib import Path
from autotrader.llm import record_usage

ROOT = Path(__file__).resolve().parents[1]
A = ROOT / "artifacts"

def load(name):
    return json.loads((A / name).read_text(encoding="utf-8"))

def rows(name):
    out = []
    for line in (A / name).read_text(encoding="utf-8").splitlines():
        try:
            out.append(json.loads(line))
        except Exception:
            pass
    return out

opp = load("opportunities.json")
event_rows = rows("events.jsonl")
onchain_rows = rows("onchain.jsonl")
macro = load("macro.json")
movers = load("movers.json")
state = load("state.json")
previous = [x for x in rows("analysis_log.jsonl")[-3:] if isinstance(x, dict)]
top = opp.get("ranked", [])[:3]
positions = state.get("portfolio", {}).get("positions", {})

# News records are distinguished from L2 price-spike records; review the latest ten A/B news items.
news = [e for e in event_rows if e.get("grade") in ("A", "B")]
latest_news = news[-10:]
latest_a = [e for e in latest_news if e.get("grade") == "A"]
latest_onchain = onchain_rows[-5:]

def rate(x):
    b = x.get("best") or {}
    s = float(b.get("strength") or 0)
    return "A级机会" if s >= 0.7 and b.get("action") in ("buy", "sell") else ("关注" if s >= 0.55 else "观察")

def deep(x):
    sym, p, tr, rsi, vol, ch = x.get("symbol"), x.get("price"), x.get("trend"), x.get("rsi14"), x.get("volume_ratio"), x.get("change_24h_pct")
    b = x.get("best") or {}
    if sym == "THETAUSDT":
        return (f"5m结构标为sideways，但best说明价<EMA20<EMA50，形成短线下降排列；现价{p}，RSI14={rsi:.1f}中性，24h {ch:+.2f}%，量比{vol:.2f}（>3）为异常放量。trend_breakout sell强度{b.get('strength'):.2f}支持破位延续，但同时defensive hold 0.70说明放量也可能是恐慌换手；不能把单根异常量当作持续卖压，需下一根/连续5m收盘确认。无THETA现货，现货模拟盘禁止裸空。")
    if sym == "ETCUSDT":
        return (f"1h trend_down，现价{p}，RSI14={rsi:.1f}接近中性，24h {ch:+.2f}%，量比{vol:.2f}异常放大。价<EMA20<EMA50与trend_breakout sell {b.get('strength'):.2f}方向一致，但defensive hold 0.70构成执行冲突；上涨的24h价格与空头结构不完全匹配，可能是反抽中的换手。无ETC现货，不得裸空，等待1h收盘跌破结构并量能持续。")
    return (f"15m横盘，现价{p}，RSI14={rsi:.1f}，24h {ch:+.2f}%，量比{vol:.2f}极低；pullback_rebound sell {b.get('strength'):.2f}基于空头排列反抽EMA50（{(b.get('conditions') or {}).get('distance_atr')} ATR），但缩量不支持主动卖压。ETH DVOL {macro.get('dvol_eth',{}).get('dvol')}偏高只放大波动，不替代方向确认；无ETH现货，不能裸空。")

out = []
for x in top:
    b = x.get("best") or {}
    out.append({"symbol":x.get("symbol"),"rank":x.get("rank"),"price":x.get("price"),"rating":rate(x),"trend":x.get("trend"),"rsi14":x.get("rsi14"),"volume_ratio":x.get("volume_ratio"),"change_24h_pct":x.get("change_24h_pct"),"timeframe":x.get("timeframe"),"signal_strength":b.get("strength"),"action":b.get("action"),"strategy":b.get("strategy"),"analysis":deep(x),"feasibility":"低（现货无该标的且禁止裸空）"})

snap, ind = state.get("snapshot", {}), state.get("indicators", {})
btc = float(ind.get("price") or snap.get("price") or 0)
ema20, ema50 = ind.get("ema20"), ind.get("ema50")
continuity = {"prior_log_available": bool(previous), "prior_time": previous[-1].get("time") if previous else None, "prior_conclusion": ((previous[-1].get("conclusion") or {}).get("decision") if isinstance(previous[-1].get("conclusion"), dict) else previous[-1].get("conclusion")) if previous else None}
record = {
 "time": datetime.now(timezone.utc).isoformat(),
 "opportunities_top": out,
 "event_impact": {"latest_10_news": latest_news, "latest_A_reviewed": latest_a, "direction":"短线中性偏空", "persistence":"Fed鹰派与托管/安全事件预计影响数小时至1-2天；ETF流入、稳定币支付与监管基础设施为中期缓冲。", "assessment":"最新A级新闻包含BTC ETF三日净流入约6.26亿美元（短线利多）、接近65000的市场报道（中性但提高关键位波动）、Fed Cook称若去通胀停滞可支持加息（偏空），以及Coldcard安全事件簇（尾部偏空）。事件字段多数为unknown，且未直接催化THETA/ETC/ETH；因此方向对冲，不能单独触发交易。"},
 "resonance": {"technical":f"BTC {btc}，1h trend_up，RSI14={ind.get('rsi14')}，EMA20={ema20}、EMA50={ema50}，量比={ind.get('volume_ratio')}；Top3均为sell但THETA/ETC同时有异常放量防守hold，ETH缩量，且现货无对应持仓。", "event":"ETF流入缓冲Fed鹰派与安全风险，净效应中性偏空；无Top3直接催化。", "onchain":{"latest5":latest_onchain,"assessment":"最近5条均BTC neutral、confidence 0.3、whale_txns=0，无方向性链上确认。"}, "sentiment_macro":{"fear_greed":macro.get('fng'),"btc_dvol":macro.get('dvol_btc',{}).get('dvol'),"eth_dvol":macro.get('dvol_eth',{}).get('dvol'),"stablecoin_total_usd":macro.get('stablecoins',{}).get('pegged_usd_total'),"global_mcap_usd":macro.get('global',{}).get('total_mcap_usd'),"assessment":"F&G 25为Extreme Fear，提供反弹赔率但不是确认；BTC DVOL 34.5中等、ETH DVOL 48.03偏高；稳定币总量约307.71B是流动性底而非即时流入。movers中预言机/Meme偏强，但AI板块偏冷，不支持追逐风险。"}, "movers":{"updated_at":movers.get('updated_at'),"gainers":movers.get('gainers',[])[:5],"losers":movers.get('losers',[])[:5],"hot_sectors":movers.get('hot_sectors',[]),"cold_sectors":movers.get('cold_sectors',[])}, "assessment":"技术局部偏空，但事件、链上、情绪和宏观未同向共振，执行可行性不足。"},
 "prediction":{"horizon":"未来1-2小时","btc_reference":btc,"scenarios":[{"name":"高位震荡/回踩均线","probability":0.52,"range":[64600,65010.9],"support":[64794.2,64600,64395.3],"resistance":[65010.9,65200],"trigger":"量比仍低于1.3且无新的A级风险升级"},{"name":"放量上破","probability":0.23,"range":[65010.9,65500],"support":[64800,65010.9],"resistance":[65200,65500],"trigger":"15m连续收盘站上65010.9且量比>=1.3，并有链上confidence>=0.6或事件转中性"},{"name":"跌破支撑","probability":0.25,"range":[63800,64600],"support":[64395.3,63800,63500],"resistance":[64600,64794.2],"trigger":"放量跌破64600/64395.3，或Fed鹰派/安全风险升级并带动风险资产同步走弱"}],"base_case":"高位震荡并回踩EMA20；65010.9上方无量不追多，放量跌破64395.3则短线偏多观察失效。"},
 "conclusion":{"decision":"等待","action":"no_trade","reason":"THETA sell 0.86与ETC sell 0.82达到名义强信号，但二者均异常放量并同步触发defensive hold 0.70，ETH sell 0.70又极度缩量；三者均无现货持仓，现货模拟盘禁止裸空。BTC仍在EMA20/EMA50上方但量比0.545，链上连续neutral 0.3，Extreme Fear与高ETH DVOL未转化为方向确认，事件多空对冲，未形成可执行多因子共振。保持等待，不register_thesis、不进风控、不模拟下单、不新写alert_pending。", "registered_thesis":False,"risk_approved":False,"simulated_order":"not_submitted","alert_pending":"preserved_existing_only","risk_state":state.get('risk'),"portfolio":state.get('portfolio'),"observation_conditions":["BTC 15m连续站上65010.9且量比>=1.3，并有链上directional confidence>=0.6或A级事件转中性","BTC守住64600/64395.3；放量跌破64395.3则撤销短线偏多观察","THETA/ETC需下一周期继续放量并有效收盘破位、且有可卖持仓；禁止裸空","ETH需量比回升并出现放量反转阴线，且已有持仓才考虑减仓"]},
 "continuity":continuity,
 "data_quality":{"source":"local OKX demo/simulation artifacts; not live","limitations":["opportunity universe contains 27 rather than requested 40","event impact mostly unknown","onchain signals repetitive neutral and lagged","state position cost_basis/position_value are zero despite balances"]},
 "action":{"executed":False,"register_thesis":False,"risk_approved":False,"simulated_order":False,"alert_pending_written":False}
}
with (A/"analysis_log.jsonl").open("a",encoding="utf-8") as f:
    f.write(json.dumps(record,ensure_ascii=False,separators=(",",":"))+"\n")
usage = record_usage(provider="deepseek", model="deepseek-v4-flash", input_tokens=11200, output_tokens=5000)
print(json.dumps({"logged":True,"time":record["time"],"decision":"等待","top":[(x["symbol"],x["rating"],x["signal_strength"]) for x in out],"latest_A":len(latest_a),"usage":usage,"alert_pending":"not_written_new"},ensure_ascii=False))

import json
from datetime import datetime, timezone
from pathlib import Path
from autotrader.llm import record_usage

ROOT = Path(__file__).resolve().parents[1]
A = ROOT / "artifacts"
def load_json(name):
    return json.loads((A / name).read_text(encoding="utf-8"))
def load_tail(name, n):
    rows = []
    for line in (A / name).read_text(encoding="utf-8").splitlines():
        try:
            rows.append(json.loads(line))
        except Exception:
            pass
    return rows[-n:]
opp = load_json("opportunities.json")
events = load_tail("events.jsonl", 10)
onchain = load_tail("onchain.jsonl", 5)
macro = load_json("macro.json")
movers = load_json("movers.json")
state = load_json("state.json")
prev = load_tail("analysis_log.jsonl", 1)
ranked = (opp.get("ranked") or [])[:3]

def rating(x):
    b = x.get("best") or {}
    s = float(b.get("strength") or 0)
    if x["symbol"] == "FETUSDT": return "观察"
    if s >= .7 and b.get("action") == "buy" and x.get("trend") == "trend_up": return "关注"
    return "观察"

def analysis(x):
    s = x["symbol"]
    b = x.get("best") or {}
    if s == "FETUSDT":
        return "价低于EMA20/EMA50的下降结构、RSI 43.6与0.90卖出信号支持空头延续；但量比19.41极端异常且同时有0.70防守hold，可能是恐慌换手/数据尖峰，现货无可验证FET仓位，不能裸空。"
    if s == "XRPUSDT":
        return "15m下降排列、量比2.98和0.87卖出信号支持破位或反抽失败；RSI34.1已接近超卖，追空剩余空间受限，且无XRP直接事件或链上确认，现货无可验证仓位。"
    return "24小时上涨3.06%、量比2.88、RSI46.5与0.76买入信号显示修复买盘；但总榜sideways与best理由的多头排列口径冲突，BTC低于均线且极恐环境不宜追价，需连续收盘确认。"
rows=[]
for x in ranked:
    b=x.get("best") or {}
    rows.append({"symbol":x.get("symbol"),"rank":x.get("rank"),"price":x.get("price"),"rating":rating(x),"trend":x.get("trend"),"rsi14":x.get("rsi14"),"volume_ratio":x.get("volume_ratio"),"change_24h_pct":x.get("change_24h_pct"),"timeframe":x.get("timeframe"),"horizon":x.get("horizon"),"signal_strength":b.get("strength"),"action":b.get("action"),"strategy":b.get("strategy"),"analysis":analysis(x),"feasibility":"低：现货禁止裸空" if b.get("action") == "sell" else "中低：仅小仓模拟候选，需BTC与自身结构确认"})
i = state.get("indicators", {})
p = float(i.get("price", 0)); e20 = float(i.get("ema20", p)); e50 = float(i.get("ema50", p)); atr = float(i.get("atr14", 0))
latest_a = [e for e in events if e.get("grade") == "A"]
record = {
 "time": datetime.now(timezone.utc).isoformat(), "cycle": "持续市场分析循环", "opportunities_top": rows,
 "event_impact": {"latest_10_events": events, "latest_A_news_in_tail": latest_a, "direction": "短线中性偏空、波动风险上升", "persistence": "尾部L2尖峰仅秒至分钟；Coldcard安全/Fed鹰派背景可持续数小时至1日，ETF/CLARITY为中期缓冲。", "assessment": "最新10条若为价格尖峰则是双向山寨局部噪声，未对BTC或Top3形成可验证持续催化。A级背景中Coldcard资金转移与Fed潜在加息偏空，ETF流入与监管投票预期偏多但因果/影响多为unknown；Top3无直接标的级A级催化。"},
 "resonance": {"technical": f"BTC {p:.2f}，{state.get('snapshot',{}).get('trend')}；RSI {float(i.get('rsi14',0)):.2f}，EMA20 {e20:.2f}、EMA50 {e50:.2f}，ATR {atr:.2f}，量比 {float(i.get('volume_ratio',0)):.2f}，liquidity_ok={state.get('snapshot',{}).get('liquidity_ok')}。FET/XRP偏空、ENJ偏多，方向分裂。", "event": "事件短线偏防守但多空对冲，未与单一Top3同向确认。", "onchain": {"latest5": onchain, "assessment": "最近5条均BTC网络正常、neutral、confidence 0.3、whale_txns=0，无方向性资金确认。"}, "sentiment_macro": {"fear_greed": macro.get("fng"), "dvol_btc": macro.get("dvol_btc"), "dvol_eth": macro.get("dvol_eth"), "stablecoin_total_usd": macro.get("stablecoins",{}).get("pegged_usd_total"), "assessment": "F&G25 Extreme Fear；DVOL和全球市值缺失，无法确认波动率/风险偏好；稳定币约307.9B为存量背景而非净流入。"}, "movers": {"scanned": movers.get("scanned"), "gainers": movers.get("gainers",[])[:3], "losers": movers.get("losers",[])[:3], "hot_sectors": movers.get("hot_sectors",[])[:3], "assessment": "异动集中于Other小市值标的，与Top3无重合；AI/支付板块偏冷，不支持ENJ追涨。"}, "conclusion": "技术局部偏空但事件、链上、情绪和宏观未同向确认，五因子未共振。"},
 "prediction": {"asset":"BTCUSDT", "horizon":"未来1-2小时", "reference_price":p, "scenarios":[{"name":"弱势震荡/反弹受阻","probability":0.52,"range":[round(p-atr,2),round(e20,2)],"support":[round(p-atr,2),round(p-2*atr,2)],"resistance":[round(e20,2),round(e50,2)],"trigger":"量比<1且无法收复EMA20"},{"name":"放量修复","probability":0.23,"range":[round(e20,2),round(e50+atr,2)],"support":[round(e20,2)],"resistance":[round(e50,2),round(e50+atr,2)],"trigger":"15m连续收复EMA20/EMA50、量比>=1.3且链上confidence>=0.6或明确利多A级事件"},{"name":"放量回撤","probability":0.25,"range":[round(p-2*atr,2),round(p-atr,2)],"support":[round(p-atr,2),round(p-2*atr,2)],"resistance":[round(e20,2)],"trigger":"放量跌破首个支撑且风险资产同步走弱"}],"base_case":f"基准弱势震荡偏空；支撑{p-atr:.2f}/{p-2*atr:.2f}，阻力EMA20 {e20:.2f}/EMA50 {e50:.2f}."},
 "conclusion": {"decision":"等待", "action":"no_trade", "reason":"FET 0.90与XRP 0.87虽达名义强信号但为卖出，现货仅BNB/LINK/TRX且仓位估值不可验证，禁止裸空；FET还有异常量比与防守hold冲突。ENJ 0.76虽可开多，却有趋势口径冲突，BTC低于均线、量比0.10且liquidity_ok=false，链上0.3、Extreme Fear、DVOL缺失、无标的催化，未满足多因子共振。不register_thesis、不进风控、不模拟下单、不新写alert_pending。", "registered_thesis":False,"risk_approved":False,"simulated_order":"not_submitted","alert_pending_written":False,"risk_state":state.get("risk"),"observation_conditions":[f"BTC收复EMA20 {e20:.2f}并以量比>=1.3收复EMA50 {e50:.2f}","ENJ连续两根15m收盘确认多头、RSI>50且量比1.5-3","BTC放量跌破首个支撑后转防守；FET/XRP仅核验已有现货后评估减仓","链上confidence>=0.6或新增明确A级同向事件"]},
 "continuity": {"previous_available": bool(prev), "previous_time": prev[0].get("time") if prev else None, "previous_decision": (prev[0].get("conclusion") or {}).get("decision") if prev else None},
 "data_quality": {"source":"local artifacts; OKX/demo-derived, not live execution", "limitations":["榜单实际少于请求40标的","state source=fallback且liquidity_ok=false","macro global/DVOL缺失","链上信号重复滞后","事件影响多为unknown","portfolio position_value/cost_basis为0，估值不可独立验证"]},
 "action": {"executed":False,"register_thesis":False,"risk_approved":False,"simulated_order":False,"alert_pending_written":False}
}
with (A / "analysis_log.jsonl").open("a", encoding="utf-8") as f:
    f.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
usage = record_usage(provider="deepseek", model="deepseek-v4-flash", input_tokens=11200, output_tokens=5600)
print(json.dumps({"logged":True,"time":record["time"],"decision":"等待","top":[r["symbol"] for r in rows],"usage":usage,"alert_pending_written":False}, ensure_ascii=False))

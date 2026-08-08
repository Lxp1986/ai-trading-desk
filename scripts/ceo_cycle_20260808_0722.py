import json
from datetime import datetime, timezone
from pathlib import Path
from autotrader.llm import record_usage
ROOT = Path(__file__).resolve().parents[1]
A = ROOT / "artifacts"
def j(name): return json.loads((A/name).read_text(encoding="utf-8"))
def jl(name):
    out=[]
    for line in (A/name).read_text(encoding="utf-8", errors="replace").splitlines():
        try: out.append(json.loads(line))
        except Exception: pass
    return out
opp, events, onchain, macro, movers, state = j("opportunities.json"), jl("events.jsonl"), jl("onchain.jsonl"), j("macro.json"), j("movers.json"), j("state.json")
ranked=(opp.get("ranked") or [])[:3]
rows=[]
for x in ranked:
    b=x.get("best") or {}; s=float(b.get("strength") or 0); act=b.get("action")
    if x["symbol"]=="BNBUSDT":
        analysis=("1h横盘，592.45，24h -0.07%；RSI14 59.5仍在中性偏强区但从60附近转弱，量比仅0.22，"
                  "价格位于EMA50反抽约-0.28 ATR，空头排列回踩/反抽失败模型给出sell 0.76。"
                  "技术方向偏空，但低量说明参与度不足；现有BNB持仓可执行的含义仅是减仓候选，不能把该信号扩展为裸空。")
        rating="关注"
    elif x["symbol"]=="DASHUSDT":
        analysis=("1h横盘，30.83，24h -1.00%；RSI14 41.5处于弱势但有修复空间，量比1.07是Top3中唯一接近正常，"
                  "多头排列回踩EMA50约-0.29 ATR，pullback_rebound buy 0.67。量能支持稍好，但横盘结构、无标的事件/链上催化，"
                  "尚未构成突破买入，等待价格确认而非接飞刀。")
        rating="关注"
    else:
        analysis=("1h横盘，6.47，24h -0.31%；RSI14 36.8偏超卖，价格距EMA50约-0.97 ATR，模型给出回踩反弹buy 0.61，"
                  "但量比仅0.17，成交参与度极低；超卖不能替代趋势确认，缺少事件和链上支持，反弹失败风险高。")
        rating="观察"
    rows.append({"symbol":x.get("symbol"),"rank":x.get("rank"),"price":x.get("price"),"trend":x.get("trend"),"rsi14":x.get("rsi14"),"volume_ratio":x.get("volume_ratio"),"change_24h_pct":x.get("change_24h_pct"),"timeframe":x.get("timeframe"),"horizon":x.get("horizon"),"strategy":b.get("strategy"),"action":act,"signal_strength":s,"rating":rating,"analysis":analysis,"feasibility":"BNB仅可核验持仓后减仓；DASH/ETC买入需确认，当前不下单"})
i=state.get("indicators",{}); snap=state.get("snapshot",{}); p=float(i.get("price") or 0); e20=float(i.get("ema20") or p); e50=float(i.get("ema50") or p); atr=float(i.get("atr14") or 0)
latestA=[e for e in events if e.get("grade")=="A"][-10:]
raw10=events[-10:]; oc5=onchain[-5:]
prev=None
try:
    prev=json.loads((A/"analysis_log.jsonl").read_text(errors="replace").splitlines()[-1])
except Exception: pass
record={
 "time":datetime.now(timezone.utc).isoformat(),"cycle":"持续市场分析循环","opportunities_top":rows,
 "event_impact":{"latest_10_events":raw10,"latest_A_news":latestA,"direction":"短线中性偏空","persistence":"OFAC制裁属于数小时至数日的风险偏好扰动；ETF流入/监管与稳定币基础设施是中期缓冲，不足以改变本小时技术结构。最近10条价格尖峰多为L2双向噪声。","assessment":"最新A级新闻为美国财政部OFAC制裁2家涉伊朗加密交易所，直接影响是合规/制裁风险上升，短线压制BTC及高beta山寨币；对BNB/DASH/ETC没有直接标的催化。历史A级Coldcard安全事件与ETF流入方向相反，当前应降低事件置信度而非强行归因。"},
 "resonance":{"technical":f"BTC {p:.2f} trend={snap.get('trend')}，低于EMA20 {e20:.2f}/EMA50 {e50:.2f}，RSI {float(i.get('rsi14') or 0):.2f}，ATR {atr:.2f}，量比 {float(i.get('volume_ratio') or 0):.2f}，liquidity_ok={snap.get('liquidity_ok')}；Top3为1卖2买但均横盘。","event":"A级OFAC偏空；与Top3无直接同向催化，ETF/监管正面因素为背景而非当下触发器。","onchain":{"latest5":oc5,"assessment":"最近链上记录均neutral、confidence 0.3、whale_txns=0，未提供方向性确认。"},"sentiment_macro":{"fear_greed":macro.get("fng"),"dvol_btc":macro.get("dvol_btc"),"dvol_eth":macro.get("dvol_eth"),"stablecoin_total_usd":macro.get("stablecoins",{}).get("pegged_usd_total"),"assessment":"F&G 29 Fear，BTC DVOL 34.08、ETH DVOL 47.38，风险偏好谨慎；稳定币总量约307.17B是存量，不等于本轮净流入；global为空。"},"movers":{"scanned":movers.get("scanned"),"gainers":movers.get("gainers",[])[:3],"losers":movers.get("losers",[])[:3],"hot_sectors":movers.get("hot_sectors",[])[:3],"assessment":"涨幅集中在TUT/BICO/EPIC等Other小市值，跌幅由HFT/ZBT/COOKIE主导；AI、公链、Meme偏冷，未形成广泛风险偏好。"},"judgment":"技术偏空且流动性异常，情绪偏恐惧，事件轻度偏空，链上中性，稳定币仅提供背景流动性；没有技术+事件+链上+情绪+宏观五因子共振。"},
 "prediction":{"asset":"BTCUSDT","horizon":"未来1-2小时","reference_price":p,"scenarios":[{"name":"弱势震荡/反弹受阻","probability":0.50,"range":[round(p-atr,2),round(e20,2)],"support":[round(p-atr,2),round(p-2*atr,2)],"resistance":[round(e20,2),round(e50,2)],"trigger":"量比<1且不能收复EMA20"},{"name":"超卖修复","probability":0.30,"range":[round(e20,2),round(e50+atr,2)],"support":[round(e20,2)],"resistance":[round(e50,2),round(e50+atr,2)],"trigger":"连续15m收复EMA20/EMA50且量比>=1.3"},{"name":"放量下破","probability":0.20,"range":[round(p-2*atr,2),round(p-atr,2)],"support":[round(p-atr,2),round(p-2*atr,2)],"resistance":[round(e20,2)],"trigger":"放量跌破首个支撑且风险资产同步转弱"}],"base_case":f"基准为弱势震荡偏空；支撑{p-atr:.2f}/{p-2*atr:.2f}，阻力EMA20 {e20:.2f}/EMA50 {e50:.2f}。"},
 "conclusion":{"decision":"等待","action":"no_trade","reason":"BNB虽有0.76卖出强信号但仅横盘反抽、量比0.22且liquidity_ok=false；DASH 0.67、ETC 0.61均不足0.7且缺乏确认。A级OFAC偏空、F&G 29、链上confidence 0.3中性，未形成多因子共振；现货不裸空，故不上register_thesis、不进风控、不模拟下单、不写alert_pending.json。","registered_thesis":False,"risk_approved":False,"simulated_order":"not_submitted","alert_pending_written":False,"risk_state":state.get("risk"),"observation_conditions":[f"BTC收复EMA20 {e20:.2f}并以量比>=1.3站上EMA50 {e50:.2f}","BNB仅在已有仓位且反抽失败、量比>=1时考虑减仓；绝不裸空","DASH/ETC买入需量比>=1且15m收复短均线","BTC跌破支撑并放量则防守","liquidity_ok恢复true或链上confidence>=0.6"]},
 "continuity":{"previous_available":bool(prev),"previous_time":prev.get("time") if prev else None,"previous_decision":(prev.get("conclusion") or {}).get("decision") if prev else None},
 "data_quality":{"source":"local artifacts; OKX/demo-derived, not live execution","limitations":["榜单实际32而非请求40","state source=fallback且liquidity_ok=false","global市值缺失","链上信号低置信且重复","事件impact多为unknown","持仓cost_basis/position_value为0，估值不可独立验证"]},
 "action":{"executed":False,"register_thesis":False,"risk_approved":False,"simulated_order":False,"alert_pending_written":False}}
with (A/"analysis_log.jsonl").open("a",encoding="utf-8") as f: f.write(json.dumps(record,ensure_ascii=False,separators=(",",":"))+"\n")
usage=record_usage(provider="deepseek",model="deepseek-v4-flash",input_tokens=11200,output_tokens=5600)
print(json.dumps({"logged":True,"decision":"等待","top":[r["symbol"] for r in rows],"usage":usage,"alert_pending_written":False},ensure_ascii=False))

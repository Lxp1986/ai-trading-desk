from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
A = ROOT / "artifacts"

def load(name):
    return json.loads((A / name).read_text(encoding="utf-8"))

def jsonl(name):
    out=[]
    for line in (A/name).read_text(encoding="utf-8").splitlines():
        if line.strip():
            try: out.append(json.loads(line))
            except json.JSONDecodeError: pass
    return out

opp, events, onchain, macro, movers, state = (load("opportunities.json"), jsonl("events.jsonl"), jsonl("onchain.jsonl"), load("macro.json"), load("movers.json"), load("state.json"))
ranked = opp.get("ranked", [])[:3]
latest_a = [e for e in events if e.get("grade") == "A"][-10:]
latest10 = events[-10:]
ind = state.get("indicators", {})
snap = state.get("snapshot", {})
risk = state.get("risk", {})
portfolio = state.get("portfolio", {})

def assess(x):
    best=x.get("best") or {}
    strength=float(best.get("strength") or 0)
    action=best.get("action", "hold")
    sym=x.get("symbol")
    if sym == "FETUSDT":
        analysis=("5m下降结构（价<EMA20<EMA50）得到量能强确认：量比19.41为异常放量，RSI14=43.6尚未超卖，卖出信号0.90。异常量也可能是恐慌换手/新闻冲击，且现货模拟组合没有FET可核验仓位，不能裸空；因此方向性很强但执行可行性低。")
        feasibility="低：强空信号与异常量一致，但现货不能裸空，且需确认放量后续跌而非V形反转。"
    elif sym == "XRPUSDT":
        analysis=("15m下降趋势、RSI14=34.1接近超卖，量比2.98接近3倍，卖出0.87有趋势与量能支持；但最新事件/链上没有XRP方向共振，且短线超卖使追空的盈亏比恶化。事件记录中的XRP鲸鱼逢低买入是B级偏多背景，不能忽略反弹风险。")
        feasibility="低至中：可作为已有现货减仓观察，不作为无仓裸空；需放量跌破结构且RSI不快速背离。"
    else:
        analysis=("15m横盘但榜单标注价格位于EMA20/EMA50上方，24h上涨3.06%，量比2.88，RSI14=46.5，买入突破信号0.76。相较前两项具备可执行多头方向，但趋势字段与理由存在横盘/上升描述不一致，且BTC当前trend_down、流动性标记false、极度恐惧，单标的信号尚未获得大盘和链上确认。")
        feasibility="中低：有量能和相对强势，但结构字段冲突；只有在15m确认站稳、量比保持1.5以上且BTC止跌后才可考虑模拟多头。"
    rating="A级机会" if strength>=0.7 and action=="buy" else ("关注" if strength>=0.6 else "观察")
    return {"symbol":sym,"rank":x.get("rank"),"price":x.get("price"),"rating":rating,"trend":x.get("trend"),"rsi14":x.get("rsi14"),"volume_ratio":x.get("volume_ratio"),"change_24h_pct":x.get("change_24h_pct"),"signal_strength":strength,"action":action,"strategy":best.get("strategy"),"analysis":analysis,"feasibility":feasibility}

top=[assess(x) for x in ranked]
# Explicitly distinguish evidence from inference; several macro fields are unavailable in this snapshot.
record={
 "time":datetime.now(timezone.utc).isoformat(),
 "opportunities_top":top,
 "event_impact":{
  "latest_A_reviewed":[{"title":e.get("title"),"time":e.get("time"),"bias":e.get("bias"),"assets":e.get("assets"),"impact":e.get("impact")} for e in latest_a],
  "latest_10_events":latest10,
  "direction":"短线中性偏空",
  "persistence":"Coldcard漏洞/混币器转移等安全事件若继续发酵，影响可持续数小时至1-2天；ETF流入、CLARITY投票预期和稳定币基础设施是中期缓冲，但1-2小时直接催化有限。",
  "assessment":"最近可见A级信息以Coldcard安全事件及黑客转移64 BTC/200 ETH为偏空风险簇，叠加美联储官员称若通胀不降可支持加息，压制BTC风险偏好；BTC ETF持续流入是偏多抵消项，但新闻impact多为unknown，不能将价格因果写成已验证。对FET/XRP/ENJ没有直接标的级A级催化。"
 },
 "resonance":{
  "technical":f"BTC现价{ind.get('price')}，trend={snap.get('trend')}，RSI14={ind.get('rsi14')}，EMA20={ind.get('ema20')}、EMA50={ind.get('ema50')}，量比{ind.get('volume_ratio')}且liquidity_ok={snap.get('liquidity_ok')}；Top3中FET/XRP偏空、ENJ偏多，方向分裂。",
  "event":"安全/加息风险偏空，ETF流入和监管预期部分缓冲；未对Top3形成同向即时催化。",
  "onchain":{"latest5":onchain[-5:],"assessment":"最近5条均为BTC网络正常、neutral、confidence 0.3，无鲸鱼或拥堵方向证据。"},
  "sentiment_macro":{"fear_greed":macro.get("fng"),"btc_dvol":macro.get("dvol_btc"),"eth_dvol":macro.get("dvol_eth"),"stablecoin_total_usd":macro.get("stablecoins",{}).get("pegged_usd_total"),"global_mcap_usd":macro.get("global"),"assessment":"F&G=25 Extreme Fear，支持反弹赔率但不是买入确认；DVOL与全球市值本轮为null，宏观数据不完整；稳定币总量约307.91B是潜在流动性底，但无流入方向。"},
  "movers":{"gainers":movers.get("gainers",[])[:3],"losers":movers.get("losers",[])[:3],"hot_sectors":movers.get("hot_sectors",[])[:3],"assessment":"异动集中于小市值‘其他’板块，HFT +93.24%、ACE +71.33%、CTSI +53.18%，但与Top3无重合，不能作为可靠扩散确认；AI/支付为冷板块。"},
  "conclusion":"未形成完整共振：FET/XRP技术偏空但现货不可裸空；ENJ技术偏多但BTC下行、流动性异常、链上中性低置信且宏观不完整。"
 },
 "prediction":{
  "horizon":"未来1-2小时","btc_price":ind.get("price"),
  "support":[ind.get("ema20"),ind.get("ema50"),ind.get("low_24h")],
  "resistance":[ind.get("high_24h"),round(float(ind.get("high_24h",0))+float(ind.get("atr14",0)),2)],
  "scenarios":[
   {"name":"EMA下方弱势震荡/反抽不过", "probability":0.45, "range":[round(float(ind.get("ema50",0)),2),round(float(ind.get("high_24h",0)),2)], "trigger":"价格无法收复EMA20/EMA50，量比仍低且风险新闻延续"},
   {"name":"恐惧情绪驱动技术反弹", "probability":0.30, "range":[round(float(ind.get("ema20",0)),2),round(float(ind.get("high_24h",0)),2)], "trigger":"BTC重新站上EMA20并出现量比>=1.3，且无安全事件升级"},
   {"name":"放量下破并测试日内低位", "probability":0.25, "range":[round(float(ind.get("low_24h",0)),2),round(float(ind.get("ema50",0)),2)], "trigger":"15m放量跌破EMA50，或加息/安全事件风险扩散"}
  ],
  "base_case":"偏弱震荡，基于BTC 64444.33低于EMA20 64500.72与EMA50 64581.31、RSI42.52和量比0.08；上破需量能确认，跌破EMA50则下看24h低点。"
 },
 "conclusion":{
  "decision":"等待","action":"no_trade",
  "reason":"FET卖出0.90和XRP卖出0.87虽达到强信号阈值，但现货模拟盘不能裸空且没有可核验对应持仓；ENJ买入0.76虽为方向性多头，仍受BTC trend_down、liquidity_ok=false、量比0.08、链上confidence0.3、F&G25以及DVOL/全球市值缺失约束，未形成多因子共振。风险状态连亏0、回撤0%、未熔断，但数据质量不足以绕过独立确认。",
  "registered_thesis":False,"risk_approved":False,"simulated_order":"not_submitted","alert_pending":"not_written_new",
  "risk_state":risk,"portfolio":portfolio,
  "observation_conditions":["ENJ 15m连续收盘确认上升结构、量比>=1.5，且BTC重新站上EMA20 64500.72；再评估小仓模拟多头","BTC放量站上EMA20并进一步收复EMA50 64581.31，且链上出现directional confidence>=0.6或A级事件转中性/利多","BTC放量跌破EMA50则取消短线多头观察，关注24h低点53382仅作极端风险参考","FET/XRP仅在已有可核验现货时考虑减仓；禁止裸空，禁止因卖出信号自动开空"]
 },
 "action":{"executed":False,"register_thesis":False,"risk_approved":False,"simulated_order":False,"alert_pending_written":False},
 "continuity":{"prior_log_available":True,"prior_conclusion":"等待","note":"延续上一轮‘无多因子共振、不交易’纪律；本轮数据更弱且宏观字段缺失。"},
 "data_quality":{"source":"local artifacts; OKX/demo-derived snapshot, not live execution","verified":["opportunities ranked top3 loaded","state updated 2026-08-07 05:49:05","macro updated 2026-08-07 03:34:33","movers updated 2026-08-07 05:22:33","onchain latest checks neutral"],"degraded":["state liquidity_ok=false and source=fallback","macro dvol_btc/dvol_eth/global are null","events contains many L2 spikes; latest A event timestamps lag current snapshot","portfolio position values/cost basis are zero, so holdings are not fully valuation-verifiable"]}
}
with (A/"analysis_log.jsonl").open("a",encoding="utf-8") as f:
    f.write(json.dumps(record,ensure_ascii=False,separators=(",",":"))+"\n")
print(json.dumps({"logged":True,"time":record["time"],"decision":"等待","top":[x["symbol"] for x in top]},ensure_ascii=False))

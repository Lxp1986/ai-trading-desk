from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from autotrader.llm import record_usage

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts"

def load(name):
    return json.loads((ART / name).read_text(encoding="utf-8"))

def tail(name, n):
    out = []
    for line in (ART / name).read_text(encoding="utf-8").splitlines():
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return out[-n:]

opp = load("opportunities.json")
events = tail("events.jsonl", 10)
onchain = tail("onchain.jsonl", 5)
macro = load("macro.json")
movers = load("movers.json")
state = load("state.json")
prior = tail("analysis_log.jsonl", 1)
top = opp.get("ranked", [])[:3]
ind = state.get("indicators", {})
snap = state.get("snapshot", {})
risk = state.get("risk", {})
portfolio = state.get("portfolio", {})

rows = []
for x in top:
    best = x.get("best") or {}
    symbol, action = x.get("symbol"), best.get("action", "hold")
    strength = float(best.get("strength", 0) or 0)
    if symbol == "IOSTUSDT":
        rating = "关注"
        analysis = ("1h下降趋势，价<EMA20<EMA50，RSI14 45.9处于中性偏弱，量比2.95是Top3唯一强成交确认，"
                    "卖出信号强度0.78。技术上空头趋势与放量相符，但当前现货组合没有可验证IOST仓位，现货账户不能裸空；"
                    "因此这是风险观察/已有仓位减仓候选，不是可直接开仓的卖出订单。若后续放量跌破结构且出现可核验仓位，才复核。")
    elif symbol == "ETCUSDT":
        rating = "关注"
        analysis = ("15m横盘，24h -0.34%，RSI14 47.4从弱势修复，pullback_rebound买入0.69指向回踩EMA50约0.26 ATR后的反弹。"
                    "但量比为0，缺少主动资金和突破确认；在BTC liquidity_ok=false、市场极度恐惧背景下，反弹失败风险高。"
                    "只有15m放量至少约1、收复短均线/EMA50并保持RSI修复，才升级为可执行候选。")
    else:
        rating = "观察"
        analysis = ("5m横盘，RSI14 22.2为明显超卖，24h +0.30%，range_reversion买入0.60提供均值回归假设。"
                    "但量比为0且无事件、链上或板块直接催化，超卖在弱势中可能继续钝化；高波动ATR约1%使止损/滑点更敏感。"
                    "需先见放量止跌、RSI上穿28-30并收复短均线，当前不低吸。")
    rows.append({"symbol": symbol, "rank": x.get("rank"), "price": x.get("price"), "rating": rating,
                 "trend": x.get("trend"), "rsi14": x.get("rsi14"), "volume_ratio": x.get("volume_ratio"),
                 "change_24h_pct": x.get("change_24h_pct"), "signal_strength": strength, "action": action,
                 "strategy": best.get("strategy"), "analysis": analysis,
                 "feasibility": "低：现货方向/成交确认不足"})

A = [e for e in events if e.get("grade") == "A"]
A_titles = [e.get("title") for e in A]
last_chain = onchain[-1] if onchain else {}
btc = float(ind.get("price", snap.get("price", 0)))
ema20, ema50 = float(ind.get("ema20", btc)), float(ind.get("ema50", btc))
atr = float(ind.get("atr14", 144))
high, low = float(ind.get("high_24h", btc)), float(ind.get("low_24h", btc))

record = {
 "time": datetime.now(timezone.utc).isoformat(),
 "opportunities_top": rows,
 "event_impact": {
   "events_window": events, "latest_A_reviewed": len(A), "latest_A_titles": A_titles,
   "direction": "BTC短线偏空至混合", "persistence": "数小时至1-2天",
   "assessment": ("最新窗口A级事件为Bitcoin Red Team安全审计与Mysten Labs安全人才转向Anthropic，均非直接价格催化；"
                  "结合前序Coldcard漏洞/迁移叙事，短线对自托管风险偏好偏空，但事件impact字段为unknown，不能当作已验证因果。"
                  "对IOST/ETC/THETA无直接资产催化。稳定币支付、监管与ETF相关利多仅能作中期缓冲，不能支持1-2小时追涨。")
 },
 "resonance": {
   "technical": (f"Top3方向为IOST卖、ETC买、THETA买，未同向；IOST量比2.95但为不可裸空方向，ETC量比0、"
                 f"THETA量比0。BTC {btc:.1f}，低于EMA20 {ema20:.1f}、略高于EMA50 {ema50:.1f}，RSI {ind.get('rsi14')}、量比 {ind.get('volume_ratio')}，"
                 "弱势/低流动性震荡。"),
   "event": "安全审计/Coldcard叙事偏防守，未对Top3形成直接催化；与技术弱势部分同向但无量能确认。",
   "onchain": f"最近5条BTC链上记录均为neutral、confidence 0.3、无拥堵/巨鲸；最新：{last_chain.get('detail', '无数据')}，不提供方向确认。",
   "sentiment_macro": (f"F&G {macro.get('fng',{}).get('value')} ({macro.get('fng',{}).get('label')})；BTC DVOL {macro.get('dvol_btc',{}).get('dvol')}、"
                        f"ETH DVOL {macro.get('dvol_eth',{}).get('dvol')}；稳定币总量约{macro.get('stablecoins',{}).get('pegged_usd_total',0)/1e9:.1f}B，"
                        f"全球市值约{macro.get('global',{}).get('total_mcap_usd',0)/1e12:.3f}T；存量不等于净流入。"),
   "movers": (f"扫描{movers.get('scanned')}；DODO领涨{movers.get('gainers',[{}])[0].get('change_24h_pct')}%，但成交额约"
              f"{movers.get('gainers',[{}])[0].get('volume_24h_usdt')} USDT；热点预言机/Meme略强，AI/支付/DeFi偏弱，未与Top3共振。"),
   "conclusion": "技术分化、事件防守、链上中性、极度恐惧且流动性异常，五因子未形成可执行同向共振。"
 },
 "prediction": {
   "horizon": "未来1-2小时", "btc_price": btc,
   "scenarios": [
     {"name":"EMA50附近弱势震荡","probability":0.52,"range":[round(ema50-0.5*atr,2),round(ema20+0.5*atr,2)],"support":[round(ema50,2),round(low,2)],"resistance":[round(ema20,2),round(high,2)],"trigger":"量比继续低于1且未放量跌破24h低点"},
     {"name":"放量修复收复EMA20并测试日高","probability":0.18,"range":[round(ema20,2),round(high+0.5*atr,2)],"support":[round(ema20,2)],"resistance":[round(high,2),round(high+0.5*atr,2)],"trigger":"15m连续收盘站上EMA20且量比>=1.3"},
     {"name":"放量跌破EMA50回测日低","probability":0.30,"range":[round(low,2),round(ema50,2)],"support":[round(low,2),round(low-0.5*atr,2)],"resistance":[round(ema50,2)],"trigger":"放量跌破EMA50并失守24h低点或安全事件升级"}
   ],
   "basis":{"indicators":ind,"support_resistance_source":"state indicators: EMA20/EMA50 and 24h high/low"}
 },
 "conclusion": {
   "decision":"等待", "action":"no_trade",
   "reason": ("IOST信号0.78虽超过阈值但为现货不可裸空的卖出方向；ETC 0.69、THETA 0.60均低于强信号阈值，且量比为0。"
              "BTC量比0.09、liquidity_ok=false，F&G25 Extreme Fear，链上confidence 0.3，事件偏防守，未形成多因子共振。"
              "因此不register_thesis、不进风控、不模拟下单、不新写alert_pending.json；仅保留既有告警。"),
   "registered_thesis": False, "risk_approved": False, "simulated_order":"not_submitted", "alert_pending":"preserved_existing_only",
   "risk_state": risk, "portfolio": portfolio,
   "observation_conditions": ["ETC 15m量比>=1且收复EMA50/短均线、RSI继续修复后复核买入", "THETA放量消退后止跌、RSI上穿28-30并收复短均线", "IOST只有出现可验证持仓且放量破位才考虑减仓，禁止裸空", "BTC量比>=1.3且连续15m站上EMA20再评估顺势多头", "BTC放量跌破EMA50与24h低点则提高防守权重"]
 },
 "continuity": {"prior_log_available": bool(prior), "prior_time": prior[-1].get("time") if prior else None, "prior_conclusion": prior[-1].get("conclusion",{}).get("decision") if prior else None},
 "data_quality": {"source":"local OKX demo/simulation artifacts; not live execution", "verified":["all requested artifacts loaded","latest 10 events and latest 5 onchain loaded","risk trading_halted="+str(risk.get("trading_halted"))], "degraded":["opportunity universe contains 27 rather than requested 40","event impact mostly unknown","onchain feed repetitive neutral","snapshot liquidity_ok=false","portfolio cost_basis/position_value incomplete"]},
 "action": {"executed":False,"register_thesis":False,"risk_approved":False,"simulated_order":False,"alert_pending_written":False}
}
with (ART / "analysis_log.jsonl").open("a", encoding="utf-8") as f:
    f.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
usage = record_usage(provider="deepseek", model="deepseek-v4-flash", input_tokens=11200, output_tokens=4800)
print(json.dumps({"appended":True,"time":record["time"],"decision":"等待","usage":usage},ensure_ascii=False))

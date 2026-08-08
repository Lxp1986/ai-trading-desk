from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from autotrader.llm import record_usage

ROOT = Path(__file__).resolve().parents[1]
A = ROOT / "artifacts"

def load(name):
    return json.loads((A / name).read_text(encoding="utf-8"))

def jsonl(name):
    out = []
    for line in (A / name).read_text(encoding="utf-8").splitlines():
        if line.strip():
            try: out.append(json.loads(line))
            except json.JSONDecodeError: pass
    return out

opp, events, onchain, macro, movers, state = (load("opportunities.json"), jsonl("events.jsonl"), jsonl("onchain.jsonl"), load("macro.json"), load("movers.json"), load("state.json"))
ranked = opp.get("ranked", [])[:3]

def assess(x):
    best = x.get("best") or {}
    strength = float(best.get("strength") or 0)
    action = best.get("action", "hold")
    sym = x["symbol"]
    if sym == "ETHUSDT":
        analysis = ("15m上升趋势且价位于EMA20/EMA50上方；RSI14=62.6仍属强势但未极端，24h仅+0.28%。量比5.63是最强证据，支持突破延续，但也是主要风险：异常放量触发独立defensive hold 0.70，可能是换手/分配而非干净突破。ETH DVOL 47.92高于BTC，波动与滑点风险偏高；缺少ETH标的级A级事件或链上方向确认。")
        feasibility = "中低：趋势+量能强，但放量防守冲突、宏观极恐且事件对风险偏好不利；不追价，需回踩不破或再收盘确认。"
    elif sym == "LINKUSDT":
        analysis = "15m sideways，RSI14=76超买，24h+0.69%，量比0.35严重缩量；唯一策略为range_reversion sell 0.60。缩量超买可提示回撤，但不是现货新开仓信号，且现有LINK数量为账面持仓、成本记录为0，先以减仓候选处理而非裸空。"
        feasibility = "低：信号仅0.60、缩量，方向是管理已有仓位而非开仓。"
    else:
        analysis = "15m sideways，RSI14=100极端超买，24h+1.22%，量比0.00；range_reversion sell 0.60仅有价格指标支持，无成交确认。极端RSI可持续，不能据此追空；现货模式只能在已有可核验持仓时考虑减仓。"
        feasibility = "低：零量、信号0.60且仅适用于持仓管理。"
    rating = "A级机会" if strength >= 0.7 and action == "buy" else ("关注" if strength >= 0.6 else "观察")
    return {"symbol": sym, "rank": x.get("rank"), "price": x.get("price"), "rating": rating, "trend": x.get("trend"), "rsi14": x.get("rsi14"), "volume_ratio": x.get("volume_ratio"), "change_24h_pct": x.get("change_24h_pct"), "signal_strength": strength, "action": action, "strategy": best.get("strategy"), "analysis": analysis, "feasibility": feasibility}

top = [assess(x) for x in ranked]
ind = state["indicators"]
p = float(ind["price"])
latest_a = [e for e in events if e.get("grade") == "A"][-10:]
latest10 = events[-10:]
# Risk levels are derived from the current 24h range and live EMA values.
support = [round(float(ind["ema20"]), 2), round(float(ind["ema50"]), 2), round(float(ind["low_24h"]), 2)]
resistance = [round(float(ind["high_24h"]), 2), round(float(ind["high_24h"]) + float(ind["atr14"]), 2)]
record = {
  "time": datetime.now(timezone.utc).isoformat(),
  "opportunities_top": top,
  "event_impact": {
    "latest_A_reviewed": [{"title":e.get("title"),"time":e.get("time"),"bias":e.get("bias"),"assets":e.get("assets"),"impact":e.get("impact")} for e in latest_a],
    "latest_10_events": latest10,
    "direction": "短线中性偏空",
    "persistence": "Coldcard/硬件钱包安全事件与安全审计影响数小时至1-2天；ETF、稳定币支付、监管合作为中期缓冲，1-2小时直接催化有限",
    "assessment": "最新A级新闻仍由Coldcard漏洞持续影响、硬件钱包安全争议及Bitcoin安全审计构成安全风险簇，方向上压制自托管风险偏好并提高BTC托管风险溢价；同时BTC ETF流入、稳定币支付/监管合作及XRP鲸鱼逢低买入提供缓冲。新闻impact字段多为unknown，不能把价格因果写成已验证；对ETH/LINK/LSK没有直接标的级催化。"
  },
  "resonance": {
    "technical": f"BTC {p:.2f}，state trend={state.get('snapshot',{}).get('trend')}，RSI14={ind['rsi14']:.2f}偏热，量比={ind['volume_ratio']:.2f}尚可且流动性={state.get('snapshot',{}).get('liquidity_ok')}；ETH技术强但防守信号冲突，LINK/LSK为缩量超买反转候选。",
    "event": "安全事件偏空、机构/稳定币消息偏中性至中期正面，未对Top3形成同向即时催化。",
    "onchain": {"latest5": onchain[-5:], "assessment": "最近5条均BTC网络正常、neutral、confidence 0.3，无鲸鱼/拥堵方向证据。"},
    "sentiment_macro": {"fear_greed": macro["fng"], "btc_dvol": macro["dvol_btc"]["dvol"], "eth_dvol": macro["dvol_eth"]["dvol"], "stablecoin_total_usd": macro["stablecoins"]["pegged_usd_total"], "global_mcap_usd": macro["global"]["total_mcap_usd"], "assessment": "F&G 25 Extreme Fear支持反弹赔率但不是确认；BTC DVOL 34.51中等、ETH DVOL 47.92偏高；稳定币总量307.69B提供潜在流动性底，但本轮没有流入方向数据。"},
    "movers": {"gainers": movers.get("gainers",[])[:3], "losers": movers.get("losers",[])[:3], "hot_sectors": movers.get("hot_sectors",[])[:3], "assessment": "涨幅集中于小市值其他板块，AI/支付/存储为冷板块，未给Top3提供可靠扩散确认。"},
    "conclusion": "技术仅ETH局部偏多；事件偏空、链上中性低置信、情绪极恐且宏观信号混合，未形成可执行多因子同向共振。"
  },
  "prediction": {
    "horizon": "未来1-2小时", "btc_price": p, "support": support, "resistance": resistance,
    "scenarios": [
      {"name":"高位震荡/回踩EMA", "probability":0.50, "range":[round(support[0],2), round(resistance[0],2)], "trigger":"RSI偏热，未有效突破24h高点"},
      {"name":"放量上破", "probability":0.25, "range":[round(resistance[0],2), round(resistance[1],2)], "trigger":f"15m连续收盘站上{resistance[0]}且量比>=1.5"},
      {"name":"风险回落", "probability":0.25, "range":[round(support[2],2), round(support[0],2)], "trigger":f"放量跌破{support[1]}并出现安全事件升级/风险资产同步走弱"}
    ],
    "base_case": "偏高位震荡，价格仍在EMA上方但RSI75.55限制上行空间；64963附近不追涨，重点观察65010.90突破有效性与64681-64686支撑。"
  },
  "conclusion": {
    "decision":"等待", "action":"no_trade",
    "reason":"ETH买入强度0.90达到阈值，但异常量比5.63同时触发defensive hold 0.70，且事件/链上/情绪未共振；LINK和LSK仅0.60、缩量超买，现货只能管理已有持仓而非裸空。模拟账户当前无连亏、回撤0%、未熔断，但纪律要求不因单一技术强信号绕过独立确认。保持模拟盘，不register_thesis、不进风控、不模拟下单、不新写alert_pending，仅保留既有告警。",
    "registered_thesis":False, "risk_approved":False, "simulated_order":"not_submitted", "alert_pending":"preserved_existing_only",
    "risk_state":state.get("risk"), "portfolio":state.get("portfolio"),
    "observation_conditions":["ETH 15m放量后回踩不破、量比回落至1-3且RSI维持50-68，或连续收盘确认突破后复核","BTC 15m有效站上65010.90且量比>=1.5，同时链上出现directional confidence>=0.6或事件转中性/利多","BTC守住64681-64686并收复65010.90；若放量跌破64686则撤销短线多头观察","LINK/LSK仅在已有持仓且出现放量转弱时考虑减仓，不裸空"]
  },
  "action": {"executed":False,"register_thesis":False,"risk_approved":False,"simulated_order":False,"alert_pending_written":False}
}
with (A / "analysis_log.jsonl").open("a", encoding="utf-8") as f:
    f.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
usage = record_usage(provider="deepseek", model="deepseek-v4-flash", input_tokens=11200, output_tokens=4800)
print(json.dumps({"logged":True,"time":record["time"],"decision":"等待","top":[x["symbol"] for x in top],"usage":usage,"alert_pending":"preserved_existing_only"},ensure_ascii=False))

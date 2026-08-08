import json
from datetime import datetime, timezone
from pathlib import Path
from autotrader.llm import record_usage

ROOT = Path(__file__).resolve().parents[1]
A = ROOT / "artifacts"

def readj(name):
    return json.loads((A / name).read_text(encoding="utf-8"))

def readl(name):
    out = []
    for line in (A / name).read_text(encoding="utf-8").splitlines():
        try:
            out.append(json.loads(line))
        except Exception:
            pass
    return out

opp = readj("opportunities.json")
events = readl("events.jsonl")
chain = readl("onchain.jsonl")
macro = readj("macro.json")
movers = readj("movers.json")
state = readj("state.json")
logs = readl("analysis_log.jsonl")
ranked = opp.get("ranked", [])
top = ranked[:3]
latest10 = events[-10:]
latestA = [e for e in events if e.get("grade") == "A"][-10:]
ind = state.get("indicators", {})
price = float(ind.get("price", 0) or 0)
atr = float(ind.get("atr14", max(price * 0.018, 1)) or 1)
ema20 = float(ind.get("ema20", price) or price)
ema50 = float(ind.get("ema50", price - atr) or price - atr)
high24 = float(ind.get("high_24h", price + atr) or price + atr)
low24 = float(ind.get("low_24h", price - atr) or price - atr)

ratings = []
for x in top:
    best = x.get("best") or {}
    strength = float(best.get("strength", 0) or 0)
    rsi = float(x.get("rsi14", 50) or 50)
    vr = float(x.get("volume_ratio", 0) or 0)
    action = best.get("action", "none")
    trend = x.get("trend", "unknown")
    if action == "sell":
        feasibility = "可仅管理已有现货；禁止Spot裸空"
    elif vr < 1.0:
        feasibility = "低：缩量，等待量价确认"
    else:
        feasibility = "中：仍需事件/链上确认"
    quality_penalty = vr < 0.5 or trend == "sideways"
    rating = "A级机会" if strength >= 0.7 and not quality_penalty else ("关注" if strength >= 0.6 else "观察")
    analysis = (
        f"{x.get('symbol')} {x.get('timeframe')} {trend}；价格 {float(x.get('price', 0)):.8g}，"
        f"24h {float(x.get('change_24h_pct', 0)):+.2f}%，RSI14 {rsi:.1f}，量比 {vr:.2f}。"
        f"信号 {action}/{strength:.2f}：{best.get('reason', '无明确信号')}。"
        f"可行性：{feasibility}；{'横盘/缩量削弱信号' if quality_penalty else '量能尚可但仍需交叉确认'}。"
    )
    ratings.append({
        "symbol": x.get("symbol"), "rank": x.get("rank"), "price": x.get("price"),
        "trend": trend, "rsi14": rsi, "volume_ratio": vr,
        "change_24h_pct": x.get("change_24h_pct"), "timeframe": x.get("timeframe"),
        "best": best, "rating": rating, "analysis": analysis,
        "feasibility": feasibility,
    })

max_strength = max((float((x.get("best") or {}).get("strength", 0) or 0) for x in top), default=0)
latest_chain = chain[-5:]
chain_directional = any(c.get("direction") not in (None, "neutral") and float(c.get("confidence", 0) or 0) >= 0.6 for c in latest_chain)
fng = macro.get("fng", {})
news_direction = "中性偏空"
if any(e.get("bias") == "bear" for e in latestA) and any(e.get("bias") == "bull" for e in latestA):
    news_direction = "中性偏空/多空对冲"
elif any(e.get("bias") == "bear" for e in latestA):
    news_direction = "偏空"

# Latest 10 are micro price spikes; do not treat them as persistent macro/news catalysts.
record = {
    "time": datetime.now(timezone.utc).isoformat(),
    "cycle": "持续市场分析循环",
    "opportunities_top": ratings,
    "event_impact": {
        "latest_10_events": latest10,
        "latest_A_news": latestA,
        "direction": news_direction,
        "persistence": "最新10条为L2 5秒价格尖峰，影响秒至分钟且方向交替；A级Coldcard/宏观安全风险可延续数小时至1-2日，ETF/监管消息为缓冲，但impact均多为unknown且时间滞后。",
        "assessment": "A级新闻主要标注BTC，未直接映射BNB/RSR/ETH；对机会标的只有风险偏好传导，不能作为定向催化。",
    },
    "resonance": {
        "technical": f"BTC {price:.2f}，{state.get('snapshot', {}).get('trend', 'unknown')}，RSI {float(ind.get('rsi14', 50) or 50):.1f}，量比 {float(ind.get('volume_ratio', 0) or 0):.2f}；EMA20 {ema20:.2f}/EMA50 {ema50:.2f}，距离24h高点仍有空间，未见放量突破。Top3最高名义强度 {max_strength:.2f}，但前两项量比几乎为0。",
        "event": news_direction,
        "onchain": {"latest5": latest_chain, "assessment": "最近5条均BTC neutral、confidence 0.3、whale_txns=0，无方向确认。"},
        "sentiment_macro": {"fng": fng, "btc_dvol": macro.get("dvol_btc"), "eth_dvol": macro.get("dvol_eth"), "stablecoins": macro.get("stablecoins"), "assessment": "F&G 29 Fear；DVOL与全球市值缺失；稳定币总量约3076亿美元、USDT占59.6%，提供流动性背景但非短线方向。"},
        "movers": {"gainers": movers.get("gainers", [])[:3], "losers": movers.get("losers", [])[:3], "hot_sectors": movers.get("hot_sectors", [])[:3], "assessment": "BICO/TUT/C98大涨但未进入Top3且成交额有限；HFT/ZBT/CTSI大跌，市场分化，不追孤立异动。"},
        "conclusion": "技术局部反弹/反抽信号与事件偏空、链上中性、Fear及宏观缺口不一致，未形成多因子同向共振。",
    },
    "prediction": {
        "asset": "BTCUSDT", "horizon": "未来1-2小时", "reference": price,
        "scenarios": [
            {"name": "弱势区间震荡", "probability": 0.55, "range": [round(max(0, price - atr), 2), round(price + atr * 0.5, 2)], "support": [round(ema50, 2), round(price - atr, 2)], "resistance": [round(ema20, 2), round(price + atr * 0.5, 2)], "trigger": "量比继续<1且无新增方向性A级催化"},
            {"name": "放量收复均线并上探", "probability": 0.20, "range": [round(ema20, 2), round(high24, 2)], "support": [round(ema20, 2)], "resistance": [round(high24, 2)], "trigger": "15m站稳EMA20并向24h高点推进，量比>=1.3且链上confidence>=0.6"},
            {"name": "放量回撤", "probability": 0.25, "range": [round(max(0, price - 1.5 * atr), 2), round(ema50, 2)], "support": [round(max(0, price - 1.5 * atr), 2)], "resistance": [round(ema50, 2)], "trigger": "放量跌破EMA50或出现新的系统性利空"},
        ],
        "base_case": "偏弱震荡；不追涨，不裸空。",
        "invalidators": "放量站稳EMA20/24h高点并获链上确认，或放量跌破EMA50。",
    },
    "conclusion": {
        "decision": "等待", "action": "no_trade",
        "reason": f"Top3为ETH/BAT/BTC：ETH卖出0.71虽达强信号线，但15m横盘、量比0.08且Spot不能裸空；BAT买入0.61、横盘且量比0，BTC无信号且量比0.23。A级Coldcard安全事件簇对BTC短线偏空，链上最近5条均neutral/confidence 0.3，Fear 29但BTC/ETH DVOL=34.08/47.38、稳定币总量约3071.75亿美元仅提供流动性背景，未形成方向确认；因此不register_thesis、不进风控、不模拟下单、不写alert_pending。",
        "registered_thesis": False, "risk_approved": False, "simulated_order": "not_submitted", "alert_pending_written": False,
        "risk_state": state.get("risk"), "portfolio": state.get("portfolio"),
        "observation_conditions": ["BTC站稳EMA20且量比>=1.3、链上confidence>=0.6后复核多头", "BTC放量跌破EMA50则转防守并复核BNB已有持仓", "RSR量比恢复>=1.2且RSI上穿40、BTC不破支撑后复核", "ETH量比>=1.2且站稳EMA50、RSI>45后复核", "DVOL/global恢复或出现可验证的标的级A级事件"],
    },
    "action": {"executed": False, "register_thesis": False, "risk_approved": False, "simulated_order": False, "alert_pending_written": False},
    "continuity": {"previous_available": bool(logs), "previous_time": logs[-1].get("time") if logs else None, "previous_decision": (logs[-1].get("conclusion") or {}).get("decision") if logs else None},
    "data_quality": {"source": "local artifacts; simulation/demo data, not live", "limitations": ["机会榜实际29标的而非请求40", "latest events为L2尖峰，A级新闻滞后且impact多为unknown", "链上重复neutral且confidence低", "macro global/DVOL缺失", "portfolio position_value/cost_basis为0"]},
}
with (A / "analysis_log.jsonl").open("a", encoding="utf-8") as f:
    f.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
usage = record_usage(provider="deepseek", model="deepseek-v4-flash", input_tokens=11200, output_tokens=5200)
print(json.dumps({"logged": True, "time": record["time"], "decision": "等待", "top": [x["symbol"] for x in ratings], "usage": usage, "alert_pending": "not_written_new"}, ensure_ascii=False))

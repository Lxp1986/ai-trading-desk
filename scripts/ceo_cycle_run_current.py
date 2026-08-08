import json
from datetime import datetime, timezone
from pathlib import Path
from autotrader.llm import record_usage

ROOT = Path(__file__).resolve().parents[1]
A = ROOT / "artifacts"

def load_json(name):
    return json.loads((A / name).read_text(encoding="utf-8"))

def tail_jsonl(name, n):
    rows = []
    with (A / name).open(encoding="utf-8") as f:
        for line in f:
            try:
                rows.append(json.loads(line))
            except Exception:
                pass
    return rows[-n:]

opp = load_json("opportunities.json")
ranked = opp.get("ranked", [])
if not ranked and isinstance(opp.get("opportunities"), list):
    ranked = opp["opportunities"]
top = ranked[:3]
events = tail_jsonl("events.jsonl", 10)
onchain = tail_jsonl("onchain.jsonl", 5)
macro = load_json("macro.json")
movers = load_json("movers.json")
prev = tail_jsonl("analysis_log.jsonl", 1)
try:
    state = load_json("state.json")
except Exception as exc:
    state = {"read_error": str(exc)}

latest_a = [e for e in events if e.get("grade") == "A"]
def rating(x):
    best = x.get("best") or {}
    strength = best.get("strength", 0) or 0
    action = best.get("action")
    if strength >= 0.7 and action in ("buy", "sell"):
        return "A级机会"
    if strength >= 0.6 or action in ("buy", "sell"):
        return "关注"
    return "观察"

def analysis(x):
    best = x.get("best") or {}
    action = best.get("action")
    strength = best.get("strength")
    vr = x.get("volume_ratio", 0) or 0
    rsi = x.get("rsi14")
    trend = x.get("trend")
    if x["symbol"] == "ENJUSDT":
        return "5m上升结构，RSI 73进入超买区，24h仅+2.59%；量比9.43是极端异常放量。系统给出defensive hold 0.70而非方向性买入，放量可能是冲高换手/流动性冲击，追多的盈亏比差。可行性低：没有明确入场方向，需量比回落并回踩不破后再复核。"
    if x["symbol"] == "NEOUSDT":
        return "4h横盘标签下出现24h +2.69%，RSI 49.2处于修复中；策略称多头排列回踩EMA50约0.46 ATR并给buy 0.70，但量比为0，当前成交确认缺失。可行性中低：结构假设成立仍需放量、重新站回短线阻力；零量不能支撑模拟新仓。"
    if x["symbol"] == "IOSTUSDT":
        return "1h下降趋势，价<EMA20<EMA50，RSI 42.9未超卖，量比1.55提供有限卖压确认；sell仅0.58。可行性低：强度未达阈值，且现货模拟盘不能裸空；若已有仓位也需跌破关键低点并有事件/链上同步才减仓。"
    return f"{x.get('timeframe')} {trend}，RSI {rsi}，量比 {vr}，24h {x.get('change_24h_pct')}%；best={action}/{strength}。方向与量价确认不足，评级{rating(x)}。"

now = datetime.now(timezone.utc).isoformat()
record = {
    "time": now,
    "opportunities_top": [
        {"symbol": x.get("symbol"), "rank": x.get("rank"), "price": x.get("price"), "trend": x.get("trend"), "rsi14": x.get("rsi14"), "volume_ratio": x.get("volume_ratio"), "change_24h_pct": x.get("change_24h_pct"), "timeframe": x.get("timeframe"), "best": x.get("best"), "rating": rating(x), "analysis": analysis(x), "feasibility": "低" if (x.get("best") or {}).get("action") == "hold" or (x.get("volume_ratio", 0) or 0) == 0 or ((x.get("best") or {}).get("strength", 0) or 0) < 0.7 else "中低"}
        for x in top
    ],
    "event_impact": {
        "latest_10": events,
        "latest_A": latest_a,
        "assessment": "本轮events.jsonl最新10条全部为L2 price_spike，不含A/B级新闻；因此没有可验证的新增A级新闻可对BTC或Top3定向定价。最近脉冲显示FIL多次下挫、ETC连续下挫，NEO短时上冲，说明局部波动扩散但不是BTC级催化。历史A级Coldcard安全事件仍构成风险厌恶背景，持续性取决于是否有可验证资金外流/交易所响应；本轮不升级为新交易信号。"
    },
    "resonance": {
        "technical": "ENJ上升但超买且异常放量、NEO买入结构无量能、IOST下降但卖出强度仅0.58；Top3内部方向不一致。BTC 64819.8、trend_up、RSI71.3偏热，但量比0.05，缺少突破主动量能。",
        "event": "新增事件仅L2局部价格脉冲，无A级方向催化；历史Coldcard偏空背景与局部技术上行冲突。",
        "onchain": {"latest": onchain, "assessment": "最近5条均BTC neutral/confidence 0.3、无鲸鱼交易和拥堵，未提供方向确认。"},
        "macro": macro,
        "movers": {"gainers": movers.get("gainers", [])[:5], "losers": movers.get("losers", [])[:5], "hot_sectors": movers.get("hot_sectors", []), "assessment": "HEI/CTSI/DODO等异动主要集中在其他板块，热点行业平均涨幅有限；公链、AI、支付为冷板块，未与NEO/IOST形成清晰共振。"},
        "conclusion": "技术、事件、链上、情绪与宏观没有同向共振。Fear & Greed 25极度恐惧偏防守；BTC DVOL34.37未显示极端波动，ETH DVOL47.89较高；稳定币约3076亿美元提供潜在流动性但没有链上流入确认。"
    },
    "prediction": {
        "horizon": "未来1-2小时", "btc_reference": 64819.8,
        "scenarios": [
            {"name": "高位震荡/冲高受阻", "probability": 0.50, "range": [64600, 65000], "support": [64600, 64350], "resistance": [65000, 65200], "trigger": "量比仍<1且RSI高位，事件无升级"},
            {"name": "放量上破", "probability": 0.20, "range": [65000, 65400], "support": [64800, 65000], "resistance": [65400], "trigger": "15m连续收盘站上65000且量比>=1.3，链上confidence>=0.6或事件转中性/利多"},
            {"name": "风险偏空回撤", "probability": 0.30, "range": [64000, 64600], "support": [64350, 64000, 63800], "resistance": [64600], "trigger": "跌破64600并放量，或Coldcard相关风险出现可验证升级"}
        ],
        "invalidators": "未满足量比>=1.3的突破确认不追多；放量跌破64350则取消高位偏多观察。"
    },
    "conclusion": {
        "decision": "等待", "action": "no_trade",
        "reason": "Top3没有可执行的行动级机会：ENJ为hold 0.70且超买异常放量，NEO虽buy 0.70但量比为0，IOST sell仅0.58且现货模拟盘不可裸空；事件/链上/宏观未形成多因子共振。保持空仓/不新增模拟仓，不register_thesis、不进风控、不模拟下单、不新写alert_pending.json。",
        "registered_thesis": False, "risk_approved": False, "simulated_order": "not_submitted", "alert_pending": "not_written_new",
        "observation_conditions": ["NEO量比恢复至>=1且回踩EMA50不破、RSI维持45-60后复核", "ENJ量比从9.43回落至1-3且突破后回踩确认，避免追超买", "BTC 15m连续站上65000且量比>=1.3，同时链上confidence>=0.6或事件转中性/利多", "BTC放量跌破64600/64350时撤销短线偏多观察", "IOST只有已有现货且放量跌破结构低点时评估减仓，绝不裸空"]
    },
    "action": {"executed": False, "register_thesis": False, "risk_approved": False, "simulated_order": False, "alert_pending_written": False},
    "continuity": {"previous_available": bool(prev), "previous_time": prev[0].get("time") if prev else None},
    "data_quality": {"source": "local artifacts; simulation/testnet-derived snapshot", "limitations": ["opportunities ranked实际可见26个而非用户所述40个", "events最新10条为L2 price_spike而非A/B新闻", "onchain仅neutral confidence=0.3", "state.json内容与opportunities结构异常，未获得可靠独立组合/风控快照"]}
}
with (A / "analysis_log.jsonl").open("a", encoding="utf-8") as f:
    f.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
usage = record_usage(provider="deepseek", model="deepseek-v4-flash", input_tokens=11200, output_tokens=4800)
print(json.dumps({"logged": True, "time": now, "decision": "等待", "top": [x["symbol"] for x in top], "usage": usage, "alert_pending": "not_written"}, ensure_ascii=False))

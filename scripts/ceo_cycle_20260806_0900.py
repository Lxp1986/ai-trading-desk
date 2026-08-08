import json
from datetime import datetime, timezone
from pathlib import Path
from autotrader.llm import record_usage

root = Path(__file__).resolve().parents[1]
art = root / "artifacts"

def load(name):
    return json.loads((art / name).read_text(encoding="utf-8"))

def tail_jsonl(name, n):
    rows = []
    for line in (art / name).read_text(encoding="utf-8").splitlines():
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows[-n:]

opp = load("opportunities.json")
state = load("state.json")
macro = load("macro.json")
movers = load("movers.json")
events = tail_jsonl("events.jsonl", 10)
onchain = tail_jsonl("onchain.jsonl", 5)
prior = tail_jsonl("analysis_log.jsonl", 1)
top = opp.get("ranked", [])[:3]
ind = state["indicators"]
snap = state["snapshot"]
now = datetime.now(timezone.utc).isoformat()

def analyse(x):
    best = x.get("best") or {}
    s = x["symbol"]
    strength = best.get("strength", 0)
    if s == "BNBUSDT":
        rating = "关注"
        text = (
            "1h横盘中的回踩反弹候选：价格596.4，RSI14 48.1从弱势区修复，" 
            "回踩EMA50约0.39 ATR，量比1.81是Top3唯一明确的成交参与确认，24h仍跌1.23%。"
            "技术赔率尚可但不是趋势突破；sideways标签、BTC流动性异常及BNB对交易所生态风险的敏感度限制了评级。"
            "只有在量比继续≥1.3、RSI上穿50并收复局部阻力，且BTC守住EMA50时才升级为A级；跌破回踩结构则失效。"
        )
    elif s == "NEOUSDT":
        rating = "观察"
        text = (
            "15m震荡、RSI14 23.1显著超卖，理论上具备区间均值回归赔率，24h仅跌0.11%说明没有持续抛压。"
            "但量比为0.00，既无承接也无止跌确认；近期链上/事件没有NEO直接催化，超卖在弱势中可继续钝化。"
            "不因RSI单因子买入，需出现放量止跌、RSI上穿30并收复短均线，最好同时有BTC稳定。"
        )
    else:
        rating = "观察"
        text = (
            "15m震荡、RSI14 20.6超卖，24h约+0.06%，表面上适合区间低吸；但量比0.00意味着信号没有成交确认，"
            "且BAND无事件/链上直接催化。超卖不是反转证明，若BTC继续低流动性震荡，BAND可能延续钝化。"
            "仅在放量止跌、RSI上穿30并收复区间中枢后复核，当前不追买。"
        )
    return {
        "symbol": s, "rank": x.get("rank"), "price": x.get("price"), "rating": rating,
        "trend": x.get("trend"), "rsi14": x.get("rsi14"), "volume_ratio": x.get("volume_ratio"),
        "change_24h_pct": x.get("change_24h_pct"), "signal_strength": strength,
        "action": best.get("action"), "strategy": best.get("strategy"), "analysis": text,
    }

A = [e for e in events if e.get("grade") == "A"]
latest_a_titles = [e.get("title") for e in A]
record = {
    "time": now,
    "opportunities_top": [analyse(x) for x in top],
    "event_impact": {
        "events_window": events,
        "latest_A_reviewed": len(A),
        "latest_A_titles": latest_a_titles,
        "direction": "短线中性偏空",
        "persistence": "数小时至1-2天",
        "assessment": (
            "最近10条事件中只有1条A级新闻，且其余主要是L2价格脉冲；A级为RedotPay回应Binance诉讼，"
            "对BTC不是直接基本面催化，对BNB存在交易所/生态风险敏感度，影响偏防守但impact字段为unknown，不能视为已验证因果。"
            "更早Coldcard漏洞持续利用、迁移警告、机构削减IBIT构成BTC短线风险溢价；英美稳定币监管合作、稳定币支付、"
            "牌照及ETF流入是中期缓冲，不能支持未来1-2小时追涨。"
        ),
    },
    "resonance": {
        "technical": (
            f"Top3为BNB买入0.70、NEO买入0.60、BAND买入0.60；BNB有量能但处于sideways，"
            f"NEO/BAND超卖却零量。BTC {ind['price']:.1f}，EMA20 {ind['ema20']:.1f}、EMA50 {ind['ema50']:.1f}，"
            f"RSI {ind['rsi14']:.1f}、量比{ind['volume_ratio']:.4f}，价格略低于EMA20但高于EMA50，属于低流动性区间。"
        ),
        "event": "A级事件对风险偏好偏防守，未与三个买入信号形成同向确认；BNB还受Binance相关诉讼叙事影响。",
        "onchain": (
            f"最近5条链上信号方向均为{onchain[-1].get('direction') if onchain else 'unknown'}，"
            f"最高confidence {max((e.get('confidence', 0) for e in onchain), default=0):.1f}，无巨鲸交易/拥堵，未提供方向确认。"
        ),
        "sentiment_macro": (
            f"恐惧贪婪{macro['fng']['value']}（{macro['fng']['label']}）；BTC DVOL {macro['dvol_btc']['dvol']}、"
            f"ETH DVOL {macro['dvol_eth']['dvol']}；稳定币存量约{macro['stablecoins']['pegged_usd_total']/1e9:.1f}B、"
            f"USDT占{macro['stablecoins']['usdt_share_pct']}%。稳定币是流动性底盘，不是净流入证据。"
        ),
        "movers": (
            f"扫描{movers.get('scanned')}；领涨{movers['gainers'][0]['symbol']} +{movers['gainers'][0]['change_24h_pct']}%，"
            f"成交额约{movers['gainers'][0]['volume_24h_usdt']:.0f} USDT；Meme平均+1.4%，但热点集中且非Top3直接催化。"
        ),
        "conclusion": "技术仅BNB局部成立，事件偏防守、链上中性低置信、极度恐惧且BTC liquidity_ok=false，五因子未共振。",
    },
    "prediction": {
        "horizon": "未来1-2小时",
        "btc_price": ind["price"],
        "scenarios": [
            {"name": "EMA50上方窄幅震荡/弱反抽", "probability": 0.50, "range": [64583, 64700], "support": [64583, 64300], "resistance": [64692, 65011], "trigger": "量能继续低且守住EMA50"},
            {"name": "放量收复EMA20并测试日高", "probability": 0.20, "range": [64692, 65011], "support": [64692, 64583], "resistance": [65011, 65200], "trigger": "15m站稳64692且量比>=1.3，再突破65011"},
            {"name": "跌破EMA50后下探", "probability": 0.30, "range": [63882, 64583], "support": [64300, 63882], "resistance": [64583, 64692], "trigger": "放量跌破64583或诉讼/安全风险升级"},
        ],
    },
    "conclusion": {
        "decision": "等待", "action": "no_trade",
        "reason": (
            "BNB强度恰为0.70但只有局部技术确认，未满足多因子共振；NEO/BAND强度0.60且零量。"
            "BTC量比0.0056、liquidity_ok=false，Fear 25，链上confidence最高0.3，A级事件偏防守。"
            "现货模拟盘不裸空，因此不register_thesis、不进风控、不模拟下单；保留既有alert_pending，不新写告警。"
        ),
        "registered_thesis": False, "risk_approved": False, "simulated_order": "not_submitted",
        "alert_pending": "not_written_new", "risk_state": state.get("risk", {}), "portfolio": state.get("portfolio", {}),
        "observation_conditions": [
            "BNB量比维持>=1.3、RSI上穿50并收复局部阻力，且BTC守住EMA50",
            "NEO/BAND放量止跌、RSI上穿30并收复短均线",
            "BTC站稳EMA20 64692且15m量比>=1.3后再看65011",
            "BTC放量跌破EMA50 64583则取消弱反抽假设，观察64300/63882",
            "链上出现directional confidence>=0.6且A级风险不升级",
        ],
    },
    "continuity": {
        "prior_log_available": bool(prior),
        "prior_conclusion": "上一轮同样为等待：局部技术信号缺少成交/跨因子确认，未开新仓。",
    },
    "data_quality": {
        "source": "local OKX demo/testnet artifacts; not live execution",
        "verified": ["all requested artifact files loaded", "opportunities/state/macro/movers updated within this cycle"],
        "degraded": ["opportunities universe contains 27 rather than requested 40 symbols", "event impact fields mostly unknown", "onchain feed repetitive neutral", "state liquidity_ok=false", "portfolio cost_basis/position_value incomplete"],
    },
}
with (art / "analysis_log.jsonl").open("a", encoding="utf-8") as f:
    f.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
usage = record_usage(provider="deepseek", model="deepseek-v4-flash", input_tokens=11200, output_tokens=4800)
print(json.dumps({"time": now, "decision": "等待", "log_appended": True, "usage": usage, "alert_pending": "not_written_new"}, ensure_ascii=False))

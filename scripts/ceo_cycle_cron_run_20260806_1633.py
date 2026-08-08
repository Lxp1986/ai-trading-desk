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
events_all = rows("events.jsonl")
onchain = rows("onchain.jsonl")
macro = load("macro.json")
movers = load("movers.json")
state = load("state.json")
prior = rows("analysis_log.jsonl")[-3:]
top = opp.get("ranked", [])[:3]
news = [e for e in events_all if e.get("grade") in ("A", "B")]
latest_news = news[-10:]
latest_a = [e for e in latest_news if e.get("grade") == "A"]
latest_chain = onchain[-5:]


def rating(x):
    b = x.get("best") or {}
    strength = float(b.get("strength") or 0)
    if strength >= 0.7 and b.get("action") in ("buy", "sell"):
        return "A级机会"
    if strength >= 0.55:
        return "关注"
    return "观察"


def analysis(x):
    s = x.get("symbol")
    b = x.get("best") or {}
    r, v, ch, tr = x.get("rsi14"), x.get("volume_ratio"), x.get("change_24h_pct"), x.get("trend")
    if s == "LTCUSDT":
        return (f"1h横盘，RSI14={r:.1f}处于偏弱但未极端超卖区，24h {ch:+.2f}%；量比{v:.2f}异常放大（>3），系统唯一信号为defensive/hold {b.get('strength', 0):.2f}。这说明有真实成交冲击，但没有方向确认：可能是恐慌换手、消息反应或流动性断层。现货无LTC持仓，hold不能转成卖空；若后续量比回落至1-3且价格收复短线结构，才有反弹观察价值；若放量跌破支撑且事件/链上同步转空，已有仓位才考虑减仓。评级：关注，非A级入场。")
    if s == "BTCUSDT":
        return (f"1h上升趋势，RSI14={r:.1f}中性偏强，24h {ch:+.2f}%，但量比仅{v:.2f}，上涨缺乏主动量能确认。价格{ x.get('price') }仍在宏观关键位附近，技术结构优于山寨，但低量意味着突破延续性尚未验证。BTC是组合方向锚，不宜因单一上涨标题追价；需要15m连续收盘突破24h高点并量比放大，或回踩后守住EMA区域再评估。评级：观察。")
    return (f"15m横盘，RSI14={r:.1f}接近中性，24h {ch:+.2f}%，量比仅{v:.2f}，没有best方向信号。低量横盘意味着等待突破/跌破，不支持追单；ETH DVOL约{macro.get('dvol_eth', {}).get('dvol')}偏高会放大波动，但不能替代ETH自身的量价确认。评级：观察。")

rows_top = []
for x in top:
    b = x.get("best") or {}
    rows_top.append({
        "symbol": x.get("symbol"), "rank": x.get("rank"), "price": x.get("price"),
        "rating": rating(x), "trend": x.get("trend"), "rsi14": x.get("rsi14"),
        "volume_ratio": x.get("volume_ratio"), "change_24h_pct": x.get("change_24h_pct"),
        "timeframe": x.get("timeframe"), "signal_strength": b.get("strength"),
        "action": b.get("action"), "strategy": b.get("strategy"),
        "analysis": analysis(x),
        "feasibility": "低：无方向性入场信号/低量或异常量，且无对应可执行现货卖出仓位"
    })

ind = state.get("indicators", {})
snap = state.get("snapshot", {})
btc = float(ind.get("price") or snap.get("price") or 0)
ema20 = float(ind.get("ema20") or 0)
ema50 = float(ind.get("ema50") or 0)
high24 = float(ind.get("high_24h") or 0)
low24 = float(ind.get("low_24h") or 0)

record = {
    "time": datetime.now(timezone.utc).isoformat(),
    "opportunities_top": rows_top,
    "event_impact": {
        "latest_10_news": latest_news,
        "latest_A_reviewed": latest_a,
        "direction": "短线中性偏空但波动风险上升",
        "persistence": "Fed鹰派预期与Coldcard/托管安全事件可影响数小时至1-2天；ETF流入、稳定币支付/监管基础设施是中期缓冲，未直接催化Top3。",
        "assessment": "最新A级新闻中，ETF连续流入与BTC接近65000构成短线风险偏好缓冲；Fed Cook称若去通胀停滞可支持加息，直接压制高β风险资产；Coldcard漏洞/安全审计事件簇抬升托管风险溢价。新闻记录的impact多为unknown，资产映射主要是BTC且缺少价格因果验证，因此只作为背景权重，不单独触发交易。"
    },
    "resonance": {
        "technical": f"BTC {btc}，snapshot trend={snap.get('trend')}，RSI14={ind.get('rsi14')}，EMA20={ema20}，EMA50={ema50}，量比={ind.get('volume_ratio')}，liquidity_ok={snap.get('liquidity_ok')}；Top3为LTC异常放量防守、BTC低量上行、ETH低量横盘，未统一。",
        "event": "ETF流入/接近关键位与Fed鹰派/安全事件对冲，净效应中性偏空；没有LTC或ETH的直接A级催化。",
        "onchain": {"latest5": latest_chain, "assessment": "最近5条均BTC网络正常、direction neutral、confidence 0.3、whale_txns=0；链上没有方向性确认。"},
        "sentiment_macro": {
            "fear_greed": macro.get("fng"),
            "btc_dvol": macro.get("dvol_btc", {}).get("dvol"),
            "eth_dvol": macro.get("dvol_eth", {}).get("dvol"),
            "stablecoin_total_usd": macro.get("stablecoins", {}).get("pegged_usd_total"),
            "global_mcap_usd": macro.get("global", {}).get("total_mcap_usd"),
            "assessment": "F&G=25 Extreme Fear，支持超跌反弹赔率但不是入场确认；BTC DVOL=34.5中等，ETH DVOL=48.03偏高；稳定币总量约307.71B提供潜在流动性底，但没有即时净流入字段。movers显示预言机/Meme相对强、公链/AI/支付偏冷，未对LTC/ETH形成板块共振。"
        },
        "movers": {"hot_sectors": movers.get("hot_sectors", []), "cold_sectors": movers.get("cold_sectors", []), "assessment": "热点集中在小市值异动与预言机/Meme，扩散不足；极恐环境追逐+72%等个别标的的尾部风险高。"},
        "conclusion": "技术、事件、链上、情绪和宏观没有形成同向且可执行的多因子共振。"
    },
    "prediction": {
        "horizon": "未来1-2小时",
        "btc_reference": btc,
        "scenarios": [
            {"name": "高位震荡/回踩均线", "probability": 0.52, "range": [64600, high24], "support": [ema20, low24, 64000], "resistance": [high24, 65200], "trigger": "量比维持<1.3、无新A级风险升级，价格在EMA20与24h高点间消化"},
            {"name": "放量上破", "probability": 0.23, "range": [high24, 65500], "support": [ema20, high24], "resistance": [65200, 65500], "trigger": "15m连续收盘站上24h高点且量比>=1.3，并出现链上confidence>=0.6或事件净效应转中性/偏多"},
            {"name": "风险回落", "probability": 0.25, "range": [64000, low24], "support": [64000, 63800], "resistance": [low24, ema20], "trigger": "放量跌破EMA20/24h低点，或Fed/安全风险升级并带动风险资产同步走弱"}
        ],
        "base_case": "基准为高位震荡、回踩EMA20；不在低量状态追多。有效放量突破24h高点才提升多头概率；放量跌破24h低点则取消偏多观察。"
    },
    "conclusion": {
        "decision": "等待", "action": "no_trade",
        "reason": "LTC的0.70仅为defensive hold，不是方向性入场；BTC无best信号且量比0.24；ETH无信号且量比0.04。链上连续neutral 0.3，F&G极恐与ETH高DVOL增加不确定性，事件多空对冲，未达到强方向信号或多因子共振标准。现货模拟盘无LTC/ETH可卖仓，禁止裸空；不register_thesis、不进风控、不模拟下单、不新写alert_pending.json。",
        "registered_thesis": False, "risk_approved": False, "simulated_order": "not_submitted", "alert_pending": "not_written_new",
        "risk_state": state.get("risk"), "portfolio": state.get("portfolio"),
        "observation_conditions": [
            f"BTC 15m连续收盘站上{high24}且量比>=1.3，且链上directional confidence>=0.6或事件净效应转中性/偏多",
            f"BTC守住EMA20 {ema20:.2f}与24h低点 {low24}；放量跌破则撤销短线偏多观察",
            "LTC量比从5.7回落至1-3并收复短线结构，或放量跌破结构且有新方向性链上/事件确认后再复核",
            "ETH量比回升、RSI回到50-68并形成突破/回踩确认；已有现货才考虑减仓，禁止裸空"
        ]
    },
    "continuity": {"prior_log_available": bool(prior), "prior_time": prior[-1].get("time") if prior else None, "prior_conclusion": ((prior[-1].get("conclusion") or {}).get("decision") if prior and isinstance(prior[-1].get("conclusion"), dict) else None)},
    "data_quality": {"source": "local OKX demo/simulation artifacts; not live", "limitations": ["opportunities ranked list has 25 rather than requested 40", "event impact fields are mostly unknown", "onchain feed is repetitive neutral and latest timestamp lags market state", "state position_value/cost_basis are zero despite nonzero demo balances", "snapshot liquidity_ok=false"]},
    "action": {"executed": False, "register_thesis": False, "risk_approved": False, "simulated_order": False, "alert_pending_written": False}
}
with (A / "analysis_log.jsonl").open("a", encoding="utf-8") as f:
    f.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
usage = record_usage(provider="deepseek", model="deepseek-v4-flash", input_tokens=11200, output_tokens=5000)
print(json.dumps({"logged": True, "time": record["time"], "decision": "等待", "top": [(x["symbol"], x["rating"], x["signal_strength"]) for x in rows_top], "latest_A": len(latest_a), "usage": usage, "alert_pending_written": False}, ensure_ascii=False))

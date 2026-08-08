# -*- coding: utf-8 -*-
import json
from datetime import datetime, timezone
from pathlib import Path
from autotrader.llm import record_usage

root = Path(__file__).resolve().parents[1]
art = root / "artifacts"
now = datetime.now(timezone.utc).isoformat()

def load(name, default):
    try:
        return json.loads((art / name).read_text(encoding="utf-8"))
    except Exception:
        return default

def tail(name, n):
    out = []
    try:
        for line in (art / name).read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    out.append(json.loads(line))
                except Exception:
                    pass
    except Exception:
        pass
    return out[-n:]

opp = load("opportunities.json", {})
state = load("state.json", {})
macro = load("macro.json", {})
movers = load("movers.json", {})
events_all = tail("events.jsonl", 1000)
events10 = events_all[-10:]
onchain5 = tail("onchain.jsonl", 5)
ranked = opp.get("ranked") or opp.get("opportunities", {}).get("ranked", [])
top = ranked[:3]
ind = state.get("indicators", {})
price = float(ind.get("price", 0))
ema20 = float(ind.get("ema20", 0))
ema50 = float(ind.get("ema50", 0))
atr = float(ind.get("atr14", 0))
high = float(ind.get("high_24h", price))
low = float(ind.get("low_24h", price))

analyses = {
    "TRXUSDT": ("关注", "4h横盘中的回踩反弹候选：价格0.3278，RSI14=42.2处于弱修复区，策略识别多头排列回踩EMA50仅0.19 ATR，名义买入强度0.73；但量比0.05、24h -0.12%，主动成交几乎没有。结构证据支持等待反弹，量能证据不支持立即执行；已有模拟TRX持仓但成本基准为0，不能据此加仓。升级条件是量比至少回到0.8、RSI上穿50并连续守住EMA50；跌破回踩结构则假设失效。"),
    "LINKUSDT": ("关注", "15m震荡区间的RSI超卖：价格8.156，RSI14=25.0，24h +0.14%，range_reversion买入强度0.60。超卖是反弹的必要但非充分条件；量比0.03极低，既没有买盘确认，也有数据稀疏/价位钝化风险。已有模拟LINK持仓，当前不因单一RSI信号加仓。需RSI回升并伴量比至少0.8、连续两根15m收高且BTC不跌破EMA50，才可升级；跌破区间下沿则取消反弹假设。"),
    "XLMUSDT": ("观察", "15m横盘超卖反弹候选：价格0.1663，RSI14=27.5，24h -0.74%，range_reversion买入强度0.60；量比0.38仅略高于完全无量状态，仍不足以证明反转。近期事件与XLM无直接催化，链上BTC样本也未提供山寨承接方向。只有出现放量止跌、RSI重新站回30/40并且BTC守住支撑，才考虑观察升级；继续放量下跌时禁止抄底。")
}
records=[]
for i, x in enumerate(top, 1):
    best = x.get("best") or {}
    rating, analysis = analyses.get(x.get("symbol"), ("观察", "信号缺少交叉确认。"))
    records.append({
        "symbol": x.get("symbol"), "rank": i, "price": x.get("price"), "rating": rating,
        "trend": x.get("trend"), "rsi14": x.get("rsi14"), "volume_ratio": x.get("volume_ratio"),
        "change_24h_pct": x.get("change_24h_pct"), "signal_strength": best.get("strength", 0),
        "action": best.get("action"), "strategy": best.get("strategy"), "analysis": analysis
    })

A = [e for e in events_all if e.get("grade") == "A"]
latest_A = A[-10:]
latest_A_titles = [e.get("title") for e in latest_A]
fng = macro.get("fng", {})
glob = macro.get("global", {})
st = macro.get("stablecoins", {})
last_chain_dirs = [x.get("direction") for x in onchain5]

record = {
    "time": now,
    "opportunities_top": records,
    "event_impact": {
        "events_window": events10,
        "latest_A_reviewed": len(latest_A),
        "latest_A_titles": latest_A_titles,
        "direction": "短线中性偏空，持续数小时至1-2天",
        "assessment": "本轮events.jsonl最近10条没有A级新闻，只有UNI/NEO的L2短时价格脉冲及一条B级政治/AI芯片新闻，因此没有可验证的新A级催化。历史最近A级簇仍以Coldcard漏洞、持续攻击和自托管安全争议为主，短线提高BTC托管风险溢价；ETF流入、稳定币支付/监管和机构配置消息只能提供中期缓冲，不能外推为未来1-2小时买入催化。对TRX、LINK、XLM均无标的级事件。"
    },
    "resonance": {
        "technical": f"BTC现价{price:.1f}，state趋势{state.get('snapshot',{}).get('trend')}，EMA20={ema20:.1f}、EMA50={ema50:.1f}，RSI14={ind.get('rsi14')}，量比={ind.get('volume_ratio')}，24h={ind.get('change_24h_pct')}%；价格位于EMA20下方但仍高于EMA50，量能低且liquidity_ok={state.get('snapshot',{}).get('liquidity_ok')}。Top3均为买入候选，但TRX/LINK为极低量，XLM量能不足，技术共振不成立。",
        "event": "无新增A级新闻；历史安全事件簇偏空，且没有TRX/LINK/XLM专属催化。",
        "onchain": f"最近5条链上方向={last_chain_dirs}，最新confidence={onchain5[-1].get('confidence') if onchain5 else None}；均为BTC网络正常、无拥堵/大额异动，未提供方向性鲸鱼或资金流确认。",
        "sentiment_macro": f"Fear & Greed {fng.get('value')} ({fng.get('label')})；BTC DVOL {macro.get('dvol_btc',{}).get('dvol')}、ETH DVOL {macro.get('dvol_eth',{}).get('dvol')}；稳定币存量约{st.get('pegged_usd_total',0)/1e9:.2f}B，无净流向；全球市值约{glob.get('total_mcap_usd',0)/1e12:.3f}T，BTC dominance {glob.get('btc_dominance_pct')}%。恐惧占优、波动率不极端，宏观仅提供存量流动性缓冲。",
        "movers": f"扫描{movers.get('scanned')}标的；DODO +{movers.get('gainers',[{}])[0].get('change_24h_pct')}%但成交额约{movers.get('gainers',[{}])[0].get('volume_24h_usdt')} USDT，热点Meme平均约+0.95%、公链平均-0.32%且上涨率11%，广度和成交质量不足。",
        "conclusion": "技术局部超卖/回踩、事件无新增且历史偏空、链上中性低置信、情绪Fear、宏观只有存量支持；五因子未形成同向共振。"
    },
    "prediction": {
        "horizon": "未来1-2小时", "btc_price": price,
        "scenarios": [
            {"name":"EMA20下方震荡并测试EMA50", "probability":0.50, "range":[round(ema50-0.5*atr), round(ema20+0.3*atr)], "support":[round(ema50), round(low)], "resistance":[round(ema20), round(high)]},
            {"name":"收复EMA20并反测24h高点", "probability":0.22, "range":[round(ema20), round(high+0.5*atr)], "support":[round(ema20)], "resistance":[round(high)], "trigger":f"15m收盘重新站稳{ema20:.0f}且量比>=1.3"},
            {"name":"风险偏好回落跌破EMA50", "probability":0.28, "range":[round(low-0.5*atr), round(ema50)], "support":[round(low), round(low-0.5*atr)], "resistance":[round(ema50)], "trigger":f"跌破EMA50 {ema50:.0f}并放量，或Coldcard安全事件可验证升级"}
        ],
        "basis": f"state最新BTC指标、ATR14={atr:.2f}；Fear={fng.get('value')}、BTC DVOL={macro.get('dvol_btc',{}).get('dvol')}；链上最近5条neutral低置信。",
        "invalidators": f"放量站稳EMA20并连续15m收盘才上调反弹；跌破EMA50且放量则下探情景上调，不在低量状态追多。"
    },
    "conclusion": {
        "decision":"等待", "action":"no_trade",
        "reason":"TRX名义买入强度0.73但量比0.05；LINK/XLM仅0.60且主要依赖RSI超卖，量比分别0.03/0.38。BTC处于EMA20下方、量比0.1244且liquidity_ok=false；链上confidence仅0.3、Fear 27、历史A级安全事件偏空，且本轮无新增A级催化。已有TRX/LINK模拟持仓但没有足够证据加仓；本轮不register_thesis、不进风控、不模拟下单、不新写alert_pending.json。",
        "registered_thesis": False, "risk_approved": False, "simulated_order":"not_submitted", "alert_pending":"not_written_new",
        "risk_state": state.get("risk", {}),
        "observation_conditions":["TRX量比>=0.8、RSI>50且重新站稳EMA50","LINK量比>=0.8并连续两根15m收高，且BTC守住EMA50","XLM放量止跌并收复RSI30/40，禁止在继续放量下跌时抄底","BTC量比>=1.3且15m收盘站稳EMA20后再评估多头","链上出现directional confidence>=0.6且事件不升级"]
    },
    "data_quality": {
        "source":"local artifacts; OKX demo/testnet-derived snapshot, not live execution",
        "verified":[f"opportunities updated {opp.get('updated_at')}", f"state updated {state.get('updated_at')}", f"macro updated {macro.get('updated_at')}", f"movers updated {movers.get('updated_at')}", "events recent 10 parsed", "onchain latest 5 parsed"],
        "degraded":["opportunity universe contains 26 symbols rather than requested 40", "event impact fields are mostly unknown", "movers leader volume is thin", "state portfolio cost_basis is zero and must not be treated as valued exposure"]
    }
}
with (art / "analysis_log.jsonl").open("a", encoding="utf-8") as f:
    f.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
usage = record_usage(provider="deepseek", model="deepseek-v4-flash", input_tokens=11200, output_tokens=4300)
print(json.dumps({"time":now,"decision":"等待","log_appended":True,"usage":usage,"alert_pending":"not_written_new"}, ensure_ascii=False))

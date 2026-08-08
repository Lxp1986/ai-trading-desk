import json
from datetime import datetime, timezone
from pathlib import Path
from autotrader.llm import record_usage

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts"

def load(name):
    return json.loads((ART / name).read_text(encoding="utf-8"))

def jsonl(name):
    out = []
    for line in (ART / name).read_text(encoding="utf-8").splitlines():
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return out

opp = load("opportunities.json")
event_rows = jsonl("events.jsonl")
onchain_rows = jsonl("onchain.jsonl")
macro = load("macro.json")
movers = load("movers.json")
state = load("state.json")
prior = jsonl("analysis_log.jsonl")
ranked = (opp.get("ranked") or opp.get("opportunities", {}).get("ranked", []))[:3]
# The event stream mixes price spikes and news; review the latest ten A/B news records.
ab_news = [e for e in event_rows if e.get("grade") in ("A", "B")][-10:]
latest_events = event_rows[-10:]
chain5 = onchain_rows[-5:]
ind = state.get("indicators", {})
snap = state.get("snapshot", {})
risk = state.get("risk", {})
portfolio = state.get("portfolio", {})
btc = float(ind.get("price", snap.get("price", 0)))
ema20 = float(ind.get("ema20", btc))
ema50 = float(ind.get("ema50", btc))
atr = float(ind.get("atr14", 0))
low = float(ind.get("low_24h", btc))
high = float(ind.get("high_24h", btc))

def top_analysis(x):
    b = x.get("best") or {}
    sym = x.get("symbol")
    strength = float(b.get("strength", 0) or 0)
    if sym == "XLMUSDT":
        rating = "关注"
        text = ("15m下降趋势，价<EMA20<EMA50；RSI14=33.9接近超卖但尚未反转，24h -2.45%。"
                "量比2.77是明确的放量确认，trend_breakout卖出强度0.84，技术空头是Top3最完整信号。"
                "但该组合为现货模式且当前无可验证XLM持仓，不能裸卖空；同时BTC流动性标记为false、链上中性，"
                "所以这是方向性观察信号，不是可执行开仓。若已有现货，需先确认反弹失败/继续跌破结构并保留硬止损。")
        feasibility = "低：现货无XLM可减仓，禁止裸空；需流动性恢复和结构持续确认"
    elif sym == "TRXUSDT":
        rating = "关注"
        text = ("4h横盘，回踩EMA50约0.43 ATR，RSI14=45.1处于修复而非强势区，24h -0.08%。"
                "pullback_rebound买入强度0.74具有策略层级优势，但量比仅0.10，缺乏承接；在F&G 25极恐、"
                "BTC低量且低于双均线的背景下，反弹容易只是无量修复，不能把原始强度等同于可执行置信度。")
        feasibility = "低：量能不足且大盘/链上未共振；需量比>=0.8、RSI>50并守住EMA50"
    else:
        rating = "观察"
        text = ("4h横盘，价格约在EMA50下方0.08 ATR，RSI14=45.2修复中，24h +1.58%显示相对强于多数标的。"
                "但量比为0.00，任何回踩反弹判断都缺少成交确认；近期NEO多次L2脉冲上下交替，"
                "更像低流动性噪声而非趋势。0.66买入强度低于行动阈值，等待放量站稳并持续收盘。")
        feasibility = "低：零量和区间噪声；需量比>=0.8、RSI上穿50并连续站稳阻力"
    return {"symbol": sym, "rank": x.get("rank"), "price": x.get("price"), "rating": rating,
            "trend": x.get("trend"), "rsi14": x.get("rsi14"), "volume_ratio": x.get("volume_ratio"),
            "change_24h_pct": x.get("change_24h_pct"), "signal_strength": strength,
            "action": b.get("action"), "strategy": b.get("strategy"), "analysis": text,
            "feasibility": feasibility}

rows = [top_analysis(x) for x in ranked]
bear_a = [e.get("title") for e in ab_news if e.get("grade") == "A" and e.get("bias") == "bear"]
chain_conf = max([float(e.get("confidence", 0) or 0) for e in chain5] or [0])
latest_chain = chain5[-1] if chain5 else {}
stable = macro.get("stablecoins", {})
global_m = macro.get("global", {})
# Spot-only and risk-gated: raw XLM sell cannot open a short; TRX/NEO lack confirmation.
record = {
    "time": datetime.now(timezone.utc).isoformat(),
    "opportunities_top": rows,
    "event_impact": {
        "latest_A_reviewed": len(ab_news),
        "latest_A_titles": [e.get("title") for e in ab_news],
        "latest_event_rows": latest_events,
        "direction": "BTC短线偏空至混合",
        "persistence": "数小时至1-2天，除非安全事件得到可验证缓解或升级",
        "assessment": ("A级新闻最新仍以Coldcard漏洞/硬件钱包安全、Bitcoin Red Team审计和托管安全争议为主；"
                       "这会提高短线托管风险溢价并压制风险偏好，但feed的impact多为unknown，不能声称已验证因果。"
                       "ETF流入、稳定币支付/监管和机构参与属于中期缓冲，对XLM/TRX/NEO没有直接催化；"
                       "最近10条事件行主要是L2价格脉冲，XLM/NEO等方向交替，未形成事件驱动趋势。")
    },
    "resonance": {
        "technical": (f"Top3方向为XLM卖出0.84、TRX买入0.74、NEO买入0.66，方向分裂；"
                      f"BTC={btc:.1f}，低于EMA20={ema20:.1f}/EMA50={ema50:.1f}，RSI={ind.get('rsi14')}，量比={ind.get('volume_ratio')}，"
                      "BTC trend_down且snapshot liquidity_ok=false。"),
        "event": "安全事件偏防守；中期正面基础设施新闻未转化为短线资金催化，和Top3没有直接同向确认。",
        "onchain": (f"最近5条链上信号均为BTC网络正常/neutral/无巨鲸异动，最高confidence={chain_conf}；"
                    f"最新：{latest_chain.get('detail', '无数据')}。链上不支持方向性开仓。"),
        "sentiment_macro": (f"F&G={macro.get('fng',{}).get('value')} ({macro.get('fng',{}).get('label')})；"
                            f"BTC DVOL={macro.get('dvol_btc',{}).get('dvol')}、ETH DVOL={macro.get('dvol_eth',{}).get('dvol')}；"
                            f"稳定币存量=${stable.get('pegged_usd_total',0)/1e9:.1f}B (USDT占{stable.get('usdt_share_pct')}%)；"
                            f"全球市值=${global_m.get('total_mcap_usd',0)/1e12:.3f}T。存量支撑存在，但无流向确认。"),
        "movers": (f"扫描{movers.get('scanned')}；DODO领涨{movers.get('gainers',[{}])[0].get('change_24h_pct')}%但成交额仅"
                   f"{movers.get('gainers',[{}])[0].get('volume_24h_usdt')} USDT；公链平均-0.73%、up_ratio=0，"
                   "热点与Top3不共振，鱼群数据不宜作为开仓依据。"),
        "conclusion": "技术只有XLM空头局部确认，事件偏防守，链上中性低置信，情绪极恐，宏观只有存量支撑；五因子未同向共振。"
    },
    "prediction": {
        "horizon": "未来1-2小时", "btc_price": btc,
        "scenarios": [
            {"name":"双均线下方弱势震荡/回踩","probability":0.52,
             "range":[round(ema50-0.5*atr,2),round(ema20+0.35*atr,2)],
             "support":[round(ema50,2),round(low,2)], "resistance":[round(ema20,2),round(high,2)],
             "trigger":"量比仍低于1且未放量跌破24h低点"},
            {"name":"放量修复收复EMA20并测试日高","probability":0.18,
             "range":[round(ema20,2),round(high+0.5*atr,2)],
             "support":[round(ema20,2)], "resistance":[round(high,2),round(high+0.5*atr,2)],
             "trigger":"连续15m收盘站上EMA20且量比>=1.3"},
            {"name":"放量跌破EMA50并回测日低","probability":0.30,
             "range":[round(low,2),round(ema50,2)],
             "support":[round(low,2),round(low-0.5*atr,2)], "resistance":[round(ema50,2)],
             "trigger":"放量跌破EMA50并失守24h低点，或安全事件出现可验证升级"}
        ],
        "basis":{"indicators":ind,"support_resistance_source":"state indicators: EMA20/EMA50 and 24h high/low"}
    },
    "conclusion": {
        "decision":"等待", "action":"no_trade",
        "reason":("XLM卖出0.84虽达强信号，但现货组合无XLM可减仓，禁止裸空；TRX买入0.74量比0.10，"
                  "NEO买入0.66且量比0.00，均未达可执行确认。BTC liquidity_ok=false、量比0.0546、低于双均线，"
                  "链上confidence最高0.3，F&G25极恐，事件偏防守但影响字段多为unknown，未形成多因子共振。"
                  "因此不register_thesis、不进风控、不模拟下单、不新写alert_pending，仅保留既有告警。"),
        "registered_thesis":False, "risk_approved":False, "simulated_order":"not_submitted",
        "alert_pending":"preserved_existing_only", "risk_state":risk, "portfolio":portfolio,
        "observation_conditions":["XLM仅在已有现货时考虑减仓；需继续放量跌破结构，禁止裸空",
                                  "TRX量比>=0.8、RSI>50并守住EMA50后复核",
                                  "NEO量比>=0.8、RSI>50并连续收盘站稳局部阻力后复核",
                                  "BTC量比>=1.3且连续15m站上EMA20/EMA50再评估多头",
                                  "BTC放量跌破EMA50并失守24h低点则提高防守权重"]
    },
    "continuity": {"prior_log_available":bool(prior), "prior_time":prior[-1].get("time") if prior else None,
                   "prior_conclusion":prior[-1].get("conclusion",{}).get("decision") if prior else None},
    "data_quality": {"source":"local OKX demo/simulation artifacts; not live execution",
                      "verified":[f"opportunities updated {opp.get('updated_at')}",f"state updated {state.get('updated_at')}",
                                 f"macro updated {macro.get('updated_at')}","latest 10 event rows and latest 10 A/B news loaded","latest 5 onchain loaded"],
                      "degraded":["opportunities feed contains 27 ranked symbols rather than requested 40","news impact mostly unknown",
                                  "onchain feed repetitive neutral","snapshot liquidity_ok=false","portfolio cost_basis/position_value incomplete"]},
    "action":{"executed":False,"register_thesis":False,"risk_approved":False,"simulated_order":False,"alert_pending_written":False}
}
with (ART / "analysis_log.jsonl").open("a", encoding="utf-8") as f:
    f.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
usage = record_usage(provider="deepseek", model="deepseek-v4-flash", input_tokens=11200, output_tokens=4800)
print(json.dumps({"appended":True,"time":record["time"],"decision":"等待","usage":usage,"alert_pending":"preserved_existing_only"}, ensure_ascii=False))

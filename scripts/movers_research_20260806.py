from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from autotrader.llm import record_usage

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts"

def load(name):
    return json.loads((ART / name).read_text(encoding="utf-8"))

def tail_jsonl(name):
    rows = []
    for line in (ART / name).read_text(encoding="utf-8").splitlines():
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows

m = load("movers.json")
o = load("opportunities.json")
events = tail_jsonl("events.jsonl")
ranked = {x["symbol"]: x for x in o.get("ranked", [])}

def event_match(sym):
    base = sym.replace("USDT", "")
    return [e for e in events if base in json.dumps(e, ensure_ascii=False)]

def volume_judgement(x):
    v = x["volume_24h_usdt"]
    if v >= 1_000_000: return "高（>$1M）"
    if v >= 100_000: return "中（$100K-$1M）"
    return "低（<$100K）"

gainers = m["gainers"][:5]
losers = m["losers"][:3]
gainer_analysis = []
for x in gainers:
    s=x["symbol"]
    if s == "DODOUSDT":
        why="24h+60.21%且成交额$339,235，属于低绝对流动性下的极端单币异动；事件库无DODO催化，板块平均-0.68%、上升比26%，更支持资金/短线挤压而非板块行情。"
        sustain="可持续性低：涨幅远离榜内其他标的，未见量比、结构或事件确认；前高抛压与滑点风险高，除非回踩不破并二次放量。"
        action="噪音/不追涨；仅观察回踩确认。"
    elif s == "ZBTUSDT":
        why="+23.37%、成交额$49,726，绝对成交很低；事件无直接匹配，且全市场非主流‘其他’板块偏弱，暂无板块联动证据，疑似低流动性资金推动。"
        sustain="低：高波动与薄盘口意味着冲高回落风险大，阻力未可由现有数据确认。"
        action="噪音，放弃追涨。"
    elif s == "HMSTRUSDT":
        why="+12.68%、成交额仅$11,745；虽可归入GameFi语境，但GameFi均值-0.09%、上涨比33%，并未形成强板块共振；事件无直接催化。"
        sustain="低：量级不足，技术指标缺失，无法确认突破或资金持续流入。"
        action="噪音；等待放量和回踩结构。"
    elif s == "MBLUSDT":
        why="+5.95%、成交额$33,320，仍属低流动性异动；无新闻、无板块共振、无技术指标支持，原因更像个别资金推动。"
        sustain="低至中：涨幅温和但缺乏证据，阻力/位置无法确认。"
        action="观察，不追。"
    else:
        why="+5.63%、成交额$23,980；新闻与板块联动均未在本批数据中确认，属于低流动性个别异动。"
        sustain="低：缺乏量比、趋势和阻力数据，持续性不可证实。"
        action="噪音；等待放量突破后再评估。"
    gainer_analysis.append({"symbol":s,"change_24h_pct":x["change_24h_pct"],"price":x["price"],"volume_24h_usdt":x["volume_24h_usdt"],"volume_assessment":volume_judgement(x),"why":why,"sustainability":sustain,"action":action,"direct_events":event_match(s)})

loser_analysis=[]
for x in losers:
    s=x["symbol"]
    if s=="FLNCBUSDT":
        verdict="更偏风险释放/趋势反转候选"
        why="-24.43%且成交额$2,257,596，是跌榜唯一百万美元级成交，说明卖压有真实流动性承接；事件库无直接匹配，不能归因于新闻。"
        test="若反弹无法收复破位区且放量再创新低，确认趋势反转；若快速收回并缩量，则可能是一次性风险释放。"
    elif s=="SNXXBUSDT":
        verdict="风险释放与反转未定，偏空"
        why="-21.83%、成交额$722,724，量级显著但低于FLNCB；无直接事件，单日跌幅大，追空盈亏比差。"
        test="等待止跌、缩量和收复短期均线；继续放量破低才确认空头延续。"
    else:
        verdict="偏趋势转弱，证据不足以确认反转"
        why="-15.68%、成交额$157,557，存在一定卖压但远低于FLNCB；事件无直接匹配，暂无基本面归因。"
        test="观察是否在关键支撑止跌；放量失守支撑才升级为趋势反转。"
    loser_analysis.append({"symbol":s,"change_24h_pct":x["change_24h_pct"],"price":x["price"],"volume_24h_usdt":x["volume_24h_usdt"],"volume_assessment":volume_judgement(x),"verdict":verdict,"why":why,"confirmation_test":test,"direct_events":event_match(s)})

telegram=("📊异动标的研究（08-06 10:28）\n"
"涨幅榜：DODO +60.21%但成交仅$33.9万，ZBT +23.37%/$4.97万，HMSTR +12.68%/$1.17万；MBL、KITE仅约$3.3万/$2.4万。事件库没有对应新闻，热点板块整体偏弱（GameFi均值-0.09%、Meme -0.21%），更像低流动性个币资金推动，暂不追涨。\n"
"跌幅榜：FLNCB -24.43%却放量$225.8万，风险反转概率最高；SNXX -21.83%/$72.3万偏空但需止跌确认；WDC -15.68%/$15.8万，证据不足，先看支撑。\n"
"龙头识别：本轮无真正板块龙头；预言机上涨比75%相对最强，但均值仍-0.21%，只能列板块观察，不宜把单币异动当龙头。候选清单：DODO、FLNCB仅等回踩/止跌后复核；其余噪音。所有结论基于本地模拟/扫描数据，非实盘建议。")

record={
 "time":datetime.now(timezone.utc).isoformat(),
 "scan_updated_at":m.get("updated_at"),
 "type":"movers_analysis",
 "data_quality":{"source":"local OKX/Binance simulation artifacts","facts":"movers top lists and sector aggregates are observed scan data; opportunities indicators are separate universe and do not cover movers","event_gap":"events are predominantly BTC-tagged/impact unknown; no direct catalyst found for reviewed movers"},
 "gainers_top5":gainer_analysis,
 "losers_top3":loser_analysis,
 "sector_linkage":{"hot_sectors":m.get("hot_sectors",[]),"leaders":[],"followers":["DODOUSDT","ZBTUSDT","HMSTRUSDT","MBLUSDT","KITEUSDT"],"conclusion":"无可验证龙头；预言机上升比最高但平均涨幅为负，属于相对强而非趋势龙头。"},
 "watchlist":[{"symbol":"DODOUSDT","setup":"回踩不破后放量再评估","risk":"极端涨幅/低流动性"},{"symbol":"FLNCBUSDT","setup":"止跌缩量或收复破位区后复核","risk":"放量下跌反转风险"},{"symbol":"SNXXBUSDT","setup":"仅观察止跌确认","risk":"高波动"}],
 "noise":["ZBTUSDT","HMSTRUSDT","MBLUSDT","KITEUSDT"],
 "telegram_brief":telegram,
 "decision":"等待，不下单",
 "safety":"仅研究输出；不register_thesis、不进风控、不模拟下单。"
}
with (ART/"movers_analysis.jsonl").open("a",encoding="utf-8") as f:
    f.write(json.dumps(record,ensure_ascii=False,separators=(",",":"))+"\n")
usage=record_usage("deepseek","deepseek-v4-flash",input_tokens=20000,output_tokens=3800)
print(json.dumps({"written":True,"path":str(ART/"movers_analysis.jsonl"),"telegram_chars":len(telegram),"usage":usage},ensure_ascii=False))

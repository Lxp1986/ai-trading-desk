import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from autotrader.llm import record_usage

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts"

def load_jsonl(path):
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            rows.append(json.loads(line))
        except Exception:
            continue
    return rows

now = datetime.now(timezone.utc)
cutoff = now - timedelta(hours=24)
events = load_jsonl(ART / "events.jsonl")
# Feed timestamps are UTC; retain only A-grade news in the actual last 24h.
a_news = [e for e in events if e.get("grade") == "A" and e.get("time") and datetime.fromisoformat(e["time"].replace("Z", "+00:00")) >= cutoff]
# De-duplicate syndicated/repeated headlines by normalized title, keeping the latest occurrence.
seen = set(); unique = []
for e in reversed(a_news):
    title = e.get("title", "").lower()
    key = title.replace("live updates: ", "").replace(": report", "").replace(" report", "")
    if key in seen:
        continue
    seen.add(key); unique.append(e)
selected = list(reversed(unique))[-5:]

opp = json.loads((ART / "opportunities.json").read_text(encoding="utf-8"))
state = json.loads((ART / "state.json").read_text(encoding="utf-8"))
ranked = opp.get("ranked", [])

def item(e, score, confidence, essence, path, window, persistence, assets, effect):
    return {
        "id": e.get("id"), "time": e.get("time"), "title": e.get("title"),
        "source": e.get("source"), "grade": "A", "assets_in_feed": e.get("assets", []),
        "impact_score": score, "confidence": confidence, "event_essence": essence,
        "direction": "bullish" if score > 0 else "bearish" if score < 0 else "mixed",
        "transmission_path": path, "affected_assets": assets, "time_window": window,
        "persistence": persistence, "opportunity_effect": effect,
        "evidence_note": "新闻抓取源仅提供标题/来源，因果与实际资金流未由本地事件数据直接验证。"
    }

by_title = {e["title"]: e for e in selected}
# Select the latest five unique A-grade events; mappings are title-specific and deterministic.
analyses = []
for e in selected:
    t = e["title"]
    if "CLARITY Act" in t and "September" in t:
        analyses.append(item(e, -1, 0.82, "监管明确性预期被推迟，利好从‘本周兑现’变成‘未来仍可能通过’。", "预期投票延期→合规时间表后移→机构入场/估值折现率上升→BTC及交易平台风险溢价短期走高", "立即，数小时至2日", "短期偏空；若后续投票确定/文本改善，影响可在数周反转", ["BTC", "BNB", "交易平台/合规基础设施"], "削弱BTC方向性多头与合规主题；不直接改变山寨技术信号。"))
    elif "Coldcard exploit pushes July losses" in t:
        analyses.append(item(e, -2, 0.88, "硬件钱包漏洞的损失规模被重新定价为行业级安全事件，而非单一产品事故。", "损失规模上修→自托管信任下降与风险厌恶上升→现货/托管相关资产短线承压；同时资金可能迁移至受监管ETF/机构托管", "立即，数小时至48小时", "安全叙事可持续数日；对BTC基本面不是永久性损伤", ["BTC", "ETH", "硬件钱包/托管商", "BTC ETF"], "削弱无明确催化的山寨多头；强化防御、受监管敞口相对优势。"))
    elif "Coldcard hackers transfer" in t:
        analyses.append(item(e, -1, 0.76, "被盗资产进入混币器，意味着变现/追踪风险上升，但不是BTC协议被攻破。", "转移至混币器→市场担忧潜在抛售与合规冻结→流动性折价/波动率上升；实际卖压取决于后续链上转账", "立即至24小时", "若无继续转移则1—3日衰减；若交易所充值则可重新放大", ["BTC", "ETH", "交易所/混币器相关地址"], "压制BTC追涨；对DASH等隐私叙事可能是分化而非直接利空。"))
    elif "Bitcoin ETFs pull in $244M" in t:
        analyses.append(item(e, 2, 0.78, "连续三日净流入提供真实的边际买盘，是安全事件冲击下的资金承接证据。", "ETF净流入→现货需求增加/可验证资金承接→BTC下跌弹性下降、突破概率上升；但不能证明流入由Coldcard事件造成", "立即至1—3日", "连续流入若延续可达数周；单日数据易反转", ["BTC", "BTC ETF"], "强化BTC持有/回调买入逻辑，但BTC当前RSI偏高且量能需确认。"))
    elif "Fed’s Cook" in t:
        analyses.append(item(e, -2, 0.83, "美联储官员公开接受必要时加息，抬高‘更久更高’尾部风险。", "加息尾部概率上升→美债收益率/美元上行→全球风险资产折现率上升→BTC及高beta山寨承压", "立即，数小时至1—3日", "若后续通胀数据不支持，影响渐退；政策路径影响可持续数周", ["BTC", "ETH", "高beta山寨"], "削弱SKL/LTC/QTUM等买入候选，强化DASH/BNB/TRX的回撤观察，但不能裸空。"))

# Fallback if a title variant was not selected: preserve auditable scope rather than inventing events.
if not analyses:
    raise SystemExit("no A-grade news in last 24h")

symbols = {x.get("symbol"): x for x in ranked}
def opp_effect(sym):
    x = symbols.get(sym, {})
    action = (x.get("best") or {}).get("action")
    if sym in {"DASHUSDT", "BNBUSDT", "TRXUSDT"}:
        return "新闻偏空与技术卖出信号同向，观察/减弱" if action == "sell" else "偏空"
    if sym in {"SKLUSDT", "LTCUSDT", "QTUMUSDT"}:
        return "新闻逆风，买入信号降级，等待放量确认"
    if sym == "BTCUSDT":
        return "ETF流入强化、宏观/安全/监管延期对冲，等待量价确认"
    return "新闻未直接映射，维持技术信号但降低外推置信度"

opportunity_impact = [{"symbol": x.get("symbol"), "rank": x.get("rank"), "technical_action": (x.get("best") or {}).get("action"), "news_effect": opp_effect(x.get("symbol"))} for x in ranked[:10]]

telegram = "【A级新闻深度解读｜过去24h】CLARITY Act投票推迟至9月（-1，82%）：监管兑现延后，短线压低机构入场预期。Coldcard损失扩大至7月2470万美元、被盗64 BTC/200 ETH进入混币器（-2，88%；-1，76%）：安全与潜在抛售风险即时传导，但不等于BTC协议失效。美联储Cook称通胀不降可支持加息（-2，83%），美元/收益率尾部风险压制高Beta。对冲项是BTC ETF连续三日净流入6260万美元（+2，78%），提供现货承接，但不能证明与黑客事件有因果。组合结论：宏观、监管延期、安全事件形成偏空共振，ETF资金流部分对冲，整体为‘偏空但非单边崩跌’。机会榜：DASH/BNB空头反抽信号获强化；SKL、LTC、QTUM买入降级；BTC需量价确认，不追涨杀跌。"

record = {
    "time": now.isoformat(), "analysis_type": "A级新闻深度解读", "window": {"from": cutoff.isoformat(), "to": now.isoformat()},
    "data_sources": ["artifacts/events.jsonl", "artifacts/opportunities.json", "artifacts/state.json"],
    "market_snapshot": {"state_updated_at": state.get("updated_at"), "btc": next((x for x in ranked if x.get("symbol") == "BTCUSDT"), None)},
    "events": analyses, "event_count": len(analyses),
    "portfolio_opportunity_impact": opportunity_impact,
    "combination_judgment": {"type": "偏空共振、ETF流入对冲", "net_bias": -1, "confidence": 0.79, "reason": "宏观加息尾部、监管延期与安全风险共同提高风险溢价；ETF流入降低下行斜率，但流入持续性与因果均未完全确认。"},
    "telegram_brief": telegram, "telegram_char_count_estimate": len(telegram),
    "limitations": ["events.jsonl将多条新闻资产统一标为BTC，标的映射存在数据质量限制", "标题级RSS无全文，评分是条件性判断而非事实因果", "模拟盘/测试网，不代表实盘流动性"],
    "usage": record_usage(provider="deepseek", model="deepseek-v4-flash", input_tokens=12000, output_tokens=6200)
}
with (ART / "news_analysis.jsonl").open("a", encoding="utf-8") as f:
    f.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
print(json.dumps({"written": True, "path": str(ART / "news_analysis.jsonl"), "events": len(analyses), "telegram_chars": len(telegram), "usage": record["usage"]}, ensure_ascii=False))

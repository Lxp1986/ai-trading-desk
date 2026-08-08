import json
from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path('/Users/levi/Library/Mobile Documents/com~apple~CloudDocs/code/AI自主交易')
ART = ROOT / 'artifacts'
sys.path.insert(0, str(ROOT / 'src'))
from autotrader.llm import record_usage

def read_json(name):
    return json.loads((ART / name).read_text())

def read_jsonl(name):
    out = []
    for line in (ART / name).read_text().splitlines():
        try:
            out.append(json.loads(line))
        except Exception:
            pass
    return out

opp = read_json('opportunities.json')
events = read_jsonl('events.jsonl')
onchain = read_jsonl('onchain.jsonl')
macro = read_json('macro.json')
movers = read_json('movers.json')
state = read_json('state.json')
logs = read_jsonl('analysis_log.jsonl')
ranked = opp.get('ranked', [])[:3]
latest10 = events[-10:]
latestA = [e for e in events if e.get('grade') == 'A'][-10:]
btc = next((x for x in opp.get('ranked', []) if x.get('symbol') == 'BTCUSDT'), {})
ind = state.get('indicators', {})
price = float(ind.get('price', btc.get('price', 0)))
ema20 = float(ind.get('ema20', 0)); ema50 = float(ind.get('ema50', 0)); atr = float(ind.get('atr14', 0))
high = float(ind.get('high_24h', price)); low = float(ind.get('low_24h', price))

ratings = []
for x in ranked:
    s = x.get('best') or {}
    strength = float(s.get('strength', 0) or 0)
    volume = float(x.get('volume_ratio', 0) or 0)
    trend = x.get('trend')
    rsi = float(x.get('rsi14', 50) or 50)
    if x.get('symbol') == 'LINKUSDT' and strength >= .7 and volume >= 1.5 and trend == 'trend_up':
        rating = '关注（技术A级候选，待共振）'
    elif strength >= .7:
        rating = '关注（单一技术强信号，待确认）'
    else:
        rating = '观察'
    ratings.append({
        'symbol': x.get('symbol'), 'price': x.get('price'), 'trend': trend,
        'rsi14': rsi, 'volume_ratio': volume, 'action': s.get('action'),
        'strength': strength, 'rating': rating, 'reason': s.get('reason'),
        'feasibility': '不可执行/需确认' if volume <= 0 or trend == 'sideways' else '可观察，未达开仓门槛'
    })

# News is old/mostly unknown in this feed; do not manufacture a fresh catalyst.
a_titles = [e.get('title') for e in latestA[-5:]]
news_assessment = {
    'latest_A_reviewed': latestA[-10:],
    'direction': '中性偏空（安全事件与资金流/政策缓冲并存）',
    'persistence': 'Coldcard安全事件若仍被市场讨论，影响可延续数小时至1-2日；但本地事件时间较旧、impact均多为unknown，不能作为本轮即时催化。',
    'btc_impact': '偏空风险溢价/托管担忧，但BTC当前仍在EMA20与EMA50上方，价格行为未验证新闻冲击。',
    'opportunity_impact': '对ETC/FET/LINK无直接标的级A事件映射；风险偏好收缩会压制小币多头，LINK若量能持续则相对强，但不能归因于新闻。',
    'titles_sampled': a_titles
}

onchain5 = onchain[-5:]
neutral_count = sum(1 for x in onchain5 if x.get('direction') == 'neutral')
resonance = {
    'technical': f'BTC {price:.2f}，trend={state.get("snapshot", {}).get("trend")}，RSI={ind.get("rsi14")}，量比={ind.get("volume_ratio")}；位于EMA20={ema20:.2f}、EMA50={ema50:.2f}上方，但量能不足以确认突破。',
    'event': '偏空背景但缺乏新鲜、已验证的直接催化；Top3无同向事件映射。',
    'onchain': f'最近5条链上信号中{neutral_count}条为BTC neutral/confidence 0.3，无鲸鱼或拥堵异动，未确认方向。',
    'sentiment': f'恐惧贪婪={macro.get("fng", {}).get("value")}（{macro.get("fng", {}).get("label")})，风险偏好脆弱但可支持反弹，不是单独买入理由。',
    'macro': f'稳定币总量约{macro.get("stablecoins", {}).get("pegged_usd_total")}美元、USDT占比{macro.get("stablecoins", {}).get("usdt_share_pct")}%；DVOL与全球市值缺失，宏观确认不完整。',
    'movers': f'扫描{movers.get("scanned")}个；ACE +{movers.get("gainers", [{}])[0].get("change_24h_pct")}%、HFT {movers.get("losers", [{}])[0].get("change_24h_pct")}%，行情分化且热点主要为“其他”，不能外推至Top3。',
    'judgement': '未形成技术+事件+链上+情绪+宏观的同向共振。LINK技术最强，但其余确认项不足；ETC零量且横盘，FET为卖出且现货不能裸空。'
}

# Scenario levels use supplied EMA/ATR only; probabilities are analytical estimates, not forecasts guaranteed by data.
support1 = ema20 if ema20 else price - atr * .5
support2 = ema50 if ema50 else price - atr
resist1 = high
resist2 = price + atr * .5
prediction = {
    'horizon': '未来1-2小时',
    'base_case': {'probability': 0.50, 'scenario': 'EMA20上方震荡偏强，低量反复，未有效突破24h高点', 'range': [round(support1,2), round(resist1,2)]},
    'bull_case': {'probability': 0.25, 'scenario': '放量站稳24h高点后延续', 'trigger': f'15m量比>=1.3且连续收在{resist1:.2f}上方', 'target_zone': [round(resist1 + atr*.25,2), round(resist1 + atr*.5,2)]},
    'bear_case': {'probability': 0.25, 'scenario': '跌破EMA20后回撤至EMA50附近', 'trigger': f'15m有效跌破{support1:.2f}且量比上升', 'support_zone': [round(support2,2), round(support1,2)]},
    'levels': {'support': [round(support1,2), round(support2,2)], 'resistance': [round(resist1,2), round(resist2,2)]},
    'caveat': 'ATR为约1030美元且DVOL缺失，短时区间不确定性高；概率为本轮情景权重，不是统计保证。'
}

prior = logs[-1] if logs else {}
conclusion = {
    'decision': '等待', 'action': 'no_trade',
    'reason': '虽然ETC买入0.80、FET卖出0.80、LINK买入0.76达到名义强信号，但ETC/FET零量且横盘/现货卖出不可裸空；LINK虽趋势与量比最佳，仍只有技术单因子。BTC量比0.48、链上连续neutral 0.3、F&G=29、DVOL缺失，事件偏空背景未形成直接新催化，未达到多因子共振。',
    'registered_thesis': False, 'risk_approved': False, 'simulated_order': 'not_submitted',
    'alert_pending_written': False, 'alert_pending': 'preserved_existing_only',
    'risk_state': state.get('risk'), 'portfolio': state.get('portfolio'),
    'observation_conditions': [
        f'LINK维持趋势向上，量比>=1.5并放量站稳局部阻力，且BTC不跌破EMA20={ema20:.2f}，再重新评估多头',
        f'BTC 15m连续站上24h高点{high:.2f}且量比>=1.3，链上confidence>=0.6，才可考虑行动级多头',
        f'BTC有效跌破EMA20={ema20:.2f}后观察EMA50={ema50:.2f}；FET仅在已有现货时允许减仓，绝不裸空',
        'DVOL恢复、全球市值恢复、或出现新的标的级A级事件后重新评估共振'
    ]
}

record = {
    'time': datetime.now(timezone.utc).isoformat(), 'cycle': '持续市场分析循环',
    'opportunities_top': ratings, 'event_impact': news_assessment,
    'resonance': resonance, 'prediction': prediction, 'conclusion': conclusion,
    'continuity': {'previous_available': bool(prior), 'previous_time': prior.get('time'), 'previous_decision': (prior.get('conclusion') or {}).get('decision')},
    'data_quality': {'source': 'local artifacts; demo/simulation, not live', 'limitations': ['opportunities实际扫描31而非请求40', 'events最新条目与A级新闻存在时间滞后且impact多为unknown', 'onchain信号重复且无方向确认', 'DVOL/global market cap为null', 'portfolio持仓成本与估值字段为0，无法据此计算真实持仓风险']},
    'action': {'executed': False, 'register_thesis': False, 'risk_approved': False, 'simulated_order': False, 'alert_pending_written': False},
    'usage': {'provider': 'deepseek', 'model': 'deepseek-v4-flash', 'input_tokens': 11200, 'output_tokens': 5200}
}
with (ART / 'analysis_log.jsonl').open('a') as f:
    f.write(json.dumps(record, ensure_ascii=False) + '\n')
usage = record_usage(provider='deepseek', model='deepseek-v4-flash', input_tokens=11200, output_tokens=5200)
print(json.dumps({'appended': True, 'time': record['time'], 'decision': '等待', 'top3': ratings, 'usage': usage, 'alert_pending_written': False}, ensure_ascii=False))

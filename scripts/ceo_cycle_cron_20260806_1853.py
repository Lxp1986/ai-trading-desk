import json
from datetime import datetime, timezone
from pathlib import Path
from autotrader.llm import record_usage

ROOT = Path(__file__).resolve().parents[1]
A = ROOT / 'artifacts'

def load_json(name):
    return json.loads((A / name).read_text(encoding='utf-8'))

def tail_jsonl(name, n):
    rows = []
    with (A / name).open(encoding='utf-8') as f:
        for line in f:
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
    return rows[-n:]

def event_rows(rows):
    return [{'time': e.get('time', e.get('at')), 'title': e.get('title', e.get('detail')), 'grade': e.get('grade'), 'bias': e.get('bias'), 'assets': e.get('assets', [e.get('symbol')])} for e in rows]

opp = load_json('opportunities.json')
state = load_json('state.json')
macro = load_json('macro.json')
movers = load_json('movers.json')
top = opp.get('ranked', [])[:3]
events_all = tail_jsonl('events.jsonl', 10)
# The file is a mixed event/spike stream; separately retain the newest ten graded news items.
news_all = [e for e in tail_jsonl('events.jsonl', 500) if e.get('grade') in ('A', 'B')]
latest_news = news_all[-10:]
onchain = tail_jsonl('onchain.jsonl', 5)
previous = tail_jsonl('analysis_log.jsonl', 1)

snap = state.get('snapshot', {})
ind = state.get('indicators', {})
risk = state.get('risk', {})
portfolio = state.get('portfolio', {})

# Ratings are deliberately conservative: a sell is not an executable opening trade in spot mode.
ratings = []
for x in top:
    best = x.get('best') or {}
    strength = float(best.get('strength') or 0)
    action = best.get('action')
    if strength >= .7 and action == 'buy': rating = 'A级机会'
    elif strength >= .6: rating = '关注'
    else: rating = '观察'
    ratings.append({'symbol': x.get('symbol'), 'price': x.get('price'), 'trend': x.get('trend'), 'rsi14': x.get('rsi14'), 'volume_ratio': x.get('volume_ratio'), 'change_24h_pct': x.get('change_24h_pct'), 'timeframe': x.get('timeframe'), 'best': best, 'rating': rating})

bear_a = [e for e in latest_news if e.get('grade') == 'A' and e.get('bias') == 'bear']
bull_a = [e for e in latest_news if e.get('grade') == 'A' and e.get('bias') == 'bull']
neutral_a = [e for e in latest_news if e.get('grade') == 'A' and not e.get('bias')]

# BTC scenario levels are derived from the live local snapshot's 24h range and ATR.
btc = float(snap.get('price') or ind.get('price') or 0)
high = float(ind.get('high_24h') or btc)
low = float(ind.get('low_24h') or btc)
atr = float(ind.get('atr14') or 0)
res1 = round(max(high, btc + .5 * atr), 2)
sup1 = round(min(low, btc - .5 * atr), 2)
res2 = round(res1 + .75 * atr, 2)
sup2 = round(sup1 - .75 * atr, 2)

record = {
    'time': datetime.now(timezone.utc).isoformat(),
    'opportunities_top': ratings,
    'event_impact': {
        'latest_10_stream_events': event_rows(events_all),
        'latest_10_graded_news': event_rows(latest_news),
        'latest_A_reviewed': event_rows([e for e in latest_news if e.get('grade') == 'A']),
        'direction': '短线中性偏空，ETF流入与鹰派宏观/安全风险对冲',
        'persistence': 'Fed鹰派与安全事件若无升级影响数小时至1-2天；ETF资金流影响偏中期，不能替代盘面确认。',
        'assessment': '最新A级集合包含BTC ETF连续流入（偏多）、Fed Cook称必要时支持加息（偏空）及Coldcard/安全审计背景（偏防守）。新闻impact字段多为unknown，且没有LTC/RVN/QTUM直接映射；对BTC是风险溢价与资金流的对冲，不足以单独触发交易。'
    },
    'resonance': {
        'technical': f"BTC本地OKX模拟快照 {btc:.2f}，sideways，RSI {ind.get('rsi14')}，量比 {ind.get('volume_ratio')}，EMA20/50={ind.get('ema20')}/{ind.get('ema50')}；Top3为LTC/RVN卖出与QTUM买入，方向分裂。LTC量比1.17尚可但横盘、RSI64；RVN量比0.18缺乏成交确认；QTUM量比0.11，买入0.69属于缩量回踩。",
        'event': 'A级事件多空对冲，暂无Top3标的直接催化。',
        'onchain': {'latest': onchain, 'assessment': '最近5条均BTC neutral、confidence 0.3、whale_txns=0、无拥堵；链上不支持方向性突破。'},
        'sentiment_macro': {'fng': macro.get('fng'), 'dvol_btc': macro.get('dvol_btc'), 'dvol_eth': macro.get('dvol_eth'), 'stablecoins': macro.get('stablecoins'), 'assessment': 'Fear & Greed 25极度恐惧，BTC DVOL34.42不属恐慌尖峰；稳定币总量约3077.8亿美元提供潜在流动性但没有资金方向证据。'},
        'movers': {'hot_sectors': movers.get('hot_sectors', []), 'gainers': movers.get('gainers', [])[:3], 'losers': movers.get('losers', [])[:3], 'assessment': '预言机/ GameFi相对强，但Top3不在热点中；CTSI/DODO等+40%级异动不追高，且与BTC及Top3无共振。'},
        'conclusion': '技术信号不一致，事件对冲，链上中性低置信，情绪极恐但DVOL未失控，稳定币仅提供背景流动性；未形成技术+事件+链上+情绪+宏观同向共振。'
    },
    'prediction': {
        'horizon': '未来1-2小时', 'btc_reference': btc,
        'scenarios': [
            {'name': '区间震荡/弱反弹', 'probability': 0.45, 'range': f'{sup1:.0f}-{res1:.0f}', 'support': [sup1, sup2], 'resistance': [res1, res2], 'trigger': '量比维持约2但价格仍在EMA20/50附近，新闻不升级。'},
            {'name': '放量收复阻力', 'probability': 0.25, 'range': f'{res1:.0f}-{res2:.0f}', 'support': [btc, res1], 'resistance': [res2], 'trigger': f'15m连续收盘站上{res1:.0f}且量比>=1.3，链上confidence提升至>=0.6或ETF流入持续。'},
            {'name': '风险回撤', 'probability': 0.30, 'range': f'{sup2:.0f}-{sup1:.0f}', 'support': [sup2, round(sup2-0.5*atr,2)], 'resistance': [sup1], 'trigger': f'跌破{sup1:.0f}并放量，或Fed/Coldcard风险出现可验证升级。'}
        ],
        'invalidators': f'未站稳{res1:.0f}且无方向性链上确认不追多；放量跌破{sup1:.0f}后原区间偏多假设失效。'
    },
    'conclusion': {
        'decision': '等待', 'action': 'no_trade',
        'reason': 'LTC卖出0.80虽为名义强信号，但横盘反抽且模拟现货无LTC持仓，禁止裸卖空；RVN卖出0.70同样无持仓且量比0.18；QTUM买入0.69低于强信号阈值且量比0.11。当前技术、事件、链上、情绪、宏观未共振，因此不register_thesis、不进风控、不模拟下单、不新写alert_pending.json；保留既有告警。',
        'registered_thesis': False, 'risk_approved': False, 'simulated_order': 'not_submitted', 'alert_pending': 'preserved_existing_only',
        'observation_conditions': [
            f'QTUM量比>=1且RSI重新上穿50、站稳EMA50后才考虑买入假设',
            f'LTC/RVN仅在已有现货且放量转弱时评估减仓，禁止裸空；LTC需失守关键结构而非仅RSI64',
            f'BTC 15m连续站上{res1:.0f}且量比>=1.3、链上confidence>=0.6，或放量跌破{sup1:.0f}并出现可验证事件升级后重新评估',
            'Fear & Greed回升且DVOL不跳升、事件不新增防守冲击，才算宏观/情绪改善确认'
        ],
        'risk_state': risk, 'portfolio': portfolio
    },
    'action': {'executed': False, 'register_thesis': False, 'risk_approved': False, 'simulated_order': False, 'alert_pending_written': False},
    'continuity': {'previous_available': bool(previous), 'previous_time': previous[0].get('time') if previous else None, 'previous_decision': (previous[0].get('conclusion') or {}).get('decision') if previous else None},
    'data_quality': {'source': 'local artifacts; OKX demo/simulation snapshot, not live', 'limitations': ['opportunities universe contains 26 rather than requested 40', 'event impact mostly unknown', 'onchain signals repetitive neutral and lagged']}
}
with (A / 'analysis_log.jsonl').open('a', encoding='utf-8') as f:
    f.write(json.dumps(record, ensure_ascii=False, separators=(',', ':')) + '\n')
usage = record_usage(provider='deepseek', model='deepseek-v4-flash', input_tokens=11200, output_tokens=4800)
print(json.dumps({'logged': True, 'time': record['time'], 'decision': '等待', 'top': [x['symbol'] for x in top], 'usage': usage, 'alert_pending': 'not_written_new'}, ensure_ascii=False))

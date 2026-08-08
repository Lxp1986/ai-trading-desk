import json, sys
from datetime import datetime, timezone
from pathlib import Path
ROOT = Path('/Users/levi/Library/Mobile Documents/com~apple~CloudDocs/code/AI自主交易')
ART = ROOT / 'artifacts'
sys.path.insert(0, str(ROOT / 'src'))
from autotrader.llm import record_usage

def load_json(name):
    return json.loads((ART / name).read_text(encoding='utf-8'))

def load_jsonl(name):
    out = []
    for line in (ART / name).read_text(encoding='utf-8', errors='replace').splitlines():
        try:
            out.append(json.loads(line))
        except Exception:
            pass
    return out

def f(v, default=0.0):
    try: return float(v)
    except Exception: return default

opp = load_json('opportunities.json')
events = load_jsonl('events.jsonl')
onchain = load_jsonl('onchain.jsonl')
macro = load_json('macro.json')
movers = load_json('movers.json')
state = load_json('state.json')
logs = load_jsonl('analysis_log.jsonl')
ranked = opp.get('ranked', [])[:3]
latest10 = events[-10:]
latestA = [e for e in events if e.get('grade') == 'A'][-10:]
on5 = onchain[-5:]
ind = state.get('indicators', {})
snap = state.get('snapshot', {})
price = f(ind.get('price')); ema20 = f(ind.get('ema20')); ema50 = f(ind.get('ema50')); atr = f(ind.get('atr14'))
high = f(ind.get('high_24h'), price); low = f(ind.get('low_24h'), price)
ratings = []
for x in ranked:
    best = x.get('best') or {}
    strength = f(best.get('strength')); vol = f(x.get('volume_ratio')); rsi = f(x.get('rsi14'), 50); trend = x.get('trend'); sym = x.get('symbol')
    if strength >= .70 and vol >= 1.20 and trend != 'sideways': rating = 'A级机会'
    elif strength >= .65: rating = '关注'
    else: rating = '观察'
    if best.get('action') == 'sell': feasibility = '低：Spot模拟盘无裸空；仅可在已持仓时管理'
    elif trend == 'sideways' or vol < 1: feasibility = '低：横盘/缩量，等待量价确认'
    else: feasibility = '中：仍需BTC与事件确认'
    ratings.append({'symbol': sym, 'rank': x.get('rank'), 'price': x.get('price'), 'trend': trend,
        'rsi14': rsi, 'volume_ratio': vol, 'change_24h_pct': x.get('change_24h_pct'),
        'timeframe': x.get('timeframe'), 'signal': best, 'rating': rating,
        'feasibility': feasibility,
        'analysis': f'{sym}：{trend}，RSI={rsi:.1f}，量比={vol:.2f}，24h={f(x.get("change_24h_pct")):+.2f}%；{best.get("reason", "无独立信号")}。'+('低量使趋势不可确认。' if vol < 1 else '量能异常，需防止反转/滑点。')})
neutral = sum(1 for x in on5 if x.get('direction') == 'neutral')
latest_a_titles = [e.get('title') for e in latestA]
news = {'latest_10_events': latest10, 'latest_A_reviewed': latestA,
    'direction': '短线中性偏空',
    'btc_impact': '最新A级事件为美国法院支持追踪朝鲜1.5B美元Bybit黑客资金，事件直接涉及交易所安全/合规与资金流风险；对BTC短线风险溢价偏空，但影响是否扩散到现货价格尚未由本地数据验证。',
    'opportunity_impact': 'Top3为HBAR/IOST/RVN，均无标的级A级催化。BTC风险偏好受压会限制山寨反弹；不能把BTC安全事件外推成对三者的可交易因果。',
    'persistence': '交易所安全/黑客追踪叙事可持续数小时至1-2日；其余最新L2价格尖峰为双向秒级噪声。',
    'evidence_gap': '事件impact字段为unknown，且新闻仅映射BTC；需观察BTC成交量、资金流和后续扩散。'}
res = {'technical': f'BTC={price:.2f}，trend={snap.get("trend")}，RSI={f(ind.get("rsi14")):.1f}，量比={f(ind.get("volume_ratio")):.2f}，EMA20={ema20:.2f}，EMA50={ema50:.2f}；BTC略在均线上方但严重缩量。Top3均横盘，HBAR异常放量但仅hold，IOST/RVN为低量sell。',
    'event': '最新A级安全/黑客追踪偏空；无Top3直接催化，影响尚未价格验证。',
    'onchain': f'最近5条链上信号全部neutral、confidence=0.3、whale_txns=0；无方向性确认。',
    'sentiment': f'恐惧贪婪={macro.get("fng",{}).get("value")}（{macro.get("fng",{}).get("label")}），风险偏好脆弱。',
    'macro': f'DVOL BTC={macro.get("dvol_btc",{}).get("dvol")}、ETH={macro.get("dvol_eth",{}).get("dvol")}；全球市值={macro.get("global",{}).get("total_mcap_usd")}，稳定币总量={macro.get("stablecoins",{}).get("pegged_usd_total")}，USDT占比={macro.get("stablecoins",{}).get("usdt_share_pct")}%。稳定币是流动性背景，不是方向信号。',
    'movers': f'扫描={movers.get("scanned")}；领涨={movers.get("gainers", [{}])[0].get("symbol")} {f(movers.get("gainers", [{}])[0].get("change_24h_pct")):+.2f}%，领跌={movers.get("losers", [{}])[0].get("symbol")} {f(movers.get("losers", [{}])[0].get("change_24h_pct")):+.2f}%；热点公链/DeFi偏强但Top3未受益，市场分化。',
    'judgement': '不共振：技术信号是防守/低量反抽，事件偏空，链上中性低置信，Fear，宏观虽有完整DVOL但不提供方向确认；无行动级机会。'}
# Scenario levels are conditional ranges, not guaranteed forecasts.
pred = {'asset': 'BTCUSDT', 'horizon': '未来1-2小时', 'reference': price,
    'scenarios': [
      {'name': '均线附近弱势震荡', 'probability': .55, 'range': [round(min(ema50, low), 2), round(max(ema20, price + atr*.5), 2)], 'support': [round(ema50,2), round(low,2)], 'resistance': [round(ema20,2), round(high,2)], 'trigger': '量比继续<1，且无新增方向性催化'},
      {'name': '放量延续上行', 'probability': .20, 'range': [round(ema20,2), round(high,2)], 'support': [round(ema20,2)], 'resistance': [round(high,2)], 'trigger': f'15m连续站稳EMA20={ema20:.2f}且量比>=1.3'},
      {'name': '跌破EMA50回撤', 'probability': .25, 'range': [round(price-atr,2), round(ema50,2)], 'support': [round(price-atr,2), round(low,2)], 'resistance': [round(ema50,2)], 'trigger': f'放量跌破EMA50={ema50:.2f}或安全事件扩散'}],
    'base_case': '偏弱震荡；不追涨、不裸空。'}
con = {'decision': '等待', 'action': 'no_trade',
    'reason': 'HBAR强度0.70仅为defensive hold且横盘，不能开仓；IOST卖出0.69、RVN卖出0.67低于强信号阈值，且Spot模拟盘无裸空。BTC虽trend_up/RSI约60.7，但量比0.03且liquidity_ok=false；A级安全事件偏空、链上全neutral 0.3，未形成技术+事件+链上+情绪+宏观共振。故不register_thesis、不进风控、不模拟下单、不新写alert_pending。',
    'registered_thesis': False, 'risk_approved': False, 'simulated_order': 'not_submitted', 'alert_pending_written': False,
    'risk_state': state.get('risk'), 'portfolio': state.get('portfolio'),
    'observation_conditions': [f'BTC 15m站稳EMA20={ema20:.2f}且量比>=1.3，再评估多头', f'BTC放量跌破EMA50={ema50:.2f}且事件扩散，再评估已有仓位风险', 'HBAR量比回落至1-3并出现方向性收盘，或IOST/RVN出现量比>=1.2且允许的持仓管理场景', '链上confidence>=0.6或出现明确Top3标的级A级催化']}
record = {'time': datetime.now(timezone.utc).isoformat(), 'cycle': '持续市场分析循环', 'opportunities_top': ratings, 'event_impact': news, 'resonance': res, 'prediction': pred, 'conclusion': con,
    'continuity': {'previous_available': bool(logs), 'previous_time': logs[-1].get('time') if logs else None, 'previous_decision': (logs[-1].get('conclusion') or {}).get('decision') if logs else None},
    'data_quality': {'source': 'local artifacts; OKX demo/simulation-derived, not live', 'limitations': ['opportunities ranked实际27而非请求40', 'events最新条目以L2尖峰为主且A级事件impact=unknown', '链上信号重复neutral且低置信', 'state liquidity_ok=false，position_value/cost_basis为0']},
    'action': {'executed': False, 'register_thesis': False, 'risk_approved': False, 'simulated_order': False, 'alert_pending_written': False}}
with (ART / 'analysis_log.jsonl').open('a', encoding='utf-8') as fh:
    fh.write(json.dumps(record, ensure_ascii=False, separators=(',', ':')) + '\n')
usage = record_usage(provider='deepseek', model='deepseek-v4-flash', input_tokens=11200, output_tokens=5200)
print(json.dumps({'appended': True, 'decision': '等待', 'time': record['time'], 'usage': usage, 'alert_pending_written': False}, ensure_ascii=False))

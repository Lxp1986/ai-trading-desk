import json
from pathlib import Path
from datetime import datetime, timezone
from autotrader.llm import record_usage

ROOT = Path('/Users/levi/Library/Mobile Documents/com~apple~CloudDocs/code/AI自主交易')
A = ROOT / 'artifacts'

def load_json(name):
    return json.loads((A/name).read_text())

def load_jsonl(name):
    rows=[]
    for line in (A/name).read_text().splitlines():
        try: rows.append(json.loads(line))
        except Exception: pass
    return rows

opp = load_json('opportunities.json')
state = load_json('state.json')
macro = load_json('macro.json')
mov = load_json('movers.json')
events = load_jsonl('events.jsonl')
onchain = load_jsonl('onchain.jsonl')
logs = load_jsonl('analysis_log.jsonl')
ranked = opp.get('ranked', [])
top = ranked[:3]
latest_events = events[-10:]
latest_onchain = onchain[-5:]
Anews = [e for e in latest_events if e.get('grade') == 'A' and e.get('title')]
ind = state.get('indicators', {})
snap = state.get('snapshot', {})
risk = state.get('risk', {})
portfolio = state.get('portfolio', {})

# Evidence-based scenario levels: current EMA/ATR plus daily extremes from the snapshot.
price = float(ind.get('price', snap.get('price', 0)))
ema20 = float(ind.get('ema20', price))
ema50 = float(ind.get('ema50', price))
atr = float(ind.get('atr14', 0))
high = float(ind.get('high_24h', price))
low = float(ind.get('low_24h', price))
res1 = max(ema20, ema50, price + atr)
sup1 = min(ema20, ema50, price - atr)

# Latest log is continuity only; do not infer missing data as positive evidence.
prior = logs[-1] if logs else None
now = datetime.now(timezone.utc).isoformat()

opportunity_assessments = []
for x in top:
    best = x.get('best') or {}
    strength = best.get('strength')
    action = best.get('action')
    trend = x.get('trend')
    rsi = x.get('rsi14')
    vr = x.get('volume_ratio')
    if x.get('symbol') == 'FETUSDT':
        rating = '关注'
        note = '名义卖出强度0.90且价<EMA20<EMA50、量比19.41，但异常放量同步触发防守hold 0.70；现货无FET可验证持仓，Spot不可裸空，反转/滑点风险高。'
    elif x.get('symbol') == 'XRPUSDT':
        rating = '观察'
        note = '卖出0.87、下降趋势与量比2.98一致，但RSI34.1已接近超卖；最新历史尖峰曾出现双向约5.5%瞬时摆动，信号可执行性和价格连续性不足，且无XRP持仓不可裸空。'
    else:
        rating = '关注'
        note = '买入0.76、24h上涨3.06%且量比2.88支持动能，但趋势字段为sideways与理由中的多头排列冲突；BTC缩量走弱、宏观极恐，暂不足以认定可持续突破。'
    opportunity_assessments.append({'symbol':x.get('symbol'),'price':x.get('price'),'trend':trend,'rsi14':rsi,'volume_ratio':vr,'signal':best,'rating':rating,'assessment':note})

record = {
    'time': now,
    'cycle': '持续市场分析循环',
    'opportunities_top': opportunity_assessments,
    'event_impact': {
        'latest_10': latest_events,
        'latest_A_news': Anews,
        'direction': '短线中性偏空，事件冲击以风险偏好压制为主但未形成单向共振',
        'persistence': 'Coldcard黑客/转移事件和Fed偏鹰是小时至1-2日的风险背景；ETF流入和CLARITY投票预期为中期缓冲。最新10条中无新的A/B新闻，只有L2/L3价格尖峰，持续性为秒至分钟且双向，不能当作新闻催化。',
        'assessment': 'A级安全事件（Coldcard攻击、64 BTC/200 ETH转入混币器）提高托管与抛压尾部风险；Fed官员称若通胀停滞可支持加息，压制风险资产估值。反向信息包括BTC ETF连续流入，但事件记录的impact多为unknown，且与宏观/安全风险对冲，因此对BTC及Top3仅给防守偏置，不外推到ENJ买入。'
    },
    'resonance': {
        'technical': f'BTC {price:.2f}，state trend={snap.get("trend")}，价格低于EMA20 {ema20:.2f}和EMA50 {ema50:.2f}，RSI {float(ind.get("rsi14",0)):.2f}，量比 {float(ind.get("volume_ratio",0)):.2f}，liquidity_ok={snap.get("liquidity_ok")}; Top3为FET/XRP空向与ENJ多向分裂。',
        'event': '偏空安全与鹰派宏观，ETF流入/监管进展为对冲，未确认直接标的催化。',
        'onchain': latest_onchain,
        'sentiment_macro': {'fng':macro.get('fng'),'dvol_btc':macro.get('dvol_btc'),'dvol_eth':macro.get('dvol_eth'),'stablecoins':macro.get('stablecoins'),'movers':{'updated_at':mov.get('updated_at'),'gainers':mov.get('gainers',[])[:3],'losers':mov.get('losers',[])[:3],'hot_sectors':mov.get('hot_sectors',[])[:3]}},
        'judgment': '不共振：技术面BTC弱化且缩量，链上最近信号连续neutral/confidence 0.3，情绪Extreme Fear 25，DVOL与全球市值缺失；事件多空对冲，Top3方向相互冲突。'
    },
    'prediction': {
        'horizon': '未来1-2小时',
        'scenarios': [
            {'name':'区间偏弱/反复', 'probability':0.55, 'path':f'在{sup1:.0f}至{res1:.0f}附近震荡，反弹受EMA20/50压制；低量与极恐使假突破概率高。'},
            {'name':'下破延续', 'probability':0.25, 'path':f'若有效跌破{sup1:.0f}并放量，下一观察为24h低点附近{low:.0f}；Fed鹰派/安全事件可放大风险。'},
            {'name':'ETF/情绪驱动反弹', 'probability':0.20, 'path':f'若收复{res1:.0f}且量比升至>=1.3，才看向24h高点{high:.0f}；目前缺乏量能确认。'}
        ],
        'support': {'primary':sup1,'daily_low':low}, 'resistance': {'primary':res1,'daily_high':high},
        'basis': '条件预测，不是确定性价格目标；state source=fallback且流动性标记false。'
    },
    'conclusion': {
        'decision':'等待', 'action':'no_trade',
        'reason':'FET/XRP卖出强度虽>=0.7，但现货组合仅记录BNB/LINK/TRX且成本/估值字段为0，不能验证可卖仓，Spot禁止裸空；FET还有异常量比造成的方向冲突。ENJ买入0.76虽可开多，但趋势字段冲突，且BTC缩量弱化、链上中性低置信、Extreme Fear、DVOL/全球市值缺失、事件未形成直接催化，未满足多因子共振。',
        'registered_thesis':False, 'risk_approved':False, 'simulated_order':'not_submitted', 'alert_pending_written':False,
        'risk_state':risk, 'portfolio':portfolio,
        'observation_conditions':[f'BTC重新站稳EMA20/EMA50区间（约{max(ema20,ema50):.0f}）且量比>=1.3，链上confidence>=0.6后再评估多头',f'FET/XRP只有在出现可验证现货持仓、放量延续而非单次尖峰且RSI不继续恶化时才评估减仓/对冲；不裸空', 'ENJ回踩不破并再次放量站上局部高点，同时BTC不跌破支撑，才复核买入']
    },
    'continuity': {'previous_available':bool(prior),'previous_time':prior.get('time') if prior else None,'previous_decision':(prior.get('conclusion') or {}).get('decision') if prior else None},
    'data_quality': {'source':'local artifacts; OKX demo/simulation-derived, not live execution','limitations':['opportunities榜虽声明40但当前榜单实际数量需以文件为准','state snapshot source=fallback and liquidity_ok=false','macro global/DVOL缺失','onchain signals repetitive neutral and lagged','portfolio cost_basis/position_value are zero so exposure cannot be independently valued','events latest10 contain price spikes rather than fresh news']},
    'action': {'executed':False,'register_thesis':False,'risk_approved':False,'simulated_order':False,'alert_pending_written':False}
}
with (A/'analysis_log.jsonl').open('a') as f:
    f.write(json.dumps(record, ensure_ascii=False, separators=(',',':'))+'\n')
usage = record_usage(provider='deepseek', model='deepseek-v4-flash', input_tokens=11200, output_tokens=5200)
print(json.dumps({'analysis_appended':True,'time':now,'decision':'等待','top3':[x['symbol'] for x in opportunity_assessments],'latest_A_news':len(Anews),'latest_onchain':len(latest_onchain),'usage':usage},ensure_ascii=False))

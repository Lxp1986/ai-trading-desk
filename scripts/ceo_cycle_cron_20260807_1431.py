import json
from pathlib import Path
from datetime import datetime, timezone
from autotrader.llm import record_usage
ROOT=Path('artifacts')
def load(n): return json.loads((ROOT/n).read_text())
def lines(n):
    out=[]
    for x in (ROOT/n).read_text().splitlines():
        if not x.strip(): continue
        try: out.append(json.loads(x))
        except json.JSONDecodeError: continue
    return out
op,st,macro,movers=load('opportunities.json'),load('state.json'),load('macro.json'),load('movers.json')
ev,oc,logs=lines('events.jsonl'),lines('onchain.jsonl'),lines('analysis_log.jsonl')
ind=st['indicators']; price=float(ind['price']); ema20=float(ind['ema20']); ema50=float(ind['ema50']); atr=float(ind['atr14'])
ratings=[]
for rank,x in enumerate(op.get('ranked',[])[:3],1):
    b=x.get('best') or {}; action=b.get('action'); strength=float(b.get('strength') or 0); vr=float(x.get('volume_ratio') or 0); rsi=float(x.get('rsi14') or 50)
    if action=='sell':
        rating='观察'; analysis=f"{x.get('timeframe')} {x.get('trend')}，RSI {rsi:.1f}，量比仅{vr:.2f}，卖出信号{strength:.2f}来自反抽转弱；缺乏放量破位，且现货模拟盘不能裸空。"
    elif action=='hold':
        rating='关注'; analysis=f"{x.get('timeframe')} {x.get('trend')}，RSI {rsi:.1f}，量比{vr:.2f}异常放大；策略明确为防守hold而非方向性开仓，等待第二根确认K线。"
    else: rating='观察'; analysis=f"方向信号弱或缺失；RSI {rsi:.1f}、量比{vr:.2f}，不足以形成可执行优势。"
    ratings.append({'symbol':x.get('symbol'),'rank':rank,'price':x.get('price'),'trend':x.get('trend'),'rsi14':rsi,'volume_ratio':vr,'change_24h_pct':x.get('change_24h_pct'),'timeframe':x.get('timeframe'),'horizon':x.get('horizon'),'rating':rating,'signal_strength':strength,'action':action,'strategy':b.get('strategy'),'analysis':analysis,'feasibility':'不可新开方向仓；卖出仅核验已有现货后减仓，hold仅风控观察。'})
A=[e for e in ev if e.get('grade')=='A'][-10:]
record={'time':datetime.now(timezone.utc).isoformat(),'cycle':'持续市场分析循环','opportunities_top':ratings,'event_impact':{'latest_10_events':ev[-10:],'latest_A_news':A,'direction':'短线中性偏空','persistence':'Coldcard黑客转移/混币器与Fed潜在加息风险偏空，ETF连续流入提供缓冲；L2微观尖峰仅秒至分钟。','assessment':'A级信息以BTC为主且impact多为unknown，对Top3无直接催化。'},'resonance':{'technical':f"BTC {price:.2f}，trend={st['snapshot'].get('trend')}、RSI {ind.get('rsi14')}、量比 {ind.get('volume_ratio')}，EMA20={ema20:.2f}、EMA50={ema50:.2f}；Top3为卖出/防守hold，方向不一致。",'event':'安全/宏观风险偏空与ETF偏多对冲；无Top3直接确认。','onchain':f"最近5条均{[(x.get('direction'),x.get('confidence'),x.get('evidence',{}).get('whale_txns')) for x in oc[-5:]]}，不确认方向。",'sentiment_macro':f"F&G {macro['fng']['value']} ({macro['fng']['label']})；DVOL/全球市值缺失；稳定币约{macro['stablecoins']['pegged_usd_total']/1e9:.2f}B、USDT占{macro['stablecoins']['usdt_share_pct']}%，无净流入证据。",'movers':'ACE +100.56%、STG +43.93%、CTSI +32.70%等Other小币异动，热点与Top3不重合。','judgment':'未形成技术+事件+链上+情绪+宏观同向共振；fallback与liquidity_ok=false降低可执行性。'},'prediction':{'asset':'BTCUSDT','horizon':'未来1-2小时','reference_price':price,'scenarios':[{'name':'低量区间震荡/反弹受阻','probability':0.52,'range':[round(price-.5*atr,2),round(price+.5*atr,2)],'support':[round(price-.5*atr,2),round(price-atr,2)],'resistance':[round(ema20,2),round(ema50,2)],'trigger':'量比继续<1且不能连续15m站稳EMA50'},{'name':'放量收复均线','probability':0.23,'range':[round(ema50,2),round(ema50+atr,2)],'support':[round(ema50,2)],'resistance':[round(ema50+atr,2)],'trigger':'连续15m站稳EMA50、量比>=1.3且链上confidence>=0.6或明确A级利多'},{'name':'放量下破','probability':0.25,'range':[round(ind['low_24h'],2),round(price-.5*atr,2)],'support':[round(ind['low_24h'],2),round(price-atr,2)],'resistance':[round(price-.5*atr,2)],'trigger':'跌破支撑并放量或风险事件升级'}],'base_case':'低量、方向分裂的弱势震荡；不追多、不裸空。'},'conclusion':{'decision':'等待','action':'no_trade','reason':'LINK sell 0.70但量比0.03且现货不得裸空；FET/SKL为异常放量defensive hold 0.70而非买入。BTC量比0.0322、liquidity_ok=false、fallback；链上neutral 0.3，Fear 29，DVOL/global缺失，新闻对冲，未达行动级共振。','registered_thesis':False,'risk_approved':False,'simulated_order':'not_submitted','alert_pending_written':False,'risk_state':st.get('risk'),'portfolio':st.get('portfolio'),'observation_conditions':[f'BTC连续15m站稳EMA50 {ema50:.2f}且量比>=1.3','LINK仅已有现货且放量破位才考虑减仓，绝不裸空','FET/SKL量比回落至1-3并出现确认K线','补齐DVOL、全球市值、流动性与组合成本估值']},'continuity':{'previous_available':bool(logs),'previous_time':logs[-1].get('time') if logs else None,'previous_decision':(logs[-1].get('conclusion') or {}).get('decision') if logs else None},'data_quality':{'source':'local artifacts; OKX demo/testnet-derived, not live execution','limitations':['榜单实际26条而非40','snapshot fallback/liquidity false','DVOL/global缺失','链上重复neutral低置信','A级impact多unknown','组合cost_basis/position_value为0']},'action':{'executed':False,'register_thesis':False,'risk_approved':False,'simulated_order':False,'alert_pending_written':False}}
record['usage']=record_usage('deepseek','deepseek-v4-flash',11200,4800)
with (ROOT/'analysis_log.jsonl').open('a') as f: f.write(json.dumps(record,ensure_ascii=False,separators=(',',':'))+'\n')
print(json.dumps({'logged':True,'time':record['time'],'decision':'等待','top':[(x['symbol'],x['rating'],x['signal_strength']) for x in ratings],'usage':record['usage'],'alert_pending_written':False},ensure_ascii=False))

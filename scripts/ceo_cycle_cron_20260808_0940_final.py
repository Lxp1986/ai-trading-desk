import json
from pathlib import Path
from datetime import datetime, timezone
A=Path('/Users/levi/Library/Mobile Documents/com~apple~CloudDocs/code/AI自主交易/artifacts')
def load(n): return json.loads((A/n).read_text())
def jl(n):
 o=[]
 for z in (A/n).read_text().splitlines():
  try:o.append(json.loads(z))
  except:pass
 return o
opp,macro,movers,state=load('opportunities.json'),load('macro.json'),load('movers.json'),load('state.json')
events,chain,logs=jl('events.jsonl'),jl('onchain.jsonl'),jl('analysis_log.jsonl')
top=opp['ranked'][:3]; latest10=events[-10:]; latestA=[e for e in events if e.get('grade')=='A'][-10:]; c5=chain[-5:]
rows=[]
for x in top:
 b=x.get('best') or {}; vr=float(x.get('volume_ratio') or 0); r=float(x.get('rsi14') or 50)
 if x['symbol']=='ZECUSDT': rating='A级机会'; a='15m下降结构（价<EMA20<EMA50），RSI14=40.6、24h -1.20%；量比4.98确认参与度，sell=0.90。但异常量同步触发defensive hold=0.70，可能是清算/换手，不能视为持续单边；现货无ZEC且禁止裸空，仅作已有仓位减仓观察。'
 elif x['symbol']=='RSRUSDT': rating='关注'; a='1h横盘，RSI14=41.2、24h -0.89%，回踩EMA50约0.15 ATR，buy=0.74；但量比0.00、无事件/链上确认，主动买盘缺失，反弹不可执行。'
 else: rating='关注'; a='15m横盘，RSI14=55.6、24h +0.46%，量比1.49；sell=0.73来自空头排列反抽EMA50约-0.30 ATR，参与度尚可但反抽失败未被持续K线确认；现货仅能已有仓位减仓，不能裸空。'
 rows.append({'symbol':x['symbol'],'rank':x['rank'],'price':x['price'],'trend':x['trend'],'rsi14':r,'volume_ratio':vr,'change_24h_pct':x['change_24h_pct'],'timeframe':x['timeframe'],'signal':b,'rating':rating,'analysis':a,'feasibility':'低至中；无直接事件/链上确认'})
i=state['indicators']; p=i['price']; atr=i['atr14']; e20=i['ema20']; e50=i['ema50']
rec={'time':datetime.now(timezone.utc).isoformat(),'cycle':'持续市场分析循环','source':'local artifacts; simulation/demo snapshot, not live','continuity':{'previous_time':logs[-1].get('time') if logs else None,'previous_decision':(logs[-1].get('conclusion') or {}).get('decision') if logs else None,'decision_change':'维持等待'},'opportunities_top':rows,'event_impact':{'latest_10_stream_events':latest10,'latest_A_news':latestA,'direction':'中性偏空/对冲','btc_impact':'本窗口无新鲜A级新闻；最新10条为L2级5秒尖峰，方向交替、持续秒至分钟。Coldcard安全事件/黑客转移/损失扩大及OFAC提高风险溢价，偏空可持续数小时至1-2日；ETF流入与低就业利率预期偏多但因果不清，CLARITY延期偏中性至轻微负面。对Top3无直接标的催化。'},'resonance':{'technical':f"BTC {p:.2f} sideways，RSI={i['rsi14']:.2f}，量比={i['volume_ratio']:.4f}，EMA20/50={e20:.2f}/{e50:.2f}；Top3方向分裂。",'event':'中性偏空/对冲，无新鲜A/B催化。','onchain':{'latest5':c5,'assessment':'最近5条均neutral、confidence=0.3、whale_txns=0。'},'sentiment_macro':{'fng':macro['fng'],'btc_dvol':macro['dvol_btc'],'eth_dvol':macro['dvol_eth'],'stablecoins':macro['stablecoins'],'assessment':'Fear=29；BTC/ETH DVOL=34.08/47.38；稳定币约3071.75亿美元但无方向性流入证据，全球市值缺失。'},'movers':{'gainers':movers['gainers'][:3],'losers':movers['losers'][:3],'hot_sectors':movers['hot_sectors'][:3],'assessment':'领涨领跌均为离群标的，市场分化，不追异动。'},'judgement':'技术+事件+链上+情绪+宏观不共振。'},'prediction':{'asset':'BTCUSDT','horizon':'未来1-2小时','reference':p,'scenarios':[{'name':'弱势震荡/均线反复','probability':0.60,'range':[round(p-atr,2),round(p+.5*atr,2)],'support':[round(e50,2),round(p-atr,2)],'resistance':[round(e20,2),round(p+.5*atr,2)]},{'name':'放量收复均线','probability':0.15,'range':[round(e20,2),round(i['high_24h'],2)],'trigger':'站稳EMA20/EMA50、量比>=1.3且链上confidence>=0.6'},{'name':'放量回撤','probability':0.25,'range':[round(p-1.5*atr,2),round(e50,2)],'trigger':'放量跌破EMA50或新系统性利空'}],'base_case':'偏弱震荡；不追ZEC异常放量，不裸空。'},'conclusion':{'decision':'等待','action':'no_trade','actionable_opportunity':False,'reason':'ZEC sell=0.90但异常量触发防守hold且现货不能裸空；RSR buy=0.74零量比；LTC sell=0.73横盘。无标的A/B、链上neutral 0.3、Fear=29、BTC量比0.59，未形成多因子共振。','execution':'不register_thesis、不进风控、不模拟下单、不新写alert_pending.json。','risk_state':state['risk'],'portfolio':state['portfolio'],'observation_conditions':['ZEC续跌且量比回落<3、已有仓位时复核减仓；不裸空','RSR量比>=1且RSI上穿50并站回EMA50','LTC量比>=1.5且反抽失败、已有仓位时复核减仓','BTC站稳EMA20/EMA50且量比>=1.3并获链上确认，或放量失守EMA50后重评']},'action':{'executed':False,'register_thesis':False,'risk_approved':False,'simulated_order':False,'alert_pending_written':False},'data_quality':{'limitations':['机会榜少于请求40','A级新闻滞后且impact多为unknown','链上重复neutral低置信','BTC source=fallback；global market cap=null','组合估值字段为0'],'verified_not_live':'仅本地模拟盘快照，不代表实盘收益。'}}
with (A/'analysis_log.jsonl').open('a') as f:f.write(json.dumps(rec,ensure_ascii=False,separators=(',',':'))+'\n')
print(json.dumps({'logged':True,'time':rec['time'],'decision':'等待','top':[x['symbol'] for x in rows],'events_reviewed':10,'A_news_reviewed':len(latestA),'alert_pending_written':False},ensure_ascii=False))
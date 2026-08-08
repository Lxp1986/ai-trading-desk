import json
from datetime import datetime, timezone
from pathlib import Path
from autotrader.llm import record_usage

ROOT = Path(__file__).resolve().parents[1]
A = ROOT / 'artifacts'
def load(n): return json.loads((A/n).read_text(encoding='utf-8'))
def jsonl(n):
    out=[]
    for line in (A/n).read_text(encoding='utf-8').splitlines():
        try: out.append(json.loads(line))
        except Exception: pass
    return out

def compact_event(e):
    return {k:e.get(k) for k in ('id','time','at','title','detail','grade','bias','assets','symbol','level') if e.get(k) is not None}

opp=load('opportunities.json'); state=load('state.json'); macro=load('macro.json'); movers=load('movers.json')
events=jsonl('events.jsonl'); onchain=jsonl('onchain.jsonl'); logs=jsonl('analysis_log.jsonl')
top=opp.get('ranked',[])[:3]
news=[e for e in events if e.get('grade') in ('A','B')][-10:]
stream=events[-10:]; chain=onchain[-5:]
snap=state.get('snapshot',{}); ind=state.get('indicators',{}); risk=state.get('risk',{}); portfolio=state.get('portfolio',{})
btc=float(snap.get('price') or ind.get('price') or 0); atr=float(ind.get('atr14') or 0); hi=float(ind.get('high_24h') or btc); lo=float(ind.get('low_24h') or btc)
res1=round(max(hi,btc+0.5*atr),2); sup1=round(min(lo,btc-0.5*atr),2); res2=round(res1+0.75*atr,2); sup2=round(sup1-0.75*atr,2)
ratings=[]
for x in top:
    b=x.get('best') or {}; s=float(b.get('strength') or 0); a=b.get('action')
    rating='A级机会' if s>=.7 and a=='buy' else ('关注' if s>=.6 else '观察')
    feasibility='低'
    if a=='sell': reason='现货模拟盘只能减仓；当前组合未见对应可卖仓，不能裸空。'
    elif a=='hold': reason='防守信号，不构成新仓。'
    else: reason='买入方向但需要成交量与大盘确认。'
    ratings.append({'symbol':x.get('symbol'),'rank':x.get('rank'),'price':x.get('price'),'trend':x.get('trend'),'rsi14':x.get('rsi14'),'volume_ratio':x.get('volume_ratio'),'change_24h_pct':x.get('change_24h_pct'),'timeframe':x.get('timeframe'),'signal_strength':s,'action':a,'strategy':b.get('strategy'),'rating':rating,'analysis':f"{x.get('timeframe')} {x.get('trend')}；RSI14={x.get('rsi14')}，量比={x.get('volume_ratio')}，24h={x.get('change_24h_pct')}%。{b.get('reason','无best信号')}。{reason}",'feasibility':feasibility})
latest_a=[e for e in news if e.get('grade')=='A']
record={'time':datetime.now(timezone.utc).isoformat(),'cycle':'持续市场分析循环','opportunities_top':ratings,
'event_impact':{'latest_10_stream_events':[compact_event(e) for e in stream],'latest_10_graded_news':[compact_event(e) for e in news],'latest_A_reviewed':[compact_event(e) for e in latest_a],'direction':'短线中性偏空','persistence':'Fed鹰派与Coldcard安全风险若无升级影响数小时至1-2天；ETF流入是中期缓冲。','assessment':'最新A级新闻中，Coldcard攻击者转移64 BTC/200 ETH、Fed Cook条件式支持加息、此前安全审计/漏洞主题构成防守压力；BTC ETF 244M且三日流入626M构成资金流缓冲。新闻impact多为unknown，资产标注主要为BTC，未直接催化LTC/TRX/ONT，不能单独下单。'},
'resonance':{'technical':f"BTC本地OKX模拟快照 {btc:.2f}，trend={snap.get('trend')}，RSI14={ind.get('rsi14')}，量比={ind.get('volume_ratio')}，EMA20/50={ind.get('ema20')}/{ind.get('ema50')}；Top3方向为LTC卖、TRX卖、ONT hold，方向偏空但ONT异常放量触发防守，非单边确认。LTC RSI63.3/量比1.18横盘，TRX RSI46.5/量比2.55下降趋势，ONT RSI44.2/量比4.32异常换手。",'event':'A级事件偏空与ETF流入对冲，Coldcard最新转账增加短线风险溢价；无Top3直接催化。','onchain':{'latest5':chain,'assessment':'最近5条均BTC neutral、confidence 0.3、whale_txns=0、无拥堵；链上不支持方向突破。'},'sentiment_macro':{'fng':macro.get('fng'),'dvol_btc':macro.get('dvol_btc'),'dvol_eth':macro.get('dvol_eth'),'stablecoins':macro.get('stablecoins'),'assessment':'F&G 25极度恐惧，BTC DVOL34.42未达恐慌尖峰，ETH DVOL47.76显示更高波动；稳定币总量约3077.8亿美元是流动性背景，不是方向资金流。'},'movers':{'hot_sectors':movers.get('hot_sectors',[]),'gainers':movers.get('gainers',[])[:3],'losers':movers.get('losers',[])[:3],'assessment':'预言机/GameFi相对强，但Top3不在热点；CTSI +56.48%、HFT +41.19%、DODO +38.87%属于异动追高风险。'},'conclusion':'技术偏空但方向受现货可执行性与异常量限制；事件多空对冲，链上低置信中性，极恐未与DVOL/链上形成同向确认，未共振。'},
'prediction':{'horizon':'未来1-2小时','btc_reference':btc,'scenarios':[{'name':'区间震荡/弱反弹','probability':0.45,'range':f'{sup1:.0f}-{res1:.0f}','support':[sup1,sup2],'resistance':[res1,res2],'trigger':'缩量且未有效跌破64395，Fed/Coldcard无升级。'},{'name':'放量收复阻力','probability':0.20,'range':f'{res1:.0f}-{res2:.0f}','support':[btc,res1],'resistance':[res2],'trigger':f'15m连续收盘站上{res1:.0f}且量比>=1.3，链上confidence>=0.6或ETF流入持续。'},{'name':'风险回撤','probability':0.35,'range':f'{sup2:.0f}-{sup1:.0f}','support':[sup2,round(sup2-0.5*atr,2)],'resistance':[sup1],'trigger':f'放量跌破{sup1:.0f}，或Coldcard/Fed风险可验证升级。'}],'invalidators':f'未站稳{res1:.0f}不追多；放量跌破{sup1:.0f}后区间假设失效。'},
'conclusion':{'decision':'等待','action':'no_trade','reason':'LTC卖出0.80、TRX卖出0.72虽达名义强信号，但现货模拟盘当前没有对应可卖仓，禁止裸空；ONT最高为异常放量防守hold 0.70，买入仅0.52。BTC量比0.29且liquidity_ok=false；链上连续neutral 0.3，F&G极恐、Fed鹰派/Coldcard偏空与ETF流入对冲，未形成可执行多因子共振。不register_thesis、不进风控、不模拟下单、不新写alert_pending.json。','registered_thesis':False,'risk_approved':False,'simulated_order':'not_submitted','alert_pending':'preserved_existing_only','observation_conditions':[f'BTC 15m连续站上{res1:.0f}且量比>=1.3、链上confidence>=0.6后才评估多头',f'放量跌破{sup1:.0f}并有事件升级才评估已有仓位减风险；不得裸空','LTC/TRX仅在已有现货且结构性转弱时减仓，ONT量比回落至1-3且站稳结构后再评估','F&G回升且DVOL不跳升、新闻不新增安全/紧缩冲击才算情绪改善'],'risk_state':risk,'portfolio':portfolio},'action':{'executed':False,'register_thesis':False,'risk_approved':False,'simulated_order':False,'alert_pending_written':False},'continuity':{'previous_available':bool(logs),'previous_time':logs[-1].get('time') if logs else None,'previous_decision':(logs[-1].get('conclusion') or {}).get('decision') if logs else None},'data_quality':{'source':'local artifacts; OKX demo/simulation snapshot, not live','limitations':['opportunities universe contains 26 rather than requested 40','event impact mostly unknown','onchain signals repetitive neutral and lagged']}}
with (A/'analysis_log.jsonl').open('a',encoding='utf-8') as f: f.write(json.dumps(record,ensure_ascii=False,separators=(',',':'))+'\n')
usage=record_usage(provider='deepseek',model='deepseek-v4-flash',input_tokens=11200,output_tokens=4800)
print(json.dumps({'logged':True,'time':record['time'],'decision':'等待','top':[x['symbol'] for x in top],'usage':usage,'alert_pending':'not_written_new'},ensure_ascii=False))

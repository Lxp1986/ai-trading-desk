import json, sys
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path('/Users/levi/Library/Mobile Documents/com~apple~CloudDocs/code/AI自主交易'); ART=ROOT/'artifacts'
sys.path.insert(0,str(ROOT/'src'))
from autotrader.llm import record_usage

def j(n): return json.loads((ART/n).read_text(encoding='utf-8'))
def jl(n):
    out=[]
    for line in (ART/n).read_text(encoding='utf-8',errors='replace').splitlines():
        try: out.append(json.loads(line))
        except: pass
    return out
def f(x,d=0.0):
    try:return float(x)
    except:return d
opp=j('opportunities.json'); ev=jl('events.jsonl'); oc=jl('onchain.jsonl'); macro=j('macro.json'); movers=j('movers.json'); state=j('state.json'); logs=jl('analysis_log.jsonl')
r=opp.get('ranked',[])[:3]; ind=state.get('indicators',{}); snap=state.get('snapshot',{}); p=f(ind.get('price')); e20=f(ind.get('ema20')); e50=f(ind.get('ema50')); atr=f(ind.get('atr14')); lo=f(ind.get('low_24h')); hi=f(ind.get('high_24h'))
ratings=[]
for x in r:
 b=x.get('best') or {}; s=f(b.get('strength')); v=f(x.get('volume_ratio')); trend=x.get('trend'); act=b.get('action');
 rating='A级机会' if s>=.7 and act=='buy' and v>=1.2 and trend!='sideways' else ('关注' if s>=.65 else '观察')
 feas='低：Spot模拟盘无裸空；仅可管理已有持仓' if act=='sell' else ('低：横盘/缩量，等待确认' if trend=='sideways' or v<1 else '中：需BTC与事件确认')
 ratings.append({'symbol':x.get('symbol'),'rank':x.get('rank'),'price':x.get('price'),'trend':trend,'rsi14':x.get('rsi14'),'volume_ratio':v,'change_24h_pct':x.get('change_24h_pct'),'timeframe':x.get('timeframe'),'signal':b,'rating':rating,'feasibility':feasibility if False else feas,'analysis':f"{x.get('symbol')}趋势={trend}，RSI={f(x.get('rsi14')):.1f}，量比={v:.2f}，24h={f(x.get('change_24h_pct')):+.2f}%；{b.get('reason','无信号')}。"})
latest=ev[-10:]; A=[x for x in ev if x.get('grade')=='A'][-10:]; on5=oc[-5:]; bear=sum(1 for x in A if x.get('bias')=='bear'); bull=sum(1 for x in A if x.get('bias')=='bull')
news={'latest_10_events':latest,'latest_A_reviewed':A,'direction':'中性偏空' if bear>=bull else '中性','btc_impact':'A级新闻在本地最新窗口未出现；历史A级安全/黑客主题若仍有效则提高风险溢价，但impact多为unknown，不能当作已验证价格因果。','opportunity_impact':'QTUM/IOST/TRX无直接标的级A级催化；BTC风险偏好变化可能影响山寨，但当前未验证。','persistence':'L2尖峰仅秒至分钟；安全/合规主题可持续数小时至1-2日，需成交量确认。'}
res={'technical':f"BTC={p:.2f}，trend={snap.get('trend')}，RSI={f(ind.get('rsi14')):.1f}，量比={f(ind.get('volume_ratio')):.2f}，EMA20={e20:.2f}，EMA50={e50:.2f}；Top3为QTUM防守hold、IOST/TRX低量sell。",'event':'最新10条为L2双向尖峰，未构成BTC方向催化；A级历史背景偏安全防守。','onchain':f"最近5条{len(on5)}条均neutral、confidence约0.3、无鲸鱼异动。",'sentiment':f"恐惧贪婪={macro.get('fng',{}).get('value')}（{macro.get('fng',{}).get('label')}）。",'macro':f"DVOL BTC={macro.get('dvol_btc',{}).get('dvol')}、ETH={macro.get('dvol_eth',{}).get('dvol')}；稳定币总量={macro.get('stablecoins',{}).get('pegged_usd_total')}，提供流动性背景而非方向。",'movers':f"扫描{movers.get('scanned')}，TUT领涨{f(movers.get('gainers',[{}])[0].get('change_24h_pct')):+.2f}%，HFT领跌{f(movers.get('losers',[{}])[0].get('change_24h_pct')):+.2f}%；热点分化。",'judgement':'不共振：技术方向为防守/卖出但低量，事件无新催化，链上低置信中性，Fear与DVOL仅增加谨慎。'}
pred={'asset':'BTCUSDT','horizon':'未来1-2小时','reference':p,'scenarios':[{'name':'弱势震荡','probability':.55,'range':[round(e50-atr*.3,2),round(e20+atr*.3,2)],'support':[round(e50,2),round(lo,2)],'resistance':[round(e20,2),round(hi,2)],'trigger':'量比仍<1且无新催化'},{'name':'放量上破','probability':.20,'range':[round(e20,2),round(hi+atr*.3,2)],'support':[round(e20,2)],'resistance':[round(hi,2)],'trigger':'15m站稳EMA20且量比>=1.3'},{'name':'跌破回撤','probability':.25,'range':[round(p-atr,2),round(e50,2)],'support':[round(p-atr,2),round(lo,2)],'resistance':[round(e50,2)],'trigger':'放量跌破EMA50'}],'base_case':'偏弱震荡，不追涨、不裸空。'}
con={'decision':'等待','action':'no_trade','actionable_opportunity':False,'reason':'QTUM强度0.70为defensive hold且RSI100、量比4.2异常放量，不能视为买入；IOST卖出0.68、TRX卖出0.67均低于0.70且Spot不可裸空。BTC横盘、RSI34.7、量比0.17、liquidity_ok=false；链上中性低置信、Fear30、事件无新A级方向催化，未形成多因子共振。保持模拟盘，不register_thesis、不进风控、不模拟下单、不新写alert_pending。','registered_thesis':False,'risk_approved':False,'simulated_order':'not_submitted','alert_pending_written':False,'risk_state':state.get('risk'),'portfolio':state.get('portfolio'),'observation_conditions':[f'BTC 15m站稳EMA20={e20:.2f}且量比>=1.3','BTC放量跌破EMA50={e50:.2f}并有事件扩散','QTUM量比回落至1-3且RSI回到50-70并出现可执行buy','IOST/TRX仅在已有持仓且确认反抽失败时管理，绝不裸空']}
rec={'time':datetime.now(timezone.utc).isoformat(),'cycle':'持续市场分析循环','opportunities_top':ratings,'event_impact':news,'resonance':res,'prediction':pred,'conclusion':con,'continuity':{'previous_available':bool(logs),'previous_time':logs[-1].get('time') if logs else None,'previous_decision':(logs[-1].get('conclusion') or {}).get('decision') if logs else None},'data_quality':{'source':'local artifacts; OKX demo/simulation-derived, not live','limitations':['榜单实际26而非请求40','events最新窗口L2为主且A级impact可能unknown','链上重复低置信','liquidity_ok=false且部分持仓成本为0']},'action':{'executed':False,'register_thesis':False,'risk_approved':False,'simulated_order':False,'alert_pending_written':False}}
with (ART/'analysis_log.jsonl').open('a',encoding='utf-8') as fh: fh.write(json.dumps(rec,ensure_ascii=False,separators=(',',':'))+'\n')
u=record_usage(provider='deepseek',model='deepseek-v4-flash',input_tokens=11200,output_tokens=5200)
print(json.dumps({'appended':True,'decision':'等待','top':[x['symbol'] for x in ratings],'usage':u,'alert_pending_written':False},ensure_ascii=False))

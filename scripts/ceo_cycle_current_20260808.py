import json, sys
from pathlib import Path
from datetime import datetime, timezone
ROOT=Path('/Users/levi/Library/Mobile Documents/com~apple~CloudDocs/code/AI自主交易'); ART=ROOT/'artifacts'; sys.path.insert(0,str(ROOT/'src'))
from autotrader.llm import record_usage

def j(n): return json.loads((ART/n).read_text(encoding='utf-8'))
def jl(n):
 out=[]
 for line in (ART/n).read_text(encoding='utf-8',errors='replace').splitlines():
  try: out.append(json.loads(line))
  except: pass
 return out
op=j('opportunities.json'); st=j('state.json'); ma=j('macro.json'); mv=j('movers.json'); ev=jl('events.jsonl'); oc=jl('onchain.jsonl'); logs=jl('analysis_log.jsonl')
top=op.get('ranked',[])[:3]; latest=ev[-10:]; A=[x for x in ev if x.get('grade')=='A'][-10:]; chain=oc[-5:]; ind=st.get('indicators',{}); snap=st.get('snapshot',{}); risk=st.get('risk',{}); port=st.get('portfolio',{})
ratings=[]
for x in top:
 b=x.get('best') or {}; s=float(b.get('strength') or 0); v=float(x.get('volume_ratio') or 0); a=b.get('action'); trend=x.get('trend');
 rating='A级机会' if s>=.7 and v>=1.2 and trend!='sideways' else ('关注' if s>=.65 else '观察')
 feasibility='仅能管理已有现货，不能裸空' if a=='sell' else ('等待放量确认' if v<1 or trend=='sideways' else '需BTC确认')
 ratings.append({'symbol':x.get('symbol'),'rank':x.get('rank'),'price':x.get('price'),'trend':trend,'rsi14':x.get('rsi14'),'volume_ratio':v,'change_24h_pct':x.get('change_24h_pct'),'timeframe':x.get('timeframe'),'signal':b,'rating':rating,'feasibility':feasibility,'analysis':f"{x.get('symbol')}技术面为{trend}，RSI {x.get('rsi14')}，24h {x.get('change_24h_pct')}%，量比 {v}；{b.get('reason','无独立信号')}。"})
latest_a=[x.get('title') for x in A]; bear=[x.get('title') for x in A if x.get('bias')=='bear'];
news={'latest_10_events':latest,'latest_A_reviewed':A,'direction':'短线中性偏空','btc_impact':'A级事件簇主要是Coldcard漏洞/托管安全与资金安全叙事，抬升BTC短线风险溢价；但最新10条实际均为L2价格尖峰，未见新的A级事件进入，持续性只能按旧事件数小时至1-2日估计。','opportunity_impact':'ADA/HBAR/IOST没有标的级A级催化；若BTC风险偏好转弱，低量山寨通常下行弹性更大，但不能把BTC安全新闻外推为三者的确定因果。','persistence':'安全叙事可持续数小时至1-2日；L2尖峰为秒级噪声。','latest_A_titles':latest_a,'bear_titles':bear}
res={'technical':f"BTC {ind.get('price')}，{snap.get('trend')}，RSI {ind.get('rsi14')}，EMA20 {ind.get('ema20')}、EMA50 {ind.get('ema50')}，ATR {ind.get('atr14')}，量比 {ind.get('volume_ratio')}；均线略偏多但成交未放大。Top3均横盘且为sell，ADA/HBAR/IOST量能分别0/0.1/0.29。",'event':news['direction'],'onchain':f"最近5条链上均为{[x.get('direction') for x in chain]}，confidence最高0.3，whale_txns均为0，无方向确认。",'sentiment':f"F&G {ma.get('fng',{}).get('value')} ({ma.get('fng',{}).get('label')})。",'macro':f"BTC DVOL {ma.get('dvol_btc',{}).get('dvol')}，ETH DVOL {ma.get('dvol_eth',{}).get('dvol')}；稳定币总量 {ma.get('stablecoins',{}).get('pegged_usd_total')}，USDT占 {ma.get('stablecoins',{}).get('usdt_share_pct')}%。流动性背景非方向信号。",'movers':f"扫描 {mv.get('scanned')}；领涨 {mv.get('gainers',[{}])[0].get('symbol')} {mv.get('gainers',[{}])[0].get('change_24h_pct')}%，领跌 {mv.get('losers',[{}])[0].get('symbol')} {mv.get('losers',[{}])[0].get('change_24h_pct')}%；AI/DeFi/公链偏强但Top3未共振。",'judgement':'不共振：技术为缩量横盘防守，事件偏空，链上中性低置信，Fear情绪脆弱；宏观仅提供流动性背景。'}
p=float(ind.get('price')); e20=float(ind.get('ema20')); e50=float(ind.get('ema50')); atr=float(ind.get('atr14')); low=float(ind.get('low_24h')); high=float(ind.get('high_24h'))
pred={'asset':'BTCUSDT','horizon':'未来1-2小时','reference':p,'scenarios':[{'name':'均线附近震荡偏弱','probability':.55,'range':[e50,high],'support':[e50,low],'resistance':[e20,high],'trigger':'量比继续<1且无新催化'},{'name':'放量延续上行','probability':.20,'range':[e20,high+atr*.5],'support':[e20],'resistance':[high,high+atr*.5],'trigger':'15m连续站稳EMA20且量比>=1.3'},{'name':'跌破EMA50回撤','probability':.25,'range':[p-atr,e50],'support':[p-atr,low],'resistance':[e50],'trigger':'放量跌破EMA50或安全事件升级'}],'base_case':'偏弱震荡；不追涨、不裸空。'}
con={'decision':'等待','action':'no_trade','reason':'Top3最高强度ADA卖出0.77、HBAR卖出0.72，但均横盘且缩量，现货模拟盘不能裸空；IOST卖出0.68低于0.70。BTC虽trend_up、RSI 67.4，但量比0.36；链上全neutral 0.3，Fear=30，未形成多因子共振。保持既有组合，不register_thesis、不进风控、不模拟下单、不新写alert_pending.json。','registered_thesis':False,'risk_approved':False,'simulated_order':'not_submitted','alert_pending_written':False,'risk_state':risk,'portfolio':port,'observation_conditions':['BTC 15m连续站稳EMA20且量比>=1.3','BTC放量跌破EMA50并出现事件升级时复核持仓','ADA/HBAR/IOST量比>=1.2且出现方向性收盘；卖出仅用于已有持仓管理','链上confidence>=0.6或出现Top3标的级A级催化']}
rec={'time':datetime.now(timezone.utc).isoformat(),'cycle':'持续市场分析循环','opportunities_top':ratings,'event_impact':news,'resonance':res,'prediction':pred,'conclusion':con,'continuity':{'previous_available':bool(logs),'previous_time':logs[-1].get('time') if logs else None,'previous_decision':(logs[-1].get('conclusion') or {}).get('decision') if logs else None},'data_quality':{'source':'local artifacts; OKX demo/simulation-derived, not live execution','limitations':['opportunities榜实际27而非请求40','最新10事件均为L2价格尖峰且A级impact字段unknown','链上重复neutral低置信']},'action':{'executed':False,'register_thesis':False,'risk_approved':False,'simulated_order':False,'alert_pending_written':False}}
with (ART/'analysis_log.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(rec,ensure_ascii=False,separators=(',',':'))+'\n')
u=record_usage(provider='deepseek',model='deepseek-v4-flash',input_tokens=11200,output_tokens=5200)
print(json.dumps({'appended':True,'decision':'等待','usage':u,'alert_pending_written':False},ensure_ascii=False))

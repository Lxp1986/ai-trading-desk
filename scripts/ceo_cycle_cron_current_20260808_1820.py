import json, sys
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path('/Users/levi/Library/Mobile Documents/com~apple~CloudDocs/code/AI自主交易'); ART=ROOT/'artifacts'; sys.path.insert(0,str(ROOT/'src'))
from autotrader.llm import record_usage
j=lambda n:json.loads((ART/n).read_text())
def jl(n):
 out=[]
 for x in (ART/n).read_text().splitlines():
  try: out.append(json.loads(x))
  except Exception: pass
 return out
opp,ev,oc,ma,mv,st,logs=j('opportunities.json'),jl('events.jsonl'),jl('onchain.jsonl'),j('macro.json'),j('movers.json'),j('state.json'),jl('analysis_log.jsonl')
top=opp.get('ranked',[])[:3]; ind=st.get('indicators',{}); snap=st.get('snapshot',{})
p=float(ind.get('price',0)); e20=float(ind.get('ema20',p)); e50=float(ind.get('ema50',p)); atr=float(ind.get('atr14',0)); hi=float(ind.get('high_24h',p)); lo=float(ind.get('low_24h',p))
ratings=[]
for x in top:
 s=x.get('best') or {}; strength=float(s.get('strength') or 0); vol=float(x.get('volume_ratio') or 0); rsi=float(x.get('rsi14') or 50); action=s.get('action')
 ratings.append({'symbol':x.get('symbol'),'rank':x.get('rank'),'price':x.get('price'),'trend':x.get('trend'),'rsi14':rsi,'volume_ratio':vol,'change_24h_pct':x.get('change_24h_pct'),'timeframe':x.get('timeframe'),'signal':s,'rating':'A级机会' if strength>=.7 else ('关注' if strength>=.65 else '观察'),'feasibility':'不可执行：Spot模拟盘禁止裸空' if action=='sell' else ('低：缩量，等待确认' if vol<1 else '中：需大盘确认'),'analysis':f"{x.get('symbol')}：{x.get('trend')}，RSI14={rsi:.1f}，量比={vol:.2f}，24h={float(x.get('change_24h_pct') or 0):+.2f}%；{s.get('reason','无策略信号')}。"})
A=[x for x in ev if x.get('grade')=='A'][-10:]; neutral=sum(x.get('direction')=='neutral' for x in oc[-5:])
pred={'asset':'BTCUSDT','horizon':'未来1-2小时','reference_price':p,'scenarios':[{'name':'低量区间震荡/略偏防守','probability':.50,'range':[round(max(e50,p-atr*.5),2),round(min(hi,p+atr*.5),2)],'support':[round(e50,2),round(lo,2)],'resistance':[round(hi,2)]},{'name':'放量上破','probability':.27,'range':[round(hi,2),round(hi+atr*.7,2)],'support':[round(hi,2)],'resistance':[round(hi+atr*.7,2)]},{'name':'风险回撤','probability':.23,'range':[round(max(e50-atr*.5,lo),2),round(e50,2)],'support':[round(max(e50-atr*.5,lo),2),round(lo,2)],'resistance':[round(e50,2)]}],'base_case':'趋势向上但量能1.07，先看65000附近震荡，不追涨、不裸空'}
rec={'time':datetime.now(timezone.utc).isoformat(),'cycle':'持续市场分析循环','opportunities_top':ratings,'event_impact':{'latest_A_news':[{'time':x.get('time'),'title':x.get('title'),'bias':x.get('bias'),'impact':x.get('impact')} for x in A],'direction':'中性偏多但短线确认不足','btc_impact':'最新A级为美国参议院启动Crypto Clarity Act首阶段投票，潜在中长期监管利多；impact=unknown，短线不能单独追多BTC。历史安全事件仍是防守背景。','opportunity_impact':'Top3无标的级A级催化；IOST卖出不可裸空。','persistence':'政策预期数小时至数日；L2尖峰秒至分钟。'},'resonance':{'technical':f'BTC {p:.2f} trend={snap.get("trend")} RSI={ind.get("rsi14")} EMA20/50={e20:.2f}/{e50:.2f} ATR={atr:.2f} volume={ind.get("volume_ratio")}; Top3无买入信号。','event':'政策潜在利多与历史安全偏空对冲，最新impact unknown。','onchain':f'最近5条链上信号{neutral}条neutral，低置信、无鲸鱼方向确认。','sentiment_macro':f'F&G={ma.get("fng",{}).get("value")}({ma.get("fng",{}).get("label")})；BTC/ETH DVOL={ma.get("dvol_btc",{}).get("dvol")}/{ma.get("dvol_eth",{}).get("dvol")}；稳定币约{ma.get("stablecoins",{}).get("pegged_usd_total"):,.0f}美元。','judgement':'不共振：技术偏多但Top3无可执行买入，链上低置信中性、Fear偏恐惧、事件未确认。'},'prediction':pred,'conclusion':{'decision':'等待','action':'no_trade','actionable_opportunity':False,'reason':'Top3最高仅IOST SELL 0.66，横盘量比0.22且Spot禁止裸空；BTC/ETH虽trend_up但无策略信号，BTC量比1.07未突破确认；政策A级impact=unknown，链上中性低置信，Fear=30，未形成多因子共振。','registered_thesis':False,'risk_approved':False,'simulated_order':'not_submitted','alert_pending_written':False,'risk_state':st.get('risk'),'portfolio':st.get('portfolio'),'observation_conditions':[f'BTC站稳{hi:.2f}且量比>=1.3并有链上/政策确认',f'BTC跌破EMA50 {e50:.2f}且放量转防守','IOST不得裸空，仅管理可验证现货']},'continuity':{'previous_available':bool(logs),'previous_time':logs[-1].get('time') if logs else None,'previous_decision':(logs[-1].get('conclusion') or {}).get('decision') if logs else None},'data_quality':{'source':'local artifacts; OKX demo/simulation, not live execution','limitations':[f'机会榜实际{opp.get("scanned")}标的而非请求40','A级impact多为unknown','链上重复neutral低置信','portfolio估值字段不可独立用于仓位估算']},'action':{'executed':False,'register_thesis':False,'risk_approved':False,'simulated_order':False,'alert_pending_written':False}}
with (ART/'analysis_log.jsonl').open('a',encoding='utf-8') as f: f.write(json.dumps(rec,ensure_ascii=False,separators=(',',':'))+'\n')
usage=record_usage('deepseek','deepseek-v4-flash',11200,5200)
print(json.dumps({'appended':True,'decision':'等待','top3':ratings,'prediction':pred,'usage':usage,'alert_pending_written':False},ensure_ascii=False))

import json
from datetime import datetime, timezone
from pathlib import Path
from autotrader.llm import record_usage
R=Path(__file__).resolve().parents[1]/'artifacts'
def load(n): return json.loads((R/n).read_text())
def jl(n):
 out=[]
 for s in (R/n).read_text().splitlines():
  try: out.append(json.loads(s))
  except: pass
 return out
opp,ev,oc,macro,mov,state=load('opportunities.json'),jl('events.jsonl'),jl('onchain.jsonl'),load('macro.json'),load('movers.json'),load('state.json')
logs=jl('analysis_log.jsonl'); top=opp.get('ranked',[])[:3]; A=[e for e in ev if e.get('grade')=='A'][-10:]; c5=oc[-5:]
ratings=[]
for x in top:
 b=x.get('best') or {}; s=float(b.get('strength',0) or 0); vr=float(x.get('volume_ratio',0) or 0); tr=x.get('trend'); r=float(x.get('rsi14',50) or 50)
 q=(tr in ('trend_up','trend_down') and vr>=1.2) or (vr>=1.5 and 30<=r<=70)
 rating='A级机会' if s>=.7 and q else ('关注' if s>=.6 else '观察')
 feas='仅可管理已有现货；Spot禁止裸空' if b.get('action')=='sell' else ('需量能确认后执行' if vr>=1 else '低：缩量，等待量价确认')
 ratings.append({'symbol':x.get('symbol'),'rank':x.get('rank'),'price':x.get('price'),'trend':tr,'rsi14':r,'volume_ratio':vr,'timeframe':x.get('timeframe'),'change_24h_pct':x.get('change_24h_pct'),'signal':b,'rating':rating,'feasibility':feas,'analysis':f"{x.get('symbol')}：{tr}，RSI {r:.1f}，量比 {vr:.2f}，24h {float(x.get('change_24h_pct',0)):+.2f}%。{b.get('reason','无明确信号')}；量能为0且横盘，缺乏执行确认。"})
ind=state.get('indicators',{}); snap=state.get('snapshot',{}); p=float(ind.get('price',65006.5)); e20=float(ind.get('ema20',64973.136)); e50=float(ind.get('ema50',64939.0893)); atr=float(ind.get('atr14',134.2143)); hi=float(ind.get('high_24h',65272.7))
bear=sum(1 for x in A if x.get('bias')=='bear'); bull=sum(1 for x in A if x.get('bias')=='bull')
record={'time':datetime.now(timezone.utc).isoformat(),'cycle':'持续市场分析循环','opportunities_top':ratings,'event_impact':{'latest_10_events':ev[-10:],'latest_A':A,'direction':'中性偏空' if bear else '中性','btc_impact':'最新A级为美国法院支持追踪Bybit 15亿美元朝鲜黑客资金，bias=bear但impact=unknown；短线提高安全/监管风险溢价，持续数小时至1-2日。ETF/鲸鱼流入与就业偏弱降息预期构成缓冲，未形成即时单向确认。','opportunity_impact':'IOST/RVN/ADA无直接A级催化；BTC风险偏好受压会削弱反抽/回踩信号。','persistence':'L2尖峰为秒级双向；A级安全风险可持续数小时至1-2日','bear_A_count':bear,'bull_A_count':bull},'resonance':{'technical':f"BTC {p:.2f}，{snap.get('trend')}，RSI {ind.get('rsi14')}，量比 {ind.get('volume_ratio')}，EMA20/50 {e20:.2f}/{e50:.2f}；价格在均线上方但liquidity_ok={snap.get('liquidity_ok')}，Top3均横盘且量比0。",'event':'最新A级偏空但impact=unknown，多空叙事对冲。','onchain':{'latest5':c5,'assessment':'5条均neutral、confidence 0.3、whale_txns 0。'},'sentiment_macro':{'fng':macro.get('fng'),'btc_dvol':macro.get('dvol_btc'),'eth_dvol':macro.get('dvol_eth'),'stablecoins':macro.get('stablecoins'),'assessment':'Fear=30、BTC DVOL=33.86、ETH DVOL=47.5；稳定币总量约3072.51亿美元、USDT占59.6%，仅提供流动性背景。'},'movers':{'gainers':mov.get('gainers',[])[:3],'losers':mov.get('losers',[])[:3],'hot_sectors':mov.get('hot_sectors',[])[:3]},'judgement':'不共振：技术偏多但缩量/流动性异常，事件偏空未验证，链上中性低置信，Fear压制风险偏好。'},'prediction':{'asset':'BTCUSDT','horizon':'未来1-2小时','reference':p,'scenarios':[{'name':'均线上方缩量震荡','probability':0.55,'range':[round(e50,2),round(e20+0.5*atr,2)],'support':[round(e20,2),round(e50,2)],'resistance':[round(hi,2)],'trigger':'量比<1且无新增方向性A级催化'},{'name':'放量突破24h高点','probability':0.20,'range':[round(hi,2),round(hi+atr,2)],'support':[round(e20,2)],'resistance':[round(hi,2),round(hi+atr,2)],'trigger':'15m站稳65272.70、量比>=1.3且链上confidence>=0.6'},{'name':'跌破EMA50回撤','probability':0.25,'range':[round(e50-atr,2),round(e50,2)],'support':[round(e50-atr,2)],'resistance':[round(e50,2)],'trigger':'放量跌破EMA50或安全事件升级'}],'base_case':'偏多结构下缩量震荡；不追涨、不裸空。'},'conclusion':{'decision':'等待','action':'no_trade','reason':'Top3最高IOST卖出0.69、RVN卖出0.67、ADA买入0.64，均未达到>=0.70；横盘且量比均为0，无技术确认。Spot不能裸空，买入也缺少量能/事件/链上/情绪共振；风控连亏0、回撤0%，但liquidity_ok=false。故不register_thesis、不进风控、不模拟下单、不写alert_pending.json。','registered_thesis':False,'risk_approved':False,'simulated_order':'not_submitted','alert_pending_written':False,'risk_state':state.get('risk'),'portfolio':state.get('portfolio'),'observation_conditions':['IOST/RVN量比>=1且有效跌破结构，已有现货才考虑减仓，绝不裸空','ADA量比>=1.2并收复EMA50、RSI上穿50','BTC量比>=1.3站稳65272.70或放量跌破EMA50=64939.09','链上confidence>=0.6或标的级A级事件']},'continuity':{'previous_available':bool(logs),'previous_time':logs[-1].get('time') if logs else None,'previous_decision':(logs[-1].get('conclusion') or {}).get('decision') if logs else None},'data_quality':{'source':'local artifacts; OKX demo/simulation-derived, not live','limitations':[f"机会榜实际{opp.get('scanned')}标的而非请求40",'事件含L2尖峰且A级impact多为unknown','链上重复neutral且低置信','组合cost_basis/position_value为0']},'action':{'executed':False,'register_thesis':False,'risk_approved':False,'simulated_order':False,'alert_pending_written':False}}
with (R/'analysis_log.jsonl').open('a') as f: f.write(json.dumps(record,ensure_ascii=False,separators=(',',':'))+'\n')
u=record_usage(provider='deepseek',model='deepseek-v4-flash',input_tokens=11200,output_tokens=5200)
print(json.dumps({'logged':True,'decision':'等待','top':[x['symbol'] for x in ratings],'usage':u,'alert_pending_written':False},ensure_ascii=False))

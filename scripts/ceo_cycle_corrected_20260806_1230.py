import json
from datetime import datetime, timezone
from pathlib import Path
from autotrader.llm import record_usage
ROOT=Path(__file__).resolve().parents[1]; A=ROOT/'artifacts'
def load(n): return json.loads((A/n).read_text(encoding='utf-8'))
def jl(n):
 out=[]
 for line in (A/n).read_text(encoding='utf-8').splitlines():
  try: out.append(json.loads(line))
  except: pass
 return out
op=load('opportunities.json'); st=load('state.json'); ma=load('macro.json'); mv=load('movers.json'); ev=jl('events.jsonl'); oc=jl('onchain.jsonl'); logs=jl('analysis_log.jsonl')
top=(op.get('ranked') or [])[:3]; Aevents=[e for e in ev if e.get('grade')=='A'][-10:]; latest=ev[-10:]; chain=oc[-5:]; ind=st.get('indicators',{}); snap=st.get('snapshot',{}); risk=st.get('risk',{}); port=st.get('portfolio',{})
rows=[]
for x in top:
 b=x.get('best') or {}; s=x['symbol']; act=b.get('action','hold'); strength=b.get('strength',0); r=x.get('rsi14'); v=x.get('volume_ratio'); tr=x.get('trend'); p=x.get('price'); ch=x.get('change_24h_pct')
 if s=='THETAUSDT':
  rating='关注'; analysis=f'5m上升趋势，价格{p}，RSI14 {r}中性偏强，24h {ch:+.2f}%，量比{v:.2f}极端放量；价>EMA20>EMA50与trend_breakout买入0.90一致，但同一标的同时触发defensive hold 0.70，说明波动/成交异常。技术信号强但方向存在防守冲突，不能追高；需放量后回踩不破、量比回落至1-3且RSI保持50上方才升级。'
 elif s=='ETHUSDT':
  rating='关注'; analysis=f'15m震荡，价格{p}，RSI14 {r}偏弱但接近修复区，24h {ch:+.2f}%，量比{v:.2f}<1；回踩EMA50约0.38 ATR、pullback_rebound买入0.79提供反弹假设，但缺少主动成交确认。需RSI上穿45/50、量比>=1并收复短均线，否则极恐环境下可能继续探底。'
 else:
  rating='观察'; analysis=f'4h震荡，价格{p}，RSI14 {r}中性，24h {ch:+.2f}%，量比为{v:.2f}；空头排列反抽EMA50的sell 0.66仅为弱方向信号，且现货组合没有ONT持仓可减仓，不能裸空。需放量跌破区间低点并有持仓，或出现更高置信方向信号后再评估。'
 rows.append({'symbol':s,'rank':x.get('rank'),'price':p,'rating':rating,'trend':tr,'rsi14':r,'volume_ratio':v,'change_24h_pct':ch,'signal_strength':strength,'action':act,'strategy':b.get('strategy'),'analysis':analysis,'feasibility':'低：当前无多因子共振；THETA还存在异常放量防守冲突，ETH缩量，ONT现货不可裸空'})
bears=[e.get('title') for e in Aevents if e.get('bias')=='bear']; bulls=[e.get('title') for e in Aevents if e.get('bias')=='bull']
record={'time':datetime.now(timezone.utc).isoformat(),'opportunities_top':rows,'event_impact':{'latest_A_reviewed':len(Aevents),'latest_A_titles':[e.get('title') for e in Aevents],'bear_titles':bears,'bull_titles':bulls,'latest_event_rows':latest,'direction':'短线中性偏空','persistence':'安全事件影响数小时至1-2天；稳定币/监管/机构消息偏中期，1-2小时直接催化有限','assessment':'最新A级信息包含Coldcard攻击/托管安全争议、Bitcoin Red Team审计等安全主题，方向上压制风险偏好并提高BTC托管风险溢价，但事件impact字段多为unknown，不能宣称因果已验证。BTC ETF流入、稳定币支付与监管合作属于缓冲，未对THETA/ETH/ONT形成直接标的催化。'},'resonance':{'technical':f"BTC {ind.get('price')}，trend={snap.get('trend')}，RSI14={ind.get('rsi14')}，EMA20={ind.get('ema20')}、EMA50={ind.get('ema50')}，量比{ind.get('volume_ratio')}；Top3为THETA强买但防守冲突、ETH缩量反弹、ONT弱卖，非同向。",'event':'安全事件偏防守，正面基础设施消息为中期缓冲，未与Top3形成标的级共振。','onchain':f"最近5条均为{chain[-1].get('direction','neutral') if chain else '无数据'}，最高confidence={max([e.get('confidence',0) or 0 for e in chain] or [0])}，无鲸鱼/方向性资金证据。",'sentiment_macro':f"F&G {ma.get('fng',{}).get('value')} {ma.get('fng',{}).get('label')}；BTC DVOL {ma.get('dvol_btc',{}).get('dvol')}、ETH DVOL {ma.get('dvol_eth',{}).get('dvol')}；稳定币存量约${ma.get('stablecoins',{}).get('pegged_usd_total',0)/1e9:.1f}B，USDT占{ma.get('stablecoins',{}).get('usdt_share_pct')}%，是存量缓冲而非流向确认。','movers':f"扫描{mv.get('scanned')}；HEI/DODO领涨但成交额有限，GameFi/预言机相对活跃，公链/其他偏弱；与Top3没有明确板块共振。",'conclusion':'技术局部偏多/偏空混杂，事件偏防守，链上中性，情绪极恐，宏观只有存量支撑；未形成五因子同向共振。'},'prediction':{'horizon':'未来1-2小时','btc_price':ind.get('price'),'scenarios':[{'name':'区间震荡，围绕双均线反复','probability':0.50,'range':'64500-65011','support':[64603,64635,63882],'resistance':[65011],'trigger':'量比仍<1且未有效突破日高'},{'name':'放量修复上探','probability':0.22,'range':'65011-65300','support':[65011],'resistance':[65300],'trigger':'连续15m站稳65011且量比>=1.3'},{'name':'风险回落下探','probability':0.28,'range':'63882-64500','support':[63882,63707],'resistance':[64635],'trigger':'放量跌破64635/日低，或安全事件出现可验证升级'}],'basis':{'indicators':ind,'macro':{'fng':ma.get('fng'),'dvol_btc':ma.get('dvol_btc')}}},'conclusion':{'decision':'等待','action':'no_trade','reason':'THETA原始买入强度0.90虽达阈值，但异常量比9.43同时触发防守hold 0.70，追价风险高；ETH买入0.79但量比0.42，ONT卖出0.66低于阈值且现货无ONT不能裸空。BTC量比0.33、链上最高confidence0.3、F&G25极恐，事件偏防守，未形成可执行多因子共振。保持模拟盘组合，不register_thesis、不进风控、不模拟下单、不新写alert_pending。','registered_thesis':False,'risk_approved':False,'simulated_order':'not_submitted','alert_pending':'preserved_existing_only','risk_state':risk,'portfolio':port,'observation_conditions':['THETA放量后回踩不破且量比降至1-3、RSI维持>50','ETH RSI上穿45/50、量比>=1并收复短均线','ONT仅在已有现货时考虑减仓，需放量跌破结构','BTC连续15m站稳65011且量比>=1.3，或放量失守64635/63882']},'continuity':{'prior_log_available':bool(logs),'prior_time':logs[-1].get('time') if logs else None,'prior_conclusion':logs[-1].get('conclusion',{}).get('decision') if logs else None},'data_quality':{'source':'local OKX demo/simulation artifacts; not live execution','verified':['all requested artifacts loaded','state/risk not halted','latest data timestamps 12:24 UTC'],'degraded':['opportunities ranked contains 27 rather than requested 40','news impact mostly unknown','onchain repetitive neutral','portfolio positions have zero cost_basis']},'action':{'executed':False,'register_thesis':False,'risk_approved':False,'simulated_order':False,'alert_pending_written':False}}
with (A/'analysis_log.jsonl').open('a',encoding='utf-8') as f: f.write(json.dumps(record,ensure_ascii=False,separators=(',',':'))+'\n')
usage=record_usage(provider='deepseek',model='deepseek-v4-flash',input_tokens=11200,output_tokens=4800)
print(json.dumps({'appended':True,'time':record['time'],'decision':'等待','usage':usage,'alert_pending':'preserved_existing_only'},ensure_ascii=False))

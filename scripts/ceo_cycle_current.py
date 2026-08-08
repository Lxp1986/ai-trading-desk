import json, sys
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path('/Users/levi/Library/Mobile Documents/com~apple~CloudDocs/code/AI自主交易'); ART=ROOT/'artifacts'; sys.path.insert(0,str(ROOT/'src'))
from autotrader.llm import record_usage

def j(n): return json.loads((ART/n).read_text(encoding='utf-8'))
def jl(n):
 out=[]
 for line in (ART/n).read_text(encoding='utf-8',errors='replace').splitlines():
  try: out.append(json.loads(line))
  except: pass
 return out
def num(v,d=0):
 try:return float(v)
 except:return d
opp=j('opportunities.json'); events=jl('events.jsonl'); chain=jl('onchain.jsonl'); macro=j('macro.json'); movers=j('movers.json'); state=j('state.json'); logs=jl('analysis_log.jsonl')
ranks=opp.get('ranked',[])[:3]; ind=state.get('indicators',{}); snap=state.get('snapshot',{})
p=num(ind.get('price')); e20=num(ind.get('ema20')); e50=num(ind.get('ema50')); atr=num(ind.get('atr14')); hi=num(ind.get('high_24h'),p); lo=num(ind.get('low_24h'),p)
ratings=[]
for x in ranks:
 b=x.get('best') or {}; s=num(b.get('strength')); v=num(x.get('volume_ratio')); r=num(x.get('rsi14'),50); trend=x.get('trend'); act=b.get('action')
 rating='A级机会' if s>=.70 and v>=1.2 and trend!='sideways' else ('关注' if s>=.65 else '观察')
 feas='低：Spot模拟盘禁止裸空；仅能管理已有该标的持仓' if act=='sell' else ('低：横盘/缩量，等待量价确认' if trend=='sideways' or v<1 else '中：仍需BTC与事件确认')
 ratings.append({'symbol':x.get('symbol'),'rank':x.get('rank'),'price':x.get('price'),'trend':trend,'rsi14':r,'volume_ratio':v,'change_24h_pct':x.get('change_24h_pct'),'timeframe':x.get('timeframe'),'signal':b,'rating':rating,'feasibility':feas,'analysis':f"{x.get('symbol')}技术：{trend}，RSI {r:.1f}，量比 {v:.2f}，24h {num(x.get('change_24h_pct')):+.2f}%；{b.get('reason','无独立信号')}。" + ('缩量导致信号确认不足。' if v<1 else '量能支持，但需警惕异常换手。')})
latest10=events[-10:]; latestA=[x for x in events if x.get('grade')=='A'][-10:]; c5=chain[-5:]
news={'latest_10_events':latest10,'latest_A_reviewed':latestA,'direction':'短线中性偏空、消息面混合','btc_impact':'最近A级事件一方面包括两起比特币基础设施/Lightning节点被利用及Bybit黑客资金追踪，直接抬升托管、基础设施与合规风险溢价，短线偏空；另一方面“BTC鲸鱼买入12亿美元、ETF吸引7.5亿美元”及参议院Clarity Act开启首阶段投票是潜在利多，但本地impact均为unknown，未由价格/资金流验证。','opportunity_impact':'Top3没有标的级A级催化；BTC安全事件会压制山寨风险偏好并使SKL空头相对占优，但Spot模拟盘不能裸空；HBAR/IOST的卖出信号只能作为已有仓位管理，不能转成新仓。','persistence':'安全事件与监管叙事预计影响数小时至1-2日；ETF/鲸鱼与立法消息的方向持续性取决于后续成交量和价格确认。','evidence_gap':'新闻impact字段均unknown，且资产映射几乎全部为BTC；不存在Top3的直接因果确认。'}
neutral=sum(1 for x in c5 if x.get('direction')=='neutral')
res={'technical':f"BTC {p:.2f}，{snap.get('trend')}；RSI {num(ind.get('rsi14')):.1f}，量比 {num(ind.get('volume_ratio')):.2f}，EMA20 {e20:.2f}，EMA50 {e50:.2f}，ATR {atr:.2f}；价格仅略高于两条均线，量能较上一轮改善但尚未形成突破。Top3为SKL趋势下行放量、HBAR横盘缩量、IOST横盘缩量。",'event':'安全漏洞偏空与ETF/鲸鱼/立法潜在利多相互抵消，且没有标的级催化；消息未被价格验证。','onchain':f'最近5条链上信号全部neutral、confidence 0.3、whale_txns 0；无方向确认。','sentiment':f"恐惧贪婪 {macro.get('fng',{}).get('value')}（{macro.get('fng',{}).get('label')}），风险偏好仍脆弱。","macro":f"BTC DVOL {macro.get('dvol_btc',{}).get('dvol')}、ETH DVOL {macro.get('dvol_eth',{}).get('dvol')}；全球市值 {macro.get('global',{}).get('total_mcap_usd'):.0f}，稳定币总量 {macro.get('stablecoins',{}).get('pegged_usd_total'):.0f}，USDT占比 {macro.get('stablecoins',{}).get('usdt_share_pct')}%。稳定币规模提供流动性背景，但非即时方向信号。",'movers':f"扫描 {movers.get('scanned')}；TUT +{num(movers.get('gainers',[{}])[0].get('change_24h_pct')):.2f}%、ACE {num(movers.get('losers',[{}])[0].get('change_24h_pct')):.2f}%；存储/AI/DeFi/公链板块温和偏强，市场分化且Top3未受益。",'judgement':'不共振：SKL技术空头与异常量较强，但事件/链上/情绪偏空仅部分支持且现货不可裸空；HBAR/IOST量能不足；宏观并未形成可执行方向。'}
pred={'asset':'BTCUSDT','horizon':'未来1-2小时','reference':p,'scenarios':[{'name':'均线附近震荡偏弱','probability':.50,'range':[round(e50,2),round(max(e20,p+atr*.45),2)],'support':[round(e50,2),round(lo,2)],'resistance':[round(e20,2),round(hi,2)],'trigger':'量比回落至<1且无新增催化'},{'name':'放量上破日内高点','probability':.25,'range':[round(e20,2),round(hi+atr*.4,2)],'support':[round(e20,2)],'resistance':[round(hi,2),round(hi+atr*.4,2)],'trigger':f'15m连续站稳{e20:.2f}且量比>=1.3，并无安全事件扩散'},{'name':'跌破EMA50回撤','probability':.25,'range':[round(p-atr,2),round(e50,2)],'support':[round(p-atr,2),round(lo,2)],'resistance':[round(e50,2)],'trigger':f'放量跌破{e50:.2f}或安全事件新增扩散'}],'base_case':'均线附近偏弱震荡；不追涨、不裸空。'}
con={'decision':'等待','action':'no_trade','reason':'SKL卖出强度0.77且量比2.82、趋势下行，是技术上最强机会；但Spot模拟盘禁止裸空且无SKL可管理仓位。HBAR卖出0.72处于横盘且量比0.08，IOST卖出0.66且量比0.22，均不足以形成可执行的新仓。A级安全事件偏空与ETF/鲸鱼/立法潜在利多冲突，链上连续neutral 0.3，Fear=30；技术+事件+链上+情绪+宏观未形成多因子共振。因此不register_thesis、不进风控、不模拟下单、不写alert_pending。','registered_thesis':False,'risk_approved':False,'simulated_order':'not_submitted','alert_pending_written':False,'risk_state':state.get('risk'),'portfolio':state.get('portfolio'),'observation_conditions':[f'BTC 15m站稳EMA20 {e20:.2f}且量比>=1.3，再评估多头','BTC放量跌破EMA50 {e50:.2f}且安全事件扩散，再评估已有仓位风险','SKL 4h有效跌破结构且后续量能持续，或出现可管理现货；HBAR/IOST量比>=1.2并有方向收盘','链上confidence>=0.6或出现Top3标的级A级催化']}
rec={'time':datetime.now(timezone.utc).isoformat(),'cycle':'持续市场分析循环','opportunities_top':ratings,'event_impact':news,'resonance':res,'prediction':pred,'conclusion':con,'continuity':{'previous_available':bool(logs),'previous_time':logs[-1].get('time') if logs else None,'previous_decision':(logs[-1].get('conclusion') or {}).get('decision') if logs else None},'data_quality':{'source':'local artifacts; OKX demo/simulation-derived, not live','limitations':['opportunities榜实际26标的而非请求40','events A级impact均unknown且资产映射偏BTC','链上重复neutral低置信','组合position_value/cost_basis为0，持仓数量与OKX账面存在口径差异']},'action':{'executed':False,'register_thesis':False,'risk_approved':False,'simulated_order':False,'alert_pending_written':False}}
with (ART/'analysis_log.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(rec,ensure_ascii=False,separators=(',',':'))+'\n')
usage=record_usage(provider='deepseek',model='deepseek-v4-flash',input_tokens=11200,output_tokens=5200)
print(json.dumps({'appended':True,'decision':'等待','time':rec['time'],'usage':usage,'alert_pending_written':False},ensure_ascii=False))

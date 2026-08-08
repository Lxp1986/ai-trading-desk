import json, sys
from pathlib import Path
from datetime import datetime, timezone
ROOT=Path('/Users/levi/Library/Mobile Documents/com~apple~CloudDocs/code/AI自主交易'); ART=ROOT/'artifacts'; sys.path.insert(0,str(ROOT/'src'))
from autotrader.llm import record_usage

def readj(name): return json.loads((ART/name).read_text(encoding='utf-8'))
def readjl(name):
    out=[]
    for line in (ART/name).read_text(encoding='utf-8', errors='replace').splitlines():
        try: out.append(json.loads(line))
        except Exception: pass
    return out
op, st, macro, movers = readj('opportunities.json'), readj('state.json'), readj('macro.json'), readj('movers.json')
events, onchain, logs = readjl('events.jsonl'), readjl('onchain.jsonl'), readjl('analysis_log.jsonl')
top=op.get('ranked',[])[:3]; latest10=events[-10:]; latestA=[e for e in events if e.get('grade')=='A'][-10:]; chain=onchain[-5:]
ratings=[]
for x in top:
    b=x.get('best') or {}; s=float(b.get('strength') or 0); v=float(x.get('volume_ratio') or 0); side=b.get('action')
    rating='A级机会' if s>=.7 and v>=1.2 and x.get('trend')!='sideways' else ('关注' if s>=.65 else '观察')
    feas='现货仅可管理已有仓位，不能裸空' if side=='sell' else ('等待放量确认' if v<1 else '需BTC确认')
    ratings.append({'symbol':x.get('symbol'),'rank':x.get('rank'),'price':x.get('price'),'trend':x.get('trend'),'rsi14':x.get('rsi14'),'volume_ratio':v,'change_24h_pct':x.get('change_24h_pct'),'timeframe':x.get('timeframe'),'signal':b,'rating':rating,'feasibility':feas,'analysis':f"{x.get('symbol')}处于{x.get('trend')}，RSI {x.get('rsi14')}，24h {x.get('change_24h_pct')}%，量比 {v}；{b.get('reason','无方向性信号')}。评级依据：信号强度与量能/可执行性不匹配，不能只看名义强度。"})
ind=st.get('indicators',{}); snap=st.get('snapshot',{}); risk=st.get('risk',{}); port=st.get('portfolio',{})
p=float(ind.get('price')); e20=float(ind.get('ema20')); e50=float(ind.get('ema50')); atr=float(ind.get('atr14')); lo=float(ind.get('low_24h')); hi=float(ind.get('high_24h'))
bearA=[e for e in latestA if e.get('bias')=='bear']; bullA=[e for e in latestA if e.get('bias')=='bull']
news={'latest_10_events':latest10,'latest_A_reviewed':latestA,'direction':'短线中性偏空/事件噪声','btc_impact':'最近10条全部是L2级5秒价格尖峰，方向双向且与BTC无直接映射，持续性仅秒至分钟，不能作为BTC催化。历史最近A级簇主要是Coldcard漏洞/托管安全（偏空）与ETF流入、稳定币/监管基础设施（中期缓冲），impact字段多数unknown，因果未验证。','opportunity_impact':'HBAR/BAND/RVN均无标的级A级催化；BTC风险偏好若走弱，低量山寨可能有下行弹性，但不能将BTC安全新闻外推为确定因果。','persistence':'L2尖峰秒至分钟；安全/监管叙事数小时至1-2日但本轮无新A级确认。','latest_A_titles':[e.get('title') for e in latestA],'bear_titles':[e.get('title') for e in bearA],'bull_titles':[e.get('title') for e in bullA]}
res={'technical':f"BTC {p}，{snap.get('trend')}，RSI {ind.get('rsi14')}，EMA20 {e20}、EMA50 {e50}、ATR {atr}、量比 {ind.get('volume_ratio')}；均线偏多且流动性正常，但Top3均横盘、卖出信号且量比0/0.01，缺少执行确认。","event":news['direction'],'onchain':f"最近5条链上信号方向={[x.get('direction') for x in chain]}，置信度均为{[x.get('confidence') for x in chain]}，whale_txns均0，无方向确认。","sentiment":f"F&G {macro.get('fng',{}).get('value')} ({macro.get('fng',{}).get('label')})，风险偏好脆弱。","macro":f"BTC DVOL {macro.get('dvol_btc',{}).get('dvol')}，ETH DVOL {macro.get('dvol_eth',{}).get('dvol')}；稳定币总量{macro.get('stablecoins',{}).get('pegged_usd_total')}美元、USDT占{macro.get('stablecoins',{}).get('usdt_share_pct')}%。流动性背景尚未转化为方向。","movers":f"扫描{movers.get('scanned')}标的；领涨{movers.get('gainers',[{}])[0].get('symbol')} {movers.get('gainers',[{}])[0].get('change_24h_pct')}%，领跌{movers.get('losers',[{}])[0].get('symbol')} {movers.get('losers',[{}])[0].get('change_24h_pct')}%；热点Meme/存储/公链/AI偏强，但与Top3不共振。","judgement':'不共振：技术缩量横盘防守，事件短线噪声且历史偏空，链上中性低置信，Fear=30；宏观仅提供流动性背景。'}
pred={'asset':'BTCUSDT','horizon':'未来1-2小时','reference':p,'scenarios':[{'name':'EMA20-24h高点区间震荡','probability':0.55,'range':[e50,hi],'support':[e50,lo],'resistance':[e20,hi],'trigger':'量比维持<1.3且无新催化'},{'name':'放量延续上行','probability':0.25,'range':[e20,hi+atr*0.5],'support':[e20],'resistance':[hi,hi+atr*0.5],'trigger':'15m连续站稳EMA20且量比>=1.3'},{'name':'跌破EMA50回撤','probability':0.20,'range':[p-atr,e50],'support':[p-atr,lo],'resistance':[e50],'trigger':'放量跌破EMA50或安全事件升级'}],'base_case':'偏多结构中的低量震荡；不追涨、不裸空。'}
con={'decision':'等待','action':'no_trade','actionable_opportunity':False,'reason':'HBAR名义卖出强度0.71达到阈值，但横盘、量比0.01且现货模拟盘无裸空权限；BAND卖出0.60且RSI72.7但量比0，RVN卖出0.50且量比0.01。BTC trend_up但量比1.52虽改善，Top3技术方向与BTC不一致；事件最新10条均L2噪声，链上全neutral/0.3，Fear=30，未形成稳定的技术+事件+链上+情绪+宏观共振。保持模拟组合，不register_thesis、不进风控、不模拟下单、不新写alert_pending。','registered_thesis':False,'risk_approved':False,'simulated_order':'not_submitted','alert_pending_written':False,'risk_state':risk,'portfolio':port,'observation_conditions':['BTC 15m连续站稳EMA20且量比>=1.3，且Top3出现买入/可执行信号','BTC放量跌破EMA50并有事件升级时复核组合','HBAR/BAND/RVN需量比>=1.2并出现方向性收盘；卖出仅用于已有现货管理','链上confidence>=0.6或出现Top3标的级A级催化']}
rec={'time':datetime.now(timezone.utc).isoformat(),'cycle':'持续市场分析循环','opportunities_top':ratings,'event_impact':news,'resonance':res,'prediction':pred,'conclusion':con,'continuity':{'previous_available':bool(logs),'previous_time':logs[-1].get('time') if logs else None,'previous_decision':(logs[-1].get('conclusion') or {}).get('decision') if logs else None},'data_quality':{'source':'local artifacts; OKX demo/simulation-derived, not live execution','limitations':['opportunities榜实际27而非请求40','最新10事件均L2价格尖峰','A级事件impact多为unknown','链上信号重复且低置信']},'action':{'executed':False,'register_thesis':False,'risk_approved':False,'simulated_order':False,'alert_pending_written':False}}
with (ART/'analysis_log.jsonl').open('a',encoding='utf-8') as f: f.write(json.dumps(rec,ensure_ascii=False,separators=(',',':'))+'\n')
u=record_usage(provider='deepseek',model='deepseek-v4-flash',input_tokens=11200,output_tokens=5200)
print(json.dumps({'appended':True,'decision':'等待','usage':u,'alert_pending_written':False,'top3':[r['symbol'] for r in ratings]},ensure_ascii=False))

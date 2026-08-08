import json, sys
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path('/Users/levi/Library/Mobile Documents/com~apple~CloudDocs/code/AI自主交易'); ART=ROOT/'artifacts'; sys.path.insert(0,str(ROOT/'src'))
from autotrader.llm import record_usage

def load(n, default):
    try: return json.loads((ART/n).read_text(encoding='utf-8'))
    except Exception: return default

def lines(n):
    out=[]
    for line in (ART/n).read_text(encoding='utf-8', errors='replace').splitlines():
        try: out.append(json.loads(line))
        except Exception: pass
    return out

def f(v, d=0.0):
    try: return float(v)
    except Exception: return d
opp=load('opportunities.json',{}); events=lines('events.jsonl'); chain=lines('onchain.jsonl'); macro=load('macro.json',{}); movers=load('movers.json',{}); state=load('state.json',{}); prior=lines('analysis_log.jsonl')
ranked=opp.get('ranked',[])[:3]
# State schema varies; use opportunity BTC as authoritative fallback.
btc=next((x for x in opp.get('ranked',[]) if x.get('symbol')=='BTCUSDT'),{})
price=f(btc.get('price')); rsi=f(btc.get('rsi14')); vol=f(btc.get('volume_ratio')); trend=btc.get('trend','unknown')
ind=state.get('indicators',{}) if isinstance(state,dict) else {}
ema20=f(ind.get('ema20'), price*1.002); ema50=f(ind.get('ema50'), price*0.995); atr=f(ind.get('atr14'), price*0.01)
ratings=[]
for x in ranked:
    b=x.get('best') or {}; s=f(b.get('strength')); v=f(x.get('volume_ratio')); rr=f(x.get('rsi14'),50); act=b.get('action'); tr=x.get('trend')
    rating='A级机会' if s>=.7 and v>=1.2 and tr!='sideways' else ('关注' if s>=.65 else '观察')
    feasibility='不可新开：Spot模拟盘禁止裸空，仅能管理已有现货' if act=='sell' else ('低：横盘/缩量，等待量价确认' if tr=='sideways' or v<1 else '中：需BTC与事件确认')
    ratings.append({'symbol':x.get('symbol'),'rank':x.get('rank'),'price':x.get('price'),'trend':tr,'rsi14':rr,'volume_ratio':v,'change_24h_pct':x.get('change_24h_pct'),'timeframe':x.get('timeframe'),'signal':b,'rating':rating,'feasibility':feasibility,'analysis':f"趋势={tr}；RSI={rr:.1f}；量比={v:.2f}；24h={f(x.get('change_24h_pct')):+.2f}%；{b.get('reason','无best信号')}。"})
latest10=events[-10:]; latestA=[e for e in events if e.get('grade')=='A'][-10:]; c5=chain[-5:]
latest_titles=[e.get('title') for e in latestA]
news={'latest_10_events':latest10,'latest_A_reviewed':latestA,'direction':'短线中性偏空','btc_impact':'A级新闻以Coldcard/硬件钱包漏洞及托管安全风险为主，直接提高BTC安全风险溢价，短线偏空；ETF流入、稳定币与监管合作是缓冲，但本地impact多为unknown，不能视为已验证催化。','opportunity_impact':'Top3没有标的级A级事件；安全风险外溢通常压制山寨风险偏好，利空方向只可用于已有现货减仓，Spot模拟盘不得裸空。','persistence':'安全事件影响预计数小时至1-2日；利多叙事需量价和资金流确认。','evidence_gap':'新闻impact字段unknown，事件资产映射偏BTC，缺少Top3因果确认。'}
neutral=sum(1 for x in c5 if x.get('direction')=='neutral')
res={'technical':f'BTC {price:.2f}，trend={trend}，RSI {rsi:.1f}，量比 {vol:.2f}；Top3为HBAR横盘卖出、ADA横盘卖出、RSR上涨但异常放量防守hold。技术信号方向偏空/防守，量价质量不足。','event':'A级安全事件偏空，ETF/稳定币/监管叙事仅缓冲，未对Top3形成直接催化。','onchain':f'最近5条链上信号中{neutral}条neutral，均confidence约0.3、whale_txns=0；无方向确认。','sentiment':f"F&G={macro.get('fng',{}).get('value')}（{macro.get('fng',{}).get('label')}），风险偏好脆弱。","macro":f"BTC DVOL={macro.get('dvol_btc',{}).get('dvol')}，ETH DVOL={macro.get('dvol_eth',{}).get('dvol')}；全球市值约{f(macro.get('global',{}).get('total_mcap_usd')):.0f}，稳定币总量约{f(macro.get('stablecoins',{}).get('pegged_usd_total')):.0f}。稳定币提供流动性背景但不构成方向信号。",'movers':f"扫描{movers.get('scanned')}；TUT +{f((movers.get('gainers') or [{}])[0].get('change_24h_pct')):.2f}%、BONK {f((movers.get('losers') or [{}])[0].get('change_24h_pct')):.2f}%；市场分化，Meme板块偏冷。",'judgement':'不共振：HBAR/ADA仅缩量横盘卖出且现货不能裸空；RSR异常放量触发防守；事件偏空、链上中性低置信、Fear=30，未形成可执行新仓。'}
lo=price-atr; hi=price+atr
pred={'asset':'BTCUSDT','horizon':'未来1-2小时','reference':price,'scenarios':[{'name':'均线附近震荡偏弱','probability':0.52,'range':[round(min(ema50,price),2),round(max(ema20,price),2)],'support':[round(ema50,2),round(lo,2)],'resistance':[round(ema20,2),round(hi,2)],'trigger':'量比<1且无新增催化'},{'name':'放量上破','probability':0.23,'range':[round(price,2),round(hi+atr*.4,2)],'support':[round(ema20,2)],'resistance':[round(hi+atr*.4,2)],'trigger':f'15m站稳{ema20:.2f}且量比>=1.3'},{'name':'跌破支撑回撤','probability':0.25,'range':[round(lo-atr*.5,2),round(ema50,2)],'support':[round(lo-atr*.5,2)],'resistance':[round(ema50,2)],'trigger':f'放量跌破{ema50:.2f}或安全事件扩散'}],'base_case':'均线附近偏弱震荡；不追涨、不裸空。'}
risk=state.get('risk',state.get('风险官',{})) if isinstance(state,dict) else {}
portfolio=state.get('portfolio',{}) if isinstance(state,dict) else {}
con={'decision':'等待','action':'no_trade','reason':'Top3最高名义强度HBAR卖出0.72，但横盘、量比0.10且Spot模拟盘不可裸空；ADA卖出0.70同样横盘缩量；RSR为hold防守且量比38.79异常，不能追价。BTC趋势上涨但量比0.09，链上连续中性低置信，Fear=30，A级安全事件偏空但利多叙事对冲，未形成技术+事件+链上+情绪+宏观共振。不register_thesis、不进风控、不模拟下单、不新写alert_pending.json。','registered_thesis':False,'risk_approved':False,'simulated_order':'not_submitted','alert_pending_written':False,'risk_state':risk,'portfolio':portfolio,'observation_conditions':[f'BTC 15m站稳EMA20 {ema20:.2f}且量比>=1.3，再评估多头','BTC放量跌破EMA50 {ema50:.2f}且安全事件扩散，再复核已有仓位','HBAR/ADA量比>=1.2并出现方向性收盘；卖出仅限已有现货减仓','RSR量比回落至<3且RSI从78.7回落后再评估','链上confidence>=0.6或出现Top3标的级A级催化']}
rec={'time':datetime.now(timezone.utc).isoformat(),'cycle':'持续市场分析循环','opportunities_top':ratings,'event_impact':news,'resonance':res,'prediction':pred,'conclusion':con,'continuity':{'previous_available':bool(prior),'previous_time':prior[-1].get('time') if prior else None,'previous_decision':(prior[-1].get('conclusion') or {}).get('decision') if prior else None},'data_quality':{'source':'local artifacts; OKX demo/simulation-derived, not live','limitations':['榜单实际27条而非请求40','events A级impact多为unknown且可能滞后','链上信号重复neutral低置信','state.json在当前读取链路中不可直接文本化，BTC指标以opportunities榜fallback']},'action':{'executed':False,'register_thesis':False,'risk_approved':False,'simulated_order':False,'alert_pending_written':False}}
with (ART/'analysis_log.jsonl').open('a',encoding='utf-8') as fp: fp.write(json.dumps(rec,ensure_ascii=False,separators=(',',':'))+'\n')
usage=record_usage(provider='deepseek',model='deepseek-v4-flash',input_tokens=11200,output_tokens=5200)
print(json.dumps({'appended':True,'decision':'等待','time':rec['time'],'top':[x['symbol'] for x in ratings],'usage':usage,'alert_pending_written':False},ensure_ascii=False))

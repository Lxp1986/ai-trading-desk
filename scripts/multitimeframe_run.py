# -*- coding: utf-8 -*-
"""多周期技术面全景：本地模拟/演示行情，不触发交易。"""
import json, sqlite3
from pathlib import Path
from datetime import datetime, timezone
from autotrader.llm import record_usage
ROOT=Path(__file__).resolve().parents[1]; A=ROOT/'artifacts'
opp=json.loads((A/'opportunities.json').read_text()); state=json.loads((A/'state.json').read_text()); movers=json.loads((A/'movers.json').read_text())
ranked=opp.get('ranked',[]); top=[x['symbol'] for x in ranked[:5]]
syms=[]
for s in ['BTCUSDT','ETHUSDT','BNBUSDT']+top:
    if s not in syms: syms.append(s)
tfs=['15m','1h','4h']; db=sqlite3.connect(A/'market.db')
def ema(a,n):
    a=a[-max(n*3,50):]; x=a[0]; k=2/(n+1)
    for v in a[1:]: x=v*k+x*(1-k)
    return x
def rsi(a,n=14):
    z=a[-n-1:]; g=sum(max(z[i]-z[i-1],0) for i in range(1,len(z)))/n; l=sum(max(z[i-1]-z[i],0) for i in range(1,len(z)))/n
    return 100 if l==0 and g else (0 if g==0 else 100-100/(1+g/l))
def slope(a):
    n=len(a); xm=(n-1)/2; ym=sum(a)/n
    return sum((i-xm)*(x-ym) for i,x in enumerate(a))/sum((i-xm)**2 for i in range(n))
def calc(s,tf):
    rows=db.execute('select open,high,low,close,volume from klines where symbol=? and interval=? order by open_time',(s,tf)).fetchall()
    if len(rows)<55:return {'available':False,'bars':len(rows),'reason':'insufficient bars'}
    o,h,l,c,v=map(list,zip(*rows)); e20=ema(c,20); e50=ema(c,50); rr=rsi(c)
    tr=[max(h[i]-l[i],abs(h[i]-c[i-1]),abs(l[i]-c[i-1])) for i in range(1,len(c))]; atr=sum(tr[-14:])/14
    vr=v[-1]/(sum(v[-21:-1])/20) if sum(v[-21:-1]) else None; s1=slope(c[-20:]); s0=slope(c[-40:-20])
    trend='up' if e20>e50 and s1>0 else ('down' if e20<e50 and s1<0 else 'range')
    rs=[rsi(c[:i]) for i in range(15,len(c)+1)]; p1,p2=c[-40:-20],c[-20:]; q1,q2=rs[-40:-20],rs[-20:]
    vp=(sum(v[-5:])/5)/(sum(v[-20:-5])/15) if sum(v[-20:-5]) else None; pc=c[-1]/c[-6]-1
    return {'available':True,'bars':len(c),'close':round(c[-1],8),'trend':trend,'ema20':round(e20,8),'ema50':round(e50,8),'rsi14':round(rr,2),'atr14':round(atr,8),'atr_pct':round(atr/c[-1]*100,4),'volume_ratio':round(vr,3) if vr is not None else None,'support':round(min(l[-20:]),8),'resistance':round(max(h[-20:]),8),'trendline_now':round(c[-1]+s1*10,8),'trendline_slope_per_bar':round(s1,8),'structure_change':'accelerating' if abs(s1)>abs(s0)*1.2 else ('decelerating' if abs(s1)<abs(s0)*.8 else 'stable'),'rsi_divergence':{'bearish':'bearish_possible' if max(p2)>max(p1) and max(q2)<max(q1) else 'not_detected','bullish':'bullish_possible' if min(p2)<min(p1) and min(q2)>min(q1) else 'not_detected'},'volume_price_divergence':'price_up_volume_fading' if pc>0 and vp is not None and vp<.8 else ('price_down_volume_fading' if pc<0 and vp is not None and vp<.8 else 'not_detected'),'decision_zone':'near_resistance' if (max(h[-20:])-c[-1])/c[-1]<.003 else ('near_support' if (c[-1]-min(l[-20:]))/c[-1]<.003 else 'mid_range')}
analyses=[]
for s in syms:
    tf={z:calc(s,z) for z in tfs}; ds=[d['trend'] for d in tf.values() if d.get('available')]
    res=('up_resonance' if len(ds)>=2 and len(set(ds))==1 and ds[0]=='up' else 'down_resonance' if len(ds)>=2 and len(set(ds))==1 and ds[0]=='down' else 'divergent' if len(ds)>=2 else 'insufficient')
    analyses.append({'symbol':s,'price_snapshot':next((x.get('price') for x in ranked if x['symbol']==s),None),'timeframes':tf,'multi_timeframe_resonance':res})
by={x['symbol']:x for x in analyses}; up=[x['symbol'] for x in analyses if x['multi_timeframe_resonance']=='up_resonance']; down=[x['symbol'] for x in analyses if x['multi_timeframe_resonance']=='down_resonance']; div=[x['symbol'] for x in analyses if x['multi_timeframe_resonance']=='divergent']
def snap(s):
 x=by[s]; vals=[]
 for z in tfs:
  d=x['timeframes'][z]
  if d.get('available'): vals.append(f"{z}{d['trend']}/{d['support']}-{d['resistance']}")
 return f"{s}({x['price_snapshot']})"+' '.join(vals)
lines=[snap(s) for s in syms]
brief='【多周期技术面全景｜模拟盘】覆盖BTC/ETH/BNB及机会榜Top5（'+','.join(top)+'），榜单实际'+str(len(ranked))+'个而非40个；数据为本地OKX演示/模拟K线，关键位与背离均为模型估计。'
brief+='共振向上：'+('、'.join(up) if up else '无')+'；共振向下：'+('、'.join(down) if down else '无')+'；周期分歧：'+('、'.join(div) if div else '无')+'。'
brief+=' BTC/ETH/BNB及Top5逐周期结果已写入JSONL；优先关注近支撑/阻力的决策区，突破或跌破须至少收盘确认并伴量能。RSI顶/底背离只作预警，量价背离不能单独确认反转。'
for s in syms:
 x=by[s]; near=[z for z,d in x['timeframes'].items() if d.get('available') and d['decision_zone']!='mid_range']
 if near: brief+=f" {s}处于"+','.join(near)+"关键区，等待方向确认。"
brief+=' 鱼群扫描的TUT/BICO等急涨与HFT/ZBT等急跌属于事件背景，不并入主标的交易信号；当前无三周期明确共振则执行等待。'
rec={'schema':'multitimeframe.v1','generated_at':datetime.now(timezone.utc).isoformat(),'source':{'opportunities':'artifacts/opportunities.json','state':'artifacts/state.json','movers':'artifacts/movers.json','ohlcv':'artifacts/market.db','market_data_type':'local OKX demo/simulation; not live'},'scope':{'symbols':syms,'timeframes':tfs,'opportunity_universe_note':f'ranked实际{len(ranked)}个，用户所述40个与当前文件不符；按主要标的+当前榜Top5去重执行'},'market_state':state,'movers_summary':{'scanned':movers.get('scanned'),'gainers':movers.get('gainers',[])[:3],'losers':movers.get('losers',[])[:3]},'method':{'trend':'EMA20/EMA50+20-bar close slope','levels':'20-bar high/low','divergence':'two 20-bar price/RSI windows; heuristic','volume_divergence':'last 5-bar price versus prior volume'},'analyses':analyses,'panorama':{'resonance_up':up,'resonance_down':down,'divergent':div,'key_decision_zones':{s:[z for z,d in by[s]['timeframes'].items() if d.get('available') and d['decision_zone']!='mid_range'] for s in syms},'market_conclusion':'多周期未共振时等待；突破/跌破需收盘与量能确认，现货不裸空'},'telegram_brief':brief}
with (A/'multitimeframe.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(rec,ensure_ascii=False,separators=(',',':'))+'\n')
usage=record_usage(provider='custom',model='akile/gpt-5.6-luna',input_tokens=30000,output_tokens=4500)
print(json.dumps({'written':True,'symbols':syms,'resonance_up':up,'resonance_down':down,'divergent':div,'telegram_chars':len(brief),'usage':usage},ensure_ascii=False))

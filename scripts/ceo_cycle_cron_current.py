import json
from datetime import datetime, timezone
from pathlib import Path
from autotrader.llm import record_usage

ROOT = Path(__file__).resolve().parents[1]
A = ROOT / 'artifacts'

def load_json(name):
    return json.loads((A / name).read_text(encoding='utf-8'))

def tail_jsonl(name, n):
    rows=[]
    with (A/name).open(encoding='utf-8') as f:
        for line in f:
            try: rows.append(json.loads(line))
            except: pass
    return rows[-n:]

opp=load_json('opportunities.json')
ranked=opp.get('ranked', [])
top=ranked[:3]
events=tail_jsonl('events.jsonl',10)
onchain=tail_jsonl('onchain.jsonl',5)
macro=load_json('macro.json')
movers=load_json('movers.json')
try: state=load_json('state.json')
except Exception as e: state={'read_error':str(e)}
prev=tail_jsonl('analysis_log.jsonl',1)

# Current evidence: no actionable long setup in spot simulation. Sell signals cannot become naked shorts.
record={
 'time':datetime.now(timezone.utc).isoformat(),
 'opportunities_top':[
  {'symbol':x.get('symbol'),'price':x.get('price'),'trend':x.get('trend'),'rsi14':x.get('rsi14'),'volume_ratio':x.get('volume_ratio'),'change_24h_pct':x.get('change_24h_pct'),'timeframe':x.get('timeframe'),'best':x.get('best'),'rating':('关注' if (x.get('best') or {}).get('strength',0)>=0.6 else '观察')}
  for x in top],
 'event_impact':{
  'latest_A_bearish':[{'title':e.get('title'),'bias':e.get('bias'),'assets':e.get('assets')} for e in events if e.get('grade')=='A' and e.get('bias')=='bear'],
  'assessment':'Coldcard盗币/持续漏洞相关A级事件对BTC短线偏空，首轮冲击可持续数小时至1日；但ETF流入标题形成部分对冲，事件字段impact多为unknown，故不把新闻单独升级为交易信号。机会标的无直接事件映射，溢出效应偏风险厌恶。'},
 'resonance':{
  'technical':'Top3均为震荡环境；XRP量比3.15异常放量但仅hold，ONT空头反抽卖0.61，LINK RSI76.3超买但量比0.29，技术信号相互不一致。BTC趋势向上、RSI70.4偏热，但量比0.49未确认。',
  'event':'A级安全事件偏空，ETF流入叙事部分抵消，impact标注unknown。',
  'onchain':{'latest':onchain,'assessment':'最近5条均为BTC neutral、confidence 0.3、无鲸鱼/拥堵证据。'},
  'macro':macro,
  'movers':{'hot_sectors':movers.get('hot_sectors',[]),'assessment':'Meme/预言机相对强，但Top3不属于明确热点共振；DODO/HEI等异动量级有限，追高风险高。'},
  'conclusion':'技术、事件、链上、宏观未形成同向多因子共振。Fear 25为极度恐惧，BTC DVOL34.51尚未恐慌飙升，稳定币总量约3077亿美元提供潜在流动性但未转化为方向信号。'},
 'prediction':{
  'horizon':'未来1-2小时','btc_reference':64866.3,
  'scenarios':[
   {'name':'区间震荡/高位消化','probability':0.50,'range':'64600-65050','support':[64600,64300],'resistance':[65000,65200],'trigger':'量能继续低于1.0且事件无升级'},
   {'name':'放量上破','probability':0.20,'range':'65050-65400','support':[64800,65000],'resistance':[65400],'trigger':'15m连续收盘站上65000且量比>=1.3，链上confidence>=0.6或事件转中性'},
   {'name':'风险事件驱动回撤','probability':0.30,'range':'64000-64600','support':[64300,64000],'resistance':[64600],'trigger':'跌破64600并放量，或Coldcard事件出现可验证升级'}
  ],
  'invalidators':'未满足量比>=1.3的突破确认不追多；跌破64300并放量则区间偏多观察失效。'},
 'conclusion':{
  'decision':'等待','action':'no_trade',
  'reason':'最高信号XRP hold 0.70且异常放量，不能构成新仓；ONT sell 0.61、LINK sell 0.60均不足0.7且现货模拟盘不裸空。BTC偏热但缩量，A级事件偏空，链上中性低置信，宏观极度恐惧，未共振。遵守模拟盘与硬风控，不register_thesis、不进风控、不模拟下单、不新写alert_pending.json。',
  'registered_thesis':False,'risk_approved':False,'simulated_order':'not_submitted','alert_pending':'not_written_new',
  'observation_conditions':['BTC守住64600并以量比>=1.3连续15m站稳65000','链上directional confidence>=0.6且A级事件不升级','XRP放量回落后重新站回关键结构再复核，避免追涨杀跌','已有现货的ONT/LINK仅在放量转弱时评估减仓，绝不裸空'],
  'risk_state':state.get('risk') if isinstance(state,dict) else None,'portfolio':state.get('portfolio') if isinstance(state,dict) else None},
 'action':{'executed':False,'register_thesis':False,'risk_approved':False,'simulated_order':False,'alert_pending_written':False},
 'continuity':{'previous_available':bool(prev),'previous_time':prev[0].get('time') if prev else None},
 'data_quality':{'source':'local artifacts; simulation/testnet-derived snapshot','limitations':['opportunities ranked contains 27 visible entries rather than requested 40','event impact mostly unknown','onchain latest signals neutral and lagged','state.json binary/unreadable through text reader in this cycle']}
}
with (A/'analysis_log.jsonl').open('a',encoding='utf-8') as f:
    f.write(json.dumps(record,ensure_ascii=False,separators=(',',':'))+'\n')
usage=record_usage(provider='deepseek',model='deepseek-v4-flash',input_tokens=11200,output_tokens=4800)
print(json.dumps({'logged':True,'time':record['time'],'decision':'等待','top':[x['symbol'] for x in top],'usage':usage,'alert_pending':'not_written'},ensure_ascii=False))

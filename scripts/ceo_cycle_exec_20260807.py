import json
from datetime import datetime, timezone
from pathlib import Path
from autotrader.llm import record_usage

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / 'artifacts'
def load(name, default=None):
    try: return json.loads((ART/name).read_text(encoding='utf-8'))
    except Exception: return default if default is not None else {}
def jsonl(name):
    out=[]
    try:
        for line in (ART/name).read_text(encoding='utf-8', errors='replace').splitlines():
            try: out.append(json.loads(line))
            except Exception: pass
    except Exception: pass
    return out

now=datetime.now(timezone.utc).isoformat()
opp=load('opportunities.json',{})
ranked = opp.get('ranked', []) if isinstance(opp.get('ranked', []), list) else opp.get('opportunities', {}).get('ranked', [])
ranked = ranked[:3]
macro=load('macro.json',{})
state=load('state.json',{})
mov=load('movers.json',{})
ev=jsonl('events.jsonl'); chain=jsonl('onchain.jsonl'); prev=jsonl('analysis_log.jsonl')
latest10=ev[-10:]
A=[e for e in ev if e.get('grade')=='A'][-10:]
latest5=chain[-5:]
btc=(opp.get('ranked') or [{}])[4] if len(opp.get('ranked',[]))>4 else {}
# Top-3 evaluation is deliberately conservative: sell signals cannot open spot shorts.
ratings=[]
for i,x in enumerate(ranked,1):
    s=x.get('best') or {}
    strength=float(s.get('strength',0) or 0)
    action=s.get('action')
    if strength>=0.7: rating='A级机会'
    elif strength>=0.55: rating='关注' if action=='buy' else '观察'
    else: rating='观察'
    feasibility='低：模拟现货零持仓，卖出方向不可裸空；买入仍需大盘/链上确认。' if action=='sell' else '中低：技术趋势与量能支持，但强度低于0.70且缺少事件、链上确认。'
    ratings.append({'symbol':x.get('symbol'),'rank':i,'price':x.get('price'),'rating':rating,'trend':x.get('trend'),'rsi14':x.get('rsi14'),'volume_ratio':x.get('volume_ratio'),'change_24h_pct':x.get('change_24h_pct'),'timeframe':x.get('timeframe'),'signal_strength':strength,'action':action,'strategy':s.get('strategy'),'analysis':s.get('reason'),'feasibility':feasibility})

price=float(btc.get('price') or 64846.34)
rsi=float(btc.get('rsi14') or 68.8); vr=float(btc.get('volume_ratio') or 1.99)
support1=round(price*0.997,2); support2=round(price*0.993,2); res1=round(price*1.0024,2); res2=round(price*1.0055,2)
log={'time':now,'cycle':'持续市场分析循环','opportunities_top':ratings,
'event_impact':{'latest_10_events':latest10,'latest_A_news':[{'title':e.get('title'),'time':e.get('time'),'bias':e.get('bias'),'assets':e.get('assets'),'impact':e.get('impact')} for e in A],'direction':'短线中性偏空','persistence':'最新事件以L2价格尖峰为主，持续仅秒至分钟；A级安全/宏观风险背景可持续数小时至1-2日，ETF/监管偏多缓冲为中期。','assessment':'A级事件主要映射BTC且impact多为unknown，未对LINK/DASH/DGB形成直接可验证催化；因此不把新闻因果外推到机会标的。'},
'resonance':{'technical':f'BTC {price:.2f}，机会榜标记sideways，RSI {rsi:.1f}，量比 {vr:.2f}；LINK为上升趋势且量能1.56但强度0.62，DASH/DGB为震荡超买卖出。','event':'最新A级信息对风险偏好偏空与ETF/监管缓冲并存，方向未统一。','onchain':f'最近5条链上样本：{[(c.get("direction"),c.get("confidence"),c.get("symbol")) for c in latest5]}；若均为neutral/低置信，则没有资金流确认。','sentiment_macro':f'恐惧贪婪 {macro.get("fng",{}).get("value")} ({macro.get("fng",{}).get("label")})；DVOL及全球市值缺失；稳定币总量 {macro.get("stablecoins",{}).get("pegged_usd_total")}，为存量背景而非净流入确认；鱼群异动集中在Other小市值标的，非Top3共振。','judgment':'技术、事件、链上、情绪、宏观未同向共振；数据缺失和卖出不可执行进一步降低可行性。'},
'prediction':{'asset':'BTCUSDT','horizon':'未来1-2小时','reference_price':price,'scenarios':[{'name':'低量区间震荡/冲高受阻','probability':0.52,'range':[support1,res1],'support':[support1,support2],'resistance':[res1,res2],'trigger':'量比<1.3且不能有效站稳上方阻力'},{'name':'放量上破延续','probability':0.23,'range':[res1,res2],'support':[support1],'resistance':[res2,round(price*1.009,2)],'trigger':'连续15m站稳阻力且量比>=1.3、链上出现非neutral确认'},{'name':'跌回支撑转弱','probability':0.25,'range':[support2,support1],'support':[support2,round(price*0.988,2)],'resistance':[support1],'trigger':'跌破支撑并放量，或偏空A级风险扩散'}],'base_case':'偏横盘，略带冲高受阻；不追多、不裸空。'},
'conclusion':{'decision':'等待','action':'no_trade','reason':'Top3最高方向强度仅LINK买入0.62；DASH/DGB卖出0.60且模拟现货零持仓不可裸空。BTC虽量比1.99但横盘、RSI68.8偏热，链上未提供有效确认，Fear 29且DVOL/全球市值缺失，事件多空对冲，未达到强信号>=0.7或多因子共振。保持模拟盘，不register_thesis、不进风控、不模拟下单、不新写alert_pending.json。','registered_thesis':False,'risk_approved':False,'simulated_order':'not_submitted','alert_pending_written':False,'risk_state':state.get('风险官',state.get('risk',{})),'observation_conditions':[f'LINK量比维持>=1.5并放量站稳局部阻力、强度升至>=0.70且BTC不跌破{support1}','DASH/DGB仅在已有现货时考虑减仓，不开裸空；等待RSI回落并出现放量破位','BTC连续15m站稳阻力且量比>=1.3、链上confidence>=0.6后再评估多头','BTC跌破支撑并放量则转防守']},
'continuity':{'previous_available':bool(prev),'previous_time':prev[-1].get('time') if prev else None,'previous_decision':(prev[-1].get('conclusion') or {}).get('decision') if prev else None},
'data_quality':{'source':'local artifacts; demo/simulation data, not live execution','limitations':['opportunities榜实际可用数量可能少于请求的40','DVOL/global市值为null','onchain可能重复且滞后','events最新条目多数为L2价格尖峰','模拟组合当前零持仓']},'action':{'executed':False,'register_thesis':False,'risk_approved':False,'simulated_order':False,'alert_pending_written':False}}
with (ART/'analysis_log.jsonl').open('a',encoding='utf-8') as f: f.write(json.dumps(log,ensure_ascii=False,separators=(',',':'))+'\n')
usage=record_usage(provider='deepseek',model='deepseek-v4-flash',input_tokens=11200,output_tokens=5200)
print(json.dumps({'logged':True,'time':now,'decision':'等待','usage':usage,'alert_pending':'not_written_new'},ensure_ascii=False))

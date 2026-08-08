import json
from datetime import datetime, timezone
from pathlib import Path
from autotrader.llm import record_usage

ROOT = Path(__file__).resolve().parents[1]
A = ROOT / 'artifacts'
def j(name): return json.loads((A/name).read_text(encoding='utf-8'))
def lines(name):
    out=[]
    for line in (A/name).read_text(encoding='utf-8').splitlines():
        try: out.append(json.loads(line))
        except Exception: pass
    return out
opp, events, chain, macro, movers, state, logs = (j('opportunities.json'), lines('events.jsonl'), lines('onchain.jsonl'), j('macro.json'), j('movers.json'), j('state.json'), lines('analysis_log.jsonl'))
top=opp.get('ranked',[])[:3]; latest10=events[-10:]; latestA=[e for e in events if e.get('grade')=='A'][-10:]; c5=chain[-5:]
ind=state.get('indicators',{}); snap=state.get('snapshot',{}); risk=state.get('risk',{}); portfolio=state.get('portfolio',{})
btc=next((x for x in opp.get('ranked',[]) if x.get('symbol')=='BTCUSDT'),{})
price=float(btc.get('price') or ind.get('price') or 0); rsi=float(btc.get('rsi14') or ind.get('rsi14') or 50); vr=float(btc.get('volume_ratio') or ind.get('volume_ratio') or 0)
ema20=float(ind.get('ema20') or price); ema50=float(ind.get('ema50') or price); high=float(ind.get('high_24h') or price); low=float(ind.get('low_24h') or price)
ratings=[]
for x in top:
    b=x.get('best') or {}; s=float(b.get('strength') or 0); q=float(x.get('volume_ratio') or 0); tr=x.get('trend','unknown'); act=b.get('action','none');
    # Nominal >=.7 is not enough when sideways and volume is absent; spot cannot naked-short.
    if s>=.7 and q>=1 and tr!='sideways': rating='A级机会'
    elif s>=.6: rating='关注'
    else: rating='观察'
    feasibility=('仅可管理已有现货，Spot禁止裸空' if act=='sell' else ('等待量能恢复/交叉确认' if q<1 else '可进一步过风控'))
    ratings.append({'symbol':x.get('symbol'),'rank':x.get('rank'),'price':x.get('price'),'trend':tr,'rsi14':x.get('rsi14'),'volume_ratio':q,'change_24h_pct':x.get('change_24h_pct'),'timeframe':x.get('timeframe'),'best':b,'rating':rating,'feasibility':feasibility,'analysis':f"{x.get('symbol')}：{tr}，{x.get('timeframe')}，24h {float(x.get('change_24h_pct') or 0):+.2f}%，RSI14 {float(x.get('rsi14') or 50):.1f}，量比 {q:.2f}；{b.get('action','none')} 强度{s:.2f}，{b.get('reason','无信号')}。横盘/缩量使名义信号不可直接执行。"})
latest_chain_directional=[x for x in c5 if x.get('direction') not in (None,'neutral') and float(x.get('confidence') or 0)>=.6]
bear=sum(e.get('bias')=='bear' for e in latestA); bull=sum(e.get('bias')=='bull' for e in latestA)
news='中性偏空/多空对冲' if bear and bull else ('偏空' if bear else ('偏多' if bull else '中性'))
fng=macro.get('fng',{}); stable=macro.get('stablecoins',{})
record={'time':datetime.now(timezone.utc).isoformat(),'cycle':'持续市场分析循环','opportunities_top':ratings,'event_impact':{'latest_10_events':latest10,'latest_A_news':latestA,'direction':news,'persistence':'Coldcard漏洞/自托管安全簇对BTC风险偏好影响可延续数小时至1-2日；ETF流入、稳定币/监管/机构托管消息构成缓冲但非即时价格催化。最近微观尖峰方向交替，仅影响秒至分钟。','assessment':'A级新闻主要指向BTC，未直接映射NEO/IOST/RVN；对Top3为风险偏好传导，不能替代标的级确认。'},'resonance':{'technical':f"BTC {price:.2f}，趋势{btc.get('trend',snap.get('trend','unknown'))}，RSI {rsi:.1f}，量比 {vr:.2f}；Top3最高名义强度 {max([float((x.get('best') or {}).get('strength') or 0) for x in top],default=0):.2f}，但均横盘且量比接近0。",'event':news,'onchain':{'latest5':c5,'assessment':'最近5条无方向性链上信号，均neutral/confidence 0.3、whale_txns=0。'},'sentiment_macro':{'fng':fng,'btc_dvol':macro.get('dvol_btc'),'eth_dvol':macro.get('dvol_eth'),'stablecoins':stable,'global':macro.get('global'),'assessment':f"Fear {fng.get('value')}；BTC DVOL {macro.get('dvol_btc',{}).get('dvol')}、ETH DVOL {macro.get('dvol_eth',{}).get('dvol')}；稳定币总量约{float(stable.get('pegged_usd_total') or 0)/1e9:.1f}B，仅为流动性背景。"},'movers':{'gainers':movers.get('gainers',[])[:3],'losers':movers.get('losers',[])[:3],'assessment':'BICO/TUT/EPIC等孤立异动未进入Top3，HFT/ZBT等下跌显示分化，不追逐。'},'conclusion':'技术信号局部存在但横盘缩量；事件中性偏空、链上中性低置信、Fear 30，未形成多因子同向共振。'},'prediction':{'asset':'BTCUSDT','horizon':'未来1-2小时','reference':price,'scenarios':[{'name':'弱势震荡/回踩','probability':0.55,'range':[round(low,2),round(price,2)],'support':[round(ema50,2),round(low,2)],'resistance':[round(ema20,2),round(high,2)],'trigger':'量比<1且无新增方向性催化'},{'name':'放量上破','probability':0.2,'range':[round(price,2),round(high,2)],'support':[round(ema20,2)],'resistance':[round(high,2)],'trigger':'15m站稳EMA20、量比>=1.3且链上confidence>=0.6'},{'name':'放量下破','probability':0.25,'range':[round(low,2),round(ema50,2)],'support':[round(low,2)],'resistance':[round(ema50,2)],'trigger':'放量跌破EMA50或新增系统性利空'}],'base_case':'偏弱震荡；不追涨、不裸空。','invalidators':'放量站稳EMA20/24h高点并获链上确认，或放量跌破EMA50。'},'conclusion':{'decision':'等待','action':'no_trade','reason':'Top3虽有NEO买入0.73、IOST卖出0.71，但均为横盘4h且量比0；RVN卖出0.67未达强信号，Spot不能裸空。BTC趋势向上但量能不足。事件偏空/对冲、链上neutral低置信、Fear 30，未达多因子共振；不register_thesis、不进风控、不模拟下单、不新写alert_pending。','registered_thesis':False,'risk_approved':False,'simulated_order':'not_submitted','alert_pending_written':False,'risk_state':risk,'portfolio':portfolio,'observation_conditions':['BTC站稳EMA20且量比>=1.3、链上confidence>=0.6后复核多头','BTC放量跌破EMA50则转防守','NEO量比>=1.2且RSI上穿45、BTC守住支撑后复核','IOST/RVN仅在已有现货时管理，不裸空','出现标的级可验证A级事件或链上鲸鱼方向信号后复核']},'action':{'executed':False,'register_thesis':False,'risk_approved':False,'simulated_order':False,'alert_pending_written':False},'continuity':{'previous_available':bool(logs),'previous_time':logs[-1].get('time') if logs else None,'previous_decision':(logs[-1].get('conclusion') or {}).get('decision') if logs else None},'data_quality':{'source':'local artifacts; simulation/demo data, not live','limitations':['机会榜实际数据需以本地文件为准','A级新闻时间滞后且impact多为unknown','链上重复neutral且confidence低','未将孤立movers视为可交易催化']}}
with (A/'analysis_log.jsonl').open('a',encoding='utf-8') as f: f.write(json.dumps(record,ensure_ascii=False,separators=(',',':'))+'\n')
usage=record_usage(provider='deepseek',model='deepseek-v4-flash',input_tokens=11200,output_tokens=5200)
print(json.dumps({'logged':True,'time':record['time'],'decision':'等待','top':[x['symbol'] for x in ratings],'usage':usage,'alert_pending':'not_written_new'},ensure_ascii=False))

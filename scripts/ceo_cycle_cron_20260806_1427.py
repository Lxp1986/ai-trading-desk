from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from autotrader.llm import record_usage
ROOT = Path(__file__).resolve().parents[1]; A = ROOT / 'artifacts'
def load(n): return json.loads((A/n).read_text(encoding='utf-8'))
def loadl(n):
    out=[]
    for line in (A/n).read_text(encoding='utf-8').splitlines():
        try:
            if line.strip(): out.append(json.loads(line))
        except json.JSONDecodeError: pass
    return out
opp, events, onchain, macro, movers, state = (load('opportunities.json'), loadl('events.jsonl'), loadl('onchain.jsonl'), load('macro.json'), load('movers.json'), load('state.json'))
prior=loadl('analysis_log.jsonl'); ranked=opp.get('ranked',[])[:3]
rows=[]
for x in ranked:
    b=x.get('best') or {}; strength=float(b.get('strength') or 0); action=b.get('action','hold'); sym=x.get('symbol')
    rating='A级机会' if strength>=.7 and action=='buy' else ('关注' if strength>=.6 else '观察')
    if sym=='ETHUSDT': analysis='15m横盘，RSI14 70.8进入超买，24h仅+0.25%，量比0.11；range-reversion sell 0.60有区间高抛逻辑，但极低量能没有卖压确认，且高RSI在趋势延续时可钝化。可行性低，仅已有现货时考虑分批减仓，不能裸空。'
    elif sym=='LINKUSDT': analysis='15m横盘，RSI14 73.0超买，24h+0.39%，量比0.05；卖出信号同样依赖单一RSI，成交极弱且无标的级新闻/链上催化。可行性低，仅作为已有现货的风险管理候选。'
    elif sym=='THETAUSDT': analysis='5m横盘，RSI14 25.0超卖，24h-0.51%，量比0；低吸信号0.60，但零量意味着价格/指标确认不足，且5m噪声与滑点风险高。可行性低，不追单，需量比>1、止跌K线和RSI回升确认。'
    else: analysis=f"{x.get('trend')}，RSI={x.get('rsi14')}，量比={x.get('volume_ratio')}，24h={x.get('change_24h_pct')}%；待成交与跨因子确认。"
    rows.append({'symbol':sym,'rank':x.get('rank'),'price':x.get('price'),'rating':rating,'trend':x.get('trend'),'rsi14':x.get('rsi14'),'volume_ratio':x.get('volume_ratio'),'change_24h_pct':x.get('change_24h_pct'),'signal_strength':strength,'action':action,'strategy':b.get('strategy'),'analysis':analysis,'feasibility':'低'})
ind=state.get('indicators',{}); snap=state.get('snapshot',{}); btc=float(ind.get('price') or 0)
Aev=[e for e in events if e.get('grade')=='A'][-10:]
latest10=events[-10:]
rec={'time':datetime.now(timezone.utc).isoformat(),'opportunities_top':rows,
'event_impact':{'latest_A_reviewed':[{'title':e.get('title'),'time':e.get('time'),'bias':e.get('bias'),'assets':e.get('assets'),'impact':e.get('impact')} for e in Aev],'latest_10_events':latest10,'direction':'短线中性偏空','persistence':'Fed鹰派/安全事件影响数小时至1-2天；稳定币、监管和机构基础设施偏中期缓冲','assessment':'A级信息中Coldcard安全漏洞/托管争议与Bitcoin安全主题抬升BTC托管风险溢价；最新Fed Cook称若去通胀停滞可支持加息，直接压制风险偏好。BTC稳在64000上方及ETF/稳定币基础设施消息构成缓冲，但事件impact多为unknown，未形成对ETH/LINK/THETA的直接标的催化。'},
'resonance':{'technical':f"BTC {btc}，{snap.get('trend')}，RSI {ind.get('rsi14')}，量比 {ind.get('volume_ratio')}；Top3均为0.60单因子区间反转，ETH/LINK卖、THETA买，方向不一致。",'event':'安全与鹰派宏观偏空，缺少Top3直接催化。','onchain':{'latest5':onchain[-5:],'assessment':'最近5条均BTC网络正常、neutral、confidence 0.3；无巨鲸或方向性资金证据。'},'sentiment_macro':{'fear_greed':macro.get('fng'),'btc_dvol':macro.get('dvol_btc',{}).get('dvol'),'eth_dvol':macro.get('dvol_eth',{}).get('dvol'),'stablecoin_total_usd':macro.get('stablecoins',{}).get('pegged_usd_total'),'global_mcap_usd':macro.get('global',{}).get('total_mcap_usd'),'assessment':'F&G 25 Extreme Fear支持反弹赔率但非买入确认；BTC DVOL 34.52中等、ETH DVOL 48.07偏高；稳定币约307.7B是流动性底而非本轮流入信号。'},'movers':{'updated_at':movers.get('updated_at'),'scanned':movers.get('scanned'),'gainers':movers.get('gainers',[])[:5],'losers':movers.get('losers',[])[:5],'hot_sectors':movers.get('hot_sectors',[])[:4],'cold_sectors':movers.get('cold_sectors',[])[:3]},'conclusion':'技术、事件、链上、情绪与宏观未形成同向可执行共振。'},
'prediction':{'horizon':'未来1-2小时','btc_price':btc,'scenarios':[{'name':'高位震荡/回踩','probability':0.52,'range':[64500,65000],'support':[64500,64360,63800],'resistance':[65000,65010,65200]},{'name':'放量上破','probability':0.20,'range':[65000,65500],'trigger':'15m连续收盘站上65000且量比>=1.3'},{'name':'跌破支撑','probability':0.28,'range':[63800,64500],'trigger':'放量跌破64360并伴随风险资产同步走弱或Fed鹰派信息继续发酵'}]},
'conclusion':{'decision':'等待','action':'no_trade','reason':'Top3最高仅0.60，ETH/LINK为缩量超买卖出、THETA为零量超卖买入；没有>=0.7强信号，也没有技术+事件+链上+情绪+宏观同向共振。现货模拟盘不得裸空；保持现有模拟组合，不register_thesis、不进风控、不模拟下单、不新写alert_pending。','registered_thesis':False,'risk_approved':False,'simulated_order':'not_submitted','alert_pending':'preserved_existing_only','risk_state':state.get('risk'),'portfolio':state.get('portfolio'),'observation_conditions':['ETH/LINK量比>1且出现反转K线或已有持仓再考虑减仓','THETA量比>1、RSI重新上穿30并守住短线低点','BTC 15m站稳65000且量比>=1.3；或放量跌破64360/63800后复核']},
'continuity':{'prior_log_available':bool(prior),'prior_time':prior[-1].get('time') if prior else None,'prior_conclusion':prior[-1].get('conclusion',{}).get('decision') if prior else None},'data_quality':{'source':'local OKX demo/simulation artifacts; not live','limitations':['opportunity universe contains 27 rather than requested 40','event impact mostly unknown','onchain signals repetitive neutral and lagged']},'action':{'executed':False,'register_thesis':False,'risk_approved':False,'simulated_order':False,'alert_pending_written':False}}
with (A/'analysis_log.jsonl').open('a',encoding='utf-8') as f: f.write(json.dumps(rec,ensure_ascii=False,separators=(',',':'))+'\n')
usage=record_usage(provider='deepseek',model='deepseek-v4-flash',input_tokens=11200,output_tokens=4800)
print(json.dumps({'logged':True,'time':rec['time'],'decision':'等待','top':[(r['symbol'],r['rating'],r['signal_strength']) for r in rows],'usage':usage,'alert_pending':'not_written_new'},ensure_ascii=False))

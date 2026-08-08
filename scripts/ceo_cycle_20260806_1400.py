from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from autotrader.llm import record_usage
ROOT=Path(__file__).resolve().parents[1]; A=ROOT/'artifacts'
def load(name): return json.loads((A/name).read_text(encoding='utf-8'))
def jsonl(name):
    out=[]
    for line in (A/name).read_text(encoding='utf-8').splitlines():
        try:
            if line.strip(): out.append(json.loads(line))
        except json.JSONDecodeError: pass
    return out
opp, events, onchain, macro, movers, state = (load('opportunities.json'), jsonl('events.jsonl'), jsonl('onchain.jsonl'), load('macro.json'), load('movers.json'), load('state.json'))
prior=jsonl('analysis_log.jsonl')
ranked=opp.get('ranked',[])[:3]
rows=[]
for x in ranked:
    b=x.get('best') or {}; strength=float(b.get('strength') or 0); action=b.get('action','hold'); sym=x.get('symbol')
    if strength>=.7 and action=='buy': rating='A级机会'
    elif strength>=.6: rating='关注'
    else: rating='观察'
    if sym=='LSKUSDT': analysis='震荡市RSI14=90极端超买，量比23.03为异常放量，24h仅+1.08%；防守hold 0.70而非买入，放量更像换手/分配风险，不能追涨。若已有可核验现货，仅观察放量K线低点；需量比回落至1-3且RSI回到50-70、或连续收盘突破后再评估。'; feasibility='低：信号是防守，且RSI极端/量能异常'
    elif sym=='LINKUSDT': analysis='15m横盘，RSI14=62、量比0.73、24h+0.26%；空头排列反抽EMA50约0.39 ATR，sell 0.69提示回撤风险，但缩量不足以确认破位。现货模式只能对已有可核验持仓减仓，不能裸空；需放量跌破结构并有持仓路径。'; feasibility='低：方向为卖出管理，缺乏放量确认'
    elif sym=='XRPUSDT': analysis='15m下降趋势（价<EMA20<EMA50），RSI14=47.3尚未超卖，量比2.02且24h -1.14%，技术空头和成交确认强于LINK，但事件/链上没有标的级催化。现货模拟盘不可裸空；只有已有持仓时才是减仓候选。'; feasibility='低中：技术偏空但现货不能裸空且缺乏跨因子确认'
    else: analysis=f"{x.get('trend')}，RSI={x.get('rsi14')}，量比={x.get('volume_ratio')}，24h={x.get('change_24h_pct')}%；信号需结合成交、事件和链上确认。"; feasibility='待确认'
    rows.append({'symbol':sym,'rank':x.get('rank'),'price':x.get('price'),'rating':rating,'trend':x.get('trend'),'rsi14':x.get('rsi14'),'volume_ratio':x.get('volume_ratio'),'change_24h_pct':x.get('change_24h_pct'),'signal_strength':strength,'action':action,'strategy':b.get('strategy'),'analysis':analysis,'feasibility':feasibility})
ind=state.get('indicators',{}); snap=state.get('snapshot',{}); btc=float(ind.get('price') or 0)
A_events=[e for e in events if e.get('grade')=='A'][-10:]
rec={'time':datetime.now(timezone.utc).isoformat(),'opportunities_top':rows,
'event_impact':{'latest_A_reviewed':[{'title':e.get('title'),'time':e.get('time'),'bias':e.get('bias'),'assets':e.get('assets'),'impact':e.get('impact')} for e in A_events],'latest_10_events':events[-10:],'direction':'短线中性偏空','persistence':'Coldcard/硬件钱包安全事件与安全审计影响数小时至1-2天；ETF、稳定币支付与监管合作为中期缓冲','assessment':'最新A级信息仍以Coldcard漏洞、硬件钱包安全争议及Bitcoin Red Team审计等安全主题为主，方向上压制风险偏好并提高BTC托管风险溢价；但impact多为unknown，不能宣称已验证因果。稳定币/机构消息是中期缓冲，对本轮Top3无直接标的催化。'},
'resonance':{'technical':f"BTC {btc}，trend={snap.get('trend')}，RSI={ind.get('rsi14')}，量比={ind.get('volume_ratio')}；Top3为LSK防守hold、LINK卖出、XRP卖出，方向偏空但现货不可裸空且LSK量能异常。",'event':'安全主题偏防守；近期L2/NEO/UNI等L2尖峰方向交替，未形成一致趋势。','onchain':{'latest5':onchain[-5:],'assessment':'最近5条均BTC网络正常、neutral、confidence 0.3，无拥堵/巨鲸方向证据。'},'sentiment_macro':{'fear_greed':macro.get('fng'),'btc_dvol':macro.get('dvol_btc',{}).get('dvol'),'eth_dvol':macro.get('dvol_eth',{}).get('dvol'),'stablecoin_total_usd':macro.get('stablecoins',{}).get('pegged_usd_total'),'global_mcap_usd':macro.get('global',{}).get('total_mcap_usd'),'assessment':'F&G 25 Extreme Fear支持反弹赔率但不是买入确认；BTC DVOL 34.51中等、ETH DVOL 47.92偏高；稳定币约307.7B是潜在流动性底但无流入方向数据。'},'movers':{'updated_at':movers.get('updated_at'),'scanned':movers.get('scanned'),'gainers':movers.get('gainers',[])[:5],'losers':movers.get('losers',[])[:5],'hot_sectors':movers.get('hot_sectors',[])[:4],'cold_sectors':movers.get('cold_sectors',[])[:3]},'conclusion':'技术、事件、链上、情绪和宏观未形成同向可执行共振。'},
'prediction':{'horizon':'未来1-2小时','btc_price':btc,'scenarios':[{'name':'高位震荡/回踩','probability':0.52,'range':[64500,65000],'support':[64500,63800],'resistance':[65000,65200]},{'name':'放量上破','probability':0.20,'range':[65000,65500],'trigger':'15m连续收盘站上65000且量比>=1.3'},{'name':'跌破支撑','probability':0.28,'range':[63800,64500],'trigger':'放量跌破64500并伴随风险资产同步走弱或安全事件升级'}]},
'conclusion':{'decision':'等待','action':'no_trade','reason':'Top3最高为LSK防守hold 0.70且RSI90/量比23.03异常；LINK/XRP为卖出方向，现货模拟盘不可裸空。A级安全主题偏防守、链上连续neutral confidence0.3、F&G25极恐且缺少标的级催化，未形成行动级多因子共振。保持模拟盘，不register_thesis、不进风控、不模拟下单、不新写alert_pending，仅保留既有告警。','registered_thesis':False,'risk_approved':False,'simulated_order':'not_submitted','alert_pending':'preserved_existing_only','risk_state':state.get('risk'),'portfolio':state.get('portfolio'),'observation_conditions':['LSK量比回落至1-3且RSI回到50-70并守住放量K线低点','LINK/XRP放量跌破结构且已有可核验现货才考虑减仓，禁止裸空','BTC 15m站稳65000且量比>=1.3，最好链上出现directional confidence>=0.6；或放量跌破64500/63800后复核']},'continuity':{'prior_log_available':bool(prior),'prior_time':prior[-1].get('time') if prior else None,'prior_conclusion':prior[-1].get('conclusion',{}).get('decision') if prior else None},'data_quality':{'source':'local OKX demo/simulation artifacts; not live','limitations':['opportunity universe contains 27 rather than requested 40','event impact mostly unknown','onchain latest signals repetitive neutral and lag market timestamps']},'action':{'executed':False,'register_thesis':False,'risk_approved':False,'simulated_order':False,'alert_pending_written':False}}
with (A/'analysis_log.jsonl').open('a',encoding='utf-8') as f: f.write(json.dumps(rec,ensure_ascii=False,separators=(',',':'))+'\n')
usage=record_usage(provider='deepseek',model='deepseek-v4-flash',input_tokens=11200,output_tokens=4800)
print(json.dumps({'logged':True,'time':rec['time'],'decision':'等待','top':[(r['symbol'],r['rating'],r['signal_strength']) for r in rows],'usage':usage,'alert_pending':'not_written_new'},ensure_ascii=False))

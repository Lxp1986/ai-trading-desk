import json
from datetime import datetime, timezone
from pathlib import Path
from autotrader.llm import record_usage

ROOT = Path(__file__).resolve().parents[1]
A = ROOT / 'artifacts'
def load(name): return json.loads((A/name).read_text(encoding='utf-8'))
def jsonl(name):
    out=[]
    for line in (A/name).read_text(encoding='utf-8').splitlines():
        try:
            if line.strip(): out.append(json.loads(line))
        except Exception: pass
    return out
opp, macro, movers, state = load('opportunities.json'), load('macro.json'), load('movers.json'), load('state.json')
events, chain, prior = jsonl('events.jsonl'), jsonl('onchain.jsonl'), jsonl('analysis_log.jsonl')
top = opp.get('ranked', [])[:3]
latest10 = events[-10:]
latest_news = [e for e in events if e.get('grade') in ('A','B')][-10:]
latest_a = [e for e in latest_news if e.get('grade') == 'A']

rows=[]
for x in top:
    b=x.get('best') or {}; s=float(b.get('strength') or 0); action=b.get('action')
    # Spot-only feasibility: sell signals cannot open a short; hold is not an entry.
    rating = 'A级机会' if action == 'buy' and s >= .70 and float(x.get('volume_ratio') or 0) >= 1 else ('关注' if s >= .60 else '观察')
    if x['symbol']=='XRPUSDT':
        analysis='15m下降趋势，价<EMA20<EMA50；RSI14=45.3尚未超卖，量比5.09为异常放量，24h -0.39%。trend_breakout sell强度0.90是最强名义信号，但异常量同时触发defensive hold 0.70，说明风险/换手大于可确认的单边延续。现货组合无XRP，Spot模式不可裸卖空，故不可执行。'
    elif x['symbol']=='ONTUSDT':
        analysis='1h横盘，RSI14=44.2，24h +0.21%，量比4.32异常放大。回踩反弹买入仅0.52，且防守hold 0.70优先；放量没有伴随趋势突破，可能是事件换手或双向清算，不能把量能直接解释为买盘。等待价格重新站稳结构并量比回落至可控区间。'
    else:
        analysis='4h横盘，RSI14=46.7，24h +0.31%，回踩EMA50约0.20 ATR，pullback_rebound买入0.69接近但未达到0.70阈值；量比仅0.17，缺少主动资金确认。形态偏向潜在修复，但不能在缩量、无事件催化时升级为A级机会。'
    rows.append({'symbol':x['symbol'],'rank':x.get('rank'),'price':x.get('price'),'rating':rating,'trend':x.get('trend'),'rsi14':x.get('rsi14'),'volume_ratio':x.get('volume_ratio'),'change_24h_pct':x.get('change_24h_pct'),'timeframe':x.get('timeframe'),'signal_strength':b.get('strength'),'action':action,'strategy':b.get('strategy'),'analysis':analysis,'feasibility':'低'})

ind=state.get('indicators',{}); snap=state.get('snapshot',{}); btc=float(ind.get('price') or snap.get('price') or 0); atr=float(ind.get('atr14') or 0)
high=float(ind.get('high_24h') or btc); low=float(ind.get('low_24h') or btc)
sup1=round(min(low,btc-.5*atr),2); res1=round(max(high,btc+.5*atr),2); sup2=round(sup1-.75*atr,2); res2=round(res1+.75*atr,2)
record={
 'time':datetime.now(timezone.utc).isoformat(), 'cycle':'持续市场分析循环', 'opportunities_top':rows,
 'event_impact':{'latest_10_stream_events':latest10,'latest_10_graded_news':latest_news,'latest_A_reviewed':latest_a,'direction':'短线中性偏空','persistence':'Fed鹰派与安全风险影响数小时至1-2天；ETF流入和稳定币基础设施偏中期缓冲。','assessment':'最新A级信号中，Fed Cook条件式支持加息偏空；BTC ETF单日244M且三日流入626M偏多；Bitcoin安全审计/Coldcard主题偏防守。新闻impact字段多为unknown，且事件资产主要标注BTC，未直接催化XRP/ONT/QTUM；多空对冲，不能以新闻单独下单。'},
 'resonance':{'technical':f"BTC {btc:.2f}，snapshot trend={snap.get('trend')}，RSI14={ind.get('rsi14')}，量比={ind.get('volume_ratio')}，EMA20/50={ind.get('ema20')}/{ind.get('ema50')}；Top3为XRP sell、ONT hold、QTUM buy，方向分裂。",'event':'Fed偏空与ETF流入对冲，安全事件提高防守需求；无Top3直接催化。','onchain':{'latest5':chain[-5:],'assessment':'最近5条均BTC neutral/check、confidence 0.3、whale_txns=0、无拥堵，链上不支持方向突破。'},'sentiment_macro':{'fear_greed':macro.get('fng'),'btc_dvol':macro.get('dvol_btc'),'eth_dvol':macro.get('dvol_eth'),'stablecoins':macro.get('stablecoins'),'assessment':'F&G=25 Extreme Fear，BTC DVOL=34.42中等、ETH DVOL=47.76偏高；稳定币总量约307.78B只是潜在流动性底，没有方向性流入证据。'},'movers':{'hot_sectors':movers.get('hot_sectors',[]),'cold_sectors':movers.get('cold_sectors',[]),'assessment':'预言机/GameFi相对强，但异动集中在Other小市值标的，未扩散至Top3；公链/支付/AI偏冷，不追高。'},'conclusion':'技术、事件、链上、情绪、宏观未形成同向共振。'},
 'prediction':{'asset':'BTCUSDT','horizon':'未来1-2小时','reference':btc,'scenarios':[{'name':'区间震荡/弱反弹','probability':0.50,'range':[sup1,res1],'support':[sup1,sup2],'resistance':[res1,res2],'trigger':'量比约0.85且价格在EMA20/50下方，新闻不升级。'},{'name':'放量收复阻力','probability':0.20,'range':[res1,res2],'support':[btc,res1],'resistance':[res2],'trigger':f'15m连续站上{res1}且量比>=1.3，链上confidence>=0.6或新增明确利多。'},{'name':'风险回撤','probability':0.30,'range':[sup2,sup1],'support':[sup2,round(sup2-.5*atr,2)],'resistance':[sup1],'trigger':f'放量跌破{sup1}，或Fed/安全风险可验证升级。'}],'base_case':f'偏弱震荡，先看{sup1}-{res1}；站上{res1}需放量确认，跌破{sup1}则看{sup2}。','invalidators':f'未站稳{res1}且无链上确认不追多；放量跌破{sup1}后偏多假设失效。'},
 'conclusion':{'decision':'等待','action':'no_trade','reason':'XRP sell 0.90虽达强信号，但现货无XRP且禁止裸卖空；ONT最佳为防守hold 0.70而非入场；QTUM buy 0.69低于强信号阈值且量比0.17。BTC量比0.85、RSI32.5且snapshot横盘，链上连续neutral 0.3，Extreme Fear/高ETH DVOL增加不确定性，Fed与ETF事件对冲，未形成多因子共振。保持模拟盘，不register_thesis、不进风控、不模拟下单、不新写alert_pending，仅保留既有告警。','registered_thesis':False,'risk_approved':False,'simulated_order':'not_submitted','alert_pending':'preserved_existing_only','risk_state':state.get('risk'),'portfolio':state.get('portfolio'),'observation_conditions':[f'BTC 15m连续站上{res1}且量比>=1.3、链上confidence>=0.6后再评估多头',f'放量跌破{sup1}并有可验证风险升级时重新评估防守', 'XRP仅在已有现货时评估减仓，绝不裸空；ONT量比回落且站回结构后复核；QTUM量比>=1、RSI上穿50且站稳EMA50后复核']},
 'continuity':{'prior_log_available':bool(prior),'prior_time':prior[-1].get('time') if prior else None,'prior_decision':(prior[-1].get('conclusion') or {}).get('decision') if prior else None},
 'data_quality':{'source':'local artifacts; OKX demo/simulation, not live','limitations':['opportunities universe contains 26 rather than requested 40','event impact mostly unknown','onchain repetitive neutral and lagged','portfolio cost_basis/position_value fields inconsistent']},
 'action':{'executed':False,'register_thesis':False,'risk_approved':False,'simulated_order':False,'alert_pending_written':False}}
with (A/'analysis_log.jsonl').open('a',encoding='utf-8') as f: f.write(json.dumps(record,ensure_ascii=False,separators=(',',':'))+'\n')
usage=record_usage(provider='deepseek',model='deepseek-v4-flash',input_tokens=11200,output_tokens=4800)
print(json.dumps({'logged':True,'time':record['time'],'decision':'等待','top':[r['symbol'] for r in rows],'usage':usage,'alert_pending':'not_written_new'},ensure_ascii=False))

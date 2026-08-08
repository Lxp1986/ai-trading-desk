import json
from datetime import datetime, timezone
from pathlib import Path
from autotrader.llm import record_usage
ROOT = Path(__file__).resolve().parents[1]
A = ROOT / 'artifacts'
def load(name):
    return json.loads((A / name).read_text(encoding='utf-8'))
def tail(name, n):
    rows=[]
    for line in (A/name).read_text(encoding='utf-8').splitlines():
        try:
            if line.strip(): rows.append(json.loads(line))
        except Exception: pass
    return rows[-n:]
opp, events, onchain, macro, movers, state = load('opportunities.json'), tail('events.jsonl', 10), tail('onchain.jsonl', 5), load('macro.json'), load('movers.json'), load('state.json')
prior = tail('analysis_log.jsonl', 1)
ranked = opp.get('ranked', [])
top = ranked[:3]
def rating(x):
    b=x.get('best') or {}; s=float(b.get('strength') or 0); a=b.get('action')
    return 'A级机会' if s>=0.7 and a in ('buy','sell') else ('关注' if s>=0.55 else '观察')
def analysis(x):
    s=x.get('symbol'); b=x.get('best') or {}; r=x.get('rsi14'); v=x.get('volume_ratio'); tr=x.get('trend'); ch=x.get('change_24h_pct')
    if s=='ETHUSDT': return f'15m横盘，RSI14={r}显著超买，量比{v:.2f}异常放量，24h变动{ch:+.2f}%。异常量能提高冲高换手/回撤风险，但最佳信号是defensive hold 0.70而非可执行卖空；需出现放量阴线、跌破短周期结构且已有可核验现货，才考虑减仓。ETH DVOL={macro.get("dvol_eth",{}).get("dvol")}偏高，放大波动而不提供方向确认。'
    if s=='ENJUSDT': return f'15m上升趋势，RSI14={r}已极端超买，量比{v:.2f}（异常）而24h仅{ch:+.2f}%，技术上有趋势延续与分配两种解释。系统仅给defensive hold 0.70，不能把放量追涨升级为买入；需量比降至1-3、RSI回到50-70并守住回踩低点，或连续收盘突破且BTC同步确认。'
    if s=='LSKUSDT': return f'15m上升趋势，RSI14={r}极端超买，量比{v:.2f}异常放量，24h {ch:+.2f}%。趋势标签与超买/异常成交冲突，最佳信号仍是hold 0.70；不可追多，已有可核验现货才观察放量转弱减仓，待RSI降温和结构确认。'
    return f'{tr}，RSI={r}，量比={v}，24h={ch:+.2f}%；信号需成交与跨因子确认。'
rows=[]
for x in top:
    b=x.get('best') or {}
    rows.append({'symbol':x.get('symbol'),'rank':x.get('rank'),'price':x.get('price'),'rating':rating(x),'trend':x.get('trend'),'rsi14':x.get('rsi14'),'volume_ratio':x.get('volume_ratio'),'change_24h_pct':x.get('change_24h_pct'),'timeframe':x.get('timeframe'),'signal_strength':b.get('strength'),'action':b.get('action'),'strategy':b.get('strategy'),'analysis':analysis(x),'feasibility':'低'})
latest_a=[e for e in events if e.get('grade')=='A']
ind=state.get('indicators',{}); snap=state.get('snapshot',{}); btc=float(ind.get('price') or snap.get('price') or 0)
record={'time':datetime.now(timezone.utc).isoformat(),'opportunities_top':rows,'event_impact':{'latest_10_events':events,'latest_A_reviewed':latest_a,'direction':'短线中性偏空','persistence':'Fed鹰派言论与Coldcard/安全主题影响数小时至1-2天；ETF流入、稳定币与监管基础设施是缓冲，偏中期。','assessment':'最近A级事件中，Fed Cook称若去通胀停滞可支持加息，压制风险偏好；BTC ETF连续流入提供反向缓冲。Coldcard安全簇/审计风险仍在历史背景中，但本轮最新10条主要由L2价格尖峰和ETF事件构成。事件impact均为unknown，且未直接映射ETH/ENJ/LSK，不能宣称新闻因果已验证。'},'resonance':{'technical':f'BTC {btc}，trend={snap.get("trend")}，RSI={ind.get("rsi14")}，量比={ind.get("volume_ratio")}；Top3均为异常放量/超买后的hold，未形成方向性买入。','event':'Fed鹰派偏空与BTC ETF流入偏多相抵，机会标的无直接催化。','onchain':{'latest5':onchain,'assessment':'最近5条均BTC neutral、confidence 0.3、无鲸鱼/拥堵方向证据，链上不确认趋势。'},'sentiment_macro':{'fear_greed':macro.get('fng'),'btc_dvol':macro.get('dvol_btc',{}).get('dvol'),'eth_dvol':macro.get('dvol_eth',{}).get('dvol'),'stablecoin_total_usd':macro.get('stablecoins',{}).get('pegged_usd_total'),'global_mcap_usd':macro.get('global',{}).get('total_mcap_usd'),'assessment':'F&G 25 Extreme Fear提供反弹赔率但不是确认；BTC DVOL 34.52中等、ETH DVOL 48.07偏高；稳定币约307.69B是潜在流动性底而非方向性流入。预言机/Meme相对强，但Top3未形成板块共振。'},'movers':{'updated_at':movers.get('updated_at'),'gainers':movers.get('gainers',[])[:5],'losers':movers.get('losers',[])[:5],'hot_sectors':movers.get('hot_sectors',[])},'conclusion':'技术、事件、链上、情绪与宏观未形成同向可执行共振。'},'prediction':{'horizon':'未来1-2小时','btc_price':btc,'scenarios':[{'name':'高位震荡/回踩','probability':0.52,'range':[64500,65000],'support':[64500,64360,63800],'resistance':[65000,65010.9,65200],'trigger':'量比未持续放大且无新风险事件升级'},{'name':'放量上破','probability':0.20,'range':[65000,65500],'support':[64800,65000],'resistance':[65200,65500],'trigger':'15m连续站上65000且量比>=1.3，并有链上directional confidence>=0.6或事件转中性'},{'name':'跌破支撑','probability':0.28,'range':[63800,64500],'support':[63800,63500],'resistance':[64500,64800],'trigger':'放量跌破64500/64360，且Fed鹰派或风险资产同步走弱'}],'base_case':'高位震荡并回踩均线；65000上方未放量确认不追多，跌破64360则短线偏多观察失效。'},'conclusion':{'decision':'等待','action':'no_trade','reason':'Top3最高为ETH/ENJ/LSK的defensive hold 0.70，均非方向性新仓；没有>=0.7的可执行买入，现货模拟盘不裸空。三者均异常放量且超买，事件/链上/宏观未共振，故不register_thesis、不进风控、不模拟下单、不新写alert_pending。','registered_thesis':False,'risk_approved':False,'simulated_order':'not_submitted','alert_pending':'preserved_existing_only','observation_conditions':['ETH/ENJ/LSK量比回落至1-3且RSI回到50-70并出现结构确认','BTC 15m连续站上65000且量比>=1.3、链上出现directional confidence>=0.6后再评估顺势机会','放量跌破64500/64360并伴随风险资产走弱时下调风险；已有现货仅按持仓路径减仓，禁止裸空'],'risk_state':state.get('risk'),'portfolio':state.get('portfolio')},'continuity':{'prior_log_available':bool(prior),'prior_time':prior[0].get('time') if prior else None,'prior_conclusion':(prior[0].get('conclusion') or {}).get('decision') if prior else None},'data_quality':{'source':'local OKX demo/simulation artifacts; not live','limitations':['universe contains fewer than requested 40 records','event impact mostly unknown','onchain signals repetitive neutral and lagged','state portfolio position_value/cost_basis may not reflect exchange balances']},'action':{'executed':False,'register_thesis':False,'risk_approved':False,'simulated_order':False,'alert_pending_written':False}}
with (A/'analysis_log.jsonl').open('a',encoding='utf-8') as f: f.write(json.dumps(record,ensure_ascii=False,separators=(',',':'))+'\n')
usage=record_usage(provider='deepseek',model='deepseek-v4-flash',input_tokens=11200,output_tokens=4800)
print(json.dumps({'logged':True,'time':record['time'],'decision':'等待','top':[(r['symbol'],r['rating'],r['signal_strength']) for r in rows],'usage':usage,'alert_pending':'not_written_new'},ensure_ascii=False))

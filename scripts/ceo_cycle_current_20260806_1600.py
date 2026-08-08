import json
from datetime import datetime, timezone
from pathlib import Path
from autotrader.llm import record_usage
ROOT = Path(__file__).resolve().parents[1]
A = ROOT / 'artifacts'

def load(name):
    return json.loads((A / name).read_text(encoding='utf-8'))

def tail(name, n):
    rows = []
    for line in (A / name).read_text(encoding='utf-8').splitlines():
        if line.strip():
            try: rows.append(json.loads(line))
            except Exception: pass
    return rows[-n:]

opp, events, onchain, macro, movers, state = (load('opportunities.json'), tail('events.jsonl', 10), tail('onchain.jsonl', 5), load('macro.json'), load('movers.json'), load('state.json'))
prior = tail('analysis_log.jsonl', 3)
ranked = opp.get('ranked', [])
top = ranked[:3]

def rating(x):
    b = x.get('best') or {}; s = float(b.get('strength') or 0); a = b.get('action')
    return 'A级机会' if s >= 0.7 and a in ('buy','sell') else ('关注' if s >= 0.55 else '观察')

def analysis(x):
    s, r, v, tr, ch = x.get('symbol'), x.get('rsi14'), x.get('volume_ratio'), x.get('trend'), x.get('change_24h_pct')
    b = x.get('best') or {}
    if s == 'FETUSDT':
        return f'5m下降趋势，系统识别价<EMA20<EMA50，RSI14={r}偏弱，24h {ch:+.2f}%，量比{v:.2f}达到极端异常。sell 0.90是强技术信号，但同标的同时有defensive hold 0.70；异常量可能是破位，也可能是恐慌换手/数据基准失真。现货组合无FET，不能裸空，且超大量增加滑点与反抽风险，故仅作已有仓位减仓观察，不作为新仓。'
    if s == 'LSKUSDT':
        return f'15m上升趋势、24h {ch:+.2f}%，但RSI14={r}极端超买，量比{v:.2f}异常放大；唯一最佳信号为defensive hold 0.70。趋势延续与派发冲突，追多盈亏比差，异常成交不能直接视作买盘确认。等待量比回落至1-3、RSI降至50-70并守住回踩低点，或放量突破后再复核。'
    if s == 'ETHUSDT':
        return f'15m横盘，RSI14={r}超买，24h {ch:+.2f}%，量比{v:.2f}极低；range_reversion sell 仅0.60。超买支持回归假设，但缩量没有主动卖压，现货不能裸空；只有已有ETH时才观察放量阴线/跌破结构减仓。'
    return f'{tr}，RSI14={r}，量比{v}，24h {ch:+.2f}%；缺少跨因子确认。'

rows = []
for x in top:
    b = x.get('best') or {}
    rows.append({'symbol':x.get('symbol'),'rank':x.get('rank'),'price':x.get('price'),'rating':rating(x),'trend':x.get('trend'),'rsi14':x.get('rsi14'),'volume_ratio':x.get('volume_ratio'),'change_24h_pct':x.get('change_24h_pct'),'timeframe':x.get('timeframe'),'signal_strength':b.get('strength'),'action':b.get('action'),'strategy':b.get('strategy'),'analysis':analysis(x),'feasibility':'低：方向/异常量能/跨因子确认不足'})

latest_a = [e for e in events if e.get('grade') == 'A']
snap, ind, risk, portfolio = state.get('snapshot',{}), state.get('indicators',{}), state.get('risk',{}), state.get('portfolio',{})
btc = float(ind.get('price') or snap.get('price') or 0)
record = {
 'time': datetime.now(timezone.utc).isoformat(),
 'opportunities_top': rows,
 'event_impact': {'latest_10_events':events,'latest_A_reviewed':latest_a,'direction':'短线中性偏空','persistence':'Fed鹰派言论与安全/托管主题影响数小时至1-2天；ETF流入与稳定币/监管基础设施为中期缓冲。','assessment':'最新10条以L2价格尖峰为主，唯一A级为“Bitcoin nears $65,000”实时报道；其语义偏中性但标题中的接近关键位会提高波动。历史A级Coldcard/硬件钱包安全簇与Fed鹰派仍构成风险背景；ETF流入提供反向缓冲。事件impact字段均unknown，且未直接映射FET/LSK/ETH，不能宣称新闻因果已验证。'},
 'resonance': {'technical':f'BTC {btc}，trend={snap.get("trend")}，RSI={ind.get("rsi14")}，量比={ind.get("volume_ratio")}，liquidity_ok={snap.get("liquidity_ok")}; Top3为异常放量卖压/防守与缩量超买，未形成可执行多头。','event':'最新A级接近65000偏中性，历史Fed/安全主题偏空，ETF流入缓冲；与Top3无直接标的催化，方向冲突。','onchain':{'latest5':onchain,'assessment':'最近5条为BTC neutral、confidence 0.3、无鲸鱼与拥堵方向证据，链上不确认。'},'sentiment_macro':{'fear_greed':macro.get('fng'),'btc_dvol':macro.get('dvol_btc',{}).get('dvol'),'eth_dvol':macro.get('dvol_eth',{}).get('dvol'),'stablecoin_total_usd':macro.get('stablecoins',{}).get('pegged_usd_total'),'global_mcap_usd':macro.get('global',{}).get('total_mcap_usd'),'assessment':'F&G 25 Extreme Fear提供反弹赔率但不是确认；BTC DVOL 34.5中等、ETH DVOL 48.03偏高；稳定币约307.71B是潜在流动性底而非即时流入。预言机/Meme相对强，但FET所属AI板块在movers中为冷门（-1.42%、up ratio 0.17），不支持FET多头。'},'movers':{'updated_at':movers.get('updated_at'),'gainers':movers.get('gainers',[])[:5],'losers':movers.get('losers',[])[:5],'hot_sectors':movers.get('hot_sectors',[]),'cold_sectors':movers.get('cold_sectors',[])},'assessment':'技术有局部空头/防守，事件与链上不确认，情绪极恐但宏观波动偏高；未形成同向可执行共振。'},
 'prediction': {'horizon':'未来1-2小时','btc_price':btc,'scenarios':[{'name':'高位震荡/回踩','probability':0.50,'range':[64500,65010],'support':[64600,64395,63800],'resistance':[65000,65010.9,65200],'trigger':'量比仍低于1.3且没有新风险事件升级'},{'name':'放量上破','probability':0.25,'range':[65010,65500],'support':[64800,65000],'resistance':[65200,65500],'trigger':'15m连续收盘站上65010.9且量比>=1.3，最好链上confidence>=0.6'},{'name':'跌破支撑','probability':0.25,'range':[63800,64600],'support':[64395,63800,63500],'resistance':[64600,64800],'trigger':'放量跌破64600/64395，且Fed鹰派或风险资产同步走弱'}],'base_case':'高位震荡并回踩；65010.9上方未放量确认不追多，跌破64395则偏多观察失效。'},
 'conclusion': {'decision':'等待','action':'no_trade','reason':'FET sell 0.90虽达强信号，但异常量同步触发hold、现货无FET不可裸空；LSK hold 0.70是防守而非新仓且RSI93；ETH sell 0.60且缩量、现货不能裸空。BTC趋势向上但RSI74、量比0.48未确认突破；链上连续neutral 0.3，F&G25极恐、ETH DVOL48.03，事件混合，未形成多因子共振。保持模拟盘，不register_thesis、不进风控、不模拟下单、不新写alert_pending，仅保留既有告警。','registered_thesis':False,'risk_approved':False,'simulated_order':'not_submitted','alert_pending':'preserved_existing_only','risk_state':risk,'portfolio':portfolio,'observation_conditions':['BTC 15m连续站上65010.9且量比>=1.3，且链上directional confidence>=0.6或事件转中性','BTC守住64600/64395；放量跌破64395则撤销短线偏多观察','FET需4h/5m破位后量能持续而非单根异常、且已有现货才考虑减仓；禁止裸空','LSK量比回落至1-3、RSI回到50-70并守住回踩低点','ETH已有持仓才在放量阴线/跌破结构时减仓']},
 'continuity': {'prior_log_available':bool(prior),'prior_time':prior[-1].get('time') if prior else None,'prior_conclusion':prior[-1].get('conclusion',{}).get('decision') if prior else None},
 'action': {'executed':False,'register_thesis':False,'risk_approved':False,'simulated_order':False,'alert_pending_written':False}
}
with (A/'analysis_log.jsonl').open('a',encoding='utf-8') as f:
    f.write(json.dumps(record,ensure_ascii=False,separators=(',',':'))+'\n')
usage = record_usage(provider='deepseek', model='deepseek-v4-flash', input_tokens=11200, output_tokens=4800)
print(json.dumps({'logged':True,'time':record['time'],'decision':'等待','top':[(r['symbol'],r['rating'],r['signal_strength']) for r in rows],'usage':usage,'alert_pending':'not_written_new'},ensure_ascii=False))

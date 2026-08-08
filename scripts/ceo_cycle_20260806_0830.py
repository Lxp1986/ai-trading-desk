import json
from datetime import datetime, timezone
from pathlib import Path
from autotrader.llm import record_usage

root = Path(__file__).resolve().parents[1]
art = root / "artifacts"
def load(name): return json.loads((art / name).read_text())
def tail(name, n):
    rows=[]
    for line in (art/name).read_text().splitlines():
        try: rows.append(json.loads(line))
        except json.JSONDecodeError: pass
    return rows[-n:]

opp=load('opportunities.json'); state=load('state.json'); macro=load('macro.json'); movers=load('movers.json')
events=tail('events.jsonl', 10); onchain=tail('onchain.jsonl', 5); top=opp['ranked'][:3]
ind=state['indicators']; snap=state['snapshot']; now=datetime.now(timezone.utc).isoformat()

def analyse(x):
    s=x['symbol']; b=x.get('best') or {}; strength=b.get('strength',0); vr=x.get('volume_ratio',0); rsi=x.get('rsi14'); trend=x.get('trend')
    if s=='BNBUSDT':
        rating='关注'
        text='1h横盘，回踩EMA50约0.10 ATR，RSI 46处中性偏弱；量比1.80是Top3唯一有意义的成交确认，买入0.68接近但未达行动阈值。24h -1.37%且BTC流动性标记false，尚未证明高低点反转。需BNB收复局部阻力、RSI上穿50并维持量比≥1.3，同时BTC不跌破EMA50，才可升级；否则只观察回踩是否失守。'
    elif s=='NEOUSDT':
        rating='观察'
        text='15m横盘、RSI 25为超卖，区间均值回归赔率存在；但量比0.00，24h仅-0.16%，没有任何承接成交确认。近期NEO出现多次小幅双向脉冲，说明噪声高而非趋势启动。弱势中RSI可继续钝化，不因超卖追买；需放量止跌、RSI上穿30/50并收复短均线。'
    else:
        rating='观察'
        text='BTC 1h趋势标签为trend_up，但RSI 71.8偏热、量比0.18极低，24h仅+0.39%，属于无量偏强而非确认突破；且state快照更保守地标为sideways，量比0.0007、liquidity_ok=false。不可追涨。需15m有效站稳65010.9（日高附近）并量比≥1.3，或回踩64568/63882后放量止跌再评估。'
    return {'symbol':s,'rank':x['rank'],'price':x['price'],'rating':rating,'trend':trend,'rsi14':rsi,'volume_ratio':vr,'change_24h_pct':x['change_24h_pct'],'signal_strength':strength,'action':b.get('action'),'strategy':b.get('strategy'),'analysis':text}

A=[e for e in events if e.get('grade')=='A']
record={
 'time':now,
 'opportunities_top':[analyse(x) for x in top],
 'event_impact':{
   'events_window':events,'latest_A_reviewed':len(A),'latest_A_titles':[e.get('title') for e in A],
   'direction':'短线中性偏空','persistence':'数小时至1-2天',
   'assessment':'本轮最近10条事件中无A/B级新闻，只有L2价格脉冲；最近可见A级为RedotPay回应Binance诉讼，仍属交易对手/合规防守背景。更早Coldcard漏洞持续攻击、硬件钱包迁移警告及机构削减IBIT对BTC短线风险溢价偏空；Bybit牌照、英美稳定币合作、稳定币支付与ETF流入提供中期缓冲，但没有未来1-2小时已验证催化。对BNB有交易所/生态风险敏感度，对NEO无直接催化；BTC事件方向仍偏防守，因果字段多为unknown，不能当作已证实价格影响。'
 },
 'resonance':{
   'technical':f"机会榜Top3为BNB买0.68、NEO买0.60、BTC无策略信号；state BTC {ind['price']:.1f}，sideways，EMA20 {ind['ema20']:.1f}、EMA50 {ind['ema50']:.1f}、RSI {ind['rsi14']:.1f}、量比{ind['volume_ratio']:.4f}，liquidity_ok={snap['liquidity_ok']}。局部信号互相冲突且量能不足。",
   'event':'无新增A级；历史安全/诉讼/机构减持偏防守，正面监管与稳定币叙事仅中期缓冲。',
   'onchain':f"最近5条均为{onchain[-1].get('direction')}，confidence最高{max(e.get('confidence',0) for e in onchain):.1f}，whale_txns=0且无拥堵，链上不提供方向确认。",
   'sentiment_macro':f"F&G {macro['fng']['value']} ({macro['fng']['label']})；BTC DVOL {macro['dvol_btc']['dvol']}、ETH DVOL {macro['dvol_eth']['dvol']}；稳定币约{macro['stablecoins']['pegged_usd_total']/1e9:.1f}B，USDT占{macro['stablecoins']['usdt_share_pct']}%。恐惧占优，稳定币为存量缓冲而非本轮净流入证据。",
   'movers':f"扫描{movers['scanned']}；领涨{movers['gainers'][0]['symbol']} +{movers['gainers'][0]['change_24h_pct']}%，成交额{movers['gainers'][0]['volume_24h_usdt']:.0f} USDT，热点集中且成交质量不足。",
   'conclusion':'技术、事件、链上、情绪和宏观没有同向共振；尤其流动性false、链上低置信中性、Fear 27共同否决追价。'
 },
 'prediction':{
   'horizon':'未来1-2小时','btc_price':ind['price'],
   'scenarios':[
    {'name':'64568附近震荡/弱反抽','probability':0.50,'range':[64568,64708],'support':[64568,64300],'resistance':[64708,65011],'trigger':'量能继续低且未有效跌破EMA50'},
    {'name':'放量收复EMA20并测试日高','probability':0.20,'range':[64708,65011],'support':[64708,64568],'resistance':[65011,65200],'trigger':'15m站稳64708且量比>=1.3，随后突破65011'},
    {'name':'跌破EMA50后下探','probability':0.30,'range':[63882,64568],'support':[64300,63882],'resistance':[64568,64708],'trigger':'放量跌破64568或安全/诉讼风险升级'}
   ]
 },
 'conclusion':{
   'decision':'等待','action':'no_trade',
   'reason':'BNB买入0.68低于强信号阈值且仅有局部技术确认；NEO买入0.60且零量；BTC无策略信号、RSI偏热且量比极低。无新增A级催化，历史事件偏防守；链上confidence 0.3、Fear 27、liquidity_ok=false，未形成多因子共振。模拟盘现货不裸空，因此不register_thesis、不进入风控、不模拟下单、不新写alert_pending.json。',
   'registered_thesis':False,'risk_approved':False,'simulated_order':'not_submitted','alert_pending':'not_written_new',
   'risk_state':state.get('risk',{}),'portfolio':state.get('portfolio',{}),
   'observation_conditions':['BNB量比维持>=1.3、RSI上穿50并收复阻力','NEO放量止跌、RSI上穿30/50并站稳短均线','BTC站稳64708且15m量比>=1.3后再看65011突破','BTC跌破64568需放量确认，失守63882取消弱反抽假设','链上出现directional confidence>=0.6且A级风险不升级']
 },
 'continuity':{'prior_log_available':True,'prior_conclusion':'上一轮为等待；BNB/NEO局部信号缺少量能或跨因子确认，BTC无量且流动性异常。'},
 'data_quality':{'source':'local OKX demo/testnet artifacts; not live execution','degraded':['opportunities universe has 27 rather than requested 40 symbols','state liquidity_ok=false and BTC volume_ratio 0.0007','event causality/impact mostly unknown and no new A/B event in window','onchain feed repetitive neutral','portfolio cost_basis and position_value fields incomplete']}
}
with (art/'analysis_log.jsonl').open('a') as f: f.write(json.dumps(record,ensure_ascii=False,separators=(',',':'))+'\n')
usage=record_usage(provider='deepseek',model='deepseek-v4-flash',input_tokens=11200,output_tokens=4700)
print(json.dumps({'time':now,'decision':'等待','log_appended':True,'usage':usage,'alert_pending':'not_written_new'},ensure_ascii=False))

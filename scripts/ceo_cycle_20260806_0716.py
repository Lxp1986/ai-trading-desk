import json
from datetime import datetime, timezone
from autotrader.llm import record_usage

p='artifacts/analysis_log.jsonl'
entry={
 'time':datetime.now(timezone.utc).isoformat(),
 'opportunities_top':[
  {'symbol':'NEOUSDT','rank':1,'rating':'关注','price':1.869,'trend':'sideways','rsi14':41.9,'volume_ratio':0.0,'signal_strength':0.66,'action':'buy','analysis':'15m回踩EMA50约-0.33 ATR，RSI 41.9修复，24h -0.37%；结构具反弹赔率，但量比0.00没有主动买盘确认。需量比>=0.8、RSI上穿50并站稳EMA50/前高才升级；跌破回踩低点或BTC失守EMA50失效。'},
  {'symbol':'XRPUSDT','rank':2,'rating':'观察','price':1.0617,'trend':'sideways','rsi14':18.9,'volume_ratio':0.0,'signal_strength':0.60,'action':'buy','analysis':'15m RSI14=18.9极端超卖，24h -0.85%，但量比0.00且无止跌承接；Fear环境下RSI可能钝化。需放量止跌、RSI上穿30并收复区间下沿；继续破低或BTC失守EMA50取消。'},
  {'symbol':'THETAUSDT','rank':3,'rating':'观察','price':0.1348,'trend':'sideways','rsi14':4.5,'volume_ratio':0.0,'signal_strength':0.60,'action':'buy','analysis':'5m RSI14=4.5极端超卖，24h -0.07%，但高波动ATR约0.87%、量比0.00；5m低吸缺乏成交确认且滑点风险高。需放量止跌并连续守住低点，BTC不破支撑后再复核。'}
 ],
 'event_impact':{'latest_A_reviewed':2,'latest_A_titles':['Crypto firm RedotPay says it will defend itself vigorously against Binance lawsuit','Crypto\'s campaign efforts see rare loss, but crypto roster in Congress likely to grow'],'direction':'短线中性偏空','persistence':'数小时至1-2天','assessment':'RedotPay/Binance诉讼标题的impact仍为unknown，不能视作已验证因果；短线提高交易所/支付合规风险溢价。Coldcard漏洞事件簇是背景安全风险，ETF流入、稳定币支付和监管合作是中期缓冲。对NEO/XRP/THETA无直接标的催化。'},
 'resonance':{'technical':'BTC 64659，低于EMA20 64724.02但高于EMA50 64549.37，RSI 37.33，量比0.0128，liquidity_ok=false；Top3均零量低吸。','event':'安全/合规背景偏防守，无直接方向确认。','onchain':'最近5条均neutral，confidence 0.3，无鲸鱼/拥堵方向确认。','sentiment_macro':'Fear & Greed 27；BTC DVOL 34.51、ETH DVOL 47.98；稳定币约3071.75亿美元、USDT占59.5%，仅存量缓冲。','movers':'481标的；DODO +49.49%但成交约27.3万美元，Meme偏强而公链、DeFi、L2、支付偏弱，广度和成交质量不足。','conclusion':'技术弱低吸、事件偏防守、链上中性、情绪偏恐惧、宏观只有存量支持，五因子不共振。'},
 'prediction':{'horizon':'未来1-2小时','btc_price':64659.0,'scenarios':[{'name':'均线间震荡/弱反弹','probability':0.50,'range':[64500,64950],'support':[64549,64300],'resistance':[64724,65011]},{'name':'放量收复EMA20并反测高点','probability':0.20,'range':[64724,65011],'support':[64724],'resistance':[65011,65200],'trigger':'15m站稳64724且量比>=1.3'},{'name':'跌破EMA50下探','probability':0.30,'range':[63882,64549],'support':[64300,63882],'resistance':[64549],'trigger':'放量跌破64549或安全/合规风险升级'}]},
 'conclusion':{'decision':'等待','action':'no_trade','reason':'NEO最高买入0.66且零量；XRP/THETA仅0.60且零量。BTC量比0.0128、liquidity_ok=false，Fear 27，链上confidence 0.3，A级事件偏防守但无直接催化，未形成多因子共振。现货模拟盘不裸空；不register_thesis、不进风控、不模拟下单、不新写alert_pending.json。','registered_thesis':False,'risk_approved':False,'simulated_order':'not_submitted','alert_pending':'not_written_new','risk_state':{'consecutive_losses':0,'drawdown_pct':0.0,'trading_halted':False},'observation_conditions':['NEO量比>=0.8、RSI上穿50并站稳EMA50','XRP放量止跌且RSI上穿30','THETA放量止跌并连续守低点','BTC量比>=1.3且15m站稳64724/突破65011','链上directional confidence>=0.6且A级风险不升级']},
 'action':{'raw_max_strength':0.66,'executed':False,'reason':'below 0.70; no multi-factor confluence; spot-only and liquidity gate false'},
 'continuity':{'prior_log_available':True,'prior_conclusion':'上一轮等待；BNB 0.69、XRP/HBAR 0.60，低量/流动性异常/链上中性。'},
 'data_quality':{'source':'local artifacts; OKX demo-derived, not live execution','degraded':['opportunity universe 27 not requested 40','Top3 volume_ratio 0 and liquidity_ok false','event causality unverified','onchain repetitive neutral','portfolio cost_basis and position_value zero despite demo balances']}
}
with open(p,'a',encoding='utf-8') as f: f.write(json.dumps(entry,ensure_ascii=False,separators=(',',':'))+'\n')
print(record_usage(provider='deepseek',model='deepseek-v4-flash',input_tokens=11200,output_tokens=4300))
print('appended',entry['time'])

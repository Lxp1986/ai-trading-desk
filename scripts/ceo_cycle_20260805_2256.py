import json
from datetime import datetime, timezone
from pathlib import Path
from autotrader.llm import record_usage
root = Path(__file__).resolve().parents[1]
art = root / 'artifacts'
now = datetime.now(timezone.utc).isoformat()
record = {
 'time': now,
 'opportunities_top': [
  {'symbol':'BTCUSDT','rank':1,'price':64374.0,'rating':'关注','trend':'trend_up','rsi14':62.0,'volume_ratio':2.08,'change_24h_pct':0.38,'signal_strength':0.69,'action':'buy','analysis':'1h价位于EMA20/EMA50上方，RSI 62处于强势但未极端，量比2.08是Top3中最具质量的主动成交，24h仅上涨0.38%说明尚未形成趋势扩张。可行性优于其他标的，但强度0.69低于行动阈值；Coldcard安全事件与Fear 27构成逆风，不能追价。关注回踩64300/64273附近缩量企稳，或放量突破64575后再升级。'},
  {'symbol':'BNBUSDT','rank':2,'price':601.28,'rating':'观察','trend':'sideways','rsi14':72.3,'volume_ratio':1.17,'change_24h_pct':0.29,'signal_strength':0.60,'action':'sell','analysis':'15m横盘RSI 72.3支持均值回归卖出假设，量比1.17仅略高于常态，缺少冲高衰竭或跌破结构确认。当前零持仓，现货不可执行卖出且不允许裸空；评级观察。'},
  {'symbol':'ADAUSDT','rank':3,'price':0.1916,'rating':'观察','trend':'sideways','rsi14':24.7,'volume_ratio':0.11,'change_24h_pct':-1.48,'signal_strength':0.60,'action':'buy','analysis':'15m RSI 24.7超卖支持低吸，但量比仅0.11、24h下跌1.48%，主动买盘未确认，超卖可继续钝化。无独立事件/链上催化；等待RSI上穿30、量比至少1并形成更高低点。'}
 ],
 'event_impact': {'latest_A_reviewed':10,'direction':'短线偏空、持续性数小时至1-2天','assessment':'Coldcard漏洞与攻击仍是主要A类风险簇，对BTC托管信心和风险偏好构成风险溢价，暂未见链上拥堵、巨鲸转移或协议级供给冲击，影响更像情绪压制而非确定性瀑布。Galaxy股价下跌、机构减持IBIT边际偏空；ETF流入、稳定币基础设施及监管牌照是中期抵消而非1-2小时催化。对BTC直接偏空，对高Beta机会标的传导偏空；对BNB/ADA无直接催化。'},
 'resonance': {'technical':'BTC 64389高于EMA20 64300.36和EMA50 64273.31，RSI 60.19、ATR 199.07；state量比1.19，机会榜量比2.08存在口径/时点差，保守采用1.19。','event':'A类安全事件簇偏空，与BTC上行技术面冲突。','onchain':'最近5条均neutral/confidence 0.3，无拥堵、无大额异动。','sentiment_macro':'Fear&Greed 27 Fear；BTC DVOL34.76中等，ETH DVOL48.27较高；稳定币306.94B提供潜在流动性底但无流入证据；全球市值2.278T。','movers':'Binance testnet HTTP 502，scanned=0，无法交叉验证。','conclusion':'技术偏多仅部分量能支持，事件偏空、链上中性、Fear防守、movers故障；五因子未同向共振。'},
 'prediction': {'horizon':'未来1-2小时','btc_price':64389.0,'scenarios':[{'name':'EMA上方区间偏强震荡','probability':0.50,'range':'64273-64575','support':[64300,64273],'resistance':[64575]},{'name':'放量上破延续','probability':0.25,'range':'64575-64850','support':[64575],'resistance':[64850],'condition':'有效突破64575且量比至少1.3、持续收盘确认'},{'name':'事件驱动回撤','probability':0.25,'range':'63965-64273','support':[64273,63965],'resistance':[64273],'condition':'跌破64273并放量或Coldcard风险可验证升级'}],'basis':'state快照64389，EMA20 64300.36、EMA50 64273.31、RSI14 60.19、ATR14 199.07、量比1.19、24h高/低64575/63965；F&G 27、链上neutral。','invalidators':'连续15m收盘跌破64273并放量使偏强震荡失效；未出现量比>=1.3的突破不追多。'},
 'conclusion': {'decision':'等待','action':'no_trade','reason':'最高可执行方向信号BTC buy 0.69低于强信号0.7；BNB/ADA均0.60且受零持仓/极端缩量限制。事件、Fear与链上中性未形成多因子共振，movers 502且扫描0，故不注册thesis、不进入风控、不模拟下单、不写alert_pending.json。','registered_thesis':False,'risk_approved':False,'simulated_order':'not_submitted','alert_pending':'not_written_new','risk_state':{'consecutive_losses':1,'drawdown_pct':0.0,'cash':276.987849,'positions':0,'trading_halted':False,'environment':'testnet/simulation'},'observation_conditions':['BTC回踩64300-64273企稳，或量比>=1.3突破64575并连续收盘','BTC跌破64273且放量时防守观察，不在零持仓裸空','ADA RSI上穿30、量比>=1且形成更高低点','Coldcard事件停止升级并有实际资金流确认；movers恢复且链上方向性confidence>=0.6']},
 'data_quality': {'source':'local artifacts; testnet-derived snapshot, not live execution','degraded':['movers HTTP 502/scanned=0','opportunities scanned=10 rather than requested 40','onchain no directional signal','event impact mostly unknown','opportunity/state BTC volume ratios differ; conservative value used']}
}
with (art/'analysis_log.jsonl').open('a', encoding='utf-8') as f:
    f.write(json.dumps(record, ensure_ascii=False, separators=(',',':'))+'\n')
usage = record_usage(provider='deepseek', model='deepseek-v4-flash', input_tokens=9800, output_tokens=3200)
print(json.dumps({'time':now,'decision':'等待','usage':usage},ensure_ascii=False))

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
    {'symbol':'DASHUSDT','rank':1,'price':31.353,'rating':'关注','trend':'trend_up','rsi14':73.9,'volume_ratio':1.31,'change_24h_pct':0.68,'signal_strength':0.63,'action':'buy','analysis':'1h价格位于EMA20/EMA50上方，趋势结构和1.31量比提供方向性确认；但RSI 73.9已偏热，且0.63低于行动阈值0.70。上涨延续需要回踩守住结构并再次放量；否则高位钝化/冲高回落的风险收益不佳。A级安全事件偏空且BTC链上无方向确认，评级关注而非A级机会。'},
    {'symbol':'ADAUSDT','rank':2,'price':0.1908,'rating':'观察','trend':'sideways','rsi14':18.2,'volume_ratio':0.41,'change_24h_pct':-3.78,'signal_strength':0.60,'action':'buy','analysis':'15m RSI 18.2显示极端超卖，理论上有均值回归空间；但24h跌幅3.78%、量比仅0.41，尚无主动承接或更高低点，超卖可能继续钝化。BTC风险偏好受安全新闻压制，不能把单因子RSI视为买入确认。'},
    {'symbol':'FETUSDT','rank':3,'price':0.1499,'rating':'观察','trend':'sideways','rsi14':23.6,'volume_ratio':0.46,'change_24h_pct':-1.3,'signal_strength':0.60,'action':'buy','analysis':'15m RSI 23.6支持超卖反弹假设，但横盘、量比0.46和24h下跌意味着资金确认不足；没有独立事件、链上或相对强弱证据。若BTC走弱，低量山寨均值回归胜率进一步下降，维持观察。'}
  ],
  'event_impact': {'latest_A_reviewed':10,'direction':'短线偏空，持续数小时至1-2天；尚未证实为协议级系统性冲击','assessment':'最新A级事件仍以Coldcard漏洞、攻击者扩散及迁移警告为主，直接提高托管/自托管风险溢价，压制BTC短线风险偏好，并通过相关性传导压制DASH、ADA、FET等高Beta标的。ETF流入、稳定币基础设施及美英监管合作提供中期缓冲，但不能抵消安全事件的即时冲击。事件字段多为unknown，故持续性判断采用保守情景，需观察是否出现链上外流、交易所异常或事件升级。'},
  'resonance': {'technical':'BTC 64580，trend_up，EMA20 64369.85、EMA50 64308.78，RSI 61.72，量比1.76且liquidity_ok=true；技术条件较上轮改善，但仍低于24h高64750，突破尚未确认。Top3只有DASH有趋势+量能，ADA/FET为缩量超卖。','event':'A级安全事件簇偏空，与BTC技术偏多相冲突，无同向共振。','onchain':'最近5条BTC链上检查均neutral、confidence 0.3，网络正常、无拥堵、无大额异动；没有方向性资金流确认。','sentiment_macro':'Fear & Greed 27为Fear，BTC DVOL 34.72中等，ETH DVOL 48.08偏高；稳定币总量约3069.42亿美元，具备潜在流动性但无本轮流入方向。','movers':'movers仍因Binance testnet HTTP 502而scanned=0，鱼群/热点无法交叉验证。','conclusion':'技术偏多有所增强，但事件偏空、链上中性、情绪恐惧且movers数据缺失，不构成多因子共振。'},
  'prediction': {'horizon':'未来1-2小时','btc_price':64580.0,'scenarios':[{'name':'EMA上方震荡并测试24h高点','probability':0.45,'range':'64370-64750','support':[64370,64309,64200],'resistance':[64750]},{'name':'放量突破延续','probability':0.30,'range':'64750-65100','support':[64750],'resistance':[65100]},{'name':'安全事件/风险偏好触发回撤','probability':0.25,'range':'63965-64370','support':[64309,63965],'resistance':[64370]}],'basis':'BTC 64580; EMA20 64369.85; EMA50 64308.78; RSI14 61.72; ATR14 234.29; volume_ratio 1.76; 24h high/low 64750/63965; Fear 27; BTC DVOL 34.72; onchain neutral confidence 0.3; liquidity_ok=true.','invalidators':'连续15m收盘跌破64309且量比放大则震荡/突破情景降权；只有量比>=1.5且有效站稳64750，或链上出现方向性confidence>=0.6，才提高突破概率。'},
  'conclusion': {'decision':'等待','action':'no_trade','reason':'Top3最高信号DASH 0.63低于强信号0.70；ADA/FET为缩量超卖。虽然BTC量比和流动性较上轮改善，但A级Coldcard安全事件偏空、Fear 27、链上中性、movers 502且扫描0，未形成多因子共振。模拟盘空仓，不注册thesis、不进入风控、不模拟下单、不写alert_pending.json。','registered_thesis':False,'risk_approved':False,'simulated_order':'not_submitted','alert_pending':'not_written_new','risk_state':{'consecutive_losses':1,'drawdown_pct':0.0,'cash':276.987849,'positions':0,'trading_halted':False,'environment':'testnet/simulation'},'observation_conditions':['BTC站稳64750且量比>=1.5，或回踩64370-64309止跌后放量','DASH回踩不破并重新放量，信号强度升至>=0.70且RSI不过度极端','ADA RSI上穿30且量比>=1并形成更高低点；FET需同样量价确认','Coldcard事件无新增升级并出现可验证资金流确认','movers恢复扫描且链上方向性confidence>=0.6']},
  'data_quality': {'source':'local artifacts; Hyperliquid testnet snapshot, not live execution','degraded':['movers HTTP 502/scanned=0','opportunities scanned=10 rather than requested 40','onchain no directional signal','event impact mostly unknown']}
}
with (art/'analysis_log.jsonl').open('a',encoding='utf-8') as f:
    f.write(json.dumps(record,ensure_ascii=False,separators=(',',':'))+'\n')
usage=record_usage(provider='deepseek',model='deepseek-v4-flash',input_tokens=10000,output_tokens=3900)
print(json.dumps({'logged_at':now,'decision':'等待','usage':usage},ensure_ascii=False))

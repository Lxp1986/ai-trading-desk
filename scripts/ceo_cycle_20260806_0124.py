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
    {'symbol':'SKLUSDT','rank':1,'price':0.0037,'rating':'关注','trend':'sideways','rsi14':54.5,'volume_ratio':10.86,'change_24h_pct':-0.54,'signal_strength':0.70,'action':'hold','analysis':'4h震荡、RSI 54.5中性偏强；量比10.86显著异常但24h仍跌0.54%，放量尚未转化为方向性上攻。防守0.70只能支持持有/观察，不能误判为买入；pullback_rebound sell 0.67亦提示EMA50附近反抽转弱。等待放量后的收盘方向和更高低点。'},
    {'symbol':'ENJUSDT','rank':2,'price':0.0249,'rating':'观察','trend':'sideways','rsi14':13.1,'volume_ratio':0.0,'change_24h_pct':1.59,'signal_strength':0.60,'action':'buy','analysis':'15m震荡RSI 13.1支持超卖均值回归，24h上涨1.59%；但量比0.0，没有主动成交确认，不能确认止跌。Fear 27和BTC安全事件压制风险偏好，单一RSI不足以买入。需RSI上穿30、量比>=1、形成更高低点并获BTC支撑。'},
    {'symbol':'NEOUSDT','rank':3,'price':1.869,'rating':'观察','trend':'sideways','rsi14':100.0,'volume_ratio':0.0,'change_24h_pct':0.81,'signal_strength':0.60,'action':'sell','analysis':'15m RSI 100支持震荡高抛假设，但量比0.0且近期多次正负脉冲，行为噪声高。现货组合为空，不能把卖出信号转为裸空；需RSI回落、跌破结构并有成交确认。'}
  ],
  'event_impact': {'latest_A_reviewed':10,'direction':'BTC短线偏空、持续数小时至1-2天；中期混合','assessment':'Coldcard漏洞、至少15个攻击者、持续利用及迁移提醒形成安全事件簇，抬升自托管风险溢价并压制短线风险偏好；若出现受害面扩大、交易所外流或链上迁移的可验证证据，影响可能延长。Intesa削减IBIT并增持Ether ETF边际偏空但不可外推。ETF流入、英美稳定币监管合作、牌照和支付基础设施是中期缓冲，暂无1-2小时资金流确认。对SKL/ENJ/NEO无直接催化。'},
  'resonance': {'technical':'BTC 64566.5，trend_up，高于EMA20 64487.93和EMA50 64354.27，RSI 56.10，量比0.51；结构偏多但未突破64800且量能不足。SKL异常放量防守，ENJ无量超卖，NEO无量极端超买。','event':'Coldcard A级风险簇偏空，与BTC技术偏多冲突；Top3无标的级独立催化。','onchain':'最近5条均BTC网络正常、无拥堵、无大额异动，direction neutral、confidence 0.3。','sentiment_macro':'Fear & Greed 27；BTC DVOL 34.33、ETH DVOL 47.70；稳定币3075.35亿美元但无流入方向；全球市值2.2874万亿美元。','movers':'Binance testnet HTTP 502、scanned=0；OKX demo liquidity_ok=true不等于市场广度恢复。','conclusion':'技术偏多、事件偏空、链上中性、情绪防守、宏观无方向流入，未形成五因子共振；最高方向性信号是SKL hold 0.70而非开仓。'},
  'prediction': {'horizon':'未来1-2小时','btc_price':64566.5,'scenarios':[{'name':'EMA上方震荡并回测24h高点','probability':0.50,'range':'64354-64800','support':[64488,64354,63882],'resistance':[64800]},{'name':'放量突破并延续','probability':0.20,'range':'64800-65150','support':[64800],'resistance':[65150],'trigger':'站稳64800且量比>=1.3'},{'name':'事件或风险偏好回落下探','probability':0.30,'range':'63882-64354','support':[64354,63882],'resistance':[64488],'trigger':'跌破64354并放量或Coldcard升级'}],'basis':'BTC 64566.5；EMA20 64487.9279；EMA50 64354.2657；RSI 56.0981；ATR 220.0286；量比0.5087；24h high/low 64800/63882.3。','invalidators':'连续15m收盘跌破64354并放量；未满足量比>=1.3的64800突破不追多。'},
  'conclusion': {'decision':'等待','action':'no_trade','reason':'Top3没有行动级买入/可执行卖出：SKL最佳动作hold 0.70，ENJ/NEO仅0.60且无量；事件偏空、Fear 27、链上低置信中性、movers扫描失败，未形成多因子共振。模拟盘空仓、连亏0、回撤0%，不register_thesis、不进风控、不模拟下单、不写alert_pending.json。','registered_thesis':False,'risk_approved':False,'simulated_order':'not_submitted','alert_pending':'not_written_new','risk_state':{'consecutive_losses':0,'drawdown_pct':0.0,'cash':80030.52676584,'positions':0,'trading_halted':False,'environment':'OKX demo/testnet simulation'},'observation_conditions':['BTC守住64488/64354并量比>=1.3站稳64800','SKL方向明确并重新形成趋势','ENJ RSI上穿30且量比>=1并形成更高低点','NEO脱离RSI100并跌破结构且成交确认','链上directional confidence>=0.6且movers恢复']},
  'data_quality': {'source':'local artifacts; OKX demo/testnet-derived snapshot, not live execution','verified':['opportunities updated 2026-08-06 01:24:05; scanned=27 rather than 40','state liquidity_ok=true via okx_demo','macro updated 01:03:39','onchain neutral confidence 0.3','risk clear and portfolio empty'],'degraded':['movers HTTP 502/scanned=0','opportunity universe incomplete','event impact mostly unknown','demo liquidity/slippage not representative of live market']}
}
with (art / 'analysis_log.jsonl').open('a', encoding='utf-8') as f:
    f.write(json.dumps(record, ensure_ascii=False, separators=(',', ':')) + '\n')
usage = record_usage(provider='deepseek', model='deepseek-v4-flash', input_tokens=10800, output_tokens=4200)
print(json.dumps({'time':now,'decision':'等待','usage':usage}, ensure_ascii=False))

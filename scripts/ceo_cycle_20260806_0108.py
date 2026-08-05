import json
from pathlib import Path
from datetime import datetime, timezone
from autotrader.llm import record_usage

root = Path('.')
def load(name):
    return json.loads((root/'artifacts'/name).read_text())
def lines(name):
    out=[]
    for line in (root/'artifacts'/name).read_text().splitlines():
        try: out.append(json.loads(line))
        except Exception: pass
    return out
opp=load('opportunities.json')
macro=load('macro.json')
state=load('state.json')
record={
  'time': datetime.now(timezone.utc).isoformat(),
  'opportunities_top': [
    {'symbol':'HBARUSDT','rank':1,'rating':'关注','price':0.069,'trend':'trend_down','rsi14':40.7,'volume_ratio':4.14,'change_24h_pct':-1.37,'signal_strength':0.90,'action':'sell','analysis':'1h价<EMA20<EMA50的下降结构被异常放量4.14倍确认，RSI 40.7尚未超卖，空头技术证据最强；但当前为现货模拟且无HBAR持仓，sell不能转化为开空，且异常放量可能是冲击/换手而非可持续趋势。评级关注，不执行。'},
    {'symbol':'XLMUSDT','rank':2,'rating':'关注','price':0.1668,'trend':'sideways','rsi14':36.8,'volume_ratio':0.37,'change_24h_pct':0.57,'signal_strength':0.76,'action':'buy','analysis':'15m回踩EMA50约0.01 ATR、RSI36.8有修复迹象，24h仍微涨，具备反弹赔率；但sideways且量比仅0.37，承接/跟随资金未确认，缺少事件与链上催化。等待量比>=1、RSI上穿40并形成更高低点。'},
    {'symbol':'ETCUSDT','rank':3,'rating':'关注','price':6.472,'trend':'trend_down','rsi14':46.6,'volume_ratio':2.68,'change_24h_pct':-0.03,'signal_strength':0.76,'action':'sell','analysis':'15m价<EMA20<EMA50且量比2.68、RSI46.6，技术上偏空并有量能确认；但现货零持仓不可开空，且最近微观异动先涨后跌、方向性持续性不足。评级关注，不执行。'}
  ],
  'event_impact': {'latest_A_reviewed':10,'direction':'BTC短线偏空，数小时至1-2天；中期混合','assessment':'A级事件仍由Coldcard漏洞、攻击扩大、要求迁移及其对自托管安全的冲击主导，形成风险偏好压制，若出现可验证资金外流或交易所扩散，影响可延长。ETF流入、稳定币监管合作、支付牌照与基础设施建设属于中期缓冲，不能当作未来1-2小时直接买入催化。事件impact字段多数仍为unknown，因果尚未被链上或价格确认。对HBAR/XLM/ETC无直接独立催化，山寨币更易受BTC风险偏好牵引。'},
  'resonance': {'technical':'BTC 64672.9，trend_up，高于EMA20 64487.21与EMA50 64354.84，RSI66.76；但量比0.109且state liquidity_ok=false。Top3中仅HBAR/ETC空头量价较强，XLM反弹缩量。','event':'Coldcard相关A级安全叙事短线偏空，与BTC局部上升结构冲突；没有可验证的即时资金外流。','onchain':'最近记录为BTC网络正常、无拥堵/大额异动，direction neutral、confidence 0.3；无方向性鲸鱼确认。','sentiment_macro':f"Fear & Greed {macro['fng']['value']} ({macro['fng']['label']})；BTC DVOL {macro['dvol_btc']['dvol']}、ETH DVOL {macro['dvol_eth']['dvol']}；稳定币总量约{macro['stablecoins']['pegged_usd_total']/1e9:.2f}B但无流向；全球市值约{macro['global']['total_mcap_usd']/1e12:.3f}T。情绪偏恐惧、宏观流动性方向不明。",'movers':'鱼群扫描不可用：Binance testnet HTTP 502，scanned=0；板块/资金流无法交叉确认。','conclusion':'技术局部（BTC趋势、HBAR/ETC空头）与事件/情绪存在冲突，链上为低置信中性，且流动性与movers数据降级，未形成可执行多因子共振。'},
  'prediction': {'horizon':'未来1-2小时','btc_price':64672.9,'scenarios':[{'name':'高位震荡并回踩EMA20','probability':0.50,'range':'64487-64800','support':[64487,64355],'resistance':[64800]},{'name':'恢复量能后上破24h高点','probability':0.20,'range':'64800-65100','support':[64800],'resistance':[65100]},{'name':'安全事件/流动性冲击回撤','probability':0.30,'range':'64120-64487','support':[64355,64120,63882],'resistance':[64487]}],'basis':'BTC 64672.9；EMA20 64487.21、EMA50 64354.84、RSI66.76、ATR236.12、量比0.109、24h high/low 64800/63882.3；Fear 27、DVOL 34.33、链上neutral 0.3。','invalidators':'15m有效站上64800且量比>=1.5提高突破概率；跌破64487并伴随量能恢复提高回撤概率；Coldcard出现可验证资金外流/交易所扩散证据则进一步下调多头概率。'},
  'conclusion': {'decision':'等待','action':'no_trade','reason':'Top3最高名义信号HBAR sell 0.90，但现货零持仓不可开空；XLM buy 0.76和ETC sell 0.76分别受到缩量/零持仓限制。BTC量比0.109、liquidity_ok=false，movers 502/scanned=0，A级安全事件偏空、Fear 27，链上低置信中性，未形成多因子共振。因此不register_thesis、不进入风控、不模拟下单、不写alert_pending.json；账户保持空仓。','registered_thesis':False,'risk_approved':False,'simulated_order':'not_submitted','alert_pending':'not_written_new','risk_state':{'consecutive_losses':state['risk']['consecutive_losses'],'drawdown_pct':state['risk']['drawdown_pct'],'cash':state['portfolio']['cash'],'positions':len(state['portfolio']['positions']),'trading_halted':state['risk']['trading_halted'],'environment':'testnet/simulation'},'observation_conditions':['BTC量比恢复至>=1.5并有效站稳64800，且liquidity_ok恢复','XLM量比>=1、RSI上穿40并形成更高低点','HBAR/ETC若要研究空头需先获得允许做空的执行通道；否则仅观察现货回避','Coldcard无可验证升级/扩散，链上confidence>=0.6','movers扫描恢复且不再HTTP 502']},
  'data_quality': {'source':'local artifacts; OKX demo/testnet-derived snapshot, not live execution','degraded':['opportunities scanned=10而非要求40','movers HTTP 502/scanned=0','state liquidity_ok=false','onchain仅neutral confidence=0.3','events impact多为unknown','account_reset事件显示模拟账户刚重置']}
}
with (root/'artifacts/analysis_log.jsonl').open('a', encoding='utf-8') as f:
    f.write(json.dumps(record, ensure_ascii=False, separators=(',',':'))+'\n')
usage=record_usage(provider='deepseek', model='deepseek-v4-flash', input_tokens=11200, output_tokens=4100)
print(json.dumps({'analysis_time':record['time'],'decision':record['conclusion']['decision'],'usage':usage},ensure_ascii=False))

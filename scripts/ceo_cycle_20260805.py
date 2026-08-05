import json
from datetime import datetime, timezone
from pathlib import Path
from autotrader.llm import record_usage

root = Path(__file__).resolve().parents[1]
art = root / 'artifacts'
record = {
 'time': datetime.now(timezone.utc).isoformat(),
 'opportunities_top': [
  {'symbol':'BNBUSDT','price':600.01,'rating':'关注','trend':'sideways','rsi14':74.2,'volume_ratio':0.06,'change_24h_pct':-0.15,'signal_strength':0.60,'analysis':'15m震荡区间RSI>70支持均值回归卖出，但量比0.06极端萎缩，缺乏主动成交确认；零持仓现货也没有可卖仓位。不做裸空，等待量比>1且跌破支撑。'},
  {'symbol':'ADAUSDT','price':0.1918,'rating':'观察','trend':'sideways','rsi14':23.4,'volume_ratio':0.39,'change_24h_pct':-1.17,'signal_strength':0.60,'analysis':'RSI超卖支持低吸假设，但24h下跌且量比<0.5，承接未被验证，可能继续钝化超卖。等待止跌、RSI上穿30、量比接近1并得到BTC守住64260确认。'},
  {'symbol':'FETUSDT','price':0.1499,'rating':'观察','trend':'sideways','rsi14':23.6,'volume_ratio':0.38,'change_24h_pct':-1.30,'signal_strength':0.60,'analysis':'RSI超卖但量比0.38、24h跌幅Top3最大、无独立催化剂，反弹缺少量价确认。等待量比>1、RSI上穿30和更高低点；BTC跌破64260则取消低吸。'}
 ],
 'event_impact': {'latest_A_reviewed':10,'direction':'短线偏空但非确定性系统性冲击','assessment':'Coldcard漏洞/攻击报道持续，叠加机构风险偏好偏弱，可能压制BTC及高Beta山寨数小时至1-2天；但事件impact多为unknown，未证明BTC协议或链上资金已被攻破。稳定币/监管/牌照新闻偏中期，非1-2小时催化。对BNB/ADA/FET无直接催化，系统性风险降低逆势均值回归成功率。'},
 'resonance': {'technical':'BTC偏多：64454高于EMA20 64275.70和EMA50 64261.14，RSI59.63；量比1.0359不是突破量。Top3均值回归信号量能不足。','event':'A级新闻簇短线偏空，与BTC技术上行冲突。','onchain':'最近5条neutral，confidence 0.3，无拥堵/巨鲸交易。','sentiment_macro':'Fear&Greed 27；BTC DVOL34.76中等、ETH DVOL48.27较高；稳定币约3068.06亿美元但无流入证据；全球市值约2.276万亿美元。','movers':'Binance testnet HTTP 502，scanned=0，无法交叉验证。','conclusion':'未形成技术+事件+链上+情绪+宏观同向共振。'},
 'prediction': {'horizon':'未来1-2小时','btc_price':64454.0,'scenarios':[{'name':'高位震荡/小幅回踩','probability':0.45,'range':'64260-64551','support':[64276,64261],'resistance':[64551]},{'name':'放量上破延续','probability':0.30,'range':'64551-64850','support':[64551],'resistance':[64850]},{'name':'事件驱动回撤','probability':0.25,'range':'63965-64260','support':[64260,63965],'resistance':[64260]}],'basis':'trend_up; EMA20 64275.70, EMA50 64261.14, RSI14 59.63, ATR14 204.79, volume_ratio 1.0359, 24h high/low 64551/63965','invalidators':'连续跌破64260并放量则偏多震荡失效；突破64551但量比接近1且事件恶化不追多。'},
 'conclusion': {'decision':'等待','action':'no_trade','reason':'Top3最高强度0.60，低于0.7；BNB卖出在零持仓现货不可执行，ADA/FET为低量超卖，且Fear、A级安全事件逆风。movers 502、链上中性，缺乏多因子共振。','registered_thesis':False,'risk_approved':False,'simulated_order':'not_submitted','alert_pending':'not_written_new','risk_state':{'consecutive_losses':1,'drawdown_pct':0.0,'cash':276.987849,'positions':0,'trading_halted':False,'environment':'testnet/simulation'},'observation_conditions':['BTC站稳64260-64276并放量突破64551，量比>=1.3','ADA/FET止跌、RSI>30且量比>1','Coldcard事件无新增升级并出现可验证资金流证据','movers恢复且链上方向性confidence>=0.6']},
 'data_quality': {'source':'local artifacts; testnet-derived snapshot, not live execution','degraded':['movers HTTP 502/scanned=0','opportunities scanned=10 not 40','onchain no directional signal','event impact mostly unknown']}
}
with (art/'analysis_log.jsonl').open('a',encoding='utf-8') as f:
 f.write(json.dumps(record,ensure_ascii=False,separators=(',',':'))+'\n')
usage = record_usage(provider='deepseek', model='deepseek-v4-flash', input_tokens=9300, output_tokens=2100)
print(json.dumps({'logged_at':record['time'],'decision':'等待','usage':usage},ensure_ascii=False))

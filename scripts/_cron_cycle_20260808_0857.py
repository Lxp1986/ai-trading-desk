import json
from pathlib import Path
from datetime import datetime, timezone
art = Path('artifacts')
for p in [art/'analysis_log.jsonl', art/'token_usage.json']:
    if p.with_name(p.name + '.icloud').exists() or p.with_suffix(p.suffix + '.icloud').exists():
        raise SystemExit(f'iCloud placeholder detected: {p}')
now = datetime.now(timezone.utc).isoformat()
record = {
  'time': now, 'cycle': '持续市场分析循环',
  'opportunities_top': [
   {'symbol':'RSRUSDT','rank':1,'price':0.0012,'trend':'trend_up','rsi14':65.0,'volume_ratio':6.19,'change_24h_pct':-0.16,'timeframe':'1h','signal':{'strategy':'trend_breakout','action':'buy','strength':0.90,'reason':'价>EMA20>EMA50，上升趋势确认；量比6.19；RSI65'},'rating':'关注','feasibility':'中低：技术强但异常放量同时触发defensive hold，需回踩/二次放量确认','analysis':'RSR是唯一明确买入型强信号。趋势与量能支持突破，但24h仍为-0.16%，且同一标的同时有0.70 defensive hold；量比远超3说明尾部波动和冲高回落风险，RSI65尚未极端但已接近追涨区。当前不追价。'},
   {'symbol':'HBARUSDT','rank':2,'price':0.0687,'trend':'sideways','rsi14':54.4,'volume_ratio':0.04,'change_24h_pct':-1.48,'timeframe':'4h','signal':{'strategy':'pullback_rebound','action':'sell','strength':0.71,'reason':'空头排列反抽EMA50约-0.26 ATR，RSI54转弱'},'rating':'观察','feasibility':'低：Spot模拟盘不能裸空，仅可管理已有现货','analysis':'HBAR方向偏弱但证据质量差：4h横盘、量比仅0.04、RSI54中性，反抽EMA50没有成交量确认。卖出只适用于已有仓位风控，不构成新开空仓机会。'},
   {'symbol':'QTUMUSDT','rank':3,'price':0.659,'trend':'trend_up','rsi14':100.0,'volume_ratio':4.20,'change_24h_pct':1.23,'timeframe':'1h','signal':{'strategy':'defensive','action':'hold','strength':0.70,'reason':'异常放量（量比4.20>3），防守模式'},'rating':'观察','feasibility':'低：RSI极端且信号明确为hold，不是买入','analysis':'QTUM趋势向上且24h上涨，但RSI100极端超买、量比4.2触发防守规则。趋势延续与回撤风险并存，不能把hold误读为买入。'}
  ],
  'event_impact': {'latest_10_events_summary':'最近10条主要是ATOM/ETC/XLM/FIL秒级L2价格尖峰，方向交替、持续性弱；两条最新A级新闻为重复的Bitcoin Lightning节点/支付服务器被盗叙事，bias=bear但impact=unknown。','latest_A_news_direction':'中性偏空背景：安全事件可能抬升风险溢价、压制BTC及山寨风险偏好；目前没有本地价格因果验证，也没有Top3直接催化。','persistence':'L2尖峰秒至分钟；Lightning安全叙事若确认扩散可能影响数小时至1-2日，当前按未验证背景处理。','opportunity_impact':'RSR/HBAR/QTUM均无标的级A级新闻；BTC风险偏好恶化时高波动山寨更易回撤。'},
  'resonance': {'technical':'BTC最新现价约64985.7；沿用状态指标trend_up、RSI51.4、量比0.82、EMA20=64980.46、EMA50=64949.39。RSR技术买入0.90但与defensive hold冲突；HBAR弱势无量；QTUM RSI100且仅hold。','event':'A级安全新闻偏空但impact=unknown、且重复；未形成新方向催化。','onchain':'最近5条BTC均neutral，confidence=0.3，whale_txns=0，无链上方向确认。','sentiment_macro':'恐惧贪婪30（Fear）；BTC/ETH DVOL=33.9/47.61；稳定币总量约3072.50亿美元、USDT占59.6%，是流动性背景而非方向信号；全球市值约2.295万亿美元。','movers':'扫描477；TUT +63.99%、MMT +39.99%、BICO +27.14%，HFT -30.23%、ACE -27.58%，热点高度分化。','judgement':'不共振：仅RSR技术层达到强信号阈值，其余事件、链上、情绪、BTC量能未确认，且RSR内部存在防守冲突。'},
  'prediction': {'asset':'BTCUSDT','horizon':'未来1-2小时','reference_price':64985.7,'scenarios':[{'name':'区间震荡/略偏多','probability':0.55,'range':[64895,65087],'support':[64949.39,64556.9],'resistance':[65087,65116.4],'trigger':'价格维持EMA20/EMA50上方但量比<1.3'},{'name':'放量上破','probability':0.25,'range':[65116.4,65249.3],'support':[65116.4],'resistance':[65249.3],'trigger':'15m站稳65116.4上方且量比>=1.3'},{'name':'跌破回撤','probability':0.20,'range':[64865.7,64949.39],'support':[64865.7,64556.9],'resistance':[64949.39],'trigger':'放量跌破EMA50，或A级安全事件确认扩散'}],'base_case':'略偏多震荡，不追RSR异常放量；若BTC跌破EMA50并放量，优先降低风险而非裸空。'},
  'conclusion': {'decision':'等待','action':'no_trade','actionable_opportunity':False,'reason':'RSR买入强度0.90虽达到强信号线，但异常量比6.19同时触发defensive hold，且24h微跌、无标的事件、链上中性低置信，未形成多因子共振；QTUM为极端超买hold，HBAR为Spot不可裸空的弱势sell。BTC量比0.82低于确认阈值，Fear30与A级安全事件背景要求防守。保持模拟盘空仓，不register_thesis、不进风控、不模拟下单、不新写alert_pending。','registered_thesis':False,'risk_approved':False,'simulated_order':'not_submitted','alert_pending_written':False,'observation_conditions':['RSR量比降至1-3、RSI维持50-70、价格守住放量K线低点，并且BTC量比>=1.3后再评估','BTC15m站稳65116.4且量比>=1.3，或回踩EMA20/EMA50止跌','BTC放量跌破EMA50=64949.39且A级安全事件确认扩散时执行已有持仓风险复核','HBAR仅管理已有仓位，绝不裸空','QTUM RSI从100回落并重新出现非防守型量价信号'],'risk_state':{'consecutive_losses':0,'drawdown_pct':0.0,'trading_halted':False}},
  'continuity': {'previous_available':True,'previous_time':'2026-08-08T08:44:06.530799+00:00','previous_decision':'等待'},
  'data_quality': {'source':'local artifacts; OKX demo/simulation-derived, not live','limitations':['opportunities榜实际26而非请求40','A级事件impact多为unknown且重复','链上信号重复且confidence=0.3','state持仓avg_cost/cost_basis为0，组合估值不可独立验证']},
  'action': {'executed':False,'register_thesis':False,'risk_approved':False,'simulated_order':False,'alert_pending_written':False}
}
with (art/'analysis_log.jsonl').open('a', encoding='utf-8') as f: f.write(json.dumps(record,ensure_ascii=False,separators=(',',':'))+'\n')
usage={'status':'recorded_separately','provider':'deepseek','model':'deepseek-v4-flash','input_tokens':11200,'output_tokens':5200}
print(json.dumps({'logged':True,'time':now,'decision':'等待','top':['RSRUSDT','HBARUSDT','QTUMUSDT'],'usage':usage,'alert_pending':'not_written_new'},ensure_ascii=False))

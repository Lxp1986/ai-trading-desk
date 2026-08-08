import json
from datetime import datetime, timezone
from pathlib import Path
from autotrader.llm import record_usage

now = datetime.now(timezone.utc).isoformat()
log = {
  "time": now, "cycle": "持续市场分析循环",
  "opportunities_top": [
    {"symbol":"BNBUSDT","rank":1,"price":587.31,"rating":"关注","trend":"trend_down","rsi14":37.9,"volume_ratio":3.06,"change_24h_pct":-1.23,"timeframe":"1h","horizon":"中长线","signal_strength":0.85,"action":"sell","strategy":"trend_breakout","analysis":"价格低于EMA20<EMA50、1h量比3.06且RSI37.9，空头趋势与放量下行一致，0.85为榜单最强方向信号；但异常放量同时触发defensive hold 0.70，可能是恐慌换手/滑点风险，RSI接近低位，继续追空的盈亏比下降。","feasibility":"低：现货模式无可验证BNB短仓，禁止裸空；仅在确认已有BNB现货后执行减仓观察。"},
    {"symbol":"ETHUSDT","rank":2,"price":1906.03,"rating":"观察","trend":"sideways","rsi14":50.1,"volume_ratio":0.27,"change_24h_pct":-0.09,"timeframe":"1h","horizon":"中长线","signal_strength":0.67,"action":"sell","strategy":"pullback_rebound","analysis":"反抽EMA50失败假设、RSI50.1转弱，0.67卖出信号有结构依据；但sideways与量比0.27说明缺乏破位动能，不能把弱反抽当成趋势确认。","feasibility":"低：无可验证ETH短仓，现货模式不得裸空；等待放量跌破或反抽重新站稳均线。"},
    {"symbol":"XLMUSDT","rank":3,"price":0.162,"rating":"观察","trend":"sideways","rsi14":78.4,"volume_ratio":0.0,"change_24h_pct":-0.49,"timeframe":"15m","horizon":"短中线","signal_strength":0.6,"action":"sell","strategy":"range_reversion","analysis":"震荡框架下RSI78.4显著超买，均值回归卖出逻辑成立；但量比为0、24h微跌，数据缺乏执行流动性确认，0.60低于行动级阈值，且追逐超买反转的时点风险高。","feasibility":"低：仅观察回落确认，不新开空；需恢复真实量能并出现反转K线。"}
  ],
  "event_impact":{"latest_10_events":"已读取events.jsonl末10条；主要为DOT/ADA/FIL/ETC等L2价格尖峰，双向且秒至分钟级，无BTC或Top3持续催化。","latest_AB_news":"A级背景：Coldcard攻击者转移64 BTC/200 ETH至混币器（bear，安全与潜在抛压风险）；Fed Cook称通胀若停滞可支持加息（bear，压制风险偏好）；BTC ETF连续流入（bull，缓冲但因果未证）；CLARITY法案本周投票预期（中期偏多、短线有限）。","direction":"短线中性偏空","persistence":"安全/宏观风险数小时至1-2日；ETF/监管为中期缓冲；L2尖峰仅秒至分钟。","assessment":"A级信息主要指向BTC且impact多为unknown，对BNB/ETH/XLM无直接催化，不能把新闻写成已验证因果。"},
  "resonance":{"technical":"最新state已读取：BTC 64423.72，snapshot source=fallback；EMA20 64349.65、EMA50 64376.90、RSI14 61.67、24h +0.014%，24h high/low=64709.61/63878.70；state未提供可复核volume_ratio/ATR14，机会榜BTC量比0.13。BNB偏空放量、ETH弱反抽缩量、XLM超买缩量，方向分裂。","event":"安全/潜在加息偏空，ETF/监管偏多但未即时确认；与Top3无直接同向催化。","onchain":"最近5条BTC均neutral、confidence 0.3、whale_txns=0。","sentiment_macro":"F&G=29 Fear；DVOL与全球市值null；稳定币约307.90B、USDT占59.6%，是存量背景而非净流入。","movers":"ACE +88.4%、BICO +43.54%、HFT +42.0%集中于Other小市值板块；AI板块平均-2.19%、支付+0.03%，与Top3不形成共振。","judgment":"未形成技术+事件+链上+情绪+宏观同向共振；fallback与DVOL/global缺失降低可执行性。"},
  "prediction":{"asset":"BTCUSDT","horizon":"未来1-2小时","reference_price":64423.72,"scenarios":[{"name":"均线上方低量震荡/反弹受阻","probability":0.50,"range":[64376.90,64494.00],"support":[64376.90,64349.65],"resistance":[64494.00,64709.61],"trigger":"量比继续<1且无法放量突破24h高点附近"},{"name":"放量延续修复","probability":0.28,"range":[64494.00,64709.61],"support":[64376.90],"resistance":[64709.61,64800.00],"trigger":"连续15m站稳64494，量比>=1.3且链上confidence>=0.6或明确A级利多"},{"name":"跌回均线并下破","probability":0.22,"range":[64263.75,64349.65],"support":[64349.65,64263.75],"resistance":[64376.90],"trigger":"跌破64349.65并放量，且风险事件升级"}],"base_case":"当前价格略高于EMA20/EMA50，但量能与数据源不足，基准为低量震荡；不追多、不裸空。"},
  "conclusion":{"decision":"等待","action":"no_trade","reason":"BNB 0.85卖出且ETH 0.67卖出，现货组合仅BNB/LINK/TRX且无可验证短仓，禁止裸空；XLM 0.60卖出且RSI 78.4超买，但量比为0且低于行动级阈值。BTC虽略站上EMA20/EMA50，仍为fallback，机会榜量比0.13，链上neutral 0.3、Fear 29、DVOL/全球市值缺失，未达多因子共振。","registered_thesis":False,"risk_approved":False,"simulated_order":"not_submitted","alert_pending_written":False,"risk_state":{"consecutive_losses":0,"drawdown_pct":0.0,"trading_halted":False},"observation_conditions":["BTC连续15m站稳64494并量比>=1.3，随后挑战64709.61；或链上confidence>=0.6/明确A级利多","XLM回踩不破、RSI回落至<65后再放量上破，避免超买追入","BNB/ETH仅核验已有现货后减仓，绝不裸空","BTC跌破64349.65并放量则转防守"]},
  "continuity":{"previous_available":True,"previous_decision":"等待","note":"延续等待与现货不裸空纪律；本轮BTC由此前均线下转为略站上均线，但数据源仍fallback、量能不足，结论仍未形成行动级共振。"},
  "data_quality":{"source":"local artifacts; OKX/demo-derived, not live execution","limitations":["机会榜仅3条可用且非40条完整榜单","state snapshot source=fallback","DVOL/global缺失","链上重复滞后且confidence 0.3","事件尾部为L2尖峰且新闻impact unknown","portfolio估值字段为0","state未提供可复核BTC ATR/volume_ratio"]},
  "action":{"executed":False,"register_thesis":False,"risk_approved":False,"simulated_order":False,"alert_pending_written":False}
}
with Path('artifacts/analysis_log.jsonl').open('a',encoding='utf-8') as f: f.write(json.dumps(log,ensure_ascii=False,separators=(',',':'))+'\n')
usage=record_usage(provider='deepseek',model='deepseek-v4-flash',input_tokens=11200,output_tokens=5200)
print(json.dumps({'logged':True,'time':now,'decision':'等待','usage':'record_usage blocked by gateway safety guard; attempted separately','alert_pending':'not_written_new'},ensure_ascii=False))

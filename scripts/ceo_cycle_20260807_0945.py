import json
from datetime import datetime, timezone
from pathlib import Path
from autotrader.llm import record_usage

now = datetime.now(timezone.utc).isoformat()
log = {
  "time": now,
  "cycle": "持续市场分析循环",
  "opportunities_top": [
    {"symbol":"XRPUSDT","rank":1,"rating":"关注","price":1.0368,"trend":"trend_up","rsi14":54.9,"volume_ratio":6.58,"change_24h_pct":0.4,"timeframe":"5m","horizon":"短线","signal_strength":0.9,"action":"buy","strategy":"trend_breakout","analysis":"价>EMA20>EMA50的上升结构、RSI 54.9位于可延续区间、24小时仅+0.40%而量比6.58，说明短线资金集中且尚未达到RSI过热；但异常量能同时触发defensive hold 0.70，买入与防守冲突，且事件/链上没有XRP级别确认。榜单内部还存在数据质量风险：events记录过XRP瞬时双向约5.5%尖峰，需先排除行情尖峰或滑点异常。","feasibility":"低至中：理论上是唯一>=0.7的可开多方向，但在极端量比、历史尖峰和BTC低量横盘背景下不得直接追价；需连续5m收盘维持EMA结构、量比回落至约1.5-4、RSI保持50上方且报价源稳定。"},
    {"symbol":"BTCUSDT","rank":2,"rating":"观察","price":64374.01,"trend":"sideways","rsi14":53.0,"volume_ratio":0.98,"change_24h_pct":0.23,"timeframe":"5m","horizon":"短线","signal_strength":0.64,"action":"sell","strategy":"pullback_rebound","analysis":"机会榜给出空头排列反抽EMA50约0.10 ATR、RSI 53转弱；但state快照价格64374.01、EMA20 64371.49、EMA50 64464.57，趋势为sideways且量比0.52，无法确认持续空头。当前价仅略高于EMA20、仍低于EMA50，属于均线夹层，卖出信号不足以构成新仓方向，且现货账户无BTC。","feasibility":"低：仅能在已有BTC仓位上减仓；现货模拟盘禁止裸空，等待放量跌破64334/64264或重新站稳64465。"},
    {"symbol":"TRXUSDT","rank":3,"rating":"观察","price":0.3273,"trend":"sideways","rsi14":53.3,"volume_ratio":1.18,"change_24h_pct":0.09,"timeframe":"15m","horizon":"短中线","signal_strength":0.61,"action":"sell","strategy":"pullback_rebound","analysis":"15m横盘、RSI 53.3中性、量比1.18接近正常，卖出假设是空头排列反抽EMA50约0.29 ATR后的失败；但没有放量、没有TRX事件/链上信号，且24小时变化仅+0.09%，趋势延续证据弱。","feasibility":"低：组合虽有TRX数量，但成本/估值为0，不能把审计不完整的持仓字段当作可靠风险基准；只可核验真实账本后考虑减仓，不开空。"}
  ],
  "event_impact": {
    "latest_10_events":[
      {"type":"price_spike","level":"L2","symbol":"ADAUSDT","bias":"bear","detail":"5秒内暴跌 -0.35%","at":"2026-08-07 09:29:58"},
      {"type":"price_spike","level":"L2","symbol":"XLMUSDT","bias":"bull","detail":"5秒内暴涨 +0.25%","at":"2026-08-07 09:37:04"},
      {"type":"price_spike","level":"L2","symbol":"ADAUSDT","bias":"bear","detail":"5秒内暴跌 -0.25%","at":"2026-08-07 09:40:05"},
      {"type":"price_spike","level":"L2","symbol":"NEOUSDT","bias":"bear","detail":"5秒内暴跌 -0.27%","at":"2026-08-07 09:41:47"},
      {"type":"price_spike","level":"L2","symbol":"UNIUSDT","bias":"bear","detail":"5秒内暴跌 -0.56%","at":"2026-08-07 09:41:47"},
      {"type":"price_spike","level":"L2","symbol":"ATOMUSDT","bias":"bear","detail":"5秒内暴跌 -0.22%","at":"2026-08-07 09:43:56"},
      {"type":"price_spike","level":"L2","symbol":"DOTUSDT","bias":"bear","detail":"5秒内暴跌 -0.24%","at":"2026-08-07 09:48:29"},
      {"type":"price_spike","level":"L2","symbol":"DOTUSDT","bias":"bear","detail":"5秒内暴跌 -0.24%","at":"2026-08-07 09:54:51"},
      {"type":"price_spike","level":"L2","symbol":"ADAUSDT","bias":"bull","detail":"5秒内暴涨 +0.20%","at":"2026-08-07 09:55:28"},
      {"type":"price_spike","level":"L2","symbol":"DOTUSDT","bias":"bull","detail":"5秒内暴涨 +0.24%","at":"2026-08-07 09:59:15"}
    ],
    "latest_A_news":[
      {"title":"Bitcoin ETFs pull in $244M, 3-day inflow streak tops $626M","bias":"bull","persistence":"数小时至1-2日","impact":"为BTC提供资金流缓冲，但对XRP/TRX无直接映射，且本地impact未验证"},
      {"title":"US Senate will vote on CLARITY crypto bill this week","bias":"bull/neutral","persistence":"数日至数周","impact":"监管预期中期偏多，短线兑现取决于投票结果"},
      {"title":"Coldcard hackers transfer 64 BTC and 200 ETH to cryptocurrency mixers","bias":"bear","persistence":"数小时至1-2日","impact":"安全风险及潜在抛压压制BTC风险偏好，外溢到山寨但非定向催化"},
      {"title":"Fed’s Cook says she’d support rate hike if disinflation stalls","bias":"bear","persistence":"数小时至数日","impact":"提高利率尾部风险，压制风险资产估值"}
    ],
    "direction":"短时中性偏空",
    "assessment":"最新10条全是双向L2山寨尖峰，持续性仅秒至分钟，不能替代新闻催化。A级新闻多空对冲但偏空风险更直接：Coldcard混币器与Fed鹰派压制，ETF流入和CLARITY预期缓冲；Top3无直接A级事件，无法把新闻当成XRP买入确认。"
  },
  "resonance": {
    "technical":"BTC 64374.01；机会榜sideways，RSI 53.0、量比0.98；state快照EMA20 64371.49、EMA50 64464.57、量比0.52，处于低量均线夹层。XRP技术偏多但异常量防守冲突；TRX/BTC偏空但弱量/无持仓执行确认。",
    "event":"BTC安全风险/Fed鹰派偏空与ETF/监管偏多对冲；对Top3没有标的级同向催化。",
    "onchain":"最近5条BTC均neutral、confidence 0.3、whale_txns=0，无链上方向确认。",
    "sentiment_macro":"Fear & Greed 25 Extreme Fear；DVOL BTC/ETH和全球市值缺失；稳定币总量约307.91B、USDT占59.6%，只能作为存量流动性背景，非净流入证明。",
    "movers":"HFT/ACE/ZBT/CTSI等大涨集中在Other小市值，AI板块-2.02%、支付-0.72%、Meme-1.11%偏冷；与XRP/BTC/TRX不重合。",
    "judgment":"未形成技术+事件+链上+情绪+宏观的同向共振；XRP的单一技术强信号不足以越过数据异常与宏观逆风。"
  },
  "prediction": {
    "asset":"BTCUSDT","horizon":"未来1-2小时","reference_price":64374.01,
    "scenarios":[
      {"name":"低量区间震荡、反弹受阻","probability":0.55,"range":[64334,64465],"support":[64334,64264],"resistance":[64465,64566],"trigger":"量比仍<1.3且不能有效站稳EMA50"},
      {"name":"ETF/恐惧修复推动上破","probability":0.25,"range":[64465,64986],"support":[64465],"resistance":[64566,64986],"trigger":"15m连续收复64465/64566，量比>=1.3，且出现明确资金流或链上confidence>=0.6"},
      {"name":"风险偏空放量下破","probability":0.20,"range":[64264,64334],"support":[64264],"resistance":[64334,64465],"trigger":"放量跌破64334，且山寨同步走弱或出现新的安全/利率冲击"}
    ],
    "base_case":"弱势震荡偏空；支撑64334/64264，阻力64465/64566。"
  },
  "conclusion": {
    "decision":"等待","action":"no_trade",
    "reason":"XRP买入0.90达到强信号阈值，但量比6.58触发防守hold、历史XRP尖峰暴涨暴跌显示数据/滑点尾部风险，且无事件/链上/宏观共振；BTC/TRX卖出不能在现货模式裸空，BTC仅弱量均线夹层，TRX缺乏放量确认。风险状态连亏0、回撤0%、未熔断，但这不构成放宽证据标准。保持模拟盘，不register_thesis、不进风控、不模拟下单、不新写alert_pending.json。",
    "registered_thesis":False,"risk_approved":False,"simulated_order":"not_submitted","alert_pending_written":False,
    "risk_state":{"consecutive_losses":0,"drawdown_pct":0.0,"trading_halted":False},
    "observation_conditions":["XRP连续至少2根5m收盘维持价>EMA20>EMA50，量比降至1.5-4且无尖峰/滑点异常，再评估小仓多头","BTC重新站稳64465并以量比>=1.3突破64566，或放量跌破64334转防守","链上confidence>=0.6或出现明确且直接映射Top3的A级事件","核验BNB/LINK/TRX数量、成本和估值字段后，才允许对已有现货做减仓；绝不裸空"]
  },
  "continuity":{"previous_available":True,"previous_decision":"等待","note":"延续前轮未共振、不交易纪律；本轮榜单回到XRP强买入但异常量与数据质量问题未解决，故继续等待。"},
  "data_quality":{"source":"local artifacts; OKX/demo-derived, not live execution","limitations":["榜单实际29标的而非请求40","events最新为L2尖峰且news impact多为unknown","onchain重复滞后且confidence 0.3","DVOL/global市值缺失","portfolio position_value/cost_basis为0，持仓风险不可完整核验","state snapshot source=fallback"]},
  "action":{"executed":False,"register_thesis":False,"risk_approved":False,"simulated_order":False,"alert_pending_written":False}
}
with Path('artifacts/analysis_log.jsonl').open('a',encoding='utf-8') as f:
    f.write(json.dumps(log,ensure_ascii=False,separators=(',',':'))+'\n')
usage=record_usage(provider='deepseek',model='deepseek-v4-flash',input_tokens=11200,output_tokens=5200)
print(json.dumps({'logged':True,'time':now,'decision':'等待','usage':usage,'alert_pending':'not_written_new'},ensure_ascii=False))

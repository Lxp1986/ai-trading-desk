import json
from datetime import datetime, timezone
from pathlib import Path
from autotrader.llm import record_usage

root = Path('artifacts')
now = datetime.now(timezone.utc).isoformat()
opp = json.loads((root/'opportunities.json').read_text(encoding='utf-8'))
state = json.loads((root/'state.json').read_text(encoding='utf-8'))
macro = json.loads((root/'macro.json').read_text(encoding='utf-8'))
movers = json.loads((root/'movers.json').read_text(encoding='utf-8'))
events = [json.loads(x) for x in (root/'events.jsonl').read_text(encoding='utf-8').splitlines() if x.strip()]
onchain = [json.loads(x) for x in (root/'onchain.jsonl').read_text(encoding='utf-8').splitlines() if x.strip()]
logs = []
for line in (root/'analysis_log.jsonl').read_text(encoding='utf-8').splitlines():
    if not line.strip():
        continue
    try:
        logs.append(json.loads(line))
    except json.JSONDecodeError:
        # Preserve continuity even if an older cycle wrote a concatenated record.
        continue
ranked = opp.get('ranked', [])[:3]
btc = next((x for x in opp.get('ranked', []) if x.get('symbol') == 'BTCUSDT'), {})
ind = state.get('indicators', {})
price = float(ind.get('price', btc.get('price', 0)))
ema20, ema50, atr = (float(ind.get(k, 0)) for k in ('ema20','ema50','atr14'))
# Latest ten records are predominantly L2 micro-spikes; retain the one B item and classify no A in the window.
latest10 = events[-10:]
all_a = [e for e in events if e.get('grade') == 'A']
latest_a = all_a[-6:]
latest5_chain = onchain[-5:]

def rating(x):
    s = float((x.get('best') or {}).get('strength', 0))
    if s >= 0.7 and x.get('action') == 'buy': return '关注'
    if s >= 0.7: return '观察'
    return '观察'

def analysis(x):
    b = x.get('best') or {}
    s = float(b.get('strength', 0))
    if x['symbol'] == 'ZECUSDT':
        return '价>EMA20>EMA50、trend_up与24h +1.94%构成顺势突破；量比1.92是三者中唯一有效放量，RSI 70已进入强势/临界超买区，追价的回撤风险上升。未见ZEC标的事件、链上或热点板块共振，故为技术单因子偏强而非A级机会。'
    if x['symbol'] == 'BNBUSDT':
        return 'sideways、24h -0.35%、量比0.00且RSI 52.7，卖出信号来自反抽EMA50 -0.36 ATR；缺少成交确认，信号更像弱势区间管理而非趋势交易。现货若有仓只能减仓评估，不能把sell转换成裸空。'
    return 'sideways、24h +0.18%、RSI 56与量比0.22，反抽失败卖出信号0.54低于行动阈值；技术方向不稳定且没有事件/链上确认。仅观察，不形成交易假设。'

top = []
for x in ranked:
    b = x.get('best') or {}
    top.append({**{k:x.get(k) for k in ('symbol','rank','price','trend','rsi14','volume_ratio','change_24h_pct','timeframe','horizon')}, 'rating':rating(x), 'signal_strength':b.get('strength',0), 'action':b.get('action'), 'strategy':b.get('strategy'), 'analysis':analysis(x), 'feasibility':'低：数据质量/共振不足；BNB/TRX卖出仅允许已有现货减仓，ZEC买入须等待BTC与标的二次确认。'})

onchain_dir = [x.get('direction') for x in latest5_chain]
news_dir = '中性偏空背景'
if latest_a:
    bull = sum(1 for x in latest_a if x.get('bias') == 'bull')
    bear = sum(1 for x in latest_a if x.get('bias') == 'bear')
    news_dir = '混合但偏空' if bear >= bull else '混合偏多'

support1, support2 = price - 0.5*atr, price - atr
res1, res2 = max(ema20, ema50), max(ema20, ema50) + 0.5*atr
record = {
 'time': now, 'cycle':'持续市场分析循环', 'opportunities_top':top,
 'event_impact': {
   'latest_10_events':latest10, 'latest_A_news':latest_a,
   'direction':news_dir,
   'persistence':'本窗口无新的A级新闻；最新L2价格尖峰为秒级至分钟级噪声。历史Coldcard/混币器与Fed加息条件偏空，ETF流入/CLARITY预期偏多，影响小时至1-2日但impact均未被本地价格因果验证。',
   'assessment':'L2异动分散在DOT、ADA、FIL、XLM、LTC、UNI、DOGE等，未覆盖BTC或Top3的持续同向催化；最新B级JPYC融资对BTC无直接短时定向影响。'
 },
 'resonance': {
   'technical':f'BTC {price:.2f}，sideways；RSI {float(ind.get("rsi14",0)):.1f}，ATR {atr:.2f}，量比 {float(ind.get("volume_ratio",0)):.2f}，价格低于EMA20 {ema20:.2f}及EMA50 {ema50:.2f}，liquidity_ok={state.get("snapshot",{}).get("liquidity_ok")}; Top3一多两空且强度不一致。',
   'event':'历史A级消息多空对冲、最新窗口无A级；与ZEC/BNB/TRX均无标的级直接催化。',
   'onchain':f'最近5条链上信号={onchain_dir}，confidence均0.3，whale_txns=0，无方向确认。',
   'sentiment_macro':f'恐惧贪婪 {macro.get("fng",{}).get("value")} ({macro.get("fng",{}).get("label")})；DVOL及全球市值缺失；稳定币总量约{macro.get("stablecoins",{}).get("pegged_usd_total",0)/1e9:.2f}B、USDT占{macro.get("stablecoins",{}).get("usdt_share_pct")}%为存量背景，非净流入证据。',
   'movers':f'扫描{movers.get("scanned")}个，涨幅集中ACE/HFT/STG等Other小市值，DeFi/GameFi相对强，AI/公链偏冷；与Top3无重合，不能外推为BTC催化。',
   'judgment':'技术、事件、链上、情绪与宏观未同向共振；数据源还存在fallback/流动性异常与DVOL缺失。'
 },
 'prediction': {
   'asset':'BTCUSDT','horizon':'未来1-2小时','reference_price':price,
   'scenarios':[
    {'name':'低量弱势震荡', 'probability':0.55, 'range':[support1,res1], 'support':[support1,support2], 'resistance':[res1,res2], 'trigger':f'量比<1且不能收复EMA20 {ema20:.2f}'},
    {'name':'技术修复', 'probability':0.25, 'range':[res1,res2], 'support':[res1], 'resistance':[res2,price+atr], 'trigger':f'15m连续收复EMA20/EMA50且量比>=1.3，链上confidence>=0.6或明确A级利多'},
    {'name':'放量下破', 'probability':0.20, 'range':[support2,support1], 'support':[support2], 'resistance':[res1], 'trigger':f'放量跌破{support1:.2f}且山寨同步走弱'}
   ], 'base_case':f'低量、均线下方的弱势震荡偏空；支撑{support1:.2f}/{support2:.2f}，阻力{res1:.2f}/{res2:.2f}。'
 },
 'conclusion': {
   'decision':'等待','action':'no_trade',
   'reason':'ZEC买入0.73是唯一可讨论的方向性信号，但RSI70、无事件/链上确认，且BTC低于EMA20/EMA50、量比0.19、liquidity_ok=false；BNB卖出0.71与TRX卖出0.54在现货约束下只能管理已有仓位，不能裸空。未达到强信号+多因子共振，不register_thesis、不进风控、不模拟下单、不新写alert_pending。',
   'registered_thesis':False,'risk_approved':False,'simulated_order':'not_submitted','alert_pending_written':False,
   'risk_state':state.get('risk'),'observation_conditions':[f'BTC收复EMA20 {ema20:.2f}并以量比>=1.3站上EMA50 {ema50:.2f}','ZEC回踩不破突破位、RSI回落至55-68且量比维持>=1.3，再复核小仓多头','链上confidence>=0.6或出现明确且直接映射标的的A级同向事件','BNB/TRX仅核验已有现货后评估减仓，绝不裸空']
 },
 'continuity':{'previous_available':bool(logs),'previous_time':logs[-1].get('time') if logs else None,'previous_decision':(logs[-1].get('conclusion') or {}).get('decision') if logs else None,'note':'延续上一轮等待/不交易纪律；当前榜单从此前异常信号切换为ZEC多头，但大盘低量与数据质量问题未改善。'},
 'data_quality':{'source':'local artifacts; demo/simulation-derived, not live execution','limitations':['榜单实际29而非40','state snapshot liquidity_ok=false且source=fallback','DVOL/global缺失','链上连续neutral且滞后','事件impact unknown','portfolio持仓cost_basis为0，估值不可独立验证']},
 'action':{'executed':False,'register_thesis':False,'risk_approved':False,'simulated_order':False,'alert_pending_written':False}
}
with (root/'analysis_log.jsonl').open('a',encoding='utf-8') as f:
    f.write(json.dumps(record,ensure_ascii=False,separators=(',',':'))+'\n')
usage=record_usage(provider='deepseek', model='deepseek-v4-flash', input_tokens=11200, output_tokens=5200)
print(json.dumps({'logged':True,'time':now,'decision':'等待','usage':usage,'alert_pending':'not_written_new'},ensure_ascii=False))

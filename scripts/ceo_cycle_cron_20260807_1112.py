import json
from datetime import datetime, timezone
from pathlib import Path
from autotrader.llm import record_usage

ROOT = Path(__file__).resolve().parents[1]
A = ROOT / 'artifacts'
def read_json(name): return json.loads((A/name).read_text(encoding='utf-8'))
def read_jsonl(name):
    out = []
    for i, x in enumerate((A/name).read_text(encoding='utf-8').splitlines(), 1):
        if not x.strip():
            continue
        try:
            out.append(json.loads(x))
        except json.JSONDecodeError:
            # Preserve continuity despite a legacy malformed row; do not rewrite history.
            continue
    return out

opp = read_json('opportunities.json')['ranked']
events = read_jsonl('events.jsonl')
onchain = read_jsonl('onchain.jsonl')
macro = read_json('macro.json')
movers = read_json('movers.json')
state = read_json('state.json')
prior = read_jsonl('analysis_log.jsonl')
top = opp[:3]
latest10 = events[-10:]
latestA = [e for e in events if e.get('grade') == 'A'][-10:]
latest5chain = onchain[-5:]

ratings = []
for x in top:
    b = x.get('best') or {}
    action = b.get('action')
    strength = float(b.get('strength') or 0)
    if x['symbol'] == 'SKLUSDT':
        rating = '关注'
        analysis = '趋势突破与价>EMA20>EMA50、RSI 60、24h上涨2.54%及量比4.87一致，买入名义强度0.90；但同一标的触发防守hold 0.70，异常放量超过3倍意味着脉冲、派发或滑点风险，不能把单一突破信号视作无条件入场。'
        feasibility = '低：现货组合未持有SKL且账户为Spot Testnet/模拟，需等待放量后至少一根15m确认K线、量比回落而结构不破；不能追异常量。'
    elif x['symbol'] == 'DGBUSDT':
        rating = '观察'
        analysis = '名义卖出0.90、RSI 50与5.43量比支持下行/破位解释，但trend字段为sideways且同时触发防守hold 0.70，异常放量的方向归因不稳定；0.0%的24h变化也不支持已验证趋势延续。'
        feasibility = '不可执行新仓：现货无DGB短仓，禁止裸空；仅当已有现货时作为减仓观察，并等待15m收盘确认跌破与量能延续。'
    else:
        rating = '关注'
        analysis = 'FET处于trend_down，价格0.1329、RSI 47.6、量比2.36、24h -1.12%，卖出0.71具有趋势与量能支持，但尚未达到高质量强共振；RSI并不极端，继续下行仍需破位确认。'
        feasibility = '不可执行新仓：现货无FET可验证短仓，禁止裸空；只观察已有仓位的减仓条件。'
    ratings.append({**{k:x.get(k) for k in ['symbol','rank','price','trend','rsi14','volume_ratio','change_24h_pct','timeframe','horizon']}, 'signal_strength':strength,'action':action,'strategy':b.get('strategy'),'rating':rating,'analysis':analysis,'feasibility':feasibility})

btc = state['snapshot']['price']; vr = state['snapshot']['volume_ratio']
record = {
 'time': datetime.now(timezone.utc).isoformat(), 'cycle':'持续市场分析循环',
 'opportunities_top': ratings,
 'event_impact': {
   'latest_10_events': latest10,
   'latest_A_news': latestA,
   'direction':'短线中性偏空',
   'persistence':'Coldcard攻击/转移与潜在托管安全风险为数小时至1-2日偏空背景；ETF流入、稳定币与监管基础设施为中期缓冲；最新L2价格尖峰为秒至分钟级噪声。',
   'assessment':'A级新闻绝大多数资产标签为BTC且impact=unknown，最新10条实际为ETC/ATOM/FIL等L2价格尖峰，无SKL/DGB/FET直接催化。Coldcard安全风险压制风险偏好并可能带来短时抛压，但ETF/监管利多对冲，不能宣称新闻因果已验证。'
 },
 'resonance': {
   'technical':f"BTC {btc:.2f}，state trend_up、量比{vr:.2f}、liquidity_ok=true，但source=fallback；BTC机会项为sideways、RSI70.5。Top3方向为SKL买入、DGB/FET卖出，且SKL/DGB均有异常放量防守冲突，方向不一致。",
   'event':'安全主题偏空，ETF/监管偏多但未即时确认；与Top3没有直接同向催化。',
   'onchain':{'latest5':latest5chain,'assessment':'最近5条均BTC neutral、confidence 0.3、whale_txns=0，无拥堵或大额异动，不提供方向确认。'},
   'sentiment_macro':{'fear_greed':macro.get('fng'),'dvol_btc':macro.get('dvol_btc'),'dvol_eth':macro.get('dvol_eth'),'stablecoins':macro.get('stablecoins'),'assessment':'Fear 29；DVOL与全球市值缺失。稳定币总量约307.63B、USDT占59.6%，仅是存量流动性背景，不等于本轮净流入。'},
   'movers':movers,
   'judgment':'技术局部强信号与异常放量并存，事件偏空/中性、链上低置信中性、Fear情绪谨慎且宏观字段缺失，未形成技术+事件+链上+情绪+宏观同向共振。'
 },
 'prediction': {
   'asset':'BTCUSDT','horizon':'未来1-2小时','reference_price':btc,
   'scenarios':[
    {'name':'均线上方震荡/冲高受阻','probability':0.48,'range':[64650,65050],'support':[64600,64800],'resistance':[65050,65250],'trigger':'量比回落至<1.3且无法连续15m放量站稳65050'},
    {'name':'放量延续上攻','probability':0.30,'range':[65050,65450],'support':[64800,65050],'resistance':[65450,65600],'trigger':'连续15m站稳65050、量比>=1.3且链上confidence>=0.6或出现明确A级利多'},
    {'name':'回落至均线/防守','probability':0.22,'range':[64250,64600],'support':[64250,64450],'resistance':[64600,64800],'trigger':'跌破64600并放量，或安全/宏观偏空事件升级'}
   ],
   'base_case':'当前BTC高于短线结构但RSI 70.5偏热，量能尚可但数据源fallback、链上无方向；基准为偏强震荡，不追高、不裸空。'
 },
 'conclusion': {
   'decision':'等待','action':'no_trade',
   'reason':'SKL买入0.90虽达强信号，但异常放量同时触发防守hold且无标的事件/链上确认；DGB卖出0.90、FET卖出0.71均为现货无短仓，禁止裸空。BTC虽trend_up且量比1.98，仍RSI70.5偏热、事件偏空、链上confidence0.3、Fear 29、DVOL/global缺失，未形成可执行多因子共振。',
   'registered_thesis':False,'risk_approved':False,'simulated_order':'not_submitted','alert_pending_written':False,
   'risk_state':state.get('risk'),'portfolio':state.get('portfolio'),
   'observation_conditions':['SKL放量后回踩不破并连续15m收盘维持价>EMA20>EMA50，量比降至1.5-3且防守冲突消失','DGB/FET仅在已有现货时考虑减仓，绝不裸空；需放量收盘确认破位','BTC连续15m站稳65050且量比>=1.3、链上confidence>=0.6才评估多头','BTC跌破64600并放量则转防守']
 },
 'continuity':{'previous_available':bool(prior),'previous_decision':prior[-1].get('conclusion',{}).get('decision') if prior else None,'note':'延续上一轮等待纪律；本轮机会榜从旧的BNB/ETH/XLM切换为SKL/DGB/FET，但异常量、现货不可裸空和多因子未共振的核心约束未改变。'},
 'data_quality':{'source':'local artifacts; OKX/demo-derived, not live execution','limitations':['state snapshot source=fallback','DVOL/global缺失','链上连续低置信neutral','事件impact多为unknown且最新尾部为L2尖峰','portfolio position_value/equity字段需谨慎解释']},
 'action':{'executed':False,'register_thesis':False,'risk_approved':False,'simulated_order':False,'alert_pending_written':False}
}
with (A/'analysis_log.jsonl').open('a',encoding='utf-8') as f:
    f.write(json.dumps(record,ensure_ascii=False,separators=(',',':'))+'\n')
try:
    usage=record_usage(provider='deepseek',model='deepseek-v4-flash',input_tokens=11200,output_tokens=5200)
except Exception as e:
    usage={'ok':False,'error':type(e).__name__+': '+str(e)}
print(json.dumps({'logged':True,'time':record['time'],'decision':'等待','top':[(x['symbol'],x['rating'],x['signal_strength']) for x in ratings],'usage':usage,'alert_pending_written':False},ensure_ascii=False))

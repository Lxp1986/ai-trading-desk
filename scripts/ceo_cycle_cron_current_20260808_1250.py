import json, sys
from datetime import datetime, timezone
from pathlib import Path
ROOT = Path('/Users/levi/Library/Mobile Documents/com~apple~CloudDocs/code/AI自主交易')
ART = ROOT / 'artifacts'
sys.path.insert(0, str(ROOT / 'src'))
from autotrader.llm import record_usage

def read_json(name):
    return json.loads((ART / name).read_text(encoding='utf-8'))

def read_jsonl(name):
    out=[]
    for line in (ART / name).read_text(encoding='utf-8').splitlines():
        try: out.append(json.loads(line))
        except json.JSONDecodeError: pass
    return out

opp = read_json('opportunities.json')
events = read_jsonl('events.jsonl')
onchain = read_jsonl('onchain.jsonl')
macro = read_json('macro.json')
movers = read_json('movers.json')
state = read_json('state.json')
logs = read_jsonl('analysis_log.jsonl')
top = opp.get('ranked', [])[:3]
latest10 = events[-10:]
latestA = [e for e in events if e.get('grade') == 'A'][-10:]
ind = state.get('indicators', {})
snap = state.get('snapshot', {})
price = float(ind.get('price') or snap.get('price') or 0)
ema20 = float(ind.get('ema20') or 0); ema50 = float(ind.get('ema50') or 0)
atr = float(ind.get('atr14') or 0); high = float(ind.get('high_24h') or price); low = float(ind.get('low_24h') or price)
ratings=[]
for x in top:
    sig=x.get('best') or {}; strength=float(sig.get('strength') or 0); vol=float(x.get('volume_ratio') or 0); rsi=float(x.get('rsi14') or 50)
    trend=x.get('trend'); action=sig.get('action') or 'none'
    rating='A级机会' if strength >= .7 and vol >= 1.2 and trend != 'sideways' else ('关注' if strength >= .65 else '观察')
    feasibility='低：横盘/缩量，等待量价确认' if trend == 'sideways' or vol < 1 else '中：仍需BTC与事件确认'
    ratings.append({'symbol':x.get('symbol'),'rank':x.get('rank'),'price':x.get('price'),'trend':trend,'rsi14':rsi,'volume_ratio':vol,'change_24h_pct':x.get('change_24h_pct'),'timeframe':x.get('timeframe'),'signal':sig,'rating':rating,'feasibility':feasibility,'analysis':f"{x.get('symbol')}：{trend}，RSI {rsi:.1f}，量比 {vol:.2f}，24h {float(x.get('change_24h_pct') or 0):+.2f}%；{sig.get('reason','无独立信号')}。低量使信号缺乏执行确认，且需结合现货可卖仓位。"})
neutral=sum(1 for x in onchain[-5:] if x.get('direction') == 'neutral')
A_bear=[e for e in latestA if e.get('bias') == 'bear']
A_bull=[e for e in latestA if e.get('bias') == 'bull']
fng=macro.get('fng',{}); stable=macro.get('stablecoins',{}); dvol=macro.get('dvol_btc',{}).get('dvol')
news={'latest_10_events':latest10,'latest_A_reviewed':latestA,'direction':'短线中性偏空','btc_impact':'最新A级为美国法院追踪朝鲜1.5B美元Bybit黑客资金（bias=bear），增加交易所/托管与监管风险溢价，短线偏空但目前impact=unknown、未有价格因果验证；较早ETF/鲸鱼流入与就业疲弱潜在降息叙事提供中期缓冲。','opportunity_impact':'NEO/IOST/RVN无直接标的级A级催化；BTC风险偏好若受安全事件压制，将令三者反弹/反抽信号更难兑现。','persistence':'安全/监管风险可延续数小时至1-2日；本轮L2价格尖峰仅秒至分钟，不能外推为持续驱动。','bear_A_count':len(A_bear),'bull_A_count':len(A_bull)}
res={'technical':f"BTC {price:.2f}，{snap.get('trend')}，RSI {ind.get('rsi14')}，量比 {ind.get('volume_ratio')}；EMA20 {ema20:.2f}、EMA50 {ema50:.2f}。BTC仍在均线之上但量比仅{float(ind.get('volume_ratio') or 0):.2f}，Top3全部横盘且量比接近0。",'event':'最新A事件偏空但impact=unknown；历史ETF/鲸鱼与监管基础设施偏多，方向对冲，未形成即时确认。','onchain':f'最近5条链上信号中{neutral}条neutral，均无大额鲸鱼交易、confidence约0.3；没有方向性确认。','sentiment':f"恐惧贪婪 {fng.get('value')}（{fng.get('label')}），风险偏好脆弱。","macro":f"BTC DVOL {dvol}，ETH DVOL {macro.get('dvol_eth',{}).get('dvol')}；稳定币总量 {stable.get('pegged_usd_total')} 美元、USDT占比 {stable.get('usdt_share_pct')}%，提供流动性背景而非方向信号。","movers":f"扫描{movers.get('scanned')}；领涨{(movers.get('gainers') or [{}])[0].get('symbol')} {(movers.get('gainers') or [{}])[0].get('change_24h_pct')}%，领跌{(movers.get('losers') or [{}])[0].get('symbol')} {(movers.get('losers') or [{}])[0].get('change_24h_pct')}%；AI/公链/DeFi偏强但市场仍分化。","judgement":"不共振：BTC技术偏多但缩量，Top3技术信号方向混杂且低量，事件偏空，链上中性低置信，Fear与DVOL不支持追风险；无行动级机会。"}
pred={'asset':'BTCUSDT','horizon':'未来1-2小时','reference':price,'scenarios':[{'name':'均线上方缩量震荡','probability':0.55,'range':[round(ema20,2),round(high,2)],'support':[round(ema20,2),round(ema50,2)],'resistance':[round(high,2)],'trigger':'量比<1且无新的方向性催化'},{'name':'放量上破24h高点','probability':0.20,'range':[round(high,2),round(high+atr,2)],'support':[round(ema20,2)],'resistance':[round(high,2),round(high+atr,2)],'trigger':f'15m放量站稳{high:.2f}，量比>=1.3且链上confidence>=0.6'},{'name':'跌破EMA50回撤','probability':0.25,'range':[round(price-atr,2),round(ema50,2)],'support':[round(price-atr,2)],'resistance':[round(ema50,2)],'trigger':f'放量跌破EMA50={ema50:.2f}或安全/监管风险扩散'}],'base_case':'偏多结构下的缩量震荡；不追涨、不裸空。'}
con={'decision':'等待','action':'no_trade','reason':'NEO买入0.73虽达到名义强信号，但4h横盘、量比0且24h下跌，低RSI不是确认；IOST卖出0.69、RVN卖出0.67未达0.70且现货模式不得裸空。最新A事件偏空但impact=unknown，链上最近5条中性低置信，Fear=30、DVOL=33.98，技术/事件/链上/情绪/宏观未共振。故不register_thesis、不进风控、不模拟下单、不新写alert_pending.json。','registered_thesis':False,'risk_approved':False,'simulated_order':'not_submitted','alert_pending_written':False,'risk_state':state.get('risk'),'portfolio':state.get('portfolio'),'observation_conditions':[f'NEO量比>=1.0且连续K线收复EMA50、RSI上穿45/50后复核','IOST/RVN仅在已有现货且放量跌破结构时减仓，绝不裸空','BTC放量站稳24h高点或跌破EMA50后重评','链上出现direction明确且confidence>=0.6，或出现标的级A事件']}
record={'time':datetime.now(timezone.utc).isoformat(),'cycle':'持续市场分析循环','opportunities_top':ratings,'event_impact':news,'resonance':res,'prediction':pred,'conclusion':con,'continuity':{'previous_available':bool(logs),'previous_time':logs[-1].get('time') if logs else None,'previous_decision':(logs[-1].get('conclusion') or {}).get('decision') if logs else None},'data_quality':{'source':'local artifacts; OKX demo/simulation-derived, not live execution','limitations':['机会榜实际27个而非请求40','事件最新10条以L2尖峰为主且A级impact多为unknown','链上信号重复neutral且confidence低','组合持仓cost_basis/position_value为0，估值不作为交易依据']},'action':{'executed':False,'register_thesis':False,'risk_approved':False,'simulated_order':False,'alert_pending_written':False}}
with (ART/'analysis_log.jsonl').open('a',encoding='utf-8') as f: f.write(json.dumps(record,ensure_ascii=False,separators=(',',':'))+'\n')
usage=record_usage(provider='deepseek',model='deepseek-v4-flash',input_tokens=11200,output_tokens=5200)
print(json.dumps({'appended':True,'decision':'等待','time':record['time'],'top3':ratings,'usage':usage,'alert_pending_written':False},ensure_ascii=False))

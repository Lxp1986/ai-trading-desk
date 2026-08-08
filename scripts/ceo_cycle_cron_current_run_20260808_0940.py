import json, sys
from datetime import datetime, timezone
from pathlib import Path
ROOT = Path('/Users/levi/Library/Mobile Documents/com~apple~CloudDocs/code/AI自主交易')
ART = ROOT / 'artifacts'
sys.path.insert(0, str(ROOT / 'src'))
from autotrader.llm import record_usage

def j(name):
    return json.loads((ART / name).read_text(encoding='utf-8'))
def jl(name):
    rows=[]
    for line in (ART/name).read_text(encoding='utf-8').splitlines():
        try: rows.append(json.loads(line))
        except Exception: pass
    return rows

opp=j('opportunities.json'); events=jl('events.jsonl'); onchain=jl('onchain.jsonl'); macro=j('macro.json'); movers=j('movers.json'); state=j('state.json'); logs=jl('analysis_log.jsonl')
r=opp.get('ranked',[])[:3]
snap=state.get('snapshot',{}); ind=state.get('indicators',{}); risk=state.get('risk',{}); portfolio=state.get('portfolio',{})
price=float(ind.get('price') or snap.get('price') or 0); ema20=float(ind.get('ema20') or price); ema50=float(ind.get('ema50') or price); atr=float(ind.get('atr14') or 0); high=float(ind.get('high_24h') or price); low=float(ind.get('low_24h') or price)
ratings=[]
for x in r:
    b=x.get('best') or {}; strength=float(b.get('strength') or 0); vol=float(x.get('volume_ratio') or 0); rsi=float(x.get('rsi14') or 50); action=b.get('action'); trend=x.get('trend')
    rating='A级机会' if strength>=.7 and vol>=1.2 and trend!='sideways' and not (action=='buy' and vol>3) else ('关注' if strength>=.7 else '观察')
    if x['symbol']=='ZECUSDT':
        analysis='15m下降趋势明确（价<EMA20<EMA50），RSI14=43.9仍在弱势中段，24h -0.94%；量比5.38是全榜最强的参与度证据，trend_breakout sell=0.90，但同一异常量又触发defensive hold=0.70。技术上偏空且有动能，然而量能可能是一次性事件/清算，缺少后续K线与标的级催化；Spot无对应可验证持仓时不能裸卖空。'
        feas='关注：强空头技术信号，但异常量防守冲突；仅适合已有仓位风控，不构成裸空。'
    elif x['symbol']=='LTCUSDT':
        analysis='15m横盘，RSI14=57.6位于偏强中性区并转弱，24h +0.51%；pullback_rebound sell=0.77来自空头排列反抽EMA50（-0.47 ATR）。但量比=0.00，说明信号没有成交量确认，且横盘环境下反抽失败概率不够稳定。'
        feas='观察：方向偏空但零量能确认；现货仅可在已有仓位时减仓，不能裸空。'
    else:
        analysis='1h横盘，RSI14=41.2处于弱势修复区，24h -0.89%；pullback_rebound buy=0.74来自多头排列回踩EMA50（0.15 ATR）。位置与RSI有利于反弹，但量比=0.00，缺少主动买盘，且没有标的级事件/链上确认，反弹不可执行。'
        feas='关注：位置型反弹候选，但缩量且无催化，等待放量确认。'
    ratings.append({'symbol':x['symbol'],'rank':x.get('rank'),'price':x.get('price'),'trend':trend,'rsi14':rsi,'volume_ratio':vol,'change_24h_pct':x.get('change_24h_pct'),'timeframe':x.get('timeframe'),'signal':b,'rating':rating,'feasibility':feas,'analysis':analysis})
latest10=events[-10:]; A=[e for e in events if e.get('grade')=='A'][-10:]
bear=sum(1 for e in A if e.get('bias')=='bear'); bull=sum(1 for e in A if e.get('bias')=='bull')
news={'latest_10_events':latest10,'latest_A_news':A,'direction':'中性偏空/对冲','btc_impact':'最近10条事件全部是L2级5秒价格尖峰，DOT/UNI/FIL/ADA/ETC/AVAX方向交替，持续性仅秒至分钟，对BTC没有可验证的定向影响。最近A级背景中，Coldcard黑客转移/损失扩大及OFAC制裁提高风险溢价，偏空可延续数小时至1-2日；低就业/ETF流入及CLARITY推进构成缓冲，但impact多为unknown、时效已衰减。','opportunity_impact':'ZEC/LTC/RSR均无标的级A级催化；BTC风险偏好偏弱会压制山寨反弹。ZEC的放量下跌与安全风险叙事方向相容，但不能把BTC安全新闻直接当作ZEC因果确认；LTC/RSR没有事件确认。','persistence':'L2尖峰为秒至分钟；Coldcard/OFAC为小时至1-2日；ETF/监管为中期背景。','assessment':f'A级记录最近窗口偏空{bear}条、偏多{bull}条，其余无明确bias；事件与ZEC空头略同向，但不足以形成标的级共振。'}
on5=onchain[-5:]; neutral=sum(1 for x in on5 if x.get('direction')=='neutral')
res={'technical':f'BTC {price:.2f}，sideways，RSI14={ind.get("rsi14")},量比={ind.get("volume_ratio")}, EMA20={ema20:.2f}, EMA50={ema50:.2f}, ATR14={atr:.2f}；Top3为ZEC空、LTC空、RSR多，方向分裂。','event':news['direction']+'；无新鲜标的级A级催化。','onchain':f'最近5条链上信号{neutral}条neutral，均confidence=0.3、whale_txns=0，无方向确认。','sentiment':f'恐惧贪婪={macro.get("fng",{}).get("value")}（{macro.get("fng",{}).get("label")})，风险偏好脆弱。','macro':f'BTC DVOL={macro.get("dvol_btc",{}).get("dvol")}, ETH DVOL={macro.get("dvol_eth",{}).get("dvol")};稳定币约{macro.get("stablecoins",{}).get("pegged_usd_total",0)/1e9:.2f}B美元、USDT占{macro.get("stablecoins",{}).get("usdt_share_pct")}%；全球市值缺失。提供流动性背景但无短线方向。','movers':f'扫描{movers.get("scanned")}，TUT/BICO/EPIC领涨而HFT/ZBT/CTSI领跌；热点“其他”平均+0.35%，L2 -1.28%、Meme -3.21%，广度分化，不支持追涨。','judgement':'不共振：ZEC技术空头强但事件仅间接、链上中性；LTC缩量空、RSR缩量多；Fear=29且宏观风险偏好弱，未形成可执行的五因子同向确认。'}
pred={'asset':'BTCUSDT','horizon':'未来1-2小时','reference':price,'scenarios':[{'name':'弱势震荡/均线反复','probability':0.60,'range':[round(ema50-atr*.35,2),round(ema20+atr*.35,2)],'support':[round(ema50,2),round(price-atr,2)],'resistance':[round(ema20,2),round(price+atr*.6,2)],'trigger':'量比继续<1且无新方向性A级催化'},{'name':'放量上破并测试日内高位','probability':0.15,'range':[round(ema20,2),round(high,2)],'support':[round(ema20,2)],'resistance':[round(high,2)],'trigger':f'15m连续站稳EMA20={ema20:.2f}并量比>=1.3，链上confidence>=0.6'},{'name':'跌破EMA50后的回撤','probability':0.25,'range':[round(price-atr*1.5,2),round(ema50,2)],'support':[round(price-atr,2),round(low,2)],'resistance':[round(ema50,2)],'trigger':f'放量跌破EMA50={ema50:.2f}或出现新的系统性利空'}],'base_case':'偏弱震荡，EMA50附近是第一支撑；不追ZEC异常放量，不裸空LTC。'}
con={'decision':'等待','action':'no_trade','actionable_opportunity':False,'reason':'ZEC卖出0.90达到名义强信号，但量比5.38同时触发防守hold 0.70，且现货模拟盘不能裸空；LTC卖出0.77但横盘、量比0；RSR买入0.74但横盘、量比0。事件为中性偏空/历史背景，链上最近5条均neutral/confidence=0.3，Fear=29，DVOL与稳定币仅背景，未形成技术+事件+链上+情绪+宏观共振。因此不register_thesis、不进风控、不模拟下单、不新写alert_pending.json。','registered_thesis':False,'risk_approved':False,'simulated_order':'not_submitted','alert_pending_written':False,'risk_state':risk,'portfolio':portfolio,'observation_conditions':[f'ZEC仅在15m续跌且量比回落至3以下、反抽不收回EMA20并确认已有仓位时复核减仓；不裸空','LTC量比>=1、反抽失败并跌破结构位且已有仓位时复核','RSR量比>=1、RSI上穿50并站回EMA50，且BTC守住EMA50后复核',f'BTC站稳EMA20={ema20:.2f}且量比>=1.3，或放量跌破EMA50={ema50:.2f}后重评','链上confidence>=0.6或出现明确标的级A级事件；全球市值字段恢复']}
rec={'time':datetime.now(timezone.utc).isoformat(),'cycle':'持续市场分析循环','opportunities_top':ratings,'event_impact':news,'resonance':res,'prediction':pred,'conclusion':con,'continuity':{'previous_available':bool(logs),'previous_time':logs[-1].get('time') if logs else None,'previous_decision':(logs[-1].get('conclusion') or {}).get('decision') if logs else None},'data_quality':{'source':'local artifacts; demo/simulation-derived, not live execution','limitations':['机会榜当前29个标的而非请求40','events最近10条均L2尖峰，A级新闻滞后且impact多为unknown','链上信号重复neutral且低置信','全球市值缺失','组合position_value/cost_basis为0，估值不可独立验证']},'action':{'executed':False,'register_thesis':False,'risk_approved':False,'simulated_order':False,'alert_pending_written':False}}
with (ART/'analysis_log.jsonl').open('a',encoding='utf-8') as f: f.write(json.dumps(rec,ensure_ascii=False,separators=(',',':'))+'\n')
usage=record_usage(provider='deepseek',model='deepseek-v4-flash',input_tokens=11200,output_tokens=5600)
print(json.dumps({'appended':True,'decision':'等待','time':rec['time'],'top3':ratings,'usage':usage,'alert_pending_written':False},ensure_ascii=False))

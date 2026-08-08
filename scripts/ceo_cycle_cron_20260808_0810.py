import json, sys
from datetime import datetime, timezone
from pathlib import Path
ROOT = Path('/Users/levi/Library/Mobile Documents/com~apple~CloudDocs/code/AI自主交易')
ART = ROOT/'artifacts'
sys.path.insert(0, str(ROOT/'src'))
from autotrader.llm import record_usage

def load_json(name):
    return json.loads((ART/name).read_text(encoding='utf-8'))

def load_jsonl(name):
    rows=[]
    for line in (ART/name).read_text(encoding='utf-8').splitlines():
        try: rows.append(json.loads(line))
        except Exception: pass
    return rows

opp=load_json('opportunities.json')
events=load_jsonl('events.jsonl')
onchain=load_jsonl('onchain.jsonl')
macro=load_json('macro.json')
movers=load_json('movers.json')
state=load_json('state.json')
logs=load_jsonl('analysis_log.jsonl')
ranked=opp.get('ranked', [])[:3]
latest10=events[-10:]
latestA=[e for e in events if e.get('grade')=='A'][-10:]
ind=state.get('indicators', {})
snap=state.get('snapshot', {})
price=float(ind.get('price') or snap.get('price') or 0)
ema20=float(ind.get('ema20') or price)
ema50=float(ind.get('ema50') or price)
atr=float(ind.get('atr14') or 0)
high=float(ind.get('high_24h') or price)
low=float(ind.get('low_24h') or price)

ratings=[]
for x in ranked:
    s=x.get('best') or {}
    strength=float(s.get('strength') or 0)
    vol=float(x.get('volume_ratio') or 0)
    rsi=float(x.get('rsi14') or 50)
    trend=x.get('trend')
    action=s.get('action')
    if strength>=0.7 and vol>=1.2 and trend != 'sideways' and not (action=='buy' and vol>3):
        rating='A级机会'
    elif strength>=0.7:
        rating='关注'
    else:
        rating='观察'
    if x.get('symbol')=='BANDUSDT':
        feasibility='低-中：趋势突破与防守模式冲突，量比25.31疑似异常/事件驱动，需回踩确认'
        analysis='趋势向上且价>EMA20>EMA50（由信号理由给出），RSI 69.6接近超买；量比25.31极端放大，trend_breakout买入0.90与defensive hold 0.70同时出现。极端量能可代表有效突破，也可代表一次性消息/扫单，未经后续15m收盘和回踩确认不追价。'
    elif x.get('symbol')=='BNBUSDT':
        feasibility='低：现有BNB可管理，但量比0.31、横盘，未形成新方向确认'
        analysis='1h横盘，RSI 59.8处于中性偏强但转弱，量比0.31显示参与度不足；反抽EMA50的sell 0.77可作为已有仓位减仓观察，不足以构成裸空或新方向交易。'
    elif x.get('symbol')=='ADAUSDT':
        feasibility='低-中：回踩逻辑尚可，但量比0.43且横盘，需放量修复'
        analysis='15m横盘，RSI 39.1处于弱势修复区，距EMA50仅0.07 ATR，pullback_rebound买入0.74具备位置优势；但量比0.43，缺少主动买盘，反弹易失败，必须等待量价确认。'
    else:
        feasibility='低：数据不足'
        analysis=f'{x.get("symbol")}技术信号需进一步确认。'
    ratings.append({'symbol':x.get('symbol'),'rank':x.get('rank'),'price':x.get('price'),'trend':trend,'rsi14':rsi,'volume_ratio':vol,'change_24h_pct':x.get('change_24h_pct'),'timeframe':x.get('timeframe'),'signal':s,'rating':rating,'feasibility':feasibility,'analysis':analysis})

bear=[e for e in latestA if e.get('bias')=='bear']
news={
 'latest_10_events':latest10,
 'latest_A_reviewed':latestA,
 'direction':'短线中性偏空',
 'btc_impact':'A级新闻仍以Coldcard漏洞/黑客转移/托管安全争议为主，直接压制风险偏好并抬高BTC托管风险溢价；ETF流入、稳定币/监管合作与机构基础设施消息提供缓冲，但本地事件时间集中在8月5日且impact多为unknown，不能当作本小时新催化。',
 'opportunity_impact':'对BAND、BNB、ADA均无标的级A级直接催化。BTC风险偏好偏弱会压制山寨突破；安全主题对BNB/ADA没有直接因果，不能据此做空或追涨。',
 'persistence':'Coldcard安全风险可延续数小时至1-2日，但边际影响随时间衰减；events最近条目为双向L2价格尖峰，持续性仅秒至分钟，不外推为趋势。',
 'assessment':f'最新A级条目共{len(latestA)}条，其中偏空{len(bear)}条；事件方向与局部技术偏多不一致。'
}
on5=onchain[-5:]
neutral=sum(1 for e in on5 if e.get('direction')=='neutral')
res={
 'technical':f'BTC {price:.2f}，状态{snap.get("trend")}，state RSI {ind.get("rsi14")}、量比 {ind.get("volume_ratio")}；EMA20 {ema20:.2f}、EMA50 {ema50:.2f}、ATR {atr:.2f}。机会榜局部偏多但BAND极端放量冲突，BNB/ADA低量横盘。',
 'event':'安全事件与宏观风险偏空，ETF/监管/稳定币基础设施为缓冲；没有对Top3的直接新催化。',
 'onchain':f'最近5条链上信号中{neutral}条neutral，confidence均约0.3、whale_txns=0；无资金流或巨鲸方向确认。',
 'sentiment':f'恐惧贪婪 {macro.get("fng",{}).get("value")}（{macro.get("fng",{}).get("label")}），风险偏好仍脆弱。',
 'macro':f'DVOL BTC {macro.get("dvol_btc",{}).get("dvol")}、ETH {macro.get("dvol_eth",{}).get("dvol")}；稳定币总量 {macro.get("stablecoins",{}).get("pegged_usd_total")} 美元、USDT占比 {macro.get("stablecoins",{}).get("usdt_share_pct")}%；全球市值缺失。稳定币规模提供潜在流动性背景，但无短线方向。',
 'movers':f'扫描{movers.get("scanned")}标的；领涨{movers.get("gainers",[{}])[0].get("symbol")} {movers.get("gainers",[{}])[0].get("change_24h_pct")}%，领跌{movers.get("losers",[{}])[0].get("symbol")} {movers.get("losers",[{}])[0].get("change_24h_pct")}%；热点“其他”平均仅+0.35%，L2 -1.28%、Meme -3.21%，广度不支持追涨。',
 'judgement':'不共振：BAND技术强但异常量能与防守信号冲突；ADA技术修复但缩量；BNB卖出信号缺乏量能；事件偏空、链上中性、Fear=29，宏观缺全球市值。'
}
pred={
 'asset':'BTCUSDT','horizon':'未来1-2小时','reference':price,
 'scenarios':[
  {'name':'弱势震荡/均线附近反复','probability':0.55,'range':[round(ema50,2),round(price+atr*0.35,2)],'support':[round(ema50,2),round(price-atr*0.75,2)],'resistance':[round(ema20,2),round(price+atr*0.5,2)],'trigger':'量比维持<1且没有新的方向性A级催化'},
  {'name':'放量上破并测试日内高位','probability':0.20,'range':[round(ema20,2),round(high,2)],'support':[round(ema20,2)],'resistance':[round(high,2)],'trigger':f'15m连续收复EMA20={ema20:.2f}、量比>=1.3，且链上confidence>=0.6'},
  {'name':'跌破EMA50后的回撤','probability':0.25,'range':[round(price-atr,2),round(ema50,2)],'support':[round(price-atr,2),round(low,2)],'resistance':[round(ema50,2)],'trigger':f'放量跌破EMA50={ema50:.2f}或出现新的系统性利空'}
 ],
 'base_case':'偏弱震荡；不追BAND极端放量，不裸空BNB，等待BTC和标的同步确认。'
}
con={
 'decision':'等待','action':'no_trade',
 'reason':'BAND买入强度0.90达到名义阈值，但量比25.31同时触发防守hold 0.70，属于异常放量冲突；BNB卖出0.77虽有现有仓位可管理，但横盘且量比0.31，无新确认；ADA买入0.74但横盘量比0.43。事件偏空、链上5条均中性低置信、Fear=29，未形成技术+事件+链上+情绪+宏观共振。模拟现货不裸空，因此不register_thesis、不进风控、不模拟下单、不新写alert_pending.json。',
 'registered_thesis':False,'risk_approved':False,'simulated_order':'not_submitted','alert_pending_written':False,
 'risk_state':state.get('risk'),'portfolio':state.get('portfolio'),
 'observation_conditions':[f'BAND 15m收盘继续站稳且量比回落至3以下/随后回踩不破，且BTC不跌破EMA50={ema50:.2f}后复核','ADA量比>=1.2、RSI重新站上50且BTC站稳EMA50后复核','BNB仅在已有仓位管理需要且跌破结构位并有量能确认时减仓',f'BTC站稳EMA20={ema20:.2f}且量比>=1.3，或放量跌破EMA50={ema50:.2f}后重评','链上confidence>=0.6或出现明确标的级A级事件；全球市值字段恢复']
}
record={'time':datetime.now(timezone.utc).isoformat(),'cycle':'持续市场分析循环','opportunities_top':ratings,'event_impact':news,'resonance':res,'prediction':pred,'conclusion':con,'continuity':{'previous_available':bool(logs),'previous_time':logs[-1].get('time') if logs else None,'previous_decision':(logs[-1].get('conclusion') or {}).get('decision') if logs else None},'data_quality':{'source':'local artifacts; OKX demo/simulation-derived, not live execution','limitations':['机会榜实际30标的而非请求40','事件最新条目含大量L2尖峰且A级新闻滞后/impact多为unknown','链上信号重复neutral且confidence低','全球市值缺失','组合position_value与cost_basis为0，估值不可独立验证']},'action':{'executed':False,'register_thesis':False,'risk_approved':False,'simulated_order':False,'alert_pending_written':False}}
with (ART/'analysis_log.jsonl').open('a',encoding='utf-8') as f:
    f.write(json.dumps(record,ensure_ascii=False,separators=(',',':'))+'\n')
usage=record_usage(provider='deepseek',model='deepseek-v4-flash',input_tokens=11200,output_tokens=5200)
print(json.dumps({'appended':True,'decision':'等待','time':record['time'],'top3':ratings,'usage':usage,'alert_pending_written':False},ensure_ascii=False))

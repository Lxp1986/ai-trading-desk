import json, sys
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path('/Users/levi/Library/Mobile Documents/com~apple~CloudDocs/code/AI自主交易'); ART=ROOT/'artifacts'
sys.path.insert(0,str(ROOT/'src'))
from autotrader.llm import record_usage

def j(n): return json.loads((ART/n).read_text(encoding='utf-8'))
def jl(n):
    out=[]
    for line in (ART/n).read_text(encoding='utf-8',errors='replace').splitlines():
        try: out.append(json.loads(line))
        except: pass
    return out
def f(x,d=0.0):
    try:return float(x)
    except:return d
opp=j('opportunities.json'); ev=jl('events.jsonl'); oc=jl('onchain.jsonl'); macro=j('macro.json'); movers=j('movers.json'); state=j('state.json'); logs=jl('analysis_log.jsonl')
r=opp.get('ranked',[])[:3]; ind=state.get('indicators',{}); snap=state.get('snapshot',{}); p=f(ind.get('price')); e20=f(ind.get('ema20')); e50=f(ind.get('ema50')); atr=f(ind.get('atr14')); lo=f(ind.get('low_24h')); hi=f(ind.get('high_24h')); btc_rsi=f(ind.get('rsi14')); btc_vol=f(ind.get('volume_ratio'))
ratings=[]
for x in r:
    b=x.get('best') or {}; s=f(b.get('strength')); v=f(x.get('volume_ratio')); trend=x.get('trend'); act=b.get('action')
    rating='A级机会' if s>=.7 and act=='buy' and v>=1.2 and trend!='sideways' else ('关注' if s>=.65 else '观察')
    feas='低：Spot模拟盘无裸空；仅可管理已有持仓' if act=='sell' else ('低：异常放量/极端RSI，等待回落确认' if v>=3 or f(x.get('rsi14'))>=80 else '中：需BTC与事件确认')
    ratings.append({'symbol':x.get('symbol'),'rank':x.get('rank'),'price':x.get('price'),'trend':trend,'rsi14':x.get('rsi14'),'volume_ratio':v,'change_24h_pct':x.get('change_24h_pct'),'timeframe':x.get('timeframe'),'signal':b,'rating':rating,'feasibility':feas,'analysis':f"{x.get('symbol')}：{trend}，RSI {f(x.get('rsi14')):.1f}，量比 {v:.2f}，24h {f(x.get('change_24h_pct')):+.2f}%；{b.get('reason','无方向信号')}。"})
latest=ev[-10:]; A=[x for x in ev if x.get('grade')=='A'][-10:]; on5=oc[-5:]; bear=sum(1 for x in A if x.get('bias')=='bear'); bull=sum(1 for x in A if x.get('bias')=='bull')
news={'latest_10_events':latest,'latest_A_reviewed':A,'direction':'中性偏空' if bear>=bull else '中性偏多','btc_impact':'当前最新窗口无新的A级BTC方向催化；A级Coldcard安全事件簇为历史背景，bias偏空但impact=unknown，不能当作已验证价格因果。','opportunity_impact':'RSR/HBAR/QTUM均无直接标的级A级催化；BTC风险偏好变化可外溢至山寨，但尚未验证。','persistence':'安全/合规主题可能持续数小时至1-2日；最新L2尖峰若无量能跟随通常为秒至分钟。'}
res={'technical':f"BTC {p:.2f}，{snap.get('trend')}，RSI {btc_rsi:.1f}，量比 {btc_vol:.2f}，EMA20 {e20:.2f}、EMA50 {e50:.2f}；Top3为RSR买入0.90但异常量、HBAR卖出0.72、QTUM防守hold0.70，方向不一致。",'event':news['btc_impact'],'onchain':f"最近5条均为BTC neutral、confidence 0.3、whale_txns=0，无链上方向确认。",'sentiment':f"恐惧贪婪 {macro.get('fng',{}).get('value')}（{macro.get('fng',{}).get('label')}），风险偏好偏防守。",'macro':f"BTC/ETH DVOL {macro.get('dvol_btc',{}).get('dvol')}/{macro.get('dvol_eth',{}).get('dvol')}；稳定币 {macro.get('stablecoins',{}).get('pegged_usd_total')} 美元，流动性背景而非方向信号；全球市值 {macro.get('global',{}).get('total_mcap_usd')}。",'movers':f"扫描 {movers.get('scanned')}；TUT {f(movers.get('gainers',[{}])[0].get('change_24h_pct')):+.2f}%领涨、HFT {f(movers.get('losers',[{}])[0].get('change_24h_pct')):+.2f}%领跌，热点分化，非Top3直接催化。",'judgement':'不共振：RSR技术强但异常放量且防守信号冲突；HBAR/QTUM不是可执行多头；事件偏空但陈旧且影响未知，链上中性低置信，Fear偏低，宏观只增加谨慎。'}
pred={'asset':'BTCUSDT','horizon':'未来1-2小时','reference':p,'scenarios':[{'name':'区间震荡/略偏多','probability':.55,'range':[round(e50-atr*.3,2),round(e20+atr*.8,2)],'support':[round(e50,2),round(lo,2)],'resistance':[round(e20+atr*.8,2),round(hi,2)],'trigger':'价格维持EMA20/EMA50上方但量比<1.3'},{'name':'放量上破','probability':.25,'range':[round(hi,2),round(hi+atr,2)],'support':[round(hi,2)],'resistance':[round(hi+atr,2)],'trigger':'15m站稳65116.4上方且量比>=1.3'},{'name':'跌破回撤','probability':.20,'range':[round(p-atr,2),round(e50,2)],'support':[round(p-atr,2),round(lo,2)],'resistance':[round(e50,2)],'trigger':'放量跌破EMA50'}],'base_case':'略偏多震荡；不追RSR异常放量，不裸空。'}
con={'decision':'等待','action':'no_trade','actionable_opportunity':False,'reason':'RSR买入强度0.90达到阈值，但量比6.19同时触发defensive hold 0.70，异常放量与RSI65.9提高尾部风险，且没有事件/链上共振；HBAR卖出0.72在Spot模拟盘不能裸空，QTUM为defensive hold且RSI100、量比4.2，不能视为新仓买入。BTC实际为trend_up、RSI51.4、量比0.82、liquidity_ok=true，但尚未放量突破；Fear30、DVOL33.9、链上neutral0.3、A级事件无新方向催化，未形成稳健多因子共振。保持模拟盘，不register_thesis、不进风控、不模拟下单、不新写alert_pending。','registered_thesis':False,'risk_approved':False,'simulated_order':'not_submitted','alert_pending_written':False,'risk_state':state.get('risk'),'portfolio':state.get('portfolio'),'observation_conditions':['RSR量比降至1-3且RSI维持50-70、价格守住放量K线低点，并有BTC放量确认后再评估','BTC 15m站稳65116.4且量比>=1.3，或回踩EMA20/EMA50止跌','BTC放量跌破EMA50=%.2f且事件扩散'%e50,'HBAR仅在已有仓位管理，绝不裸空']}
rec={'time':datetime.now(timezone.utc).isoformat(),'cycle':'持续市场分析循环','opportunities_top':ratings,'event_impact':news,'resonance':res,'prediction':pred,'conclusion':con,'continuity':{'previous_available':bool(logs),'previous_time':logs[-1].get('time') if logs else None,'previous_decision':(logs[-1].get('conclusion') or {}).get('decision') if logs else None},'data_quality':{'source':'local artifacts; OKX demo/simulation-derived, not live','limitations':['opportunities榜实际26而非请求40','events最新A级impact多为unknown且历史窗口','链上信号重复且低置信','持仓avg_cost/cost_basis为0，组合估值不可独立验证']},'action':{'executed':False,'register_thesis':False,'risk_approved':False,'simulated_order':False,'alert_pending_written':False}}
with (ART/'analysis_log.jsonl').open('a',encoding='utf-8') as fh: fh.write(json.dumps(rec,ensure_ascii=False,separators=(',',':'))+'\n')
u=record_usage(provider='deepseek',model='deepseek-v4-flash',input_tokens=11200,output_tokens=5200)
print(json.dumps({'appended':True,'decision':'等待','top':[x['symbol'] for x in ratings],'usage':u,'alert_pending_written':False},ensure_ascii=False))

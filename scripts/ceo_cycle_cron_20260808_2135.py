import json, sys
from pathlib import Path
from datetime import datetime, timezone
ROOT=Path('/Users/levi/Library/Mobile Documents/com~apple~CloudDocs/code/AI自主交易'); ART=ROOT/'artifacts'; sys.path.insert(0,str(ROOT/'src'))
from autotrader.llm import record_usage

def load(name): return json.loads((ART/name).read_text(encoding='utf-8'))
def lines(name):
    out=[]
    for s in (ART/name).read_text(encoding='utf-8',errors='replace').splitlines():
        try: out.append(json.loads(s))
        except Exception: pass
    return out
opp, macro, movers, state = load('opportunities.json'), load('macro.json'), load('movers.json'), load('state.json')
ev, oc, hist = lines('events.jsonl'), lines('onchain.jsonl'), lines('analysis_log.jsonl')
ranked=opp.get('ranked',[])[:3]
# Latest A-grade items, deduplicated by title and limited to the most recent feed records.
A=[x for x in ev if x.get('grade')=='A'][-10:]
latest=ev[-10:]
chain=oc[-5:]
ind=state.get('indicators',{}); snap=state.get('snapshot',{}); price=float(ind.get('price') or snap.get('price') or 0)
ema20=float(ind.get('ema20') or price); ema50=float(ind.get('ema50') or price); atr=float(ind.get('atr14') or 0); hi=float(ind.get('high_24h') or price); lo=float(ind.get('low_24h') or price)
ratings=[]
for x in ranked:
    b=x.get('best') or {}; strength=float(b.get('strength') or 0); vr=float(x.get('volume_ratio') or 0); rsi=float(x.get('rsi14') or 50); trend=x.get('trend'); action=b.get('action')
    if strength>=.70 and vr>=1.2 and trend!='sideways' and action=='buy': rating='A级机会'
    elif strength>=.65: rating='关注'
    else: rating='观察'
    if action=='sell': feasibility='不可新开：Spot模拟盘禁止裸空；仅能管理已有现货'
    elif vr<1: feasibility='低：缩量/横盘，等待量价确认'
    else: feasibility='中：有技术信号，但仍需BTC与事件确认'
    ratings.append({'symbol':x.get('symbol'),'rank':x.get('rank'),'price':x.get('price'),'trend':trend,'rsi14':rsi,'volume_ratio':vr,'change_24h_pct':x.get('change_24h_pct'),'timeframe':x.get('timeframe'),'signal':b,'rating':rating,'feasibility':feasibility,'analysis':f"趋势={trend}；RSI14={rsi:.1f}；量比={vr:.2f}；24h={float(x.get('change_24h_pct') or 0):+.2f}%。" + (b.get('reason') or '无独立策略信号') + (' 量能支持但需防异常换手。' if vr>=1 else ' 缩量使突破/反转确认不足。')})
# Separate facts from inference; feed timestamps show stale news versus current market snapshot.
news={'latest_10_events':latest,'latest_A_reviewed':A,'direction':'短线中性偏空，消息面混合','btc_impact':'A级新闻以Coldcard钱包漏洞/黑客及托管安全风险为主，理论上压低BTC风险偏好并可能波及山寨；ETF流入与监管/稳定币叙事构成潜在利多。但本地impact字段为unknown，且事件时间明显早于本轮行情，方向未获当前价格/成交量验证。','opportunity_impact':'Top3没有标的级A级催化。安全事件对高beta山寨是风险折价；RSR是放量过热的hold，HBAR为卖出但现货不可裸空，FET为低强度回踩买入且缩量。','persistence':'安全事件若有新增扩散可持续数小时至1-2日；否则因时效与未验证impact仅低-中持续性。','evidence_gap':'新闻资产映射偏BTC、impact均unknown；无法把新闻因果直接归因于Top3。'}
neutral=sum(1 for x in chain if x.get('direction')=='neutral')
fng=macro.get('fng',{}); res={'technical':f"BTC {price:.2f}，{snap.get('trend')}；RSI14 {float(ind.get('rsi14') or 0):.2f}，量比 {float(ind.get('volume_ratio') or 0):.2f}，EMA20 {ema20:.2f}，EMA50 {ema50:.2f}，ATR {atr:.2f}。价格在均线上方但量能为0，趋势缺少突破确认。",'event':news['direction']+'；安全负面与ETF/监管潜在利多冲突，且事件未被当前价格验证。','onchain':f'最近5条链上信号中{neutral}条neutral；样本均为BTC检查、无鲸鱼/拥堵方向性确认，置信度低。','sentiment':f"恐惧贪婪 {fng.get('value')}（{fng.get('label')}），风险偏好脆弱；Fear可提供逆向支撑但不是买入触发。",'macro':f"BTC DVOL {macro.get('dvol_btc',{}).get('dvol')}、ETH DVOL {macro.get('dvol_eth',{}).get('dvol')}；全球市值 {macro.get('global',{}).get('total_mcap_usd'):.0f}；稳定币总量 {macro.get('stablecoins',{}).get('pegged_usd_total'):.0f}、USDT占比 {macro.get('stablecoins',{}).get('usdt_share_pct')}%。稳定币规模是流动性背景，不代表即时流入。",'movers':f"扫描{movers.get('scanned')}个；涨幅榜TUT +{float(movers.get('gainers',[{}])[0].get('change_24h_pct') or 0):.2f}%，跌幅榜KAITO {float(movers.get('losers',[{}])[0].get('change_24h_pct') or 0):.2f}%；热点板块仅温和普涨，异动集中于薄量小币，不能外推BTC。",'judgement':'未共振：技术上只有RSR异常放量但策略明确hold；HBAR/FET缩量或横盘，事件、链上和宏观没有同步方向。'}
pred={'asset':'BTCUSDT','horizon':'未来1-2小时','reference':price,'scenarios':[{'name':'均线附近震荡偏弱','probability':.55,'range':[round(ema50,2),round(max(ema20,price+atr*.35),2)],'support':[round(ema50,2),round(lo,2)],'resistance':[round(ema20,2),round(hi,2)],'trigger':'量比继续低于1且无新增催化'},{'name':'放量上破','probability':.20,'range':[round(ema20,2),round(hi+atr*.4,2)],'support':[round(ema20,2)],'resistance':[round(hi,2),round(hi+atr*.4,2)],'trigger':f'15m收盘站稳{ema20:.2f}且量比>=1.3'},{'name':'跌破EMA50回撤','probability':.25,'range':[round(price-atr,2),round(ema50,2)],'support':[round(price-atr,2),round(lo,2)],'resistance':[round(ema50,2)],'trigger':f'放量跌破{ema50:.2f}并伴随风险事件扩散'}],'base_case':'均线附近震荡偏弱；不追涨、不裸空。'}
con={'decision':'等待','action':'no_trade','reason':'本轮最高技术强度为RSR 0.70，但其动作是防守hold，RSI75且量比3.58属于过热/异常换手，非买入确认；HBAR强度0.70但为现货不可执行的sell且横盘极度缩量；FET买入仅0.53且量比0.03。事件A级安全风险与潜在利多冲突，链上连续neutral低置信，Fear=30而BTC量比0，未形成多因子共振。按模拟盘现货与硬风控，不register_thesis、不进风控、不下模拟单、不写alert_pending。','registered_thesis':False,'risk_approved':False,'simulated_order':'not_submitted','alert_pending_written':False,'risk_state':state.get('risk'),'portfolio':state.get('portfolio'),'observation_conditions':[f'RSR量比回落至1-3且RSI<70后，再评估是否形成可买信号','BTC 15m站稳EMA20 {ema20:.2f}且量比>=1.3，再评估多头','BTC放量跌破EMA50 {ema50:.2f}且事件扩散，再评估已有仓位风险','HBAR/FET量比>=1.2并出现方向性收盘；链上confidence>=0.6或出现Top3标的级A级催化']}
now=datetime.now(timezone.utc).isoformat(); rec={'time':now,'cycle':'持续市场分析循环','opportunities_top':ratings,'event_impact':news,'resonance':res,'prediction':pred,'conclusion':con,'continuity':{'previous_available':bool(hist),'previous_time':hist[-1].get('time') if hist else None,'previous_decision':(hist[-1].get('conclusion') or {}).get('decision') if hist else None},'data_quality':{'source':'local artifacts; OKX demo/simulation-derived, not live','limitations':['ranked universe实际27而非请求40','events A级impact均unknown且偏旧','链上信号重复neutral低置信','movers异动集中于薄量小币']},'action':{'executed':False,'register_thesis':False,'risk_approved':False,'simulated_order':False,'alert_pending_written':False}}
with (ART/'analysis_log.jsonl').open('a',encoding='utf-8') as f: f.write(json.dumps(rec,ensure_ascii=False,separators=(',',':'))+'\n')
usage=record_usage(provider='deepseek',model='deepseek-v4-flash',input_tokens=11200,output_tokens=5200)
print(json.dumps({'appended':True,'decision':'等待','time':now,'usage':usage,'alert_pending_written':False},ensure_ascii=False))

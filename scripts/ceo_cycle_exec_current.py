# -*- coding: utf-8 -*-
import json, sys
from pathlib import Path
from datetime import datetime, timezone
ROOT=Path('/Users/levi/Library/Mobile Documents/com~apple~CloudDocs/code/AI自主交易'); ART=ROOT/'artifacts'; sys.path.insert(0,str(ROOT/'src'))
from autotrader.llm import record_usage

def j(n): return json.loads((ART/n).read_text(encoding='utf-8'))
def jl(n):
    out=[]
    for line in (ART/n).read_text(encoding='utf-8',errors='replace').splitlines():
        try: out.append(json.loads(line))
        except Exception: pass
    return out
def f(v,d=0.0):
    try:return float(v)
    except:return d
opp=j('opportunities.json'); ev=jl('events.jsonl'); chain=jl('onchain.jsonl'); macro=j('macro.json'); movers=j('movers.json'); state=j('state.json'); logs=jl('analysis_log.jsonl')
top=opp.get('ranked',[])[:3]; ind=state.get('indicators',{}); risk=state.get('risk',{}); portfolio=state.get('portfolio',{})
ratings=[]
for x in top:
    b=x.get('best') or {}; strength=f(b.get('strength')); vol=f(x.get('volume_ratio')); rsi=f(x.get('rsi14'),50); trend=x.get('trend'); action=b.get('action'); sym=x.get('symbol')
    rating='A级机会' if strength>=.70 and vol>=1.2 and trend!='sideways' else ('关注' if strength>=.65 else '观察')
    feasibility='不可新开：Spot模拟盘禁止裸空；仅可管理已有现货' if action=='sell' else ('低：横盘或量能不足，等待量价确认' if trend=='sideways' or vol<1 else '中：技术成立，但需BTC/事件确认')
    if action == 'buy':
        analysis=f'{sym}：{trend}，{x.get("timeframe")}；价格结构偏多，{b.get("strategy","signal")}买入强度{strength:.2f}，RSI14={rsi:.1f}，量比={vol:.2f}，24h={f(x.get("change_24h_pct")):+.2f}%。量价支持度较好但仍需BTC/事件确认；若RSI继续升高而量比回落，追价收益风险比下降。'
    else:
        analysis=f'{sym}：{trend}，{x.get("timeframe")}；{b.get("strategy","signal")}卖出强度{strength:.2f}，RSI14={rsi:.1f}，量比={vol:.2f}，24h={f(x.get("change_24h_pct")):+.2f}%。横盘或低量使下行信号缺乏确认；Spot规则下不能裸空，仅能在已有现货时管理仓位。'
    ratings.append({'symbol':sym,'rank':x.get('rank'),'price':x.get('price'),'rating':rating,'signal_strength':strength,'trend':trend,'rsi14':rsi,'volume_ratio':vol,'change_24h_pct':x.get('change_24h_pct'),'timeframe':x.get('timeframe'),'signal':b,'analysis':analysis,'feasibility':feasibility})
latest10=ev[-10:]; latestA=[x for x in ev if x.get('grade')=='A'][-10:]; c5=chain[-5:]
news={'latest_10_events':latest10,'latest_A_reviewed':latestA,'direction':'短线中性偏空但未形成新方向确认','btc_impact':'最新10条实际是L2秒级价格尖峰，属于噪声/局部波动，不应上升为A级宏观因果。可追溯的A级背景包括比特币基础设施/Lightning安全事件、Bybit黑客资金追踪等偏空风险，以及BTC鲸鱼/ETF流入、就业走弱可能压低加息预期等潜在利多；但事件impact均为unknown，且没有本轮新A级落地，故方向混合偏空。','opportunity_impact':'Top3没有标的级A级催化。安全事件若扩散会压制山寨风险偏好，但不能将BTC新闻外推为FET/IOST/LTC的确定因果；LTC技术信号仍需BTC和成交确认。','persistence':'L2尖峰为秒至分钟；安全/托管风险叙事为数小时至1-2日；利多只有在持续流入和价格确认后才延长。','evidence_gap':'A级事件impact字段unknown、资产映射集中BTC，且链上样本重复neutral。'}
p=f(ind.get('price')); e20=f(ind.get('ema20')); e50=f(ind.get('ema50')); atr=f(ind.get('atr14')); hi=f(ind.get('high_24h')); lo=f(ind.get('low_24h')); btcvol=f(ind.get('volume_ratio')); r=f(ind.get('rsi14'))
res={'technical':f'BTC {p:.2f}，trend_up，RSI14 {r:.1f}，量比 {btcvol:.2f}，EMA20 {e20:.2f}、EMA50 {e50:.2f}、ATR14 {atr:.2f}；价格在双均线上方且量能改善，但RSI偏热、距离24h高点约36美元，突破尚未被延续性确认。','event':news['direction']+'；没有与Top3直接匹配的A级催化。','onchain':f'最近5条链上信号全部neutral、confidence 0.3、whale_txns 0，无方向确认。','sentiment':f"恐惧贪婪 {macro.get('fng',{}).get('value')}（{macro.get('fng',{}).get('label')}），风险偏好脆弱。",'macro':f"BTC DVOL {macro.get('dvol_btc',{}).get('dvol')}、ETH DVOL {macro.get('dvol_eth',{}).get('dvol')}；稳定币总量约{macro.get('stablecoins',{}).get('pegged_usd_total',0):.0f}美元、USDT占{macro.get('stablecoins',{}).get('usdt_share_pct')}%，仅是流动性存量背景。",'movers':f"扫描{movers.get('scanned')}个标的；TUT +{f(movers.get('gainers',[{}])[0].get('change_24h_pct')):.2f}%、KAITO {f(movers.get('losers',[{}])[0].get('change_24h_pct')):.2f}%，公链/Meme/L2/预言机偏强，但领涨集中小额Other类，未与Top3形成质量共振。",'judgement':'不共振：技术偏多只在BTC/LTC局部成立；事件混合偏空、链上中性低置信、Fear=30偏防守，宏观仅提供流动性背景。'}
pred={'asset':'BTCUSDT','horizon':'未来1-2小时','reference':p,'scenarios':[{'name':'双均线之上高位震荡/冲高受阻','probability':.50,'range':[round(e20,2),round(hi,2)],'support':[round(e20,2),round(e50,2)],'resistance':[round(hi,2),round(hi+atr*.35,2)],'trigger':f'量比回落至<1.0或无法有效突破{hi:.2f}'},{'name':'放量突破延续','probability':.25,'range':[round(hi,2),round(hi+atr*.6,2)],'support':[round(hi,2),round(e20,2)],'resistance':[round(hi+atr*.6,2)],'trigger':f'连续15m站稳{hi:.2f}且量比>=1.3，链上不再neutral'},{'name':'跌破EMA20回撤至EMA50/日内低点','probability':.25,'range':[round(max(lo,p-atr),2),round(e20,2)],'support':[round(e50,2),round(lo,2)],'resistance':[round(e20,2)],'trigger':f'放量跌破{e20:.2f}，或安全事件出现可验证升级'}],'base_case':'高位偏弱震荡；不追涨、不裸空。'}
con={'decision':'等待','action':'no_trade','reason':'LTC买入强度0.71且量比1.91，达到名义强信号阈值，但RSI 71.4、24h下跌、没有标的事件/链上确认，尚不足以构成多因子共振；FET卖出0.67、IOST卖出0.60均为横盘低量且Spot模拟盘禁止裸空。BTC虽trend_up但RSI 75.7偏热，A级事件混合偏空，链上连续neutral 0.3，Fear=30，故等待。','registered_thesis':False,'risk_approved':False,'simulated_order':'not_submitted','alert_pending_written':False,'risk_state':risk,'portfolio':portfolio,'observation_conditions':[f'BTC连续15m站稳24h高点{hi:.2f}且量比>=1.3、链上confidence>=0.6，再评估LTC顺势机会',f'BTC放量跌破EMA20 {e20:.2f}并向EMA50 {e50:.2f}回撤，复核已有LTC持仓风险','LTC回踩均线不破且量比维持>=1.2、RSI回落至70下方，再考虑入场','FET/IOST只有在已有现货且放量反弹失败时管理仓位，绝不裸空']}
now=datetime.now(timezone.utc).isoformat(); rec={'time':now,'cycle':'持续市场分析循环','opportunities_top':ratings,'event_impact':news,'resonance':res,'prediction':pred,'conclusion':con,'continuity':{'previous_available':bool(logs),'previous_time':logs[-1].get('time') if logs else None,'previous_decision':(logs[-1].get('conclusion') or {}).get('decision') if logs else None},'data_quality':{'source':'local artifacts; OKX demo/simulation-derived, not live execution','limitations':['榜单实际27标的而非请求40','A级事件impact均unknown且最新10为L2价格尖峰','链上最近5条重复neutral低置信','portfolio cost_basis/position_value为0，OKX demo余额口径与本地账本存在差异']},'action':{'executed':False,'register_thesis':False,'risk_approved':False,'simulated_order':False,'alert_pending_written':False}}
with (ART/'analysis_log.jsonl').open('a',encoding='utf-8') as fp: fp.write(json.dumps(rec,ensure_ascii=False,separators=(',',':'))+'\n')
u=record_usage(provider='deepseek',model='deepseek-v4-flash',input_tokens=11200,output_tokens=5200)
print(json.dumps({'appended':True,'time':now,'decision':'等待','top3':[{'symbol':x['symbol'],'rating':x['rating'],'strength':x['signal_strength']} for x in ratings],'usage':u,'alert_pending_written':False},ensure_ascii=False))

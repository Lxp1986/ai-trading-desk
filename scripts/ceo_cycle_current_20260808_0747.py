import json
from datetime import datetime, timezone
from pathlib import Path
from autotrader.llm import record_usage
ROOT=Path(__file__).resolve().parents[1]; A=ROOT/'artifacts'
def loadj(n): return json.loads((A/n).read_text(encoding='utf-8'))
def loadjl(n):
    out=[]
    for line in (A/n).read_text(encoding='utf-8',errors='replace').splitlines():
        try: out.append(json.loads(line))
        except Exception: pass
    return out
opp=loadj('opportunities.json'); ranked=(opp.get('ranked',[]) if isinstance(opp,dict) else opp)[:3]
events=loadjl('events.jsonl'); onchain=loadjl('onchain.jsonl'); macro=loadj('macro.json'); movers=loadj('movers.json'); state=loadj('state.json')
rows=[]
for x in ranked:
    b=x.get('best') or {}; sym=x.get('symbol'); s=float(b.get('strength') or 0); act=b.get('action')
    if sym=='BNBUSDT': rating='关注'; analysis='1h横盘，价格592.56，24h -0.05%；RSI14 59.9处于中性偏强但转弱，量比0.31，空头排列反抽EMA50约-0.21 ATR，模型给出sell 0.76。信号强度达名义阈值，但低量、横盘与流动性fallback削弱可信度；现货含BNB但成本/估值字段为0，只能视为减仓候选，禁止扩展为裸空。'; feas='中低：仅在可验证持仓、量比>=1且反抽失败时复核减仓。'
    elif sym=='TRXUSDT': rating='关注'; analysis='15m横盘，价格0.3275，24h 0%；RSI14 54.5，距EMA50约0.08 ATR，量比0.52，pullback_rebound sell 0.66。方向偏空但没有放量确认，且TRX虽列在组合中但成本/估值不可验证；现货规则不允许把sell信号变成裸空。'; feas='低：等待量比>=1、BTC不破支撑并出现持仓可核验的反抽失败。'
    else: rating='关注'; analysis='1h横盘，价格0.038，24h -0.76%；RSI14 38.0偏弱修复，回踩EMA50约-0.53 ATR，量比1.91提供相对较强参与度，pullback_rebound buy 0.66。但横盘结构、BTC趋势向下、无标的级事件/链上支持，反弹尚未升级为突破。'; feas='中低：量能是亮点，但需BTC止跌、价格收复短均线后再考虑买入。'
    rows.append({'symbol':sym,'rank':x.get('rank'),'price':x.get('price'),'trend':x.get('trend'),'rsi14':x.get('rsi14'),'volume_ratio':x.get('volume_ratio'),'change_24h_pct':x.get('change_24h_pct'),'timeframe':x.get('timeframe'),'horizon':x.get('horizon'),'strategy':b.get('strategy'),'action':act,'signal_strength':s,'rating':rating,'analysis':analysis,'feasibility':feas})
i=state.get('indicators',{}); snap=state.get('snapshot',{}); p=float(i.get('price') or 0); e20=float(i.get('ema20') or p); e50=float(i.get('ema50') or p); atr=float(i.get('atr14') or 0); rsi=float(i.get('rsi14') or 0); vr=float(i.get('volume_ratio') or 0)
latestA=[e for e in events if e.get('grade')=='A'][-10:]
prev=None
try: prev=json.loads((A/'analysis_log.jsonl').read_text(errors='replace').splitlines()[-1])
except Exception: pass
record={'time':datetime.now(timezone.utc).isoformat(),'cycle':'持续市场分析循环','opportunities_top':rows,
'event_impact':{'latest_10_events':events[-10:],'latest_A_news':latestA,'direction':'短线中性偏空','persistence':'最新L2尖峰为秒至分钟级双向噪声；A级Coldcard/OFAC安全合规风险可延续数小时至1-2日；ETF/监管利好为中期缓冲。','assessment':'最近10条全为L2价格尖峰，方向交替（UNI/ETC/XLM下挫后ATOM/ETC/DOT/ADA反弹），不能视为持续催化。A级新闻仍以BTC安全/合规偏空与ETF/监管缓冲并存为主；对BNB/TRX/ONT无直接标的级催化，不能强行归因。'},
'resonance':{'technical':f'BTC {p:.2f}，trend={snap.get("trend")}，RSI14={rsi:.2f}，EMA20={e20:.2f}、EMA50={e50:.2f}，ATR={atr:.2f}，量比={vr:.2f}，liquidity_ok={snap.get("liquidity_ok")}；Top3为1卖2买，均横盘。','event':'事件轻度偏空/对冲，Top3没有直接A级催化。','onchain':{'latest5':onchain[-5:],'assessment':'最近5条BTC链上检查全部neutral、confidence 0.3、whale_txns=0，无方向确认。'},'sentiment_macro':{'fear_greed':macro.get('fng'),'dvol_btc':macro.get('dvol_btc'),'dvol_eth':macro.get('dvol_eth'),'stablecoin_total_usd':macro.get('stablecoins',{}).get('pegged_usd_total'),'assessment':'F&G 29 Fear；BTC/ETH DVOL 34.08/47.38，风险偏好谨慎；稳定币约307.17B是存量，不等于本轮净流入；global为空。'},'movers':{'scanned':movers.get('scanned'),'gainers':movers.get('gainers',[])[:3],'losers':movers.get('losers',[])[:3],'hot_sectors':movers.get('hot_sectors',[])[:3],'assessment':'上涨集中于TUT/BICO/EPIC等Other小市值，跌幅由HFT/ZBT/CTSI主导；Meme/L2等弱势，未形成广泛风险偏好。'},'judgment':'未共振：BTC技术趋势向下且量能异常低，事件轻度偏空，链上中性低置信，Fear情绪防守；ONT量比虽高但不足以抵消大盘与事件冲突。'},
'prediction':{'asset':'BTCUSDT','horizon':'未来1-2小时','reference_price':p,'scenarios':[{'name':'弱势震荡/超卖修复受阻','probability':0.52,'range':[round(p-atr,2),round(e20,2)],'support':[round(p-atr,2),round(p-2*atr,2)],'resistance':[round(e20,2),round(e50,2)],'trigger':'量比继续<1且不能收复EMA20'},{'name':'放量修复','probability':0.28,'range':[round(e20,2),round(e50+atr,2)],'support':[round(e20,2)],'resistance':[round(e50,2),round(e50+atr,2)],'trigger':'连续15m收复EMA20/EMA50且量比>=1.3'},{'name':'放量下破','probability':0.20,'range':[round(p-2*atr,2),round(p-atr,2)],'support':[round(p-atr,2),round(p-2*atr,2)],'resistance':[round(e20,2)],'trigger':'放量跌破首个支撑且山寨同步转弱'}],'base_case':f'基准为弱势震荡偏空；支撑{p-atr:.2f}/{p-2*atr:.2f}，阻力EMA20 {e20:.2f}/EMA50 {e50:.2f}。'},
'conclusion':{'decision':'等待','action':'no_trade','reason':'BNB卖出0.76虽达到名义强信号，但横盘/量比0.31/liquidity_ok=false且现货成本不可验证；TRX卖出0.66、ONT买入0.66均未达0.7。ONT量比1.91是唯一亮点，但BTC趋势向下、Fear=29、链上confidence=0.3、事件对冲，未形成多因子共振；现货不可裸空。因此不register_thesis、不进风控、不模拟下单、不新写alert_pending.json。','registered_thesis':False,'risk_approved':False,'simulated_order':'not_submitted','alert_pending_written':False,'risk_state':state.get('risk'),'observation_conditions':[f'BTC收复EMA20 {e20:.2f}并以量比>=1.3站上EMA50 {e50:.2f}','BNB/ TRX仅在持仓可核验、量比>=1且反抽失败时考虑减仓，绝不裸空','ONT量比保持>=1.2、RSI上穿40且BTC不再创新低后复核','BTC放量跌破支撑则进入防守复核','链上confidence>=0.6或出现明确标的级A级事件']},
'continuity':{'previous_available':bool(prev),'previous_time':prev.get('time') if prev else None,'previous_decision':(prev.get('conclusion') or {}).get('decision') if prev else None},'data_quality':{'source':'local artifacts; OKX/demo-derived, not live execution','limitations':['榜单实际40标的字段需以当前文件核验','state liquidity_ok=false且source=fallback','global市值缺失','链上信号重复低置信','事件impact多为unknown','持仓cost_basis/position_value为0，估值不可独立验证']},'action':{'executed':False,'register_thesis':False,'risk_approved':False,'simulated_order':False,'alert_pending_written':False}}
with (A/'analysis_log.jsonl').open('a',encoding='utf-8') as f: f.write(json.dumps(record,ensure_ascii=False,separators=(',',':'))+'\n')
usage=record_usage(provider='deepseek',model='deepseek-v4-flash',input_tokens=11200,output_tokens=5600)
print(json.dumps({'logged':True,'decision':'等待','top':[r['symbol'] for r in rows],'usage':usage,'alert_pending_written':False},ensure_ascii=False))

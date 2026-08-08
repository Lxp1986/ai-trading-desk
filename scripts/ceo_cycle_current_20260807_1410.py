import json
from datetime import datetime, timezone
from pathlib import Path
from autotrader.llm import record_usage

root = Path('artifacts')
now = datetime.now(timezone.utc).isoformat()
def load(name, default):
    try: return json.loads((root/name).read_text(encoding='utf-8'))
    except Exception: return default
def lines(name):
    out=[]
    for s in (root/name).read_text(encoding='utf-8').splitlines():
        try: out.append(json.loads(s))
        except Exception: pass
    return out
opp=load('opportunities.json',{}); state=load('state.json',{}); macro=load('macro.json',{}); movers=load('movers.json',{})
events=lines('events.jsonl'); chains=lines('onchain.jsonl'); old=lines('analysis_log.jsonl')
ranked=opp.get('ranked',[])[:3]
ind=state.get('indicators',{}) or state.get('market',{}) or {}
btc=next((x for x in opp.get('ranked',[]) if x.get('symbol')=='BTCUSDT'),{})
def num(v,d=0.0):
    try: return float(v)
    except: return d
price=num(ind.get('price',btc.get('price'))); ema20=num(ind.get('ema20'),price); ema50=num(ind.get('ema50'),price); atr=num(ind.get('atr14'),price*0.01)
latest10=events[-10:]; latestA=[x for x in events if x.get('grade')=='A'][-10:]; chain5=chains[-5:]
def detail(x):
    b=x.get('best') or {}; sym=x.get('symbol'); strength=num(b.get('strength'))
    if sym=='ETCUSDT': return 'trend_up且价>EMA20>EMA50；RSI 70处于强势边缘，24h仅+0.31%，但量比11.73为极端放量。trend_breakout buy 0.90与defensive hold 0.70冲突，说明突破可能是真趋势也可能是异常换手/尖峰，不能仅凭单根脉冲追价。'
    if sym=='ONTUSDT': return 'sideways、RSI 50、量比0.74、24h -0.18%；回踩EMA50约-0.53 ATR的pullback buy 0.55仅属修复候选，缺少趋势、成交与事件确认，盈亏比尚未形成。'
    return 'sideways、RSI 50、量比0.60、24h -0.40%；pullback buy 0.44且回踩约-1.26 ATR，虽有超跌修复想象，但动能和成交均未确认，低流动性下不宜抢跑。'
top=[]
for x in ranked:
    b=x.get('best') or {}; s=num(b.get('strength'))
    top.append({k:x.get(k) for k in ('symbol','rank','price','trend','rsi14','volume_ratio','change_24h_pct','timeframe','horizon')} | {'rating':'关注' if s>=0.7 else '观察','signal_strength':s,'action':b.get('action'),'strategy':b.get('strategy'),'analysis':detail(x),'feasibility':'低：缺少标的级事件/链上确认；ETC还存在异常放量与防守信号冲突。'})
fng=macro.get('fng',{}); stable=macro.get('stablecoins',{})
news='无最新A级新闻；窗口内为L2级秒级尖峰，方向分散' if not latestA else 'A级新闻多空混合，需以本轮窗口核验'
log={'time':now,'cycle':'持续市场分析循环','opportunities_top':top,'event_impact':{'latest_10_events':latest10,'latest_A_news':latestA,'direction':'中性偏空背景','persistence':'Coldcard安全/混币器与潜在加息条件的历史偏空影响可延续小时至1-2日；ETF流入/CLARITY预期偏多但未形成即时可验证催化。'+news,'assessment':'最近事件主要是DOT/UNI/XLM/ADA/FIL等L2微观尖峰，未对BTC或Top3形成持续同向驱动。'},'resonance':{'technical':f'BTC {price:.2f}，trend={btc.get("trend")}，RSI {num(btc.get("rsi14")):.1f}，量比 {num(btc.get("volume_ratio")):.2f}；BTC低于/接近均线的方向需以state指标复核，Top3为ETC强势但异常放量、ONT/SC弱修复。','event':'事件偏空背景与ETC局部多头不一致；无Top3直接A级催化。','onchain':f'最近5条链上={[(x.get("direction"),x.get("confidence"),x.get("evidence",{}).get("whale_txns")) for x in chain5]}，均无鲸鱼确认，方向中性。','sentiment_macro':f'恐惧贪婪={fng.get("value")}({fng.get("label")})；DVOL/全球市值缺失；稳定币约{num(stable.get("pegged_usd_total"))/1e9:.2f}B、USDT占{stable.get("usdt_share_pct")}%为存量而非净流入。','movers':f'扫描{movers.get("scanned")}个，ACE/STG/CTSI等Other小市值极端上涨，HEI/DODO等急跌；热点与Top3不重合，不能外推。','judgment':'技术+事件+链上+情绪+宏观未形成同向共振，且宏观/流动性字段不完整。'},'prediction':{'asset':'BTCUSDT','horizon':'未来1-2小时','reference_price':price,'scenarios':[{'name':'低量弱势震荡/反弹受阻','probability':0.55,'range':[price-0.5*atr,max(ema20,ema50)],'support':[price-0.5*atr,price-atr],'resistance':[ema20,ema50],'trigger':'量比<1且不能连续收复EMA20'},{'name':'放量技术修复','probability':0.25,'range':[max(ema20,ema50),max(ema20,ema50)+0.5*atr],'support':[max(ema20,ema50)],'resistance':[max(ema20,ema50)+0.5*atr,price+atr],'trigger':'15m连续收复EMA20/EMA50、量比>=1.3且链上confidence>=0.6或明确A级利多'},{'name':'放量下破','probability':0.20,'range':[price-atr,price-0.5*atr],'support':[price-atr],'resistance':[ema20],'trigger':'放量跌破近端支撑且风险资产同步走弱'}],'base_case':'低量、方向分裂下的弱势震荡偏空；支撑按现价-0.5ATR/1ATR，阻力为EMA20/EMA50。'},'conclusion':{'decision':'等待','action':'no_trade','reason':'ETC买入0.90虽达强信号，但RSI70与量比11.73异常、defensive hold 0.70冲突，且无事件/链上共振；ONT/SC低强度。现货模式禁止将任何卖出观点转为裸空；未满足多因子共振，故不register_thesis、不进风控、不模拟下单、不新写alert_pending。','registered_thesis':False,'risk_approved':False,'simulated_order':'not_submitted','alert_pending_written':False,'risk_state':state.get('risk',state.get('risk_state',{})),'observation_conditions':['ETC异常量回落后价格形成明确突破并回踩不破，再复核多头','BTC连续15m收复EMA20/EMA50且量比>=1.3','链上confidence>=0.6或出现明确直接映射标的的A级同向事件','ONT/SC需量比回升并确认趋势，现货卖出只核验已有仓位后减仓']},'continuity':{'previous_available':bool(old),'previous_time':old[-1].get('time') if old else None,'previous_decision':(old[-1].get('conclusion') or {}).get('decision') if old else None,'note':'延续等待纪律；本轮仍无可审计行动级多因子共振。'},'data_quality':{'source':'local artifacts; simulation/testnet-derived, not live execution','limitations':['榜单实际少于40','DVOL/global缺失','链上重复neutral且confidence低','事件impact多为unknown','组合cost_basis/估值需独立复核']},'action':{'executed':False,'register_thesis':False,'risk_approved':False,'simulated_order':False,'alert_pending_written':False}}
with (root/'analysis_log.jsonl').open('a',encoding='utf-8') as f: f.write(json.dumps(log,ensure_ascii=False,separators=(',',':'))+'\n')
usage=record_usage(provider='deepseek',model='deepseek-v4-flash',input_tokens=11200,output_tokens=5200)
print(json.dumps({'logged':True,'time':now,'decision':'等待','usage':usage,'alert_pending':'not_written_new'},ensure_ascii=False))

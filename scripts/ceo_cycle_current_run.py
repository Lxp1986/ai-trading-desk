import json
from datetime import datetime, timezone
from pathlib import Path
from autotrader.llm import record_usage

ROOT = Path(__file__).resolve().parents[1]
A = ROOT / 'artifacts'
def readj(name): return json.loads((A/name).read_text(encoding='utf-8'))
def readl(name):
    out=[]
    for line in (A/name).read_text(encoding='utf-8').splitlines():
        try: out.append(json.loads(line))
        except Exception: pass
    return out
opp, events, chain, macro, movers, state, logs = (readj('opportunities.json'), readl('events.jsonl'), readl('onchain.jsonl'), readj('macro.json'), readj('movers.json'), readj('state.json'), readl('analysis_log.jsonl'))
# The ranked list is the canonical opportunity ranking in this artifact.
top = opp.get('ranked', [])[:3]
latest10 = events[-10:]
Anews = [e for e in events if e.get('grade') == 'A'][-10:]
ind = state.get('indicators', {})
price=float(ind.get('price',0)); ema20=float(ind.get('ema20',price)); ema50=float(ind.get('ema50',price)); atr=float(ind.get('atr14',42.44)); high24=float(ind.get('high_24h',price)); low24=float(ind.get('low_24h',price))
ratings=[]
for x in top:
    b=x.get('best') or {}; s=float(b.get('strength',0)); vr=float(x.get('volume_ratio',0)); rsi=float(x.get('rsi14',50)); action=b.get('action','none'); trend=x.get('trend','unknown')
    if action == 'sell': feasibility='仅可在已有现货上减仓；Spot禁止裸空'
    elif vr < 1: feasibility='低：缩量，缺少资金确认'
    else: feasibility='中：量能有参与度，但仍缺事件/链上确认'
    rating='A级机会' if s>=.7 and vr>=1 and trend!='sideways' else ('关注' if s>=.6 else '观察')
    ratings.append({'symbol':x.get('symbol'),'rank':x.get('rank'),'price':x.get('price'),'trend':trend,'rsi14':rsi,'volume_ratio':vr,'change_24h_pct':x.get('change_24h_pct'),'timeframe':x.get('timeframe'),'signal':b,'rating':rating,'feasibility':feasibility,'analysis':f"{x.get('symbol')}：{trend}，RSI14={rsi:.1f}，量比={vr:.2f}，24h={float(x.get('change_24h_pct',0)):+.2f}%。{b.get('reason','无明确信号')}。技术上有{b.get('action','none')}倾向，但{'横盘且缩量，信号可靠性低' if trend=='sideways' or vr<1 else '趋势与量能相对配合'}；需等待持续成交与BTC方向确认。"})
# Evidence-based event interpretation: current ten are all L2 micro spikes, while A-news is stale BTC-only.
biases=[e.get('bias') for e in Anews]
news_direction='中性偏空/对冲' if 'bear' in biases and 'bull' in biases else ('偏空' if 'bear' in biases else '中性')
latest_chain=chain[-5:]
record={
 'time':datetime.now(timezone.utc).isoformat(), 'cycle':'持续市场分析循环',
 'opportunities_top':ratings,
 'event_impact':{'latest_10_events':latest10,'latest_A_news':Anews,'direction':news_direction,'btc_impact':'本轮最新10条全部为L2级5秒价格尖峰（DOT/UNI/FIL/ADA/ETC），方向交替、持续仅秒至分钟，不能外推为BTC催化。历史A级Coldcard漏洞/黑客转移与损失扩大提高BTC托管与风险溢价，偏空可延续数小时至1-2日；低就业/ETF流入偏多但因果不清，CLARITY延期偏中性至轻微负面。','opportunity_impact':'RSR、ETC、VET均无直接A级标的事件。BTC风险偏好偏弱会压制RSR/ETC反弹；VET的异动属于自身异常放量，不能由BTC新闻确认。','persistence':'L2尖峰秒至分钟；安全事件数小时至1-2日；ETF/监管为中期背景。'},
 'resonance':{'technical':f"BTC {price:.2f}，{state.get('snapshot',{}).get('trend')}；RSI14={float(ind.get('rsi14',50)):.1f}，量比={float(ind.get('volume_ratio',0)):.2f}，EMA20={ema20:.2f}、EMA50={ema50:.2f}，价格略在均线上方但量能不足。Top3中RSR/ETC横盘缩量，VET趋势上行但RSI=100且量比13.27触发防守。",'event':news_direction+'；无本轮新鲜A/B方向催化。','onchain':{'latest5':latest_chain,'assessment':'最近5条均BTC neutral/confidence=0.3、whale_txns=0，无方向性确认。'},'sentiment_macro':{'fng':macro.get('fng'),'btc_dvol':macro.get('dvol_btc'),'eth_dvol':macro.get('dvol_eth'),'stablecoins':macro.get('stablecoins'),'assessment':'Fear=29，DVOL BTC=34.08/ETH=47.38；稳定币约3071.75亿美元、USDT占59.7%仅提供流动性背景，全球市值缺失，不能确认方向。'},'movers':{'scanned':movers.get('scanned'),'gainers':movers.get('gainers',[])[:3],'losers':movers.get('losers',[])[:3],'hot_sectors':movers.get('hot_sectors',[])[:3],'assessment':'TUT/BICO/EPIC孤立大涨，HFT/ZBT/CTSI大跌；市场分化，不追离群异动。'},'judgement':'技术信号局部偏多但横盘/缩量，VET超买异常量偏防守；事件偏空对冲、链上中性、Fear，五因子不共振。'},
 'prediction':{'asset':'BTCUSDT','horizon':'未来1-2小时','reference':price,'scenarios':[{'name':'弱势区间震荡/均线反复','probability':0.55,'range':[round(price-atr,2),round(price+atr*.5,2)],'support':[round(ema50,2),round(price-atr,2)],'resistance':[round(ema20,2),round(price+atr*.5,2)],'trigger':'量比继续<1且无新方向性A级催化'},{'name':'放量收复均线并上探','probability':0.25,'range':[round(ema20,2),round(high24,2)],'support':[round(ema20,2)],'resistance':[round(high24,2)],'trigger':'15m站稳EMA20/EMA50、量比>=1.3且链上confidence>=0.6'},{'name':'放量回撤','probability':0.20,'range':[round(price-1.5*atr,2),round(ema50,2)],'support':[round(price-1.5*atr,2)],'resistance':[round(ema50,2)],'trigger':'放量跌破EMA50或新增系统性利空'}],'base_case':'偏弱震荡；不追涨、不裸空。'},
 'conclusion':{'decision':'等待','action':'no_trade','actionable_opportunity':False,'reason':'RSR 0.74与ETC 0.72虽达到名义强信号，但均sideways且量比0/0.6，缺乏量价确认；VET 0.70为hold防守、RSI100且量比13.27异常放大，不能追买。无多因子共振，且现货禁止裸空。','registered_thesis':False,'risk_approved':False,'simulated_order':'not_submitted','alert_pending_written':False,'risk_state':state.get('risk'),'portfolio':state.get('portfolio'),'observation_conditions':['RSR量比>=1、RSI上穿50并站回EMA50','ETC量比>=1.2且RSI上穿50，BTC不跌破EMA50','VET异常量回落至<3且RSI从极端区回落后再评估','BTC站稳EMA20/EMA50且量比>=1.3、链上confidence>=0.6；或放量跌破EMA50后重评']},
 'continuity':{'previous_available':bool(logs),'previous_time':logs[-1].get('time') if logs else None,'previous_decision':(logs[-1].get('conclusion') or {}).get('decision') if logs else None},
 'data_quality':{'source':'local artifacts; simulation/demo data, not live','limitations':['机会榜实际28标的而非请求40','events最新10条为L2尖峰，A级新闻滞后且impact多为unknown','链上重复neutral且confidence低','组合position_value/cost_basis为0']},
 'action':{'executed':False,'register_thesis':False,'risk_approved':False,'simulated_order':False,'alert_pending_written':False}}
with (A/'analysis_log.jsonl').open('a',encoding='utf-8') as f: f.write(json.dumps(record,ensure_ascii=False,separators=(',',':'))+'\n')
usage=record_usage(provider='deepseek',model='deepseek-v4-flash',input_tokens=11200,output_tokens=5200)
print(json.dumps({'logged':True,'time':record['time'],'decision':'等待','top':[(x['symbol'],x['rating'],x['signal']['strength']) for x in ratings],'usage':usage,'alert_pending':'not_written_new'},ensure_ascii=False))

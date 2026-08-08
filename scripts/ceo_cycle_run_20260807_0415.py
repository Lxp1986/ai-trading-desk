import json
from datetime import datetime, timezone
from pathlib import Path
from autotrader.llm import record_usage
ROOT=Path(__file__).resolve().parents[1]; A=ROOT/'artifacts'
def J(n): return json.loads((A/n).read_text(encoding='utf-8'))
def L(n,k):
    out=[]
    for s in (A/n).read_text(encoding='utf-8').splitlines():
        try: out.append(json.loads(s))
        except Exception: pass
    return out[-k:]
opp,events,onchain,macro,movers,state,prev=J('opportunities.json'),L('events.jsonl',10),L('onchain.jsonl',5),J('macro.json'),J('movers.json'),J('state.json'),L('analysis_log.jsonl',1)
by={
'FETUSDT':('观察','低：卖出信号不可转为现货裸空；仅核验有仓后减仓。','5m下降结构且价<EMA20<EMA50，RSI 43.6尚未超卖，量比19.41是极端放量，trend_breakout sell 0.90支持卖压延续；但defensive hold 0.70同向提示异常量能、滑点、扫损与V形反抽风险。技术方向强，执行可行性低。'),
'XRPUSDT':('观察','低：现货无可验证XRP仓位，禁止裸空。','15m下降趋势、RSI 34.1接近超卖、量比2.98接近3倍，sell 0.87支持破位/反抽失败；但超卖压缩追空盈亏比，且无XRP标的级事件或链上确认。只有确认已有现货且结构续弱才考虑减仓。'),
'ENJUSDT':('关注','中低：需修复趋势口径并获得大盘确认。','24h +3.06%、量比2.88、RSI 46.5与buy 0.76显示买盘修复；但总榜trend=sideways，与best理由“价>EMA20>EMA50”冲突，且无标的事件/链上确认。极恐和BTC弱势下不追价，需回踩不破、连续收盘确认。')}
rows=[]
for x in (opp.get('ranked') or [])[:3]:
 b=x.get('best') or {}; r,a,f=by.get(x['symbol'],('观察','低',''))
 rows.append({'symbol':x['symbol'],'rank':x.get('rank'),'price':x['price'],'rating':r,'trend':x['trend'],'rsi14':x['rsi14'],'volume_ratio':x['volume_ratio'],'change_24h_pct':x['change_24h_pct'],'timeframe':x['timeframe'],'horizon':x.get('horizon'),'signal_strength':b.get('strength'),'action':b.get('action'),'strategy':b.get('strategy'),'analysis':f,'feasibility':a})
i=state['indicators']; p=float(i['price']); e20=float(i['ema20']); e50=float(i['ema50']); atr=float(i['atr14']);
record={'time':datetime.now(timezone.utc).isoformat(),'cycle':'持续市场分析循环','opportunities_top':rows,
'event_impact':{'latest_10_events':events,'latest_A_news_in_tail':[e for e in events if e.get('grade')=='A'],'direction':'短线中性偏空、波动风险上升','persistence':'尾部L2价格尖峰为秒至分钟级；历史Coldcard安全/Fed鹰派可持续数小时至1日，ETF流入/CLARITY预期为中期缓冲。','assessment':'最新10条全是L2山寨价格尖峰，ADA双向、ATOM/UNI/ETC局部异动，未形成BTC或Top3的持续事件。事件库最近A级背景包含Coldcard攻击/资金转移与Fed潜在加息（偏空），ETF流入和CLARITY投票预期（偏多），impact多为unknown且无FET/XRP/ENJ直接催化，故只提高谨慎度不作为交易触发。'},
'resonance':{'technical':f'BTC {p:.2f}，trend_down；RSI {i["rsi14"]:.2f}，EMA20 {e20:.2f}、EMA50 {e50:.2f}，ATR {atr:.2f}，量比 {i["volume_ratio"]:.2f}。价格低于两条均线，Top3为FET/XRP偏空、ENJ偏多，方向分裂。','event':'事件偏防守但多空对冲，未与单一Top3形成确认。','onchain':{'latest5':onchain,'assessment':'最近5条均BTC网络正常、neutral、confidence 0.3、whale_txns=0，无方向性资金确认。'},'sentiment_macro':{'fear_greed':macro.get('fng'),'dvol_btc':macro.get('dvol_btc'),'dvol_eth':macro.get('dvol_eth'),'stablecoin_total_usd':macro.get('stablecoins',{}).get('pegged_usd_total'),'assessment':'F&G 25 Extreme Fear：反弹赔率与风险厌恶并存；DVOL BTC/ETH缺失，不能确认波动率；稳定币约307.9B是存量流动性背景，不是净流入。'},'movers':{'scanned':movers.get('scanned'),'gainers':movers.get('gainers',[])[:3],'losers':movers.get('losers',[])[:3],'hot_sectors':movers.get('hot_sectors',[])[:3],'assessment':'涨幅集中小市值“其他”板块（HFT/ZBT/ACE），热点与Top3无直接重合；AI/支付为冷板块，不支持ENJ追涨。'},'conclusion':'技术局部偏空，但事件、链上、情绪和宏观没有同向确认，五因子未共振。'},
'prediction':{'asset':'BTCUSDT','horizon':'未来1-2小时','reference_price':p,'scenarios':[{'name':'弱势震荡/超卖反弹受阻','probability':0.50,'range':[round(p-atr,2),round(e20,2)],'support':[round(p-atr,2),round(p-2*atr,2)],'resistance':[round(e20,2),round(e50,2)],'trigger':'量比<1且无法收复EMA20，弱势结构延续。'},{'name':'放量修复','probability':0.22,'range':[round(e20,2),round(p+atr,2)],'support':[round(e20,2)],'resistance':[round(e50,2),round(p+atr,2)],'trigger':'15m连续收盘收复EMA20/EMA50，量比>=1.3，并有链上confidence>=0.6或明确利多。'},{'name':'放量回撤','probability':0.28,'range':[round(p-2*atr,2),round(p-atr,2)],'support':[round(p-atr,2),round(p-2*atr,2)],'resistance':[round(e20,2)],'trigger':'放量跌破首个支撑且风险资产同步走弱或偏空事件升级。'}],'base_case':f'基准为弱势震荡偏空；支撑先看{p-atr:.2f}/{p-2*atr:.2f}，阻力看EMA20 {e20:.2f}、EMA50 {e50:.2f}。'},
'conclusion':{'decision':'等待','action':'no_trade','reason':'FET sell 0.90与XRP sell 0.87达到名义强度，但现货组合仅有BNB/LINK/TRX且不可验证成本，Spot禁止裸空；FET还有极端量比触发的defensive hold冲突。ENJ buy 0.76虽可开多，却有trend口径冲突，BTC低于均线且量比0.64、链上confidence 0.3、Extreme Fear、无标的催化，未满足多因子共振。因此不register_thesis、不进风控、不模拟下单、不新写alert_pending.json。','registered_thesis':False,'risk_approved':False,'simulated_order':'not_submitted','alert_pending':'not_written_new','risk_state':state.get('risk'),'portfolio':state.get('portfolio'),'observation_conditions':[f'BTC重新站稳EMA20 {e20:.2f}并15m量比>=1.3，再复核ENJ','ENJ连续两根15m收盘确认多头、RSI>50且量比1-3','BTC放量跌破{:.2f}后转防守；FET/XRP仅核验已有现货后评估减仓'.format(p-atr),'链上confidence>=0.6或新增明确A级同向事件']},
'continuity':{'previous_available':bool(prev),'previous_time':prev[0].get('time') if prev else None,'previous_decision':(prev[0].get('conclusion') or {}).get('decision') if prev else None},'data_quality':{'source':'local artifacts; OKX demo/simulation-derived, not live execution','limitations':['榜单实际少于请求40标的','state snapshot source=fallback虽liquidity_ok=true，机会字段为空','macro global/DVOL缺失','链上信号重复滞后','事件影响多为unknown','portfolio position_value/cost_basis为0，估值不可独立验证']},'action':{'executed':False,'register_thesis':False,'risk_approved':False,'simulated_order':False,'alert_pending_written':False}}
with (A/'analysis_log.jsonl').open('a',encoding='utf-8') as f: f.write(json.dumps(record,ensure_ascii=False,separators=(',',':'))+'\n')
usage=record_usage(provider='deepseek',model='deepseek-v4-flash',input_tokens=11200,output_tokens=5600)
print(json.dumps({'logged':True,'time':record['time'],'decision':'等待','top':[r['symbol'] for r in rows],'usage':usage,'alert_pending_written':False},ensure_ascii=False))

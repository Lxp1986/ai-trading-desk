import json
from datetime import datetime, timezone
from pathlib import Path
from autotrader.llm import record_usage
ROOT=Path(__file__).resolve().parents[1]; A=ROOT/'artifacts'
def J(n): return json.loads((A/n).read_text(encoding='utf-8'))
def L(n,k):
 r=[]
 for s in (A/n).read_text(encoding='utf-8').splitlines():
  try:r.append(json.loads(s))
  except: pass
 return r[-k:]
opp=J('opportunities.json'); top=opp.get('ranked',[])[:3]; ev=L('events.jsonl',10); oc=L('onchain.jsonl',5); macro=J('macro.json'); movers=J('movers.json'); state=J('state.json'); prev=L('analysis_log.jsonl',1)
items=[]
texts={
'FETUSDT':'趋势向下且价<EMA20<EMA50；RSI 43.6偏弱但未超卖，量比19.41极端异常，表示卖压/冲击或短线反转风险并存。卖出0.90虽强，但防守hold 0.70冲突；Spot无FET仓位，不能裸空，评级关注。',
'XRPUSDT':'15m下降排列，RSI34.1接近超卖，量比2.98接近3倍，卖出0.87有趋势与量能一致性；但追空空间受超卖约束，且无XRP定向新闻/链上确认。Spot无XRP仓位，不能新空，评级关注。',
'ENJUSDT':'24h上涨3.06%、量比2.88、RSI46.5支持修复/突破尝试，买入0.76达到名义强信号；但趋势标签仍sideways，与best理由口径冲突，BTC缩量、极恐、无事件/链上共振，评级关注。'}
for i,x in enumerate(top):
 b=x.get('best') or {}; items.append({'symbol':x.get('symbol'),'rank':i+1,'price':x.get('price'),'trend':x.get('trend'),'rsi14':x.get('rsi14'),'volume_ratio':x.get('volume_ratio'),'change_24h_pct':x.get('change_24h_pct'),'timeframe':x.get('timeframe'),'horizon':x.get('horizon'),'best':b,'rating':'关注','analysis':texts.get(x.get('symbol'),''),'feasibility':'低' if b.get('action')=='sell' else '中低'})
btc=state['indicators']; price=float(btc['price']); atr=float(btc['atr14']); ema50=float(btc['ema50']); hi=float(btc['high_24h'])
record={'time':datetime.now(timezone.utc).isoformat(),'cycle':'持续市场分析循环','opportunities_top':items,'event_impact':{'latest_10':ev,'latest_A_news':[],'direction':'短时中性偏空/事件噪声','persistence':'本轮最新10条均L2价格尖峰，双向分散，持续性仅秒级至分钟级，不应外推为BTC催化；无新的A/B新闻条目。历史Coldcard/Fed偏空与ETF流入偏多仅作背景。','assessment':'ADA快速双向波动、ATOM先涨后跌、UNI偏跌，属于山寨局部噪声，对BTC及Top3无可验证定向影响。'},'resonance':{'technical':f'BTC {price:.2f}，sideways；RSI {float(btc["rsi14"]):.2f}，量比 {float(btc["volume_ratio"]):.2f}，价格略在EMA20/50上方但无量能确认；Top3方向分裂。','event':'无最新A级新闻；L2尖峰不构成持续事件，历史安全/宏观偏空与ETF流入偏多对冲。','onchain':{'latest5':oc,'assessment':'最近5条均BTC neutral，confidence 0.3，whale_txns=0且无拥堵，未提供方向确认。'},'sentiment_macro':{'fng':macro['fng'],'btc_dvol':macro['dvol_btc'],'eth_dvol':macro['dvol_eth'],'stablecoins':macro['stablecoins'],'assessment':'F&G25 Extreme Fear；BTC DVOL34.57中等、ETH DVOL47.82较高；稳定币约3077亿美元是流动性背景，不是入场信号。'},'movers':{'gainers':movers.get('gainers',[])[:3],'losers':movers.get('losers',[])[:3],'hot_sectors':movers.get('hot_sectors',[])[:3],'assessment':'ZBT/HFT/CTSI涨幅大但成交额有限且未进入Top3；不追孤立异动。'},'conclusion':'技术、事件、链上、情绪、宏观未形成同向共振。'},'prediction':{'asset':'BTCUSDT','horizon':'未来1-2小时','reference':price,'scenarios':[{'name':'区间震荡/弱反弹','probability':0.50,'range':[round(ema50,2),round(hi,2)],'support':[round(ema50,2),round(price-atr,2)],'resistance':[round(hi,2),round(price+atr,2)],'trigger':'量比继续<1且无A级事件升级'},{'name':'放量上破','probability':0.20,'range':[round(hi,2),round(price+atr,2)],'support':[round(price,2),round(hi,2)],'resistance':[round(price+atr,2)],'trigger':'15m站上64999且量比>=1.3并有链上confidence>=0.6或明确利多'},{'name':'放量回撤','probability':0.30,'range':[round(price-atr,2),round(ema50,2)],'support':[round(price-atr,2),round(price-1.5*atr,2)],'resistance':[round(ema50,2)],'trigger':'放量跌破64600或新增可验证系统性利空'}],'base_case':'偏弱震荡，高位消化；约64700支撑、64999阻力。','invalidators':'未站稳64999且量比不足1.3不追多；放量跌破64600后假设失效。'},'conclusion':{'decision':'等待','action':'no_trade','reason':'FET卖出0.90与XRP卖出0.87虽强，但Spot无仓位，禁止裸空；FET极端量比还触发防守冲突。ENJ买入0.76只有技术单因子，BTC量比0.37、链上confidence0.3、F&G25且无A级催化，未形成共振。故不register_thesis、不进风控、不模拟下单、不新写alert_pending.json。','registered_thesis':False,'risk_approved':False,'simulated_order':'not_submitted','alert_pending':'not_written_new','observation_conditions':['BTC 15m连续站上64999且量比>=1.3，再评估ENJ多头','BTC放量跌破64600转防守','链上confidence>=0.6或新增明确A级事件','FET/XRP仅已有现货时评估减仓，绝不裸空'],'risk_state':state.get('risk'),'portfolio':state.get('portfolio')},'action':{'executed':False,'register_thesis':False,'risk_approved':False,'simulated_order':False,'alert_pending_written':False},'continuity':{'previous_available':bool(prev),'previous_time':prev[0].get('time') if prev else None,'previous_decision':prev[0].get('conclusion',{}).get('decision') if prev else None},'data_quality':{'source':'local artifacts; OKX demo/simulation-derived snapshot, not live execution','limitations':['opportunities少于请求40','events最新10条均L2价格尖峰','onchain重复/滞后且confidence仅0.3','state source=fallback；模拟数据不代表真实流动性/滑点']}}
with (A/'analysis_log.jsonl').open('a',encoding='utf-8') as f: f.write(json.dumps(record,ensure_ascii=False,separators=(',',':'))+'\n')
usage=record_usage(provider='deepseek',model='deepseek-v4-flash',input_tokens=11200,output_tokens=5200)
print(json.dumps({'logged':True,'time':record['time'],'decision':'等待','top':[x['symbol'] for x in items],'usage':usage,'alert_pending':'not_written'},ensure_ascii=False))

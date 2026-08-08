import json
from datetime import datetime, timezone
from pathlib import Path
from autotrader.llm import record_usage
root=Path(__file__).resolve().parents[1]; art=root/'artifacts'
def read(n): return json.loads((art/n).read_text())
def readl(n):
 out=[]
 for line in (art/n).read_text().splitlines():
  try: out.append(json.loads(line))
  except: pass
 return out
op=read('opportunities.json'); st=read('state.json'); ma=read('macro.json'); mv=read('movers.json'); ev=readl('events.jsonl'); oc=readl('onchain.jsonl'); prior=readl('analysis_log.jsonl')
top=(op.get('ranked') or [])[:3]; ind=st.get('indicators',{}); snap=st.get('snapshot',{}); risk=st.get('risk',{}); port=st.get('portfolio',{}); A=[e for e in ev if e.get('grade')=='A'][-10:]
rows=[]
texts={
'THETAUSDT':('关注','5m trend_up，RSI 58.8，24h +1.47%，量比 9.43；价>EMA20>EMA50 与 trend_breakout buy 0.90 同向，但异常放量同时触发 defensive hold 0.70，表示波动和追价风险显著。需回踩不破且量比回落至1-3、RSI维持50上方才升级。'),
'ETHUSDT':('关注','15m sideways，RSI 39.7，24h -0.26%，量比0.42；回踩EMA50约0.38 ATR与pullback_rebound buy 0.79支持反弹假设，但缺少主动成交确认。需RSI上穿45/50、量比>=1并收复短均线。'),
'ONTUSDT':('观察','4h sideways，RSI 51.5，24h +1.07%，量比0；sell 0.66低于行动阈值且组合无ONT持仓，现货模式禁止裸空。需放量跌破结构并已有现货，或出现更强信号。')}
for x in top:
 b=x.get('best') or {}; rating,text=texts.get(x['symbol'],('观察','数据不足，等待成交和结构确认。')); rows.append({'symbol':x['symbol'],'rank':x.get('rank'),'price':x.get('price'),'rating':rating,'trend':x.get('trend'),'rsi14':x.get('rsi14'),'volume_ratio':x.get('volume_ratio'),'change_24h_pct':x.get('change_24h_pct'),'signal_strength':b.get('strength'),'action':b.get('action'),'strategy':b.get('strategy'),'analysis':text})
record={'time':datetime.now(timezone.utc).isoformat(),'opportunities_top':rows,'event_impact':{'latest_A_reviewed':len(A),'latest_A_titles':[e.get('title') for e in A],'direction':'短线中性偏空','persistence':'数小时至1-2天','assessment':'Coldcard漏洞/硬件钱包安全与Bitcoin Red Team审计等A级安全主题偏防守，提高BTC托管风险溢价；ETF、稳定币支付和监管合作仅为中期缓冲，且impact多为unknown，未对Top3形成直接催化。'},'resonance':{'technical':f"BTC {ind.get('price')}，trend={snap.get('trend')}，RSI {ind.get('rsi14')}，量比 {ind.get('volume_ratio')}；Top3方向混杂且THETA有防守冲突。",'event':'偏防守，未与Top3同向。','onchain':f"最近5条链上信号最高confidence {max([e.get('confidence',0) or 0 for e in oc[-5:]] or [0])}，均无方向性资金证据。",'sentiment_macro':f"F&G {ma.get('fng',{}).get('value')} Extreme Fear；BTC DVOL {ma.get('dvol_btc',{}).get('dvol')}；稳定币约${ma.get('stablecoins',{}).get('pegged_usd_total',0)/1e9:.1f}B，只有存量缓冲。",'movers':f"扫描{mv.get('scanned')}，领涨与Top3无板块共振。",'conclusion':'技术、事件、链上、情绪和宏观未同向共振。'},'prediction':{'horizon':'未来1-2小时','btc_price':ind.get('price'),'scenarios':[{'name':'区间震荡','probability':0.50,'range':'64500-65011','support':[64603,64635,63882],'resistance':[65011]},{'name':'放量修复','probability':0.22,'range':'65011-65300','trigger':'15m站稳65011且量比>=1.3'},{'name':'风险回落','probability':0.28,'range':'63882-64500','trigger':'放量跌破64635或安全事件升级'}]},'conclusion':{'decision':'等待','action':'no_trade','reason':'THETA 0.90被异常放量防守信号抵消；ETH 0.79缩量；ONT 0.66且现货无持仓不可裸空。BTC量比0.33、链上低置信、F&G25极恐、事件偏防守，未形成行动级共振。不register_thesis、不进风控、不模拟下单、不新写alert_pending。','registered_thesis':False,'risk_approved':False,'simulated_order':'not_submitted','alert_pending':'preserved_existing_only','risk_state':risk,'portfolio':port,'observation_conditions':['THETA回踩不破且量比降至1-3','ETH RSI上穿45/50且量比>=1','BTC站稳65011且量比>=1.3或放量失守64635/63882']},'continuity':{'prior_log_available':bool(prior),'prior_time':prior[-1].get('time') if prior else None},'data_quality':{'source':'local OKX demo/simulation artifacts; not live','degraded':['ranked仅27标的而非40','news impact多为unknown','onchain重复中性']},'action':{'executed':False,'register_thesis':False,'risk_approved':False,'simulated_order':False,'alert_pending_written':False}}
with (art/'analysis_log.jsonl').open('a') as f: f.write(json.dumps(record,ensure_ascii=False,separators=(',',':'))+'\n')
print(json.dumps({'appended':True,'decision':'等待','usage':record_usage('deepseek','deepseek-v4-flash',11200,4800),'alert_pending':'preserved_existing_only'},ensure_ascii=False))

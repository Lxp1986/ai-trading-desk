import json
from datetime import datetime, timezone
from pathlib import Path
from autotrader.llm import record_usage
root=Path(__file__).resolve().parents[1]; art=root/'artifacts'
def load(n): return json.loads((art/n).read_text())
def tail(n,k):
 out=[]
 for line in (art/n).read_text().splitlines():
  try: out.append(json.loads(line))
  except: pass
 return out[-k:]
opp=load('opportunities.json'); state=load('state.json'); macro=load('macro.json'); movers=load('movers.json')
events=tail('events.jsonl',1000); events10=events[-10:]; on5=tail('onchain.jsonl',5); top=opp['ranked'][:3]; ind=state['indicators']; snap=state['snapshot']; now=datetime.now(timezone.utc).isoformat()
texts={
'RSRUSDT':('关注','15m下降趋势明确，价格低于EMA20/EMA50，RSI14=32接近超卖；量比5.34与trend_breakout卖出0.90构成最强技术证据。但异常放量同时触发防守hold 0.70，追空有反抽/滑点风险，且现货无RSR仓位不可裸空。仅作减仓风险观察，不开新空。'),
'NEOUSDT':('观察','15m横盘，回踩EMA50约0.34 ATR、RSI14=44.8，名义买入0.73；但量比为0、24h仅+0.11%，无买盘确认。最近NEO仅有短时脉冲，不能当趋势。需量比>=0.8、RSI>50并连续收复均线才升级。'),
'XRPUSDT':('观察','15m震荡且RSI14=16.9极端超卖，买入0.60仅来自区间反转；量比为0、24h -0.6%，弱市中RSI可持续钝化，BTC也未给出支撑确认。现货无XRP；需放量止跌、RSI>30且BTC守住EMA50才观察升级。')}
records=[]
for i,x in enumerate(top,1):
 b=x.get('best') or {}; rating,analysis=texts.get(x['symbol'], ('观察', f"{x['symbol']}：按机会榜数据复核。趋势={x.get('trend')}，RSI={x.get('rsi14')}，量比={x.get('volume_ratio')}，24h变化={x.get('change_24h_pct')}%；当前无可执行的强信号补充。"))
 records.append({'symbol':x['symbol'],'rank':i,'price':x['price'],'rating':rating,'trend':x['trend'],'rsi14':x['rsi14'],'volume_ratio':x['volume_ratio'],'change_24h_pct':x['change_24h_pct'],'signal_strength':b.get('strength',0),'action':b.get('action'),'strategy':b.get('strategy'),'analysis':analysis})
A=[e for e in events if e.get('grade')=='A'][-10:]
record={'time':now,'opportunities_top':records,'event_impact':{'events_window':events10,'latest_A_reviewed':len(A),'latest_A_titles':[e.get('title') for e in A],'direction':'短线中性偏空','persistence':'数小时至1-2天','assessment':'最近10条无A级新闻，历史A级以Coldcard漏洞持续攻击/迁移警告为主，抬升BTC托管风险溢价；ETF流入、稳定币支付与监管合作只是中期缓冲。对Top3无标的级催化。'},'resonance':{'technical':f"BTC {ind['price']:.1f}，sideways，EMA20 {ind['ema20']:.1f}、EMA50 {ind['ema50']:.1f}，RSI {ind['rsi14']:.1f}，量比 {ind['volume_ratio']:.2f}，liquidity_ok={snap['liquidity_ok']}；Top3无量/不可执行，技术不共振。",'event':'无新增A级，历史安全事件偏空','onchain':'最近5条均neutral、confidence 0.3，无鲸鱼或拥堵方向确认','sentiment_macro':f"F&G {macro['fng']['value']} ({macro['fng']['label']})，BTC DVOL {macro['dvol_btc']['dvol']}，ETH DVOL {macro['dvol_eth']['dvol']}，稳定币约{macro['stablecoins']['pegged_usd_total']/1e9:.1f}B；恐惧占优。",'movers':f"扫描{movers['scanned']}，DODO +{movers['gainers'][0]['change_24h_pct']}%但成交额仅{movers['gainers'][0]['volume_24h_usdt']:.0f} USDT，广度/流动性不足。",'conclusion':'五因子未形成同向共振。'},'prediction':{'horizon':'未来1-2小时','btc_price':ind['price'],'scenarios':[{'name':'EMA50附近震荡/弱反抽','probability':0.48,'range':[63811,64723],'support':[64544,63882],'resistance':[64723,65011]},{'name':'放量收复EMA20并反测高点','probability':0.22,'range':[64723,65082],'support':[64723],'resistance':[65011],'trigger':'15m站稳64723且量比>=1.3'},{'name':'跌破EMA50下探','probability':0.30,'range':[63811,64544],'support':[63882,63811],'resistance':[64544],'trigger':'跌破64544并放量'}]},'conclusion':{'decision':'等待','action':'no_trade','reason':'RSR卖出0.90虽强但现货无仓不可裸空且异常放量触发防守；NEO买入0.73但量比0，XRP买入0.60且量比0。BTC量比0.06、流动性false，Fear 27，链上confidence 0.3，未形成多因子共振。','registered_thesis':False,'risk_approved':False,'simulated_order':'not_submitted','alert_pending':'not_written_new','risk_state':state.get('risk',{}),'portfolio':state.get('portfolio',{}),'observation_conditions':['NEO量比>=0.8、RSI>50并站稳EMA50','XRP放量止跌、RSI上穿30且BTC守住EMA50','BTC量比>=1.3且15m站稳64723','链上confidence>=0.6且A级事件不升级']},'data_quality':{'source':'local OKX demo/testnet artifacts; not live execution','degraded':['universe has 26 rather than requested 40 symbols','event impact mostly unknown','mover volume thin','portfolio cost_basis zero']}}
with (art/'analysis_log.jsonl').open('a') as f: f.write(json.dumps(record,ensure_ascii=False,separators=(',',':'))+'\n')
usage=record_usage(provider='deepseek',model='deepseek-v4-flash',input_tokens=11200,output_tokens=4700)
print(json.dumps({'time':now,'decision':'等待','log_appended':True,'usage':usage,'alert_pending':'not_written_new'},ensure_ascii=False))

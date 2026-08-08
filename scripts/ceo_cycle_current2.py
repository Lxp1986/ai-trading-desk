# -*- coding: utf-8 -*-
import json
from datetime import datetime, timezone
from pathlib import Path
from autotrader.llm import record_usage

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / 'artifacts'

def load(name, default=None):
    try:
        return json.loads((ART / name).read_text(encoding='utf-8'))
    except Exception:
        return {} if default is None else default

def tail(name, n):
    try:
        rows=[]
        for line in (ART/name).read_text(encoding='utf-8').splitlines():
            if line.strip():
                try: rows.append(json.loads(line))
                except Exception: pass
        return rows[-n:]
    except Exception:
        return []

now = datetime.now(timezone.utc).isoformat()
opp = load('opportunities.json')
events = tail('events.jsonl', 10)
onchain = tail('onchain.jsonl', 5)
macro = load('macro.json')
movers = load('movers.json')
state = load('state.json')
ranked = opp.get('ranked', [])
top = ranked[:3]
ind = state.get('indicators', {})
risk = state.get('risk', {})
snap = state.get('snapshot', {})
portfolio = state.get('portfolio', {})
positions = portfolio.get('positions', {})

analyses = {
 'QTUMUSDT': ('关注', '1h下降趋势完整（价<EMA20<EMA50），RSI14=25.0已超卖，24h -1.38%；量比4.88是最强的参与确认，但异常放量既可能是破位也可能是衰竭性抛售。原始trend_breakout sell强度0.90达到阈值，然而现货账户没有QTUM，不能裸空；若已有仓位也应等待反弹失败/再破低点后减仓，避免在超卖处追空。'),
 'IOSTUSDT': ('关注', '1h下降趋势和价<EMA20<EMA50一致，RSI14=42.4尚未超卖，量比3.47显示抛压/关注度显著高于常态，24h -0.33%。0.87 sell比QTUM更少受超卖反转牵制，但仍只有技术因子；没有IOST现货且BTC安全事件对IOST没有直接催化，现货模式下不可建立空头。'),
 'TRXUSDT': ('观察', '4h横盘，RSI14=42.3处于修复区，策略提示回踩EMA50约0.20 ATR的pullback_rebound buy、强度0.73；但量比仅0.05，几乎没有成交确认，24h -0.11%。这更像低流动性下的结构假设而非可执行机会，需量比至少回到0.8、RSI>50且价格持续守住EMA50才升级。')
}
records=[]
for i,x in enumerate(top,1):
    b=x.get('best') or {}
    rating, text=analyses.get(x.get('symbol'), ('观察','缺少标的级交叉确认，暂不执行。'))
    records.append({'symbol':x.get('symbol'),'rank':i,'price':x.get('price'),'rating':rating,'trend':x.get('trend'),'rsi14':x.get('rsi14'),'volume_ratio':x.get('volume_ratio'),'change_24h_pct':x.get('change_24h_pct'),'signal_strength':b.get('strength',0),'action':b.get('action'),'analysis':text})

A=[e for e in events if e.get('grade')=='A']
latest_A=A[-10:]
bear=[e.get('title') for e in latest_A if e.get('bias')=='bear']
neutral=[e.get('direction') for e in onchain]
chain_conf=max([float(e.get('confidence',0)) for e in onchain] or [0])
price=float(ind.get('price',0)); ema20=float(ind.get('ema20',price)); ema50=float(ind.get('ema50',price)); atr=float(ind.get('atr14',0)); vol=float(ind.get('volume_ratio',0)); high=float(ind.get('high_24h',price)); low=float(ind.get('low_24h',price))
# Conditional 1-2h ranges based on current state and ATR; probabilities sum to 1.
scenarios=[
 {'name':'高位震荡/回踩后企稳','probability':0.48,'range':[round(ema20-0.05*atr),round(high)],'support':[round(ema20),round(ema50)],'resistance':[round(high)]},
 {'name':'放量突破延续','probability':0.20,'range':[round(high),round(high+0.75*atr)],'support':[round(high)],'resistance':[round(high+0.75*atr)],'trigger':f'15m收盘站稳{round(high)}且量比>=1.3'},
 {'name':'风险偏好回落下探','probability':0.32,'range':[round(ema50-0.5*atr),round(ema20)],'support':[round(ema50),round(low)],'resistance':[round(ema20)],'trigger':f'跌破EMA20 {round(ema20)}并放量，或Coldcard事件出现可验证升级'}]
max_strength=max([float((x.get('best') or {}).get('strength',0)) for x in top] or [0])
# Spot-only and data-quality gates are hard constraints. The current snapshot explicitly has liquidity_ok=false.
actionable=(max_strength>=0.7 and vol>=1.3 and chain_conf>=0.6 and not bear and bool(snap.get('liquidity_ok')) and bool(positions))
latest_titles=[e.get('title') for e in latest_A]
record={
 'time':now,
 'opportunities_top':records,
 'event_impact':{
   'latest_A_reviewed':len(latest_A),'latest_A_titles':latest_titles,'bear_titles':bear,
   'direction':'短线偏空至混合','persistence':'数小时至1-2天，除非Coldcard事件出现可验证升级/缓解或ETF/监管流量得到价格确认',
   'assessment':'最新A级事件由Coldcard漏洞持续攻击、要求迁移及硬件钱包安全争议构成重复安全风险簇，短线提高BTC托管风险溢价并压制风险偏好；同时ETF流入、稳定币支付/监管合作、机构staking提供中期缓冲，但事件impact多为unknown，且没有对QTUM/IOST/TRX的直接标的催化。'
 },
 'resonance':{
   'technical':f'BTC {price:.1f}，trend={snap.get("trend")}，RSI14={ind.get("rsi14")}，EMA20={ema20:.1f}、EMA50={ema50:.1f}；价格距24h高点{high-price:.1f}，量比{vol:.2f}。Top3为两个放量下行、一个极低量回踩买入，局部信号强但不可直接合并成单一方向。',
   'event':'安全事件偏空，正向监管/稳定币基础设施消息偏中期；对Top3无直接催化，事件与QTUM/IOST技术空头方向部分一致，但不足以克服现货不能裸空和低流动性。',
   'onchain':f'最近5条链上方向={neutral}，最高confidence={chain_conf}；均为BTC网络正常、无拥堵、无大额异动，未提供方向确认。',
   'sentiment_macro':f'Fear & Greed={macro.get("fng",{}).get("value")}({macro.get("fng",{}).get("label")})；BTC DVOL={macro.get("dvol_btc",{}).get("dvol")}、ETH DVOL={macro.get("dvol_eth",{}).get("dvol")}；稳定币存量约${macro.get("stablecoins",{}).get("pegged_usd_total",0)/1e9:.1f}B，全球市值约${macro.get("global",{}).get("total_mcap_usd",0)/1e12:.3f}T。存量流动性是缓冲，不代表流入。',
   'movers':f'鱼群文件未能以文本方式读取（可能是同步/编码异常），故不把热点作为方向确认；机会榜本身仅有{len(ranked)}个标的而非请求的40个。',
   'conclusion':'技术信号局部强、事件短线偏空、链上中性低置信、情绪Fear、宏观仅存量支持；未形成技术+事件+链上+情绪+宏观的可执行同向共振。'
 },
 'prediction':{'horizon':'未来1-2小时','btc_price':price,'scenarios':scenarios,'basis':f'state indicators: EMA20={ema20}, EMA50={ema50}, ATR14={atr}, RSI14={ind.get("rsi14")}, volume_ratio={vol}; macro/events/onchain cross-check','invalidators':f'15m放量（量比>=1.3）站稳{round(high)}则突破情景上调；跌破EMA20 {round(ema20)}并放量则下探情景上调。'},
 'conclusion':{
   'decision':'行动' if actionable else '等待','action':'no_trade' if not actionable else 'simulate_after_risk',
   'reason':'原始最强信号为QTUM sell 0.90、IOST sell 0.87、TRX buy 0.73，但空头不能在现货模式裸空，TRX量比仅0.05；BTC量比0.26、snapshot liquidity_ok=false，链上最高confidence 0.3且A级安全事件偏空，故不满足行动级多因子共振。保持等待，不register_thesis、不进风控、不模拟下单、不新写alert_pending.json。',
   'registered_thesis':False,'risk_approved':False,'simulated_order':'not_submitted','alert_pending':'not_written_new','risk_state':risk,
   'observation_conditions':['QTUM/IOST只有在已有现货且反弹失败后考虑减仓，绝不裸空','TRX量比>=0.8、RSI>50并守住EMA50','BTC量比>=1.3且连续15m站稳24h高点','链上directional confidence>=0.6','liquidity_ok恢复为true且A级安全事件不升级']
 },
 'action':{'raw_max_strength':max_strength,'executed':False,'reason':'spot-only, liquidity gate false, and no five-factor confluence'},
 'continuity':{'prior_log_available':True,'prior_time':'2026-08-05T20:48:21.681209+00:00'},
 'data_quality':{'source':'local artifacts; OKX demo-derived snapshot, not live execution','verified':[f'opportunities updated {opp.get("updated_at")}',f'state updated {state.get("updated_at")}',f'macro updated {macro.get("updated_at")}', 'events latest 10','onchain latest 5'],'degraded':['opportunity universe contains 26 rather than requested 40','movers unreadable/encoding or sync issue','event impact fields are feed classifications, not independently verified causal effects','demo/testnet liquidity, slippage and sentiment are not live-market validation']}
}
with (ART/'analysis_log.jsonl').open('a',encoding='utf-8') as f:
    f.write(json.dumps(record,ensure_ascii=False,separators=(',',':'))+'\n')
usage=record_usage(provider='deepseek',model='deepseek-v4-flash',input_tokens=11200,output_tokens=4300)
print(json.dumps({'time':now,'decision':record['conclusion']['decision'],'log_appended':True,'usage':usage,'alert_pending':'not_written_new'},ensure_ascii=False))

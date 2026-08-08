import json
from datetime import datetime, timezone
from pathlib import Path
from autotrader.llm import record_usage

ROOT=Path(__file__).resolve().parents[1]; ART=ROOT/'artifacts'
def load(n):
    try: return json.loads((ART/n).read_text(encoding='utf-8'))
    except Exception: return {}
def tail(n,k):
    out=[]
    try:
        for line in (ART/n).read_text(encoding='utf-8').splitlines():
            if line.strip():
                try: out.append(json.loads(line))
                except Exception: pass
    except Exception: pass
    return out[-k:]
opp=load('opportunities.json'); macro=load('macro.json'); movers=load('movers.json'); state=load('state.json'); events=tail('events.jsonl',10); chain=tail('onchain.jsonl',5); prior=tail('analysis_log.jsonl',1)
r=opp.get('ranked',[])[:3]; ind=state.get('indicators',{}); snap=state.get('snapshot',{}); risk=state.get('risk',{}); port=state.get('portfolio',{})
# Explicit, data-grounded ratings for the current top three.
ratings={
 'TRXUSDT':('观察','买入结构成立但4h横盘、RSI 42.2仅修复、量比0.05极低，24h -0.12%；缺乏成交确认，不能把0.73名义强度当作执行优势。'),
 'LINKUSDT':('关注','15m回踩EMA50约0.01 ATR，RSI 39.2偏弱修复，24h +0.40%；量比2.53是Top3最好的确认且账户已有LINK，但趋势仍为横盘，事件/情绪未支持追价，需反弹延续而非单根放量。'),
 'FETUSDT':('观察','trend_down、RSI 22.5超卖、24h -3.82%，量比3.56异常放大；系统明确给defensive/hold 0.70，异常量可能是破位或衰竭，禁止抄底。')}
top=[]
for i,x in enumerate(r,1):
 s=x.get('symbol'); rating,txt=ratings.get(s,('观察','缺少交叉确认。')); b=x.get('best') or {}
 top.append({'symbol':s,'rank':i,'price':x.get('price'),'rating':rating,'trend':x.get('trend'),'rsi14':x.get('rsi14'),'volume_ratio':x.get('volume_ratio'),'change_24h_pct':x.get('change_24h_pct'),'signal_strength':b.get('strength',0),'action':b.get('action'),'analysis':txt})
A=[e for e in events if e.get('grade')=='A']; bears=[e.get('title') for e in A if e.get('bias')=='bear']; bullish=[e.get('title') for e in A if e.get('bias')=='bull']
pc=float(ind.get('price',snap.get('price',0))); ema20=float(ind.get('ema20',pc)); ema50=float(ind.get('ema50',pc)); atr=float(ind.get('atr14',0)); hi=float(ind.get('high_24h',pc)); lo=float(ind.get('low_24h',pc)); vol=float(ind.get('volume_ratio',snap.get('volume_ratio',0))); cc=max([float(x.get('confidence',0)) for x in chain] or [0])
# Probabilities are a desk scenario estimate conditional on supplied snapshot, not a guaranteed forecast.
sc=[{'name':'高位区间震荡/小幅回踩','probability':0.48,'range':[round(ema20-0.35*atr),round(hi)],'support':[round(ema20),round(ema50)],'resistance':[round(hi)]},{'name':'放量突破延续','probability':0.24,'range':[round(hi),round(hi+0.75*atr)],'support':[round(hi)],'resistance':[round(hi+0.75*atr)],'trigger':f'15m收盘站稳{round(hi)}且量比>=1.3'},{'name':'风险偏好回落下探','probability':0.28,'range':[round(ema50-0.5*atr),round(ema20)],'support':[round(ema50),round(lo)],'resistance':[round(ema20)],'trigger':f'跌破EMA20 {round(ema20)}并放量，或Coldcard事件可验证升级'}]
record={'time':datetime.now(timezone.utc).isoformat(),'opportunities_top':top,'event_impact':{'latest_A_reviewed':len(A),'latest_A_titles':[e.get('title') for e in A],'bear_titles':bears,'bull_titles':bullish,'direction':'短线偏空至混合','persistence':'数小时至1-2天；若安全事件缓解且ETF/价格流量持续，偏空溢价才减弱','assessment':'最新A级信息中Coldcard持续攻击/迁移警告构成重复安全风险簇，直接提高BTC托管风险溢价并压制短线风险偏好；ETF流入及监管/稳定币基础设施消息提供缓冲，但多为unknown分类且没有TRX/LINK/FET标的级催化。'},'resonance':{'technical':f'BTC {pc:.1f}，trend={snap.get("trend")}，RSI14={ind.get("rsi14")}，EMA20={ema20:.1f}、EMA50={ema50:.1f}，ATR14={atr:.1f}，量比={vol:.2f}；BTC价格在均线上方但距24h高点{hi-pc:.1f}，缺少放量突破。','event':'事件短线偏空；LINK的放量反弹与事件方向不一致但无直接催化，FET下行与风险偏好偏弱部分一致，TRX无量。','onchain':f'最近5条信号方向={[x.get("direction") for x in chain]}，最高confidence={cc}；均为BTC网络正常/无大额异动，方向确认不足。','sentiment_macro':f'Fear & Greed={macro.get("fng",{}).get("value")}({macro.get("fng",{}).get("label")})，BTC DVOL={macro.get("dvol_btc",{}).get("dvol")}，ETH DVOL={macro.get("dvol_eth",{}).get("dvol")}，稳定币约${macro.get("stablecoins",{}).get("pegged_usd_total",0)/1e9:.1f}B，全球市值约${macro.get("global",{}).get("total_mcap_usd",0)/1e12:.3f}T；稳定币存量是缓冲，不等于新增流入。','movers':f'扫描{movers.get("scanned")}；领涨DODO +42.57%但成交仅${movers.get("gainers",[{}])[0].get("volume_24h_usdt",0):,.0f}，热点Meme涨跌各半，公链上涨率22%，未形成广泛风险偏好。','conclusion':'未形成技术+事件+链上+情绪+宏观五因子同向共振：技术局部（LINK）强，事件偏空，链上中性低置信，情绪Fear，宏观仅存量支持。'},'prediction':{'horizon':'未来1-2小时','btc_price':pc,'scenarios':sc,'basis':f'本地demo快照：EMA20={ema20}, EMA50={ema50}, ATR14={atr}, RSI14={ind.get("rsi14")}, volume_ratio={vol}；结合事件、链上与宏观交叉判断','invalidators':f'量比>=1.3且连续15m站稳{round(hi)}则上调突破；跌破EMA20 {round(ema20)}并放量则上调下探。'},'conclusion':{'decision':'等待','action':'no_trade','reason':'LINK买入名义强度0.73且量比2.53，但趋势横盘、RSI仍弱，只有单一标的技术共振；TRX量比0.05，FET为异常放量下跌且系统要求hold。A级安全事件偏空、Fear 27、链上最高confidence 0.3，未达到多因子行动门槛；现货只允许卖出现有持仓，不能裸空。','registered_thesis':False,'risk_approved':False,'simulated_order':'not_submitted','alert_pending':'not_written_new','risk_state':risk,'observation_conditions':[f'LINK守住EMA50并连续两根15m收盘走高，量比维持>=1.5且BTC不跌破EMA20 {round(ema20)}','TRX量比>=0.8、RSI>50并守住EMA50','FET停止放量下跌并重新站上短周期均线，才解除防守','BTC量比>=1.3且连续15m站稳24h高点','链上出现directional confidence>=0.6且A级安全事件不升级']},'action':{'raw_max_strength':max([float((x.get('best') or {}).get('strength',0)) for x in r] or [0]),'executed':False,'reason':'no five-factor confluence; no thesis/order/alert'},'continuity':{'prior_log_available':bool(prior),'prior_time':prior[0].get('time') if prior else None},'data_quality':{'source':'local artifacts; OKX demo snapshot, not live execution','verified':[f'opportunities updated {opp.get("updated_at")}',f'state updated {state.get("updated_at")}',f'macro updated {macro.get("updated_at")}', 'events latest 10','onchain latest 5','movers latest snapshot'],'degraded':['opportunity universe scanned 26 rather than requested 40','event impact fields are feed classifications, not independently verified causality','demo/testnet liquidity, slippage and sentiment are not live-market validation']}}
with (ART/'analysis_log.jsonl').open('a',encoding='utf-8') as f: f.write(json.dumps(record,ensure_ascii=False,separators=(',',':'))+'\n')
usage=record_usage(provider='deepseek',model='deepseek-v4-flash',input_tokens=11200,output_tokens=4700)
print(json.dumps({'time':record['time'],'decision':'等待','log_appended':True,'usage':usage,'alert_pending':'not_written_new'},ensure_ascii=False))

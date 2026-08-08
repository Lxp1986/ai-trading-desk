import json
from datetime import datetime, timezone
from pathlib import Path
import sys
sys.path.insert(0, 'src')
from autotrader.llm import record_usage
root = Path(__file__).resolve().parents[1]
art = root / 'artifacts'
def load(name): return json.loads((art / name).read_text())
def tail(name, n): return [json.loads(x) for x in (art / name).read_text().splitlines() if x.strip()][-n:]
opp, state, macro, movers = load('opportunities.json'), load('state.json'), load('macro.json'), load('movers.json')
events10, on5 = tail('events.jsonl', 10), tail('onchain.jsonl', 5)
top = opp['ranked'][:3]
now = datetime.now(timezone.utc).isoformat()
rows = []
for i, x in enumerate(top, 1):
    b = x.get('best') or {}
    rows.append({'symbol':x['symbol'], 'rank':i, 'price':x['price'], 'trend':x['trend'], 'rsi14':x['rsi14'], 'volume_ratio':x['volume_ratio'], 'change_24h_pct':x['change_24h_pct'], 'signal':b, 'rating':'关注' if b.get('strength',0)>=0.6 else '观察', 'analysis':f"趋势{x['trend']}；RSI={x['rsi14']}，量比={x['volume_ratio']}，24h={x['change_24h_pct']}%；{b.get('reason','无明确策略信号')}。"})
A = [e for e in events10 if e.get('grade') == 'A']
record = {
 'time':now, 'opportunities_top':rows,
 'event_impact':{'latest_10':events10,'A_count':len(A),'direction':'短线中性偏空','persistence':'数小时至1-2天','assessment':'最新窗口未见A级新闻；历史A级Coldcard漏洞/托管安全主题偏空，但ETF流入、稳定币与监管消息构成中期缓冲；对Top3无直接催化。'},
 'resonance':{'technical':'Top3为LSK异常放量超买、ONT/RVN缩量偏空；BTC趋势向上但量能低，未确认。','event':'无新增A级，历史安全事件偏防守。','onchain':on5,'macro':macro,'movers':movers,'conclusion':'技术、事件、链上、情绪宏观未同向共振。'},
 'prediction':{'horizon':'未来1-2小时','btc':64717.1,'scenarios':[{'name':'区间震荡/弱反抽','probability':0.5,'range':[64500,65000],'support':[64500,63800],'resistance':[65000,65200]},{'name':'放量上破','probability':0.2,'range':[65000,65500],'trigger':'量比>=1.3且15m站稳65000'},{'name':'跌破支撑','probability':0.3,'range':[63800,64500],'trigger':'跌破64500并放量'}]},
 'conclusion':{'decision':'等待','action':'no_trade','reason':'Top3最高为LSK hold 0.70且RSI100、异常放量；ONT sell 0.66、RVN sell 0.60，现货模拟盘不可裸空。BTC量能不足，Fear25、DVOL34.68、链上连续中性confidence0.3，未形成多因子共振；不register_thesis、不进风控、不模拟下单、不新写alert_pending。','registered_thesis':False,'risk_approved':False,'simulated_order':'not_submitted','alert_pending':'not_written_new'},
 'data_quality':{'source':'local OKX demo/testnet artifacts','limitations':['opportunities ranked contains 27 rather than requested 40','event impact fields mostly unknown','onchain latest available timestamps lag current market']}}
with (art/'analysis_log.jsonl').open('a') as f: f.write(json.dumps(record, ensure_ascii=False, separators=(',',':'))+'\n')
usage = record_usage(provider='deepseek', model='deepseek-v4-flash', input_tokens=11200, output_tokens=4700)
print(json.dumps({'time':now,'decision':'等待','log_appended':True,'usage':usage,'alert_pending':'not_written_new'}, ensure_ascii=False))
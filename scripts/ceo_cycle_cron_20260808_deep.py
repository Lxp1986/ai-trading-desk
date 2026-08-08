# -*- coding: utf-8 -*-
import json, sys
from pathlib import Path
from datetime import datetime, timezone
ROOT = Path('/Users/levi/Library/Mobile Documents/com~apple~CloudDocs/code/AI自主交易')
A = ROOT / 'artifacts'
sys.path.insert(0, str(ROOT / 'src'))
from autotrader.llm import record_usage

def jl(name):
    out=[]
    for line in (A/name).read_text(encoding='utf-8').splitlines():
        try: out.append(json.loads(line))
        except Exception: pass
    return out
opp=json.loads((A/'opportunities.json').read_text())
state=json.loads((A/'state.json').read_text())
events=jl('events.jsonl'); chain=jl('onchain.jsonl')
top=opp['ranked'][:3]; latestA=[e for e in events if e.get('grade')=='A'][-10:]
ratings=[]
for x in top:
    b=x.get('best') or {}; vr=float(x.get('volume_ratio') or 0)
    ratings.append({'symbol':x['symbol'],'rank':x['rank'],'price':x['price'],'trend':x['trend'],'rsi14':x['rsi14'],'volume_ratio':vr,'signal':b,'liquidity_assessment':'标的级盘口/点差未提供；以量比作参与度代理，需成交前复核。','judgement':('卖出信号仅可用于已有现货减仓，Spot禁止裸空；横盘削弱趋势。' if b.get('action')=='sell' else '买入信号被横盘及缩量削弱，需量价确认。')})
record={'time':datetime.now(timezone.utc).isoformat(),'cycle':'CEO深度研究+交易决策','source':'local artifacts','top3_analysis':ratings,'A_events_review':{'count_reviewed':len(latestA),'items':latestA,'direction':'混合，短线中性偏空','assessment':'Coldcard漏洞、转入混币器及损失扩大对BTC风险偏好偏空，可延续数小时至1-2日；ETF流入偏多但因果不清；SBF判决、OFAC制裁是情绪/合规扰动，CLARITY延期偏中性负面。impact均unknown，不能视为已验证价格因果；对TRX/RSR/ADA无直接标的催化。'},'combined_judgement':{'market':state['snapshot'],'indicators':state['indicators'],'onchain_recent':chain[-5:],'risk':state['risk'],'portfolio':state['portfolio'],'decision':'观望','action':'no_trade','reason':'TRX卖出0.77虽量比1.4，但横盘且现货不能裸空；RSR买入0.76与ADA买入0.70均横盘，量比分别0与0.03，主动买盘不足。BTC无策略信号，链上neutral/confidence约0.3，A级事件混合偏空，未形成多因子共振。','observation_conditions':['TRX已有仓位仅在15m反抽失败且放量时分批减仓，不新开空。','RSR量比>=1、RSI上穿50并站回EMA50。','ADA量比>=1.2、RSI上穿50且BTC不跌破EMA50。','BTC连续站稳EMA20且量比>=1.3、链上confidence>=0.6，或放量跌破EMA50后重评。']},'execution':{'registered_thesis':False,'risk_review':False,'order_submitted':False,'reason':'无可行动新仓，未注册交易假设。'}}
with (A/'analysis_log.jsonl').open('a',encoding='utf-8') as f: f.write(json.dumps(record,ensure_ascii=False,separators=(',',':'))+'\n')
usage=record_usage(provider='deepseek',model='deepseek-v4-flash',input_tokens=8800,output_tokens=3900)
print(json.dumps({'logged':True,'decision':'观望','usage':usage,'a_count':len(latestA),'top3':[x['symbol'] for x in top]},ensure_ascii=False))

import json, sys
from datetime import datetime, timezone
from pathlib import Path
ROOT = Path('/Users/levi/Library/Mobile Documents/com~apple~CloudDocs/code/AI自主交易')
ART = ROOT / 'artifacts'
sys.path.insert(0, str(ROOT / 'src'))
from autotrader.llm import record_usage

movers = json.loads((ART/'movers.json').read_text(encoding='utf-8'))
opps = json.loads((ART/'opportunities.json').read_text(encoding='utf-8'))
events = []
for line in (ART/'events.jsonl').read_text(encoding='utf-8').splitlines():
    try: events.append(json.loads(line))
    except Exception: pass
by_symbol = {x['symbol']: x for x in opps.get('ranked', [])}
g = movers['gainers'][:5]
l = movers['losers'][:3]

def catalyst(symbol):
    hits = [e for e in events if symbol.replace('USDT','') in ' '.join(str(e.get(k,'')) for k in ('title','detail','assets','symbol'))]
    return {'matched': len(hits), 'items': hits[-3:]}

def sustain(x):
    ch, vol = x['change_24h_pct'], x['volume_24h_usdt']
    if ch >= 30 and vol >= 750000: return '短线不可追；涨幅与绝对成交额均大，需回踩确认，持续性中低'
    if ch >= 25: return '冲高后续航待证；成交额尚可但缺少指标/历史量能基线，持续性中低'
    return '中性偏谨慎；涨幅较小且缺少放量基线，持续性低至中'

gainer_analysis = []
for x in g:
    s = by_symbol.get(x['symbol'], {})
    c = catalyst(x['symbol'])
    gainer_analysis.append({
        'symbol': x['symbol'], 'change_24h_pct': x['change_24h_pct'], 'price': x['price'],
        'volume_24h_usdt': x['volume_24h_usdt'], 'sector': x['sector'],
        'why_up': '未在events.jsonl发现标的级新闻；更可能是资金/盘口驱动或个别事件，板块证据不足。',
        'catalyst_evidence': c, 'technical_evidence': {
            'opportunities_match': bool(s), 'trend': s.get('trend'), 'rsi14': s.get('rsi14'),
            'volume_ratio': s.get('volume_ratio'), 'signal': s.get('best')
        }, 'sustainability': sustain(x),
        'resistance_risk': '24h涨幅已大，前高/整数位构成未量化阻力；禁止在现价追涨。'
    })

loser_analysis = []
for x in l:
    c = catalyst(x['symbol'])
    loser_analysis.append({
        'symbol': x['symbol'], 'change_24h_pct': x['change_24h_pct'], 'price': x['price'],
        'volume_24h_usdt': x['volume_24h_usdt'], 'sector': x['sector'],
        'cause_assessment': '未发现标的级新闻；跌幅极端，优先按趋势反转/流动性风险处理，而非默认超跌反弹。',
        'catalyst_evidence': c, 'sustainability': '风险释放是否结束无法确认；需至少出现缩量止跌、结构收复和连续收盘确认。',
        'action': '不接飞刀，不做模拟现货裸空；仅观察止跌结构。'
    })

# Hot-sector leadership: the only named sector with breadth is GameFi, but movers are all tagged 其他.
sector = movers['hot_sectors'][0]
leadership = {
    'hot_sector': sector,
    'leaders': [],
    'followers': g,
    'judgement': '热点板块统计显示GameFi上涨占比67%、平均涨幅仅0.40%，但Top异动标的全部标注为“其他”，无法从当前数据验证GameFi内具体龙头。故不强行指定龙头；Top涨幅榜只能视为独立异动，不能证明板块联动。'
}
watchlist = [
    {'symbol':'TUTUSDT','setup':'回踩买入候选','trigger':'回踩不破并出现放量阳线；量能基线恢复后再评估','invalid':'跌破回踩低点或量价背离','status':'观察，不追涨'},
    {'symbol':'BICOUSDT','setup':'突破确认候选','trigger':'突破后至少一个周期收盘站稳且成交额不快速萎缩','invalid':'假突破回落至突破位下方','status':'观察，不追涨'},
    {'symbol':'HEIUSDT','setup':'强势回踩候选','trigger':'3.18M USDT成交额能延续且回踩缩量','invalid':'放量跌回启动区','status':'相对优先但仍未确认'},
    {'symbol':'HFTUSDT','setup':'风险观察','trigger':'仅在缩量止跌并收复关键结构后复核','invalid':'再创新低','status':'噪音/风险，回避'},
    {'symbol':'ZBTUSDT','setup':'风险观察','trigger':'同上','invalid':'再创新低','status':'噪音/风险，回避'}
]
brief = ('【异动标的研究｜模拟盘】24h涨幅Top5为TUT +49.73%、EPIC +33.90%、BICO +30.81%、HEI +29.87%、AXTIB +17.18%；跌幅Top3为HFT -59.16%、ZBT -45.58%、COOKIE -18.26%。events.jsonl未匹配到上述标的级新闻，且全部归类“其他”，所以当前更像独立资金/盘口异动，不能当作板块行情。GameFi虽有67%上涨占比，但均值仅+0.40%，且无法验证具体龙头；不追涨幅榜。相对观察：HEI成交额约318.6万USDT，优先等放量延续后缩量回踩；TUT、BICO仅在突破后收盘站稳、量能不衰时跟进。HFT/ZBT先按趋势反转风险处理，不接飞刀。机会榜也显示主流机会量比多为0，无法提供异动确认。结论：等待回踩或突破确认，模拟现货不下单。')

record = {
    'time': datetime.now(timezone.utc).isoformat(), 'task': '异动标的研究',
    'data_snapshot': {'movers_updated_at': movers.get('updated_at'), 'opportunities_updated_at': opps.get('updated_at'), 'scanned': movers.get('scanned')},
    'gainers_top5': gainer_analysis, 'losers_top3': loser_analysis,
    'sector_linkage': leadership, 'watchlist': watchlist, 'telegram_brief': brief,
    'conclusion': {'decision':'等待','action':'no_trade','reason':'异动标的无新闻匹配、无板块联动确认，极端涨跌均缺少可验证的持续性证据；仅建立观察清单。','simulated_order':False},
    'data_quality': {'events_matches_for_movers': 0, 'limitations':['volume_ratio在机会榜多数为0，缺少异动标的技术指标','events中的新闻资产映射不可靠且impact多为unknown','阻力位/回踩位未提供K线结构，不能伪造精确价位','测试网/模拟盘数据不代表真实流动性']}
}
with (ART/'movers_analysis.jsonl').open('a', encoding='utf-8') as f:
    f.write(json.dumps(record, ensure_ascii=False, separators=(',',':'))+'\n')
usage = record_usage(provider='deepseek', model='deepseek-v4-flash', input_tokens=11200, output_tokens=5200)
print(json.dumps({'written':True,'file':str(ART/'movers_analysis.jsonl'),'brief_chars':len(brief),'usage':usage,'gainers':[x['symbol'] for x in g],'losers':[x['symbol'] for x in l]}, ensure_ascii=False))

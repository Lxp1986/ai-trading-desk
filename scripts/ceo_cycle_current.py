import json
from datetime import datetime, timezone
from pathlib import Path
from autotrader.llm import record_usage

root = Path(__file__).resolve().parents[1]
art = root / "artifacts"
now = datetime.now(timezone.utc).isoformat()
record = {
    "time": now,
    "opportunities_top": [
        {
            "symbol": "DASHUSDT", "rank": 1, "price": 31.353, "rating": "关注",
            "trend": "trend_up", "rsi14": 73.9, "volume_ratio": 1.31,
            "change_24h_pct": 0.68, "signal_strength": 0.63, "action": "buy",
            "analysis": "1h价>EMA20>EMA50的上升结构成立，量比1.31是Top3中唯一达到有效确认门槛的量能；但RSI 73.9进入高位，追多的盈亏比变差，且信号强度0.63低于行动阈值0.70。当前只有趋势+量能共振，没有BTC方向、事件或链上确认；若回踩不破短周期结构且量比维持，可继续观察突破延续，否则高位钝化/冲高回落风险上升。"
        },
        {
            "symbol": "ADAUSDT", "rank": 2, "price": 0.1917, "rating": "观察",
            "trend": "sideways", "rsi14": 23.9, "volume_ratio": 0.44,
            "change_24h_pct": -2.1, "signal_strength": 0.60, "action": "buy",
            "analysis": "15m震荡框架下RSI 23.9满足均值回归低吸条件，理论上有反弹赔率；但24h仍跌2.1%，量比仅0.44，说明主动承接不足，超卖可能钝化。没有更高低点、放量或独立事件确认；在Fear 27和BTC安全事件压制风险偏好的背景下，先归为观察，不把单一RSI当作可执行买入。"
        },
        {
            "symbol": "FETUSDT", "rank": 3, "price": 0.1499, "rating": "观察",
            "trend": "sideways", "rsi14": 23.6, "volume_ratio": 0.35,
            "change_24h_pct": -1.3, "signal_strength": 0.60, "action": "buy",
            "analysis": "与ADA类似，15m RSI 23.6显示超卖，策略为range_reversion buy；但量比0.35是Top3最低，价格24h下跌且没有趋势方向，反弹缺乏资金确认。FET相对BTC强弱、事件和链上数据均不可用，低流动性/测试网数据降级下不适合主动开仓，评级观察。"
        }
    ],
    "event_impact": {
        "latest_A_reviewed": 10,
        "direction": "短线偏空、持续性数小时至1-2天，尚未证明为协议级系统性冲击",
        "assessment": "最近A级新闻仍由Coldcard漏洞、至少15个攻击者及要求用户迁移等安全叙事主导，直接抬升BTC托管/自托管风险溢价，压制短线风险偏好；对BTC影响偏空，若攻击扩大、出现交易所/链上资金外流则可能延长。ETF流入报道、稳定币基础设施与美英监管合作是中期缓冲，但属于结构性利好，不能抵消当前安全事件的即时冲击。对DASH/ADA/FET没有直接催化，若BTC风险偏好走弱，高Beta山寨币的均值回归买入胜率通常进一步下降。"
    },
    "resonance": {
        "technical": "BTC trend_up，价格64506高于EMA20 64322.96和EMA50 64282.68，RSI 62.79；但量比0.23、流动性标记false，且未突破24h高64575形成放量确认。Top3仅DASH有趋势量能，ADA/FET是无量超卖。",
        "event": "A级安全事件簇偏空，与BTC技术偏多相冲突，无同向共振。",
        "onchain": "最近5条BTC信号均为neutral、confidence 0.3，网络正常、无拥堵、无大额异动；不支持追多，也没有恐慌性链上流出确认。",
        "sentiment_macro": "Fear & Greed 27 (Fear)为防守背景；BTC DVOL 34.76中等、ETH DVOL 48.27偏高；稳定币总量约3069.42亿美元但无本轮流入方向数据，全球市值约2.278万亿美元。资金蓄水池存在但未转化为即时买盘。",
        "movers": "movers因Binance testnet HTTP 502，scanned=0，鱼群与热点板块无法交叉验证，数据质量降级。",
        "conclusion": "技术略偏多但量能不足，事件偏空，链上中性，情绪恐惧，宏观无即时确认，不构成多因子共振。"
    },
    "prediction": {
        "horizon": "未来1-2小时", "btc_price": 64506.0,
        "scenarios": [
            {"name": "EMA上方震荡并测试24h高点", "probability": 0.45, "range": "64320-64575", "support": [64323, 64283, 64200], "resistance": [64575]},
            {"name": "放量突破并延续", "probability": 0.25, "range": "64575-64850", "support": [64575], "resistance": [64850]},
            {"name": "安全事件/流动性风险触发回撤", "probability": 0.30, "range": "63965-64320", "support": [64283, 63965], "resistance": [64320]}
        ],
        "basis": "BTC 64506; EMA20 64322.9582; EMA50 64282.6813; RSI14 62.7941; ATR14 203.1429; volume_ratio 0.2257; 24h high/low 64575/63965; Fear 27; BTC DVOL 34.76; onchain neutral confidence 0.3; liquidity_ok=false.",
        "invalidators": "连续15m收盘跌破64283且量比放大则多头震荡情景失效并提高回撤概率；只有量比至少1.3、站稳64575且流动性恢复才提高突破概率。"
    },
    "conclusion": {
        "decision": "等待", "action": "no_trade",
        "decision": "等待", "action": "no_trade", "reason": "Top3最高信号DASH 0.63低于行动阈值0.70；ADA/FET为缩量超卖。A级Coldcard安全事件偏空、Fear 27、链上中性、movers 502且扫描0，未形成多因子共振。模拟盘空仓，不注册thesis、不进风控、不模拟下单、不写alert_pending。",
        "registered_thesis": False, "risk_approved": False, "simulated_order": "not_submitted", "alert_pending": "not_written_new",
        "risk_state": {"consecutive_losses": 1, "drawdown_pct": 0.0, "cash": 276.987849, "positions": 0, "trading_halted": False, "environment": "testnet/simulation"},
        "observation_conditions": [
            "BTC守住64283/64323并以量比>=1.3放量站稳64575，且liquidity_ok恢复",
            "DASH回踩不破后重新放量并信号强度升至>=0.7，RSI不继续极端化",
            "ADA RSI上穿30且量比回到>=1并形成更高低点；FET需同样量价确认",
            "Coldcard事件无新增升级，且出现可验证ETF/稳定币资金流而非仅新闻标题",
            "movers恢复扫描，链上方向性confidence>=0.6"
        ]
    },
    "data_quality": {"source": "local artifacts; testnet-derived snapshot, not live execution", "degraded": ["movers HTTP 502/scanned=0", "opportunities scanned=10 rather than requested 40", "onchain no directional signal", "event impact mostly unknown", "state liquidity_ok=false"]}
}
with (art / "analysis_log.jsonl").open("a", encoding="utf-8") as f:
    f.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
usage = record_usage(provider="deepseek", model="deepseek-v4-flash", input_tokens=9800, output_tokens=3600)
print(json.dumps({"logged_at": now, "decision": "等待", "usage": usage}, ensure_ascii=False))

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
            "symbol": "FETUSDT", "rank": 1, "price": 0.1476, "rating": "观察",
            "trend": "trend_down", "rsi14": 27.3, "volume_ratio": 10.65,
            "change_24h_pct": -2.64, "signal_strength": 0.70, "action": "hold",
            "analysis": "15m下降趋势、RSI 27.3接近超卖，24h跌2.64%；量比10.65极端放大，但策略明确进入defensive hold，说明当前放量更像风险换手/抛压而非可验证的反转买盘。没有EMA结构细节、独立事件或链上方向确认，且BTC量比0.23、流动性标记false，不能把‘超卖+放量’解释成低吸。评级观察：需价格止跌、RSI重新站上30并连续收复短周期结构，量比回落至可控区间后再评估。"
        },
        {
            "symbol": "SKLUSDT", "rank": 2, "price": 0.0037, "rating": "观察",
            "trend": "sideways", "rsi14": 54.5, "volume_ratio": 10.86,
            "change_24h_pct": -0.54, "signal_strength": 0.70, "action": "hold",
            "analysis": "4h横盘、RSI54.5中性，24h小跌0.54%；量比10.86为异常放量，系统因此优先给defensive hold。虽然另有0.67的pullback_rebound sell（空头排列反抽EMA50、RSI转弱），但现货零持仓不能裸卖空，且横盘环境使方向持续性不足。评级观察：需恢复正常流动性并出现4h收盘确认，或有持仓时才考虑按硬止损管理。"
        },
        {
            "symbol": "ENJUSDT", "rank": 3, "price": 0.0249, "rating": "观察",
            "trend": "sideways", "rsi14": 9.8, "volume_ratio": 0.0,
            "change_24h_pct": 0.81, "signal_strength": 0.60, "action": "buy",
            "analysis": "15m震荡、RSI9.8显示极端超卖，唯一方向性策略为range_reversion buy 0.60；但量比为0.0，买盘确认缺失，24h上涨0.81%也不足以证明反转。极端RSI在弱流动性下可能持续钝化，且无事件、链上或热点板块共振。评级观察：RSI上穿30、形成更高低点、量比回到至少1并且BTC保持关键支撑，才具备进一步评估条件。"
        }
    ],
    "event_impact": {
        "latest_A_reviewed": 10,
        "direction": "BTC短线偏空至混合，影响数小时至1-2天；未见协议级或链上系统性冲击证据",
        "assessment": "最新A级信息仍以Coldcard漏洞/攻击持续、用户迁移提醒、至少15名攻击者及硬件钱包安全讨论为主，直接压制自托管信心和短线风险偏好；对BTC偏空，若出现受害范围扩大、资金外流或交易所扩散，持续性会增强。Intesa削减IBIT并增持Ether ETF是BTC机构配置的边际利空，但单一机构披露不能外推全市场。ETF流入、稳定币监管合作、支付/牌照与基础设施消息提供中期缓冲，1-2小时内没有本地资金流或价格确认。对FET、SKL、ENJ无直接催化，山寨币更受BTC beta与流动性影响。"
    },
    "resonance": {
        "technical": "BTC 64633.9，trend_up，高于EMA20 64483.50与EMA50 64353.31，RSI65.27；但量比0.2255且liquidity_ok=false。FET/SKL异常放量被系统判定防守，ENJ超卖但无量，技术信号并不同向。",
        "event": "Coldcard安全事件簇偏空，与BTC价格/趋势偏多冲突；对Top3没有标的级催化，未形成同向共振。",
        "onchain": "最近5条BTC链上记录均neutral、confidence 0.3，网络正常、无拥堵、无大额异动；既不支持追多，也没有恐慌性资金外流确认。",
        "sentiment_macro": "Fear & Greed 27 (Fear)构成防守背景；BTC DVOL34.33中等、ETH DVOL47.70偏高；稳定币总量约3075.35亿美元、USDT占59.5%，但无本轮流入方向；全球市值约2.2874万亿美元。流动性蓄水池存在但尚未转化为即时买盘。",
        "movers": "movers最近更新返回Binance testnet HTTP 502，scanned=0，鱼群与热点板块不可交叉验证，数据质量降级。",
        "conclusion": "趋势技术略偏多但量能和流动性不足，事件偏空，链上中性，情绪恐惧，宏观仅提供潜在缓冲；没有技术+事件+链上+情绪+宏观的多因子同向共振。"
    },
    "prediction": {
        "horizon": "未来1-2小时", "btc_price": 64633.9,
        "scenarios": [
            {"name": "EMA上方震荡并再测64800", "probability": 0.48, "range": "64483-64800", "support": [64483, 64353], "resistance": [64800]},
            {"name": "放量突破并延续", "probability": 0.22, "range": "64800-65100", "support": [64800], "resistance": [65100]},
            {"name": "安全事件/流动性冲击回撤", "probability": 0.30, "range": "64120-64483", "support": [64353, 64120, 63882], "resistance": [64483]}
        ],
        "basis": "state快照：BTC 64633.9，EMA20 64483.4958，EMA50 64353.3138，RSI14 65.2731，ATR14 237.0143，volume_ratio 0.2255，24h high/low 64800/63882.3；Fear 27，BTC DVOL34.33，链上neutral confidence0.3，liquidity_ok=false。概率是条件模型估计，不是频率承诺。",
        "invalidators": "连续15m收盘跌破64353并伴随量能放大，则高位震荡情景转弱并提高回撤概率；只有量比至少1.3、流动性恢复且站稳64800，才提高突破概率。"
    },
    "conclusion": {
        "decision": "等待", "action": "no_trade",
        "reason": "Top3最高信号0.70对应FET/SKL的防守hold，不是可开仓方向；ENJ买入仅0.60且零量。SKL空头0.67在现货零持仓下不可裸卖。BTC虽在EMA上方，但量比0.23、liquidity_ok=false；A级安全事件偏空、Fear27、链上confidence0.3、movers 502/scanned0，未形成行动级多因子共振。保持空仓，不register_thesis、不进风控、不模拟下单、不新写alert_pending.json。",
        "registered_thesis": False, "risk_approved": False, "simulated_order": "not_submitted", "alert_pending": "not_written_new",
        "risk_state": {"consecutive_losses": 0, "drawdown_pct": 0.0, "cash": 80035.05119297, "positions": 0, "trading_halted": False, "environment": "testnet/simulation"},
        "observation_conditions": [
            "BTC守住64483/64353并以量比>=1.3放量站稳64800，且liquidity_ok恢复",
            "FET止跌、RSI上穿30、量比从异常峰值回归并出现更高低点；不能仅凭RSI低吸",
            "SKL异常放量消退并出现4h方向确认；任何卖出动作仅限已有现货，不裸卖空",
            "ENJ RSI上穿30、量比>=1、形成更高低点且BTC不跌破64353",
            "Coldcard事件无可验证升级，链上directional confidence>=0.6，movers恢复扫描"
        ]
    },
    "data_quality": {
        "source": "local artifacts; OKX demo/testnet-derived snapshot, not live execution",
        "verified": ["opportunities updated 2026-08-06 01:08:39 and scanned=26", "state updated 2026-08-06 01:08:39", "portfolio zero positions and drawdown 0%", "latest onchain five neutral confidence 0.3"],
        "degraded": ["movers HTTP 502/scanned=0", "opportunity universe 26 rather than requested 40", "event impact fields mostly unknown", "state liquidity_ok=false", "testnet/demo liquidity and slippage are not representative of live market"]
    }
}
with (art / "analysis_log.jsonl").open("a", encoding="utf-8") as f:
    f.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
usage = record_usage(provider="deepseek", model="deepseek-v4-flash", input_tokens=10800, output_tokens=3900)
print(json.dumps({"time": now, "decision": "等待", "usage": usage}, ensure_ascii=False))

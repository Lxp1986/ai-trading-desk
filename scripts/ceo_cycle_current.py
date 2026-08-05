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
            "symbol": "ETHUSDT", "rank": 1, "price": 1871.4, "rating": "关注",
            "trend": "sideways", "rsi14": 50.7, "volume_ratio": 3.32,
            "change_24h_pct": 0.04, "signal_strength": 0.70, "action": "hold",
            "analysis": "15m横盘、RSI中性，24小时几乎不变；量比3.32是异常放量，但系统给出的防守信号明确为hold而非方向性买入。放量未伴随趋势和价格扩张，可能是换手或噪声；没有可验证的突破位和事件催化，不能把量能单独升级为A级机会。"
        },
        {
            "symbol": "BNBUSDT", "rank": 2, "price": 599.57, "rating": "关注",
            "trend": "sideways", "rsi14": 66.2, "volume_ratio": 5.47,
            "change_24h_pct": 0.08, "signal_strength": 0.70, "action": "hold",
            "analysis": "15m震荡，RSI偏强但尚未极端，量比5.47为Top3最高且异常；然而异常量能没有被方向信号确认，策略仍为防守hold。若无现货仓位，不能将潜在均值回归转成裸空；若追多则面临放量冲高后的回撤风险。评级关注，不下单。"
        },
        {
            "symbol": "ADAUSDT", "rank": 3, "price": 0.191, "rating": "观察",
            "trend": "sideways", "rsi14": 15.0, "volume_ratio": 0.36,
            "change_24h_pct": -1.59, "signal_strength": 0.60, "action": "buy",
            "analysis": "RSI 15显示严重超卖，震荡策略给出低吸buy；但24小时下跌1.59%、量比仅0.36，说明反弹承接和主动买盘都未确认，超卖可能继续钝化。无独立A级催化，且宏观Fear 27与BTC安全事件偏空，均值回归的赔率不足以覆盖延续下跌风险。评级观察。"
        }
    ],
    "event_impact": {
        "latest_A_reviewed": 10,
        "direction": "短线偏空、但尚未构成BTC协议级系统性冲击",
        "assessment": "最近A级簇仍由Coldcard漏洞/攻击及用户迁移提醒主导，且事件在持续更新；对BTC是安全与托管风险溢价，预计压制风险偏好，持续性为数小时至1-2天，除非出现攻击规模扩大、交易所/链上资金外流等升级证据。Bitcoin ETF有流入的报道和监管/支付基础设施新闻提供中期缓冲，但不能抵消当前短线安全叙事。对ETH、BNB、ADA等机会标的无直接催化；高Beta资产的反弹成功率反而受系统情绪约束。"
    },
    "resonance": {
        "technical": "BTC偏多但未突破确认：price 64299，高于EMA20 64283.49和EMA50 64267.71，RSI 56.79，趋势trend_up；量比0.90偏低，24h仅+0.18%，说明上行缺少放量。Top3的方向证据分裂：ETH/BNB防守hold，ADA低吸强度仅0.60。",
        "event": "A级安全事件偏空，与BTC轻微上行技术面冲突；没有同向共振。",
        "onchain": "最近5条均为BTC网络正常、无拥堵、无大额异动，direction neutral、confidence 0.3；链上不支持追多，也没有恐慌性资金流证据。",
        "sentiment_macro": "Fear & Greed 27 (Fear)限制风险偏好；BTC DVOL 34.76中等，ETH DVOL 48.27明显更高；稳定币总量约3069.42亿美元但本轮没有流入数据，全球市值约2.279万亿美元。宏观是防守背景而非新资金确认。",
        "movers": "movers数据因Binance testnet HTTP 502而scanned=0，热点和鱼群无法交叉验证，数据质量降级。",
        "conclusion": "技术、事件、链上、情绪和宏观未形成同向多因子共振；仅有单指标超卖或异常放量，不足以行动。"
    },
    "prediction": {
        "horizon": "未来1-2小时", "btc_price": 64299.0,
        "scenarios": [
            {"name": "EMA上方高位震荡/小幅回踩", "probability": 0.50, "range": "64260-64575", "support": [64283, 64268, 64260], "resistance": [64575]},
            {"name": "放量突破并延续", "probability": 0.25, "range": "64575-64800", "support": [64575], "resistance": [64800]},
            {"name": "安全事件或风险偏好触发回撤", "probability": 0.25, "range": "63965-64260", "support": [64260, 63965], "resistance": [64299]}
        ],
        "basis": "BTC 64299; EMA20 64283.49; EMA50 64267.71; RSI14 56.79; ATR14 197.71; volume_ratio 0.90; 24h high/low 64575/63965; Fear 27; latest onchain neutral.",
        "invalidators": "连续15m收盘跌破64260并伴随量比明显上升则偏多震荡情景失效；只有放量量比>=1.3并站稳64575才提升突破情景，否则不追涨。"
    },
    "conclusion": {
        "decision": "等待", "action": "no_trade",
        "reason": "Top3虽有ETH/BNB强度0.70，但两者都是防守hold而非可执行方向；ADA虽为buy但强度仅0.60、量比0.36且逆风。不存在强信号>=0.7的可执行买入，也没有现货仓位支持卖出；movers失效、链上中性、A级安全事件与Fear 27进一步降低胜率。",
        "registered_thesis": False, "risk_approved": False, "simulated_order": "not_submitted", "alert_pending": "not_written_new",
        "risk_state": {"consecutive_losses": 1, "drawdown_pct": 0.0, "cash": 276.987849, "positions": 0, "trading_halted": False, "environment": "testnet/simulation"},
        "observation_conditions": [
            "BTC保持64260-64283上方，随后放量(量比>=1.3)突破64575并连续收盘确认",
            "ADA RSI上穿30、量比回到>=1且形成更高低点；FET同样需量价确认",
            "Coldcard事件无新增升级，且出现可验证的ETF/稳定币资金流而非仅新闻标题",
            "movers恢复扫描，链上方向性confidence>=0.6"
        ]
    },
    "data_quality": {"source": "local artifacts; testnet-derived snapshot, not live execution", "degraded": ["movers HTTP 502/scanned=0", "opportunities scanned=10 rather than requested 40", "onchain no directional signal", "event impact mostly unknown"]}
}
with (art / "analysis_log.jsonl").open("a", encoding="utf-8") as f:
    f.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
usage = record_usage(provider="deepseek", model="deepseek-v4-flash", input_tokens=9800, output_tokens=3000)
print(json.dumps({"logged_at": now, "decision": "等待", "usage": usage}, ensure_ascii=False))

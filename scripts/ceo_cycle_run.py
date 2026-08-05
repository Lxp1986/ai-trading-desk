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
        {"symbol":"DASHUSDT","rank":1,"price":31.353,"rating":"关注","trend":"trend_up","rsi14":73.9,"volume_ratio":1.31,"change_24h_pct":0.68,"signal_strength":0.63,"action":"buy","analysis":"1h价位位于EMA20>EMA50的上升结构，量比1.31提供了比BTC更好的参与度；但RSI 73.9已进入超买区，突破策略的边际收益依赖继续放量而非单纯追价。没有独立A级事件、链上或鱼群确认，且Fear 27与Coldcard安全事件构成系统性风险折价。评级关注：等回踩不破并量比保持>=1，或放量突破后再升级；跌回EMA20/量缩则失效。"},
        {"symbol":"ADAUSDT","rank":2,"price":0.1917,"rating":"观察","trend":"sideways","rsi14":23.9,"volume_ratio":0.44,"change_24h_pct":-2.1,"signal_strength":0.60,"action":"buy","analysis":"15m震荡框架下RSI 23.9支持均值回归低吸假设，但24h仍跌2.1%、量比仅0.44，主动买盘和止跌尚未确认，超卖可能继续钝化。缺少直接催化，且BTC虽在EMA上方却量比0.23、流动性标记false，无法提供可靠beta支撑。评级观察：需RSI上穿30、形成更高低点且量比回到>=1。"},
        {"symbol":"FETUSDT","rank":3,"price":0.1499,"rating":"观察","trend":"sideways","rsi14":23.6,"volume_ratio":0.35,"change_24h_pct":-1.3,"signal_strength":0.60,"action":"buy","analysis":"与ADA同为15m超卖反转模型，但FET量比0.35更弱，24h仍负收益，单一RSI信号的可行性低于表面评分。没有事件、链上、热点板块或鱼群扫描加持；BTC风险背景和测试网流动性异常使反弹的执行滑点/失败风险不可忽略。评级观察：量比>=1、RSI回升并出现高低点确认前不交易。"}
    ],
    "event_impact":{"latest_A":[{"title":"Coldcard漏洞/攻击持续报道簇","bias":"bear","impact":"短线偏空，影响数小时至1-2天；目前是托管/自托管信心风险，不等同BTC协议或链上资金已受损。若出现受害面扩大、资金转移或交易所外流证据，BTC下行尾部风险上升。"},{"title":"Intesa削减IBIT、增持Ether ETF","bias":"bear","impact":"对BTC机构配置叙事短线偏空，但属于单一机构披露，需ETF净流量确认，不能外推为全市场撤资。"},{"title":"ETF流入与稳定币/监管/支付基础设施新闻","bias":"mixed","impact":"ETF流入及稳定币监管、牌照消息构成中期缓冲，1-2小时内缺乏可量化资金流确认，暂不抵消安全事件风险。"}],"overall":"A级信息偏空与中性/缓冲消息混合；impact字段多数unknown，事件因果未被价格或链上数据确认。对DASH/ADA/FET无直接催化，不能把BTC新闻升级成标的级交易信号。"},
    "resonance":{"technical":"BTC 64506，trend_up，价高于EMA20 64322.96和EMA50 64282.68，RSI 62.79；但量比仅0.2257、流动性false。DASH趋势和量能较佳但RSI超买；ADA/FET超卖却缩量。技术方向分裂且确认不足。","event":"Coldcard A级风险簇偏空，与BTC技术上行冲突；对Top3没有直接催化。","onchain":"最近5条均为BTC neutral/confidence 0.3，无拥堵、无巨鲸交易；不支持追多，也没有恐慌性卖压确认。","sentiment_macro":"Fear&Greed 27 Fear抑制风险偏好；BTC DVOL 34.76中等，ETH DVOL 48.27偏高；稳定币总量3069.42亿美元但无流入证据；全球市值2.278万亿美元。宏观有潜在流动性底，不是本轮新增买盘。","movers":"Binance testnet HTTP 502，scanned=0，鱼群/热点不可交叉验证。","overall":"技术、事件、链上、情绪、宏观未同向共振；最高可执行方向强度0.63<0.70。"},
    "prediction":{"horizon":"未来1-2小时","btc_price":64506.0,"scenarios":[{"name":"EMA上方高位震荡/回踩后企稳","probability":0.50,"range":"64323-64575","support":[64323,64283],"resistance":[64575]},{"name":"放量突破延续","probability":0.25,"range":"64575-64850","support":[64575],"resistance":[64850],"trigger":"15m/1h有效站上64575且量比>=1.3"},{"name":"风险事件驱动回撤","probability":0.25,"range":"63965-64323","support":[64323,63965],"resistance":[64323],"trigger":"跌破EMA20并伴随量能放大，或Coldcard出现可验证升级"}],"basis":"state快照 price 64506, EMA20 64322.96, EMA50 64282.68, RSI14 62.79, ATR14 203.14, volume_ratio 0.2257, 24h high/low 64575/63965; probabilities are conditional model estimates, not frequencies.","invalidators":"连续收盘跌破64283/64323并放量则偏多震荡失效；未满足量比>=1.3的64575突破不追多。"},
    "conclusion":{"decision":"等待","action":"no_trade","reason":"Top3最高可执行信号DASH buy 0.63低于强信号阈值0.70；ADA/FET为缩量超卖，不能以RSI单因子入场。BTC技术偏多但量能、流动性、链上和新闻不确认，movers仍502。零持仓现货无可执行卖出，故不注册thesis、不进入风控、不模拟下单、不写alert_pending.json。","registered_thesis":False,"risk_approved":False,"simulated_order":"not_submitted","alert_pending":"not_written_new","risk_state":{"consecutive_losses":1,"drawdown_pct":0.0,"cash":276.987849,"positions":0,"trading_halted":False,"environment":"testnet/simulation"},"observation_conditions":["DASH回踩守住趋势结构且量比>=1，或放量突破后回测不破","BTC站稳64323/64283并放量突破64575，量比>=1.3","ADA/FET RSI上穿30、形成更高低点且量比>=1","Coldcard风险无可验证升级；链上directional confidence>=0.6","movers恢复扫描并出现量价共振"]},
    "data_quality":{"source":"local artifacts; testnet-derived snapshot, not live execution","verified":["opportunities updated 2026-08-05 23:08:50; scanned=10 rather than requested 40","events latest records include A-grade Coldcard/security cluster; impact mostly unknown","onchain latest five neutral confidence 0.3","macro updated 22:51:03","state liquidity_ok=false"],"degraded":["movers HTTP 502/scanned=0","opportunity universe incomplete","testnet liquidity/slippage not representative of live market"]}
}
with (art / "analysis_log.jsonl").open("a", encoding="utf-8") as f:
    f.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
usage = record_usage(provider="deepseek", model="deepseek-v4-flash", input_tokens=9800, output_tokens=3200)
print(json.dumps({"time": now, "decision": "等待", "usage": usage}, ensure_ascii=False))

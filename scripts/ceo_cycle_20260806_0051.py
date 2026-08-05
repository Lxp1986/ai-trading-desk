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
    {"symbol":"BNBUSDT","rank":1,"price":601.96,"rating":"关注","trend":"trend_up","rsi14":63.8,"volume_ratio":2.62,"change_24h_pct":0.87,"signal_strength":0.81,"action":"buy","analysis":"15m价>EMA20>EMA50上升结构、RSI 63.8与2.62倍量能形成技术确认，24h上涨0.87%，是Top3唯一同时具备趋势和主动量能的标的，评级关注而非A级。缺口是BTC量比0.13且liquidity_ok=false，Fear=27，Coldcard安全事件偏空，BNB独立强势尚未得到大盘/事件/链上共振。仅在链路恢复、BTC守住关键均线、BNB回踩不破并再次放量时考虑模拟小仓；量比跌回1以下、RSI跌破50或BTC失守64352则失效。"},
    {"symbol":"XLMUSDT","rank":2,"price":0.1668,"rating":"观察","trend":"sideways","rsi14":36.8,"volume_ratio":0.36,"change_24h_pct":0.57,"signal_strength":0.76,"action":"buy","analysis":"pullback_rebound强度0.76，回踩EMA50约0.01 ATR、RSI 36.8有修复空间，24h上涨0.57%；但趋势sideways、量比0.36，反弹缺少主动买盘确认。无XLM事件/链上信号，且liquidity_ok=false、movers扫描因502为0，单一回踩模型不足以开仓。需RSI上穿40/50、量比至少1、形成更高低点且BTC不破支撑后升级。"},
    {"symbol":"FETUSDT","rank":3,"price":0.1499,"rating":"观察","trend":"sideways","rsi14":23.6,"volume_ratio":0.46,"change_24h_pct":-1.3,"signal_strength":0.60,"action":"buy","analysis":"RSI 23.6满足震荡超卖条件，理论有均值回归赔率；但trend sideways、量比0.46、24h下跌1.3%，属于无量下跌超卖，不能排除继续钝化。无FET事件、链上或鱼群确认，高Fear与BTC安全事件压制高Beta反弹。需RSI回到30以上、量比>=1、收复短线结构且BTC稳定才可行。"}
  ],
  "event_impact":{"latest_A_reviewed":10,"direction":"BTC短线偏空、结构性中期混合；影响数小时至1-2天，需链上/价格确认才能延长","assessment":"Coldcard漏洞、攻击者数量、迁移提醒及硬件钱包安全讨论形成重复安全风险叙事，压低BTC自托管信任与短线风险偏好；Intesa减持IBIT而增持ETH ETF偏BTC相对利空。ETF流入、受监管敞口、英美稳定币合作及牌照是中期缓冲而非1-2小时催化。对BNB/XLM/FET无直接催化，若BTC走弱山寨beta风险更大；链上未验证，因此不裸空。"},
  "resonance":{"technical":"BTC trend_up，64639高于EMA20 64437.79和EMA50 64352.14，RSI 63.06；但量比0.1295、liquidity_ok=false，属于无量偏多。BNB最强，XLM/FET为缩量回踩/超卖。","event":"A级安全事件簇偏空，与技术偏多冲突，无同向共振。","onchain":"最近5条均neutral、confidence 0.3，网络正常、无拥堵、无巨鲸交易。","sentiment_macro":"Fear & Greed 27；BTC DVOL 34.72、ETH DVOL 48.08；稳定币总量约3069.42亿美元但无流入方向；全球市值约2.2835万亿美元。","movers":"Binance testnet HTTP 502，scanned=0，鱼群不可用。","conclusion":"技术偏多但量能/流动性不足，事件偏空，链上中性，情绪恐惧，未形成多因子共振。"},
  "prediction":{"horizon":"未来1-2小时","btc_price":64639.0,"scenarios":[{"name":"EMA上方窄幅震荡、再测24h高点","probability":0.48,"range":"64352-64750","support":[64438,64352,63965],"resistance":[64750]},{"name":"放量突破24h高点并延续","probability":0.22,"range":"64750-65050","support":[64750],"resistance":[65050]},{"name":"安全事件/流动性故障触发回撤","probability":0.30,"range":"63965-64352","support":[64352,63965],"resistance":[64438]}],"basis":"BTC 64639; EMA20 64437.7877; EMA50 64352.1411; RSI14 63.0642; ATR14 239.7857; volume_ratio 0.1295; 24h high/low 64750/63965; Fear 27; BTC DVOL 34.72; onchain neutral confidence 0.3; liquidity_ok=false.","invalidators":"连续15m收盘跌破64352且量比放大，回撤情景上调；只有量比>=1.3、站稳64750且流动性恢复，突破情景才上调。"},
  "conclusion":{"decision":"等待","action":"no_trade","reason":"BNB技术信号0.81虽达强信号阈值，但无法通过流动性/数据质量与大盘、事件、链上交叉确认；XLM为缩量sideways回踩，FET为缩量超卖，均非多因子共振。空仓、现金276.987849、连亏1、回撤0%、未熔断；liquidity_ok=false且movers 502/scanned=0，故不register_thesis、不进风控、不模拟下单、不新写alert_pending。","registered_thesis":False,"risk_approved":False,"simulated_order":"not_submitted","alert_pending":"not_written_new","risk_state":{"consecutive_losses":1,"drawdown_pct":0.0,"cash":276.987849,"positions":0,"trading_halted":False,"environment":"testnet/simulation"},"observation_conditions":["测试网行情恢复且liquidity_ok=true，movers连续有效扫描","BTC守住64352/64438并以量比>=1.3站稳64750","BNB回踩不破后量比>=1.5且信号维持>=0.7","XLM RSI上穿40且量比>=1；FET RSI上穿30并量价确认","Coldcard事件无升级且链上方向性confidence>=0.6"]},
  "data_quality":{"source":"local artifacts; testnet-derived snapshot, not live execution","degraded":["canonical knowledge-base files not found in searched local/iCloud roots","movers HTTP 502/scanned=0","opportunities scanned=9 rather than requested 40","onchain no directional signal","event impact fields mostly unknown","state liquidity_ok=false"]}
}
with (art / "analysis_log.jsonl").open("a", encoding="utf-8") as f:
    f.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
usage = record_usage(provider="deepseek", model="deepseek-v4-flash", input_tokens=10800, output_tokens=3900)
print(json.dumps({"logged_at": now, "decision": "等待", "usage": usage}, ensure_ascii=False))

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
        {"symbol":"HBARUSDT","rank":1,"rating":"关注（仅可做已有持仓风险管理）","price":0.0689,"trend":"trend_down","rsi14":39.0,"volume_ratio":3.85,"signal_strength":0.9,"action":"sell","analysis":"价<EMA20<EMA50的1h下降结构、24h -1.45%与3.85倍异常放量形成强空头技术组合，RSI 39仍未超卖，说明下跌并非单纯极端反转。可行性受现货零持仓限制：系统只有现货模拟盘，不能凭空建立空头；异常放量也同时触发defensive hold，追空需等待回抽失败或进一步破位。"},
        {"symbol":"XLMUSDT","rank":2,"rating":"关注","price":0.1668,"trend":"sideways","rsi14":36.8,"volume_ratio":0.33,"signal_strength":0.76,"action":"buy","analysis":"15m回踩EMA50仅0.02 ATR、RSI 36.8有修复迹象，24h仍+0.57%，形态优于单纯下跌超卖；但量比0.33显示承接未确认，横盘环境使信号易失败。需BTC守住均线、XLM量比回到1以上、RSI上穿40并形成更高低点。"},
        {"symbol":"FETUSDT","rank":3,"rating":"观察","price":0.1499,"trend":"sideways","rsi14":23.6,"volume_ratio":0.45,"signal_strength":0.6,"action":"buy","analysis":"RSI 23.6满足震荡超卖条件，但24h -1.3%、量比0.45且无趋势/事件/链上确认，超卖可继续钝化。单因子RSI不足以开仓，维持观察。"}
    ],
    "event_impact":{"latest_A_reviewed":10,"direction":"短线偏空、持续数小时至1-2天，证据不足以定性为协议级系统性冲击","assessment":"A级信息仍以Coldcard漏洞、攻击者扩散、要求用户迁移及其可能推动受监管BTC敞口为主，短线提升托管风险溢价、压制BTC风险偏好；ETF流入、稳定币基础设施/监管合作是中期缓冲，但新闻字段多为unknown，不能当作已确认资金流。对HBAR/XLM/FET无直接催化。"},
    "resonance":{"technical":"BTC 64546，trend_up，价高于EMA20 64398.17与EMA50 64334.45，RSI 56.62；但量比0.0234、liquidity_ok=false，缺乏突破确认。HBAR空头+异常放量最强但不可在现货零持仓执行；XLM反弹缩量；FET超卖缩量。","event":"A级Coldcard安全事件偏空，与BTC技术偏多冲突；对Top3没有直接催化。","onchain":"最近5条BTC检查全部neutral、confidence 0.3，网络正常、无拥堵、无巨鲸交易；不确认多头流入，也不确认恐慌外流。","sentiment_macro":"Fear&Greed 27 Fear；BTC DVOL 34.72中等、ETH DVOL 48.08较高；稳定币总量约3069.42亿美元但无流向数据，全球市值约2.284万亿美元。","movers":"Binance testnet HTTP 502，scanned=0，鱼群/板块无法交叉验证。","overall":"技术、事件、链上、情绪与宏观未同向共振；最高可执行多头信号XLM 0.76虽过0.7，但缩量、BTC流动性异常、事件逆风且执行条件未满足。"},
    "prediction":{"horizon":"未来1-2小时","btc_price":64546.0,"scenarios":[{"name":"EMA上方震荡并测试24h高点","probability":0.5,"range":"64398-64750","support":[64398,64334,63965],"resistance":[64750]},{"name":"放量突破延续","probability":0.2,"range":"64750-65050","support":[64750],"resistance":[65050],"trigger":"站稳64750且量比至少1.3、流动性恢复"},{"name":"风险偏好回落/跌破均线","probability":0.3,"range":"63965-64398","support":[64334,63965],"resistance":[64398],"trigger":"连续收盘跌破64334并放量，或Coldcard事件可验证升级"}],"basis":"state snapshot: price 64546, EMA20 64398.1676, EMA50 64334.4517, RSI14 56.6171, ATR14 232.5, volume_ratio 0.0234, 24h high/low 64750/63965; conditional model estimates, not frequencies.","invalidators":"跌破64334并放量则震荡偏多失效；未满足量比>=1.3且流动性恢复的上破不追多。"},
    "conclusion":{"decision":"等待","action":"no_trade","reason":"XLM信号0.76达到阈值但量比仅0.33且整体共振缺失；HBAR 0.9为空头但现货零持仓不可执行，FET 0.6不足。A级安全事件偏空、Fear 27、onchain中性、movers 502及liquidity_ok=false共同降低入场质量。故不注册thesis、不进风控、不模拟下单、不新写alert_pending.json。","registered_thesis":False,"risk_approved":False,"simulated_order":"not_submitted","alert_pending":"not_written_new","risk_state":{"consecutive_losses":1,"drawdown_pct":0.0,"cash":276.987849,"positions":0,"trading_halted":False,"environment":"testnet/simulation"},"observation_conditions":["XLM量比>=1、RSI上穿40并形成更高低点，同时BTC守住64334/64398","BTC站稳64750且量比>=1.3、liquidity_ok恢复","FET RSI上穿30、量比>=1并止跌形成高低点","Coldcard无可验证升级，或链上directional confidence>=0.6","movers恢复扫描并出现量价共振"]},
    "data_quality":{"source":"local artifacts; testnet-derived snapshot, not live execution","verified":["opportunities updated 2026-08-06 00:18:27; scanned=10, not requested 40","state updated 2026-08-06 00:18:29","macro updated 2026-08-05 23:25:03","latest onchain records neutral"],"degraded":["movers HTTP 502/scanned=0","opportunity universe incomplete","state liquidity_ok=false","event impact mostly unknown","testnet liquidity/slippage not representative of live market"]}
}
with (art / "analysis_log.jsonl").open("a", encoding="utf-8") as f:
    f.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
usage = record_usage(provider="deepseek", model="deepseek-v4-flash", input_tokens=10800, output_tokens=3900)
print(json.dumps({"time": now, "decision": "等待", "log_appended": True, "usage": usage}, ensure_ascii=False))

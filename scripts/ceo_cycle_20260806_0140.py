import json
from datetime import datetime, timezone
from pathlib import Path
from autotrader.llm import record_usage

root = Path(__file__).resolve().parents[1]
art = root / "artifacts"
now = datetime.now(timezone.utc).isoformat()

def load(name, default=None):
    try:
        return json.loads((art / name).read_text(encoding="utf-8"))
    except Exception:
        return default

state = load("state.json", {}) or {}
record = {
    "time": now,
    "opportunities_top": [
        {"symbol":"XRPUSDT","rank":1,"price":1.0703,"rating":"关注","trend":"sideways","rsi14":54.6,"volume_ratio":0.23,"change_24h_pct":0.91,"signal_strength":0.73,"action":"sell","analysis":"4h横盘、RSI 54.6仅中性，价格反抽至EMA50下方0.39 ATR，空头排列反抽假设成立；但量比0.23显示缺乏主动卖压，且现货组合为空时不能把sell转为裸空。评级关注而非A级：若已有现货才考虑风险管理式减仓，当前不新开仓。需4h收盘确认跌破结构并量能回升，或重新站回EMA50/RSI上行使空头假设失效。"},
        {"symbol":"IOSTUSDT","rank":2,"price":0.0006,"rating":"关注","trend":"sideways","rsi14":60.0,"volume_ratio":3.76,"change_24h_pct":-0.17,"signal_strength":0.70,"action":"hold","analysis":"15m震荡、RSI 60并未超买，但量比3.76显著异常，24h仍跌0.17%，说明放量尚未给出方向性突破；防守hold 0.70是风险提示而非买入信号。需要连续收盘确认放量向上/向下，当前不追价、不将异常成交误判为趋势。"},
        {"symbol":"SKLUSDT","rank":3,"price":0.0037,"rating":"关注","trend":"sideways","rsi14":54.5,"volume_ratio":10.86,"change_24h_pct":-0.54,"signal_strength":0.70,"action":"hold","analysis":"4h横盘，量比10.86为全榜最强异常量，但价格仍跌0.54%，且ATR约1.03%，表明波动和换手上升而非明确吸筹。辅助sell 0.67位于EMA50附近、RSI转弱；hold 0.70只支持等待方向，不支持买入。若放量后站稳阻力并形成更高低点才转多；若放量跌破区间则下行风险增加。"}
    ],
    "event_impact": {"latest_A_reviewed":10,"direction":"短线偏空、持续数小时至1-2天；中期混合","assessment":"最新A级信息仍由Coldcard漏洞持续利用、至少15个攻击者、要求迁移及可能扩大影响的安全事件簇主导，直接抬升自托管/托管安全风险溢价，压制BTC短线风险偏好。ETF流入、英美稳定币监管合作、支付牌照和基础设施提供中期缓冲，但未给出1-2小时可验证的资金流方向；对XRP/IOST/SKL没有直接催化，若BTC回撤，低流动性山寨币的跌幅和滑点风险通常更高。"},
    "resonance": {
        "technical":"BTC 64735.5，trend_up，RSI14 59.5、量比0.86，24h +1.03%，技术结构偏多但尚无机会榜方向性信号；XRP空头反抽0.73却缩量，IOST/SKL异常放量但都是hold防守，不构成买入共振。",
        "event":"A级Coldcard安全事件簇偏空，与BTC趋势偏多冲突；机会标的无独立A级催化。",
        "onchain":"最近可见BTC链上检查均为neutral、confidence 0.3，无拥堵、无大额异动；既未确认恐慌外流，也未确认方向性鲸鱼买盘。",
        "sentiment_macro":"Fear & Greed 27 (Fear)；BTC DVOL 34.33中等、ETH DVOL 47.70较高；稳定币总量约3075.35亿美元，USDT占59.5%，但没有本轮流入方向；全球市值约2.2874万亿美元。资金池规模是缓冲，不等于即时买盘。",
        "movers":"最新movers因Binance testnet HTTP 502而scanned=0，异动和热点板块无法验证，数据质量降级。",
        "conclusion":"技术偏多但量能不足，事件偏空，链上低置信中性，情绪防守，宏观缺少流向确认；五因子不共振。"
    },
    "prediction": {"horizon":"未来1-2小时","btc_price":64735.5,"scenarios":[
        {"name":"趋势上方震荡并测试阻力","probability":0.45,"range":"64500-65000","support":[64500,64300],"resistance":[64800,65000]},
        {"name":"放量突破延续","probability":0.25,"range":"65000-65400","support":[65000],"resistance":[65400],"trigger":"15m收盘站稳65000且量比>=1.3"},
        {"name":"风险偏好回落下探","probability":0.30,"range":"64000-64500","support":[64300,64000],"resistance":[64500],"trigger":"跌破64300并放量，或Coldcard事件出现可验证升级"}
    ],"basis":"本轮机会榜BTC price 64735.5、RSI14 59.5、volume_ratio 0.86、24h +1.03%；宏观F&G 27、BTC DVOL 34.33；链上confidence 0.3；movers扫描失败。","invalidators":"连续15m收盘跌破64300并放量则震荡偏多情景失效；未满足量比>=1.3且站稳65000，不追多。"},
    "conclusion": {"decision":"等待","action":"no_trade","reason":"Top3虽有XRP sell 0.73、IOST/SKL hold 0.70，但没有可执行买入；现货空仓下sell不能裸空，hold不是开仓方向。A级安全事件偏空、Fear 27、链上confidence 0.3、movers扫描0，且BTC量比0.86未确认突破，未形成多因子共振。保持模拟盘空仓，不register_thesis、不进风控、不模拟下单、不新写alert_pending.json。","registered_thesis":False,"risk_approved":False,"simulated_order":"not_submitted","alert_pending":"not_written_new","risk_state":state.get("risk", state),"observation_conditions":["BTC守住64300并以量比>=1.3站稳65000","XRP出现放量跌破结构且组合已有现货（否则不可卖空）","IOST/SKL放量后形成明确收盘方向和更高低点","Coldcard事件不再升级且出现可验证ETF/稳定币资金流","movers恢复扫描、链上directional confidence>=0.6"]},
    "data_quality":{"source":"local artifacts; testnet/demo-derived snapshot, not live execution","verified":["opportunities updated 2026-08-06 01:39:30","macro updated 01:03:39","onchain latest visible checks neutral confidence 0.3","movers updated 01:39:13 with HTTP 502/scanned=0"],"degraded":["opportunity universe displayed 27 rather than requested 40","movers unavailable","event impact fields mostly unknown","state.json read/parse may be unavailable in this cycle"]}
}
with (art / "analysis_log.jsonl").open("a", encoding="utf-8") as f:
    f.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
usage = record_usage(provider="deepseek", model="deepseek-v4-flash", input_tokens=11200, output_tokens=4300)
print(json.dumps({"time":now,"decision":"等待","usage":usage,"log":"appended","alert_pending":"not_written"}, ensure_ascii=False))

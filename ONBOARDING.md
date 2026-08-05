# AI自主交易事业部 · 交接运行手册（ONBOARDING）

> 本文件是**任何新 Hermes 实例接管本项目**的第一入口。先读本文件，再读
> 知识库 `02-项目/AI自主交易事业项目研讨纪要.md`（治理规则全文）。
> 交接方（董事会）只负责：提供本机、提供凭证、启动/终止项目。日常经营归 CEO（接管方 Hermes）。

## 1. 项目定位（30 秒版）

研究优先、模拟优先的交易控制平面。**当前阶段不接真实交易所、不保存 API
密钥、不执行真实下单**——用 **OKX Demo Trading 模拟盘**（虚拟 USDT，主通道）
连跑 30 天模拟盘，先把可审计的决策、风控、报告、回放链路跑通。

权责链：董事会（启动/终止）→ CEO/Hermes（全部日常经营与交易决策）→
风险官（硬边界可否决）→ 执行交易员/适配器（下单，不自创方向）。

## 2. 前置条件

- macOS / Linux，Python **≥3.11**（本项目在 Homebrew python3.14 下开发验证）
- **OKX Demo Trading API Key + Secret + Passphrase**（虚拟资金，无真实资金；OKX App/网页 → 模拟交易环境 → API 管理 → 创建 API Key，选「API 交易」、权限勾含交易）
- （可选）Binance Spot Testnet API Key + Secret（兜底通道）
- Hermes Agent 运行环境（cron、Telegram 网关按需）

## 3. 凭证设置（值绝不写入本文件/代码/Git）

```bash
# OKX Demo Trading 凭证（主通道；模拟/实盘由 x-simulated-trading 请求头区分，适配器写死模拟）
export OKX_API_KEY='...'        # 36 位 UUID
export OKX_API_SECRET='...'     # 32 位 hex
export OKX_API_PASSPHRASE='...' # 创建时自设口令（OKX 界面不显示，忘记需重建 key）

# （可选）Binance 测试网凭证（兜底，在 https://testnet.binance.vision 用 GitHub 登录生成）
export BINANCE_TESTNET_API_KEY='...'
export BINANCE_TESTNET_API_SECRET='...'
```

持久化建议：追加到 `~/.zshrc`（本机专用）。Hermes 的 cron 任务通过
`~/.hermes/scripts/load_binance_env.sh` 加载，无需在 prompt 中暴露值。

### 实盘凭证（董事会授权后才配置）

```bash
# Binance 实盘（仅 LIVE_TRADING_ENABLED=1 后生效）
export BINANCE_API_KEY='...'
export BINANCE_API_SECRET='...'

# Hyperliquid（去中心化交易所）
# 测试网：https://app.hyperliquid-testnet.xyz 生成 ed25519 agent key
export HYPERLIQUID_TESTNET_PRIVATE_KEY='...'
# 实盘：https://app.hyperliquid.xyz 生成 ed25519 agent key
export HYPERLIQUID_PRIVATE_KEY='...'

# 实盘总开关（董事会授权 = 1，否则一切实盘适配器拒绝初始化）
export LIVE_TRADING_ENABLED=1
```

实盘切换流程：模拟盘验证通过 → 董事会授权 `LIVE_TRADING_ENABLED=1` →
配置对应交易所凭证 → 用 `BinanceAdapter(mode="live")` / `HyperliquidAdapter(mode="live")`。
未授权时任何实盘模式初始化都会抛错拒绝。

## 3.1 交易所适配器与执行兜底链

统一接口 `ExchangeAdapter`（src/autotrader/exchange.py）：行情/账户/下单/撤单/订单状态。
- **OkxDemoAdapter**（主通道）：OKX Demo Trading，HMAC-SHA256 base64 签名，市价买单按金额（tgtCcy=quote_ccy），纯标准库
- **BinanceAdapter / BinanceSpotTestnet**：测试网（默认）/实盘双模式，第一兜底
- **HyperliquidAdapter**：第二兜底（测试网需官方界面激活，EIP-712 签名见 hl_crypto.py）

**执行兜底链**：OKX Demo（主）→ Binance 测试网 → Hyperliquid 测试网（逐级切换，订单经风控后执行）。

**仓位与总资金匹配**：资金基准 = OKX 账户总权益（~$80k 虚拟）；单笔风险预算 = 总权益 × 1%；单笔名义上限 = min(总权益 × 20%, 可用 USDT × 30%)；最多 3 持仓。ETH 双向交易已授权（需买可买、缺 USDT 可卖已有 ETH）。

新增交易所 = 实现一个 ExchangeAdapter 子类，风控/账本/决策层无需改动。


## 4. 一键启动

```bash
./start.sh          # 启动 runner（每15分钟一轮）+ Dashboard（127.0.0.1:8765）
```

验证：
- `curl -s http://127.0.0.1:8765/api/status` → JSON 含 nav/positions/market/risk
- `tail artifacts/runner.log` → 每轮"轮次完成"记录

## 5. 接管后必做（CEO 上岗流程）

1. 读知识库研讨纪要（治理/硬风控/报告制度），确认 CEO 职责边界；
2. 运行测试确认环境健康：`PYTHONPATH=src python3 -m unittest discover -s tests -v`（应全绿）；
3. 重建 Hermes 实例级 cron（4 个任务）：
   - 每日 09:00 经营报告 → Telegram（读 `scripts/trading_report.py` 输出）
   - 每 30 分钟异常看门狗（`~/.hermes/scripts/trading_watchdog.py`，静默模式，no_agent）
- **AI交易-CEO告警即时处理**（d64ac330cde3）：看门狗告警时自动唤醒，立即处理并回报 Telegram（每 6 小时兜底）

**Telegram 隔离说明**（重要）：
- 本项目仓库**不含任何 Telegram bot token / chat_id / 频道信息**——告警投递依赖你自己 Hermes 环境的 Telegram 网关配置；
- 克隆者接管后：配置**自己的** Telegram bot + chat_id，重建 cron 时 deliver 用你自己的目标；
- `scripts/watchdog.py` 的 CEO 唤醒依赖环境变量 `CEO_PROCESSING_JOB`（默认 d64ac330cde3）——克隆者重建"CEO告警即时处理"任务后，把新 job_id 通过环境变量覆盖（`export CEO_PROCESSING_JOB=<你的job_id>`），否则 CEO 唤醒不生效（告警发送不受影响）；
   - 每日 10:00/22:00 Hermes 交易假设介入（读 `artifacts/state.json` → 草拟 → 风控 → 虚拟下单 → 简报）
4. 确认 Dashboard 只监听 127.0.0.1（无公网端口、无端口转发）；
5. 第一个月：每日查看经营报告，异常时（熔断/连续否决/Token 突增）立即上报董事会。

## 6. 目录与数据文件

```text
src/autotrader/
├── market.py            市场状态分类器 + 历史K线落盘（market.db, SQLite）
├── portfolio.py         本地账本：持仓/现金/盈亏/净值/最大回撤
├── risk.py              风控：订单级 + 硬边界（连亏5暂停/回撤15%停/25%全平/单笔风险1%）
├── engine.py            决策引擎（假设→风控→模拟执行→审计）
├── strategy.py          策略库（趋势突破/回撤反弹/震荡/防守/事件驱动）
├── news_research.py     新闻研究员：事件分级(A/B/C)+落盘
├── sentiment.py         情绪研究员：资金费率/情绪状态
├── onchain.py           链上研究员：信号记录/钱包共识置信度
├── event_trader.py      事件交易员：五阶段流程
├── llm.py               Hermes 集成：register_thesis / record_usage / 确定性降级
├── exchange.py          交易所适配器统一接口 + 实盘授权开关
├── okx.py               OKX Demo Trading 适配器（主通道：行情/执行/账户）
├── binance.py            Binance 双模式适配器（测试网/实盘，兜底）
├── hyperliquid.py        Hyperliquid 适配器（测试网/实盘，第二兜底）
├── hl_crypto.py         纯 stdlib HL 官方签名（msgpack+EIP-712+secp256k1）
├── binance_testnet.py   Binance Spot Testnet 适配器（向后兼容）
├── team.py              Agent 员工组织（17 岗位完整档案）
└── models.py            数据模型
scripts/
├── runner.py            30 天运行循环（常驻）
├── agent_dispatch.py    ★ 员工调度器：CEO 点名任意岗位立即执行
├── trading_report.py    经营报告（Markdown）
└── watchdog.py          异常看门狗（静默告警）
artifacts/
├── audit.jsonl          决策审计（可回放）
├── orders.jsonl         测试网订单账本（本地主记录）
├── token_usage.json     Token 用量（仅本项目）
├── state.json           最新市场/组合/风控状态（runner 每轮写入）
├── events.jsonl         事件记录（新闻研究员）
├── onchain.jsonl        链上信号记录
├── sentiment.json       情绪状态快照
├── dispatch_last.json   最近一次员工调度结果
├── market.db            历史 K 线（SQLite）
└── runner.log           运行日志
```

## 6.1 员工调度（随时待命）

所有 17 名员工都有工作入口（status=active，随时待命）：

```bash
python3 scripts/agent_dispatch.py --list                   # 全部员工与状态
python3 scripts/agent_dispatch.py 策略研究员                # 点名单个岗位立即执行
python3 scripts/agent_dispatch.py 风险官 组合经理            # 点名多个岗位
python3 scripts/agent_dispatch.py --all-deterministic       # 全部确定性岗位
```

确定性岗位（数据/技术/市场/策略/情绪/组合/风控/事件）直接计算；研究型岗位
（新闻/链上/聪明钱包）由 CEO 联网采集数据后经 record_event/record_signal 落盘，
调度器可随时回放其输出。

## 7. 硬风控参数（不可因 CEO 自信突破）

- 连亏 **5 笔** → 暂停新仓（只允许减仓/平仓）
- 回撤 **15%** → 停止自动开仓；**25%** → 全平模式
- 单笔风险预算：|现价 − 止损| × 数量 ≤ 现金 × **1%**
- 熔断时 SELL/HOLD 放行、BUY 冻结

## 8. 重要边界（违反即失职）

- 绝不连接正式网（适配器只允许 `testnet.binance.vision`）；
- 不保存/打印/提交任何 API Key、Secret、私钥；
- 董事长买卖观点只作研究输入，不自动转订单；
- 模型输出必须过独立风控；Hermes 不直接下单绕过风控；
- 模拟盘结果不得描述为实盘收益；未过验证门槛不申请真实交易权限；
- 不上云、不开放公网端口、不做端口转发。

## 9. 常见问题

- **测试失败 `No module named 'autotrader'`**：需要 `PYTHONPATH=src` 或 pytest（pyproject 已配 pythonpath）
- **账户/订单接口报 missing key**：环境变量未加载，先 `source ~/.zshrc`（OKX_API_KEY/SECRET/PASSPHRASE）或重新 export
- **OKX 下单报 51020 最小金额不足**：市价买单须按金额（适配器已自动 tgtCcy=quote_ccy），且单笔名义受可用 USDT × 30% 约束
- **Dashboard 打不开**：确认进程存活且只监听 127.0.0.1（`lsof -i :8765`）
- **模拟盘账户重置**：OKX App 模拟交易界面可一键重置账户（清空持仓/恢复初始虚拟资金）；重置后需清空本地账本 `orders.jsonl` 并重启 runner（events.jsonl 会记录 account_reset 事件）

## 健康检查

接管后先跑一次健康检查，确认系统全绿：

```bash
PYTHONPATH=src /opt/homebrew/bin/python3.14 scripts/health_check.py   # 退出码 0 = 健康
```

检查：进程存活 / 12 个依赖数据文件完整性 / L3 严重事件 / cron error。

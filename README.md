# AI自主交易事业部 · 自适应交易运营系统

> 一个**可打包交付、可无差别接管**的 AI 交易运营系统：Hermes 任 CEO 全权经营，
> 20 名 Agent 员工平时主动履职、随时可指派；数据驱动的策略自适应调整；
> 硬风控程序强制。当前阶段运行于 **Binance Spot Testnet 模拟盘**（30 天验证期）。

---

## 1. 这是什么

把"AI 交易事业部"做成一套**不依赖任何 LLM API 的完整运营系统**：

- **Hermes（模型执行者）= CEO**：草拟交易假设、研究归纳、证据冲突分析、持仓复核、报告文字化；
- **本地程序（确定性）= 全员员工**：行情采集、指标、市场状态、策略、风控、账本、审计、报告——零 Token 成本、7×24 常驻；
- **硬风控独立否决**：连亏 5 笔暂停新仓、回撤 15% 停自动开仓、25% 全平、单笔风险 ≤ 现金 1%，程序强制不可绕过；
- **自适应**：每笔平仓盈亏按策略归因，连亏 3 笔降权、连亏 5 笔停用、盈利恢复——策略权重随绩效自动调整。

## 2. 治理模型（一句话版）

```text
董事会（启动/终止项目）
  └─ CEO / Hermes（全部日常经营与交易决策）
       └─ 风险官（硬边界可否决）
            └─ 执行交易员/适配器（下单，不自创方向）
```

董事长观点只记录为"待验证假设"，绝不自动转换为交易指令。权责不因短期盈亏改变。

## 3. 系统架构

```text
┌───────────────────────────── 本机控制平面（127.0.0.1） ─────────────────────────────┐
│                                                                                      │
│  scripts/runner.py          每 15 分钟一轮：采集→指标→市场状态→风控→组合→策略信号→   │
│   ── 常驻运行循环            情绪→事件→审计 → 全员"最近工作"写入 state.json          │
│                                                                                      │
│  Hermes 介入（cron 10:00/22:00）  研究扫描（新闻/链上）→ 交易假设 → 风控 → 决策落盘   │
│  经营报告（cron 09:00）           净值/持仓/盈亏/风控/Token → Telegram               │
│  异常看门狗（cron 每30分钟）       API异常/订单不一致/资金预警 → 立即告警             │
│                                                                                      │
│  dashboard_server.py          Dashboard（本地浏览器，5秒自动刷新）                    │
│                                                                                      │
│  src/autotrader/                                                                      │
│  ├─ market.py         市场状态分类器（trend/sideways）+ K线落盘 SQLite               │
│  ├─ portfolio.py      本地账本：持仓/现金/盈亏/净值/最大回撤（主记录）                │
│  ├─ risk.py           硬风控：连亏5暂停 / 回撤15%停 / 25%全平 / 单笔风险1%           │
│  ├─ strategy.py       五类策略：趋势突破/回撤反弹/震荡高抛低吸/防守/事件驱动          │
│  ├─ strategy_tracker.py  策略绩效归因 + 权重自适应（降权/停用/恢复）                  │
│  ├─ sentiment.py      情绪状态（资金费率/波动率/量比 → fomo~panic）                  │
│  ├─ news_research.py  事件分级（A/B/C）→ events.jsonl                                │
│  ├─ onchain.py        链上信号记录 → onchain.jsonl                                   │
│  ├─ event_trader.py   五阶段事件交易框架                                             │
│  ├─ team.py           17 岗位完整档案（职责/输入/输出/权限/考核/失败处理）            │
│  ├─ exchange.py       交易所统一适配器接口 + LIVE_TRADING_ENABLED 实盘授权开关        │
│  ├─ binance.py        Binance 适配器（testnet 默认 / live 需授权）                    │
│  ├─ hyperliquid.py    Hyperliquid 适配器（ed25519 agent key 签名，双模式）            │
│  ├─ keccak.py         纯 Python Keccak-256（Hyperliquid 签名用）                      │
│  └─ llm.py            Hermes 集成层（register_thesis / record_usage）                 │
│                                                                                      │
│  scripts/agent_dispatch.py   员工调度器：点名即上岗 / --all-deterministic 全员出动    │
│  scripts/trading_report.py   经营报告生成（区分已验证/历史/推断/拟建设）               │
│  scripts/watchdog.py         异常看门狗脚本                                          │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

**数据流**：行情 → market.py → 指标/状态 → 策略（权重自适应）→ 信号 → Hermes 决策 → risk.py 风控 → 账本/审计 → 报告/Dashboard。

## 4. 快速上手（新 Hermes 接管，约 15 分钟）

```bash
# 1) 克隆（私库，需要授权）
git clone git@github.com:<owner>/ai-trading-desk.git
cd ai-trading-desk

# 2) 配置测试网凭证（值绝不进代码/Git）
#    在 https://testnet.binance.vision 用 GitHub 登录生成
export BINANCE_TESTNET_API_KEY='...'
export BINANCE_TESTNET_API_SECRET='...'
#    建议追加到 ~/.zshrc 本机持久化

# 3) 一键启动（幂等）
./start.sh                # runner（15分钟一轮）+ Dashboard（127.0.0.1:8765）

# 4) 验证
PYTHONPATH=src python3 -m unittest discover -s tests -v   # 全量测试
curl -s http://127.0.0.1:8765/api/status | head -c 400    # Dashboard API

# 5) 建立定时任务（Hermes cron，按需）
#    - 每日经营报告 → Telegram
#    - 异常看门狗（每30分钟）
#    - Hermes 交易假设介入（每日 10:00/22:00）
```

> **完整交接流程见 [ONBOARDING.md](ONBOARDING.md)**（新 Hermes 第一入口）。

## 5. 员工组织（17 岗位，全部"待命 + 平时主动履职"）

| 岗位 | 平时主动做什么 | 调度入口 |
|------|--------------|---------|
| CEO / 总交易代理 | 每日 10/22 点研究+决策介入，重大事件立即处理 | cron / 手动 |
| 风险官 / 风控引擎 | 每轮检查连亏/回撤/熔断 | runner 自动 |
| 执行交易员 / 交易所适配器 | 订单经风控后执行（Binance/Hyperliquid） | runner/决策触发 |
| 审计员 / 本地账本 | 审计与账本持续写入 | runner 自动 |
| 数据工程师 / 数据质量官 | K线采集落盘 | runner 自动 |
| 技术分析员 | RSI/ATR/EMA/量比计算 | runner 自动 |
| 市场状态官 | 趋势/震荡/流动性判定 | runner 自动 |
| API与应急响应官 | 看门狗 30 分钟巡检 | cron 自动 |
| 经营报告员 | 每日 09:00 经营报告 | cron 自动 |
| 成本与资源管理员 | Token 用量登记、成本监控 | 持续 |
| 宏观与新闻研究员 | 每日扫描新闻、事件分级(A/B/C)落盘 | CEO 介入时 |
| 策略研究员 | 每轮出信号 + 绩效归因 + 权重自适应 | runner 自动 |
| 组合经理 / 持仓经理 | 每轮净值/持仓/回撤核算 | runner 自动 |
| 链上数据分析员 | 链上信号记录/回放 | CEO 介入时 |
| 聪明钱包研究员 | 钱包共识置信度 | CEO 介入时 |
| 情绪与传播研究员 | 资金费率/情绪状态更新 | runner 自动 |
| 事件交易员 | 活跃事件五阶段跟踪 | runner 自动 |

**调度器**：`python3 scripts/agent_dispatch.py 策略研究员`（点名）、`--all-deterministic`（全员出动）。

## 6. 硬风控（程序强制）

| 规则 | 阈值 | 动作 |
|------|------|------|
| 连续亏损 | ≥5 笔 | 暂停新仓（只允许减仓/平仓） |
| 回撤 | ≥15% | 停止自动开仓 |
| 回撤 | ≥25% | 全平模式 |
| 单笔风险 | \|现价−止损\|×数量 > 现金×1% | 拒绝 |
| 禁止 | — | 马丁格尔 / 亏损加仓 / 满仓 / 取消硬止损 |
| 熔断 | 触发 | SELL/HOLD 放行、BUY 冻结 |

## 7. 运行形态（30 天模拟盘 · 分层调度）

- **确定性数据层（零 Token，跑满 24h）**：价格异常 **1 分钟**（guardian.py）· 新闻 RSS **5 分钟** · 链上/鱼群扫描 **15 分钟** · 情绪/宏观（恐惧贪婪/DVOL/稳定币）**60 分钟** · 常规行情/指标/风控/账本/机会扫描（40 标的）**15 分钟**（runner.py）；
- **模型分析层（deepseek-v4-flash，3 元/天预算）**：持续分析循环 **每 10 分钟**（机会榜+新闻+链上+宏观共振研判）· 决策简报 4 次/天 · 市场预测 3 次/天 · 每日前瞻/盘后复盘/历史绩效/策略研发/衍生品资金面/异动研究/新闻解读/多周期全景；
- **每日 09:00**：经营报告（净值/持仓/盈亏/风控/Token，区分已验证/推断/拟建设）；
- **每 30 分钟**：看门狗巡检，异常立即告警（不等待日报）；行动级机会 → Telegram 即时告警；
- **学习升级闭环**：盘后复盘（22:30）产出改进项 → improvements.jsonl → CEO 次日审核落地；周日策略复盘淘汰/升级策略。

## 8. 测试

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v   # 92/92 全绿
```

覆盖：引擎决策、市场分类器、组合账本、硬风控、Keccak 向量、Hyperliquid 签名、策略库、自适应权重、员工调度。

## 9. 目录与数据文件

```text
artifacts/          运行时产物（本地主记录，不提交 Git）
├─ audit.jsonl        决策审计（CEO 交易假设 + 风控结论）
├─ orders.jsonl       订单账本（主记录）
├─ state.json         最新市场/组合/风控/员工工作状态（Dashboard 数据源）
├─ signals.jsonl      策略信号历史
├─ strategy_weights.json  策略自适应权重表
├─ sentiment.json     情绪状态
├─ events.jsonl       事件记录
├─ onchain.jsonl      链上信号
├─ market.db          K线历史（SQLite）
└─ token_usage.json   本项目 Token 用量
```

## 10. 不可违反边界（违反即失职）

1. 绝不连接正式交易所（除非 `LIVE_TRADING_ENABLED=1` 且董事会授权）；
2. 不保存/打印/提交任何 API Key、Secret、钱包私钥；
3. 董事长观点不自动转订单；
4. 模型输出必须过独立风控，不得绕过风控下单；
5. 模拟盘结果不得描述为实盘收益；
6. 不上云、不开放公网端口；Dashboard 只监听 127.0.0.1；
7. 测试网数据不代表真实流动性/滑点/情绪；
8. 实盘仅在 30 天模拟验证通过后，经董事会授权开启。

## 11. 接管检查单（其他 Hermes）

- [ ] 读 [AGENTS.md](AGENTS.md)（本项目行为准则）与 [ONBOARDING.md](ONBOARDING.md)
- [ ] `git clone` 后 `PYTHONPATH=src python3 -m unittest discover -s tests` 全绿
- [ ] 配置 Binance 测试网凭证（环境变量，不入库）
- [ ] `./start.sh` 启动，`curl http://127.0.0.1:8765/api/status` 有数据
- [ ] 重建 4 个 cron（报告/看门狗/介入×2）
- [ ] 确认仅监听 127.0.0.1，无公网端口
- [ ] 前 30 天只跑模拟盘，验证通过后申请实盘授权

---

*治理规则全文与实施进展见内部知识库研讨纪要（不在本仓库）。*
*本项目零第三方运行时依赖（stdlib only）；`cryptography` 为可选依赖（仅 Hyperliquid 签名）。*

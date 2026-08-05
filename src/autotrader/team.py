"""Runtime employee registry for the simulation operation."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Employee:
    name: str
    department: str
    status: str
    mode: str
    responsibility: str


EMPLOYEES = [
    Employee("CEO / 总交易代理", "决策", "active", "deterministic", "综合证据并形成交易意图"),
    Employee("风险官 / 风控引擎", "风险", "active", "deterministic", "审核订单、现金、流动性和硬边界"),
    Employee("执行交易员 / Binance适配器", "执行", "active", "testnet", "连接Binance Spot Testnet并同步订单"),
    Employee("审计员 / 本地账本", "审计", "active", "local", "记录决策、订单、余额和报告"),
    Employee("数据工程师 / 数据质量官", "数据", "active", "deterministic", "采集行情、规则并标记数据质量"),
    Employee("技术分析员", "研究", "active", "deterministic", "计算价格变化、波动和基础结构"),
    Employee("市场状态官", "研究", "active", "deterministic", "将市场分类为观察、趋势或异常"),
    Employee("API与应急响应官", "运营", "active", "deterministic", "检查连接、超时、降级和事件记录"),
    Employee("经营报告员", "财务", "active", "local", "生成USDT净值、盈亏和运行报告"),
    Employee("成本与资源管理员", "财务", "active", "local", "统计Token、数据和运行成本"),
    Employee("宏观与新闻研究员", "研究", "ready_to_connect", "DeepSeek待接入", "核验新闻、公告和预期差"),
    Employee("策略研究员", "研究", "active", "deterministic", "比较策略并跟踪失效"),
    Employee("组合经理 / 持仓经理", "组合", "active", "deterministic", "管理组合暴露和退出计划"),
    Employee("链上数据分析员", "研究", "queued", "数据源待接入", "分析链上资金与安全标签"),
    Employee("聪明钱包研究员", "研究", "queued", "数据源待接入", "建立钱包画像，不盲目跟单"),
    Employee("情绪与传播研究员", "研究", "queued", "社媒数据源待接入", "分析传播和拥挤风险"),
    Employee("事件交易员", "研究", "queued", "新闻员工完成后启用", "进行事件分级和分阶段计划"),
]


def snapshot() -> list[dict[str, str]]:
    return [asdict(employee) for employee in EMPLOYEES]


def counts() -> dict[str, int]:
    result: dict[str, int] = {}
    for employee in EMPLOYEES:
        result[employee.status] = result.get(employee.status, 0) + 1
    return result


def research_team() -> list[dict[str, str]]:
    return [
        employee
        for employee in snapshot()
        if employee["department"] in {"研究", "数据", "组合"}
        and employee["status"] == "active"
    ]

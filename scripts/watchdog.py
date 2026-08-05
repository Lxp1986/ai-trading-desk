#!/usr/bin/env python3
"""AI自主交易事业部异常看门狗（Telegram 静默告警）。

用法: python3 scripts/watchdog.py
- 无异常: 无输出（cron no_agent 模式下静默，不打扰）
- 有异常: 输出 Markdown 告警文本（cron 会原样发到 Telegram）

检查项（分层，与研讨纪要 6.1 一致）：
1. Dashboard / 项目进程是否存活
2. 审计记录异常增长（最近 N 条全部被否决 → 策略失效预警）
3. Token 用量异常（调用次数突增 → 成本预警）
4. 审计文件可读性（损坏 → 数据完整性预警）
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "artifacts" / "audit.jsonl"
TOKEN_USAGE = ROOT / "artifacts" / "token_usage.json"
EVENTS = ROOT / "artifacts" / "events.jsonl"
ALERT_PENDING = ROOT / "artifacts" / "alert_pending.json"
ALERT_PROCESSED = ROOT / "artifacts" / "alert_processed.json"

ALERT_THRESHOLD_REJECTED = 5      # 连续否决数
TOKEN_DELTA_ALERT = 200_000       # 突增检测：30 分钟窗口内新增 tokens 阈值（≈日化 96M，正常 ~42k/30min 的 5 倍）
CALL_DELTA_ALERT = 60             # 突增检测：30 分钟窗口内新增调用次数阈值（规划 165 次/天 ≈ 3.4 次/30min 的 17 倍）
EVENT_WINDOW_MINUTES = 35         # 事件检查窗口（覆盖两轮 runner + 巡检间隔）

# 看门狗状态（记录上次检查基线，避免累计超阈值后每 30 分钟重复轰炸）
WATCHDOG_STATE = ROOT / "artifacts" / "watchdog_state.json"

# CEO 即时处理任务（看门狗告警时唤醒：hermes cron run 触发其立即处理）
# 克隆者环境：设置环境变量 CEO_PROCESSING_JOB=<自己的任务job_id>（见 ONBOARDING.md）
import os as _os

CEO_PROCESSING_JOB = _os.environ.get("CEO_PROCESSING_JOB", "d64ac330cde3")


def wake_ceo() -> None:
    """双通道闭环：告警通知董事长的同时，唤醒 CEO 立即处理。

    调用 hermes cron run 触发 CEO 告警即时处理任务（下一调度 tick 生效）。
    失败不影响告警本身输出。
    """
    import shutil

    hermes = shutil.which("hermes")
    if not hermes or not CEO_PROCESSING_JOB:
        return
    try:
        subprocess.Popen(
            [hermes, "cron", "run", CEO_PROCESSING_JOB],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except Exception:
        pass


def now_cn() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M")


def dashboard_alive() -> bool:
    try:
        import urllib.request

        with urllib.request.urlopen("http://127.0.0.1:8765/api/status", timeout=3) as resp:
            return resp.status == 200
    except Exception:
        return False


def main() -> None:
    alerts: list[str] = []

    # 1. Dashboard 存活
    if not dashboard_alive():
        alerts.append("❌ **Dashboard 未运行**（127.0.0.1:8765 无响应）——控制平面可能已停止。")

    # 2. 审计文件可读性
    records: list[dict] = []
    if AUDIT.exists():
        try:
            for line in AUDIT.read_text(encoding="utf-8").splitlines():
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        except OSError as exc:
            alerts.append(f"❌ **审计文件不可读**：{exc}")
    else:
        alerts.append("⚠️ **审计文件不存在**：`artifacts/audit.jsonl` 缺失，项目可能尚未运行过。")

    # 3. 连续否决 → 策略失效预警（hold 观望不计入否决）
    if records:
        recent = records[-ALERT_THRESHOLD_REJECTED:]
        rejected = [
            r for r in recent
            if not r.get("decision", {}).get("approved")
            and r.get("decision", {}).get("intent", {}).get("side") != "hold"
        ]
        if len(rejected) >= ALERT_THRESHOLD_REJECTED:
            alerts.append(
                f"⚠️ **策略失效预警**：最近 {len(rejected)} 条交易假设全部被风控否决。"
                "建议复核当前市场状态与假设质量。"
            )

    # 4. Token 用量异常（突增检测：30 分钟窗口内新增超阈值才告警，防重复轰炸）
    if TOKEN_USAGE.exists():
        try:
            usage = json.loads(TOKEN_USAGE.read_text(encoding="utf-8"))
            calls = int(usage.get("api_calls", 0))
            total = int(usage.get("total_tokens", 0))
            # 读上次检查基线（首次运行以当前值为基线 → 静默）
            state = {}
            if WATCHDOG_STATE.exists():
                try:
                    state = json.loads(WATCHDOG_STATE.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    state = {}
            last_total = int(state.get("last_total", total))
            last_calls = int(state.get("last_calls", calls))
            delta_total = total - last_total
            delta_calls = calls - last_calls
            # 无论是否告警都更新基线（增量口径：只反映本次窗口内的消耗）
            WATCHDOG_STATE.write_text(
                json.dumps({"last_total": total, "last_calls": calls}, ensure_ascii=False),
                encoding="utf-8",
            )
            if delta_total > TOKEN_DELTA_ALERT or delta_calls > CALL_DELTA_ALERT:
                alerts.append(
                    f"⚠️ **Token 成本预警**：30 分钟窗口新增 {delta_total} tokens / "
                    f"{delta_calls} 次调用（累计 {total} / {calls}），"
                    "远超正常消耗速率，疑似调用异常。"
                )
        except (OSError, ValueError):
            alerts.append("⚠️ **Token 用量文件损坏**：`artifacts/token_usage.json` 无法解析。")

    # 5. 新异常事件（runner 检测到但尚未告警的行情/风控事件）
    if EVENTS.exists():
        try:
            import time as _time
            now_ts = _time.time()
            for line in EVENTS.read_text(encoding="utf-8").splitlines()[-20:]:
                if not line.strip():
                    continue
                ev = json.loads(line)
                at = ev.get("at", "")
                # 事件时间解析（"2026-08-05 18:40" 格式）
                try:
                    ev_ts = datetime.strptime(at, "%Y-%m-%d %H:%M").timestamp()
                except (ValueError, TypeError):
                    continue
                if now_ts - ev_ts > EVENT_WINDOW_MINUTES * 60:
                    continue  # 旧事件不重复告警
                if ev.get("level") in ("L2", "L3", "L4"):
                    alerts.append(
                        f"⚠️ **行情异常事件**（{ev.get('type')}）：{ev.get('detail', '')}"
                    )
        except (OSError, json.JSONDecodeError):
            pass

    # 6. 持续分析循环的行动级机会/异常标记（CEO 高频分析产出）
    if ALERT_PENDING.exists():
        try:
            alert = json.loads(ALERT_PENDING.read_text(encoding="utf-8"))
            processed = {}
            if ALERT_PROCESSED.exists():
                try:
                    processed = json.loads(ALERT_PROCESSED.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    processed = {}
            generated = alert.get("generated_at", "")
            if generated and processed.get("generated_at") != generated:
                level = alert.get("level", "info")
                summary = alert.get("summary", "")
                if level in ("action", "critical"):
                    alerts.append(
                        f"🎯 **CEO行动级信号**（{level}）：{summary}"
                    )
                ALERT_PROCESSED.write_text(
                    json.dumps({"generated_at": generated}, ensure_ascii=False), encoding="utf-8"
                )
        except (OSError, json.JSONDecodeError):
            pass

    if alerts:
        print(f"🚨 **AI自主交易事业部 · 异常告警**（{now_cn()}）")
        print("")
        for alert in alerts:
            print(alert)
        print("")
        print("*此消息由本地看门狗脚本自动生成；CEO 已同时被唤醒处理。*")
        wake_ceo()  # 双通道：通知董事长的同时唤醒 CEO 立即处理


if __name__ == "__main__":
    main()

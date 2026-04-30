#!/usr/bin/env python3
"""瓶颈猎手 - 自动化扫描入口（供 GitHub Actions 与本地手动调用）.

用法：
    python scripts/run_scan.py daily
    python scripts/run_scan.py weekly
    python scripts/run_scan.py monthly
    python scripts/run_scan.py review --date 2026-04-30   # 重新复盘某日

环境变量（见 scripts/.env.example）：
    ANTHROPIC_API_KEY   必填
    CLAUDE_MODEL        默认 claude-opus-4-7
    CLAUDE_EFFORT       默认 high；推荐 xhigh 用于 agentic
    CLAUDE_MAX_TOKENS   默认 32000

可选环境变量（运行时上下文，给当日 user message 用）：
    PORTFOLIO   "$LITE 8% / $AXTI 5% / cash 30%"
    MACRO_NOTE  "MSFT 盘后财报，CPI 08:30 ET"
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

# Make `lib.*` importable when running this script directly.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import archiver, claude_client, prompts  # noqa: E402


def _today_et() -> date:
    """Best-effort 'today in ET' — fine without zoneinfo for archiving purposes."""
    return datetime.utcnow().date()  # naive UTC; close enough for filename use


def cmd_daily(_args: argparse.Namespace) -> int:
    today = _today_et().isoformat()
    portfolio = os.environ.get("PORTFOLIO", "（无持仓 / 待用户填写）")
    macro = os.environ.get("MACRO_NOTE", "（待 web_search 抓取）")

    system = prompts.build_system_prompt()
    user = prompts.build_daily_user_message(
        today=today, portfolio=portfolio, macro=macro
    )

    print(f"[scan] daily run for {today}", file=sys.stderr)
    body, usage = claude_client.run(system, user)
    target = archiver.archive(f"{today}.md", body, usage)
    print(f"[scan] wrote {target.relative_to(Path.cwd()) if target.is_absolute() else target}", file=sys.stderr)
    print(f"[scan] usage: {usage}", file=sys.stderr)
    return 0


def cmd_weekly(_args: argparse.Namespace) -> int:
    end = _today_et()
    start = end - timedelta(days=4)  # last 5 trading days approx

    system = prompts.build_system_prompt()
    user = prompts.build_weekly_review_message(start.isoformat(), end.isoformat())

    print(f"[scan] weekly review {start} → {end}", file=sys.stderr)
    body, usage = claude_client.run(system, user)
    target = archiver.archive(f"周复盘_{end.isoformat()}.md", body, usage)
    print(f"[scan] wrote {target}", file=sys.stderr)
    print(f"[scan] usage: {usage}", file=sys.stderr)
    return 0


def cmd_monthly(_args: argparse.Namespace) -> int:
    today = _today_et()
    month = today.strftime("%Y-%m")

    system = prompts.build_system_prompt()
    user = prompts.build_monthly_review_message(month)

    print(f"[scan] monthly review {month}", file=sys.stderr)
    body, usage = claude_client.run(system, user)
    target = archiver.archive(f"月复盘_{month}.md", body, usage)
    print(f"[scan] wrote {target}", file=sys.stderr)
    print(f"[scan] usage: {usage}", file=sys.stderr)
    return 0


def cmd_review(args: argparse.Namespace) -> int:
    target_date = args.date
    system = prompts.build_system_prompt()
    user = (
        f"重新复盘 {target_date}：\n\n"
        f"1. 拉取 `07-每日复盘归档/{target_date}.md`（用 web_fetch 或就你看到的内容）\n"
        f"2. 用 web_search 查每个推荐标的从 {target_date} 至今的实际表现\n"
        f"3. 按 04-自进化复盘机制.md 做归因分析\n"
        f"4. 输出 1-3 条候选规则\n"
    )
    print(f"[scan] re-review {target_date}", file=sys.stderr)
    body, usage = claude_client.run(system, user)
    target = archiver.archive(f"复盘_{target_date}.md", body, usage)
    print(f"[scan] wrote {target}", file=sys.stderr)
    print(f"[scan] usage: {usage}", file=sys.stderr)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="瓶颈猎手自动扫描")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("daily", help="每日扫描 → 07-每日复盘归档/YYYY-MM-DD.md")
    sub.add_parser("weekly", help="周复盘")
    sub.add_parser("monthly", help="月复盘")
    rv = sub.add_parser("review", help="重新复盘某日")
    rv.add_argument("--date", required=True, help="YYYY-MM-DD")

    args = parser.parse_args()

    handlers = {
        "daily": cmd_daily,
        "weekly": cmd_weekly,
        "monthly": cmd_monthly,
        "review": cmd_review,
    }
    return handlers[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())

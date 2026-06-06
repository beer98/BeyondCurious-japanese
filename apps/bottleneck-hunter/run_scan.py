#!/usr/bin/env python3
"""瓶颈猎手 - 4 阶段自进化循环.

每次运行（每日 GitHub Action cron）：
  Phase A · 复盘昨日 → 给昨日推荐打分 → 写入 08-知识沉淀/绩效台账.jsonl
  Phase B · 蒸馏规则 → 扫台账，连续 ≥3 次模式 → 写入规则库候选区
  Phase C · 今日扫描 → 用最新规则库 + 工具循环 → 出今日报告
  Phase D · 自审 → 第二轮 LLM 检查今日报告 → 追加批注

CLI:
    python scripts/run_scan.py loop              # 完整 4 阶段循环（GH Actions 默认）
    python scripts/run_scan.py daily             # 只跑 C
    python scripts/run_scan.py review            # 只跑 A+B
    python scripts/run_scan.py critic --file X.md  # 只跑 D
"""

from __future__ import annotations
import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import archiver, audit, dashboard, enrich, ledger, llm, market, prompts  # noqa: E402

# repo-root/docs/ for GitHub Pages
REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = REPO_ROOT / "docs"

# Max BLOCKER-fix regeneration loops (Phase D₃)
MAX_REGEN_ITERS = int(os.environ.get("MAX_REGEN_ITERS", "2"))


def _today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


# ---------- Phase A: review yesterday ----------


def phase_a_review() -> dict:
    """Pull yesterday's report, ask LLM to fetch actual prices and score each pick."""
    found = archiver.find_yesterday_report()
    if not found:
        print("[A] no prior report, skipping review", file=sys.stderr)
        return {"skipped": True, "reason": "no_prior_report"}

    last_path, last_text = found
    yesterday_name = last_path.name
    print(f"[A] reviewing {yesterday_name}", file=sys.stderr)

    picks_block = archiver.extract_json(last_text)
    if not picks_block or "picks" not in picks_block:
        print("[A] no picks JSON in yesterday's report", file=sys.stderr)
        return {"skipped": True, "reason": "no_picks_json"}

    system = prompts.build_system_prompt()
    user = prompts.build_review_user(
        yesterday_md=yesterday_name,
        picks_json=picks_block["picks"],
        today=_today(),
    )
    text, usage = llm.run_agent(system, user)
    review_json = archiver.extract_json(text)
    if not review_json or "entries" not in review_json:
        print("[A] couldn't parse review JSON", file=sys.stderr)
        return {"skipped": True, "reason": "parse_failed", "usage": usage}

    n = ledger.append_entries(review_json["entries"])
    print(f"[A] appended {n} entries to ledger", file=sys.stderr)
    return {"ok": True, "entries": n, "usage": usage}


# ---------- Phase B: distill rules ----------


def phase_b_distill() -> dict:
    patterns = ledger.emerging_patterns(min_count=3)
    if not patterns:
        print("[B] no emerging patterns ≥3, skipping", file=sys.stderr)
        return {"skipped": True}

    print(f"[B] {len(patterns)} emerging patterns", file=sys.stderr)
    rules_text = archiver.RULES_PATH.read_text(encoding="utf-8") if archiver.RULES_PATH.exists() else ""
    system = "你是规则蒸馏助手。基于已观察的模式产出可执行规则草案。"
    user = prompts.build_distill_user(patterns, rules_text)
    text, usage = llm.run_simple(system, user, model=llm.DEFAULT_MODEL)
    archiver.append_rules(text)
    print("[B] appended candidate rules", file=sys.stderr)
    return {"ok": True, "patterns": len(patterns), "usage": usage}


# ---------- Phase C: today's scan ----------


def phase_c_scan() -> tuple[str, list[dict], Path]:
    today = _today()
    portfolio = os.environ.get("PORTFOLIO", "（未提供）")
    macro = os.environ.get("MACRO_NOTE", "（待 web_search 抓取）")

    system = prompts.build_system_prompt()
    user = prompts.build_daily_user(today, portfolio, macro)

    print(f"[C] scanning for {today}", file=sys.stderr)
    text, usage = llm.run_agent(system, user)
    target = archiver.archive_report(f"{today}.md", text, usage)
    print(f"[C] wrote {target.name}", file=sys.stderr)
    return text, [usage], target


# ---------- Phase D: hard audit + soft critic + regen loop ----------


def _extract_picks(text: str) -> list[dict]:
    block = archiver.extract_json(text)
    if not block or not isinstance(block, dict):
        return []
    return block.get("picks") or []


def _fetch_quotes_for(picks: list[dict]) -> dict[str, dict]:
    """Pull current quotes for entry-sanity check."""
    out = {}
    for p in picks:
        sym = (p.get("ticker") or "").lstrip("$").strip().upper()
        if sym:
            out[sym] = market.get_quote(sym)
    return out


def _merge_findings(hard: list[dict], soft: list[dict]) -> list[dict]:
    # Tag source if missing
    for f in soft:
        f.setdefault("source", "llm_critic")
    return hard + soft


def _append_audit_to_report(target_path: Path, soft_text: str, all_findings: list[dict],
                            iteration: int, total_iters: int) -> None:
    """Replace any existing critic block in the report with the latest audit."""
    text = target_path.read_text(encoding="utf-8")

    # Strip prior 自审批注 block (everything from `## 自审批注` to before the footer)
    text = re.sub(
        r"\n## 自审批注.*?(?=\n---\n\n<sub>自动生成|\Z)",
        "",
        text,
        count=1,
        flags=re.DOTALL,
    )

    audit_md = (
        f"\n## 自审批注（红队复核 · 第 {iteration}/{total_iters} 轮）\n\n"
        + soft_text.replace("## 自审批注（红队复核）", "").strip()
        + "\n\n```json\n"
        + json.dumps({"findings": all_findings}, ensure_ascii=False, indent=2)
        + "\n```\n"
    )

    if "<sub>自动生成" in text:
        head, footer = text.split("---\n\n<sub>自动生成", 1)
        text = head.rstrip() + "\n" + audit_md + "\n---\n\n<sub>自动生成" + footer
    else:
        text = text.rstrip() + "\n" + audit_md
    target_path.write_text(text, encoding="utf-8")


def phase_d_audit_loop(report_text: str, target_path: Path) -> dict:
    """Hard audit → soft critic → regenerate-on-BLOCKER loop.

    Iterates up to MAX_REGEN_ITERS+1 times. Each iteration:
      1. Run audit.py hard checks (pure code)
      2. Run LLM critic for soft findings (forbidden to repeat hard checks)
      3. If real BLOCKERs remain AND iterations < max, regenerate Phase C

    Returns metadata: iterations, blocker count per iteration, final findings.
    """
    total_iters = MAX_REGEN_ITERS + 1
    history: list[dict] = []
    total_usage = {"prompt_tokens": 0, "completion_tokens": 0, "regen_calls": 0}

    for iteration in range(1, total_iters + 1):
        picks = _extract_picks(report_text)
        quotes = _fetch_quotes_for(picks)

        # Step 1: hard audit
        hard_findings = audit.run_all(picks, report_text, quotes)
        hard_blockers = audit.count_blockers(hard_findings)
        print(
            f"[D] iter {iteration}/{total_iters}: hard audit found "
            f"{len(hard_findings)} findings ({hard_blockers} BLOCKER)",
            file=sys.stderr,
        )

        # Step 2: soft LLM critic, told to skip what hard checks already cover
        system = "你是红队审计师。只审计软性问题——硬规则已由代码兜底。"
        user = prompts.build_critic_user(report_text, hard_findings=hard_findings)
        soft_text, usage = llm.run_simple(system, user)
        total_usage["prompt_tokens"] += usage.get("prompt_tokens", 0)
        total_usage["completion_tokens"] += usage.get("completion_tokens", 0)

        critic_block = archiver.extract_critic_findings(soft_text) or {}
        soft_findings = critic_block.get("findings", []) or []
        all_findings = _merge_findings(hard_findings, soft_findings)
        real_blockers = audit.count_blockers(all_findings)

        history.append({
            "iter": iteration,
            "hard_findings": len(hard_findings),
            "hard_blockers": hard_blockers,
            "soft_findings": len(soft_findings),
            "total_blockers": real_blockers,
        })

        # Always update report with latest audit (so user sees the final state)
        _append_audit_to_report(target_path, soft_text, all_findings,
                                iteration, total_iters)

        # Converged or out of retries
        if real_blockers == 0 or iteration == total_iters:
            print(f"[D] done after {iteration} iter(s); {real_blockers} BLOCKER remain",
                  file=sys.stderr)
            return {
                "ok": True,
                "iterations": iteration,
                "final_blockers": real_blockers,
                "history": history,
                "usage": total_usage,
            }

        # Step 3: regenerate Phase C with BLOCKER feedback
        print(f"[D] regenerating Phase C to fix {real_blockers} BLOCKER...",
              file=sys.stderr)
        feedback = audit.format_blocker_feedback(all_findings)
        prev_picks_json = archiver.extract_json(report_text)
        regen_user = prompts.build_regen_user(feedback, prev_picks_json)
        new_text, regen_usage = llm.run_agent(prompts.build_system_prompt(), regen_user)
        total_usage["prompt_tokens"] += regen_usage.get("prompt_tokens", 0)
        total_usage["completion_tokens"] += regen_usage.get("completion_tokens", 0)
        total_usage["regen_calls"] += 1

        # Save regenerated report (overwrites current; will be re-audited next iter)
        target_path.write_text(new_text, encoding="utf-8")
        report_text = new_text


def phase_d_critic(report_text: str, target_path: Path) -> dict:
    """Backward-compat alias — old name still works."""
    return phase_d_audit_loop(report_text, target_path)


# ---------- Phase E: enrichment (fresh prices + verdict card at top) ----------


def phase_e_enrich(target_path: Path) -> dict:
    text = target_path.read_text(encoding="utf-8")
    picks_block = archiver.extract_json(text)
    if not picks_block or "picks" not in picks_block:
        print("[E] no picks JSON, skipping enrichment", file=sys.stderr)
        return {"skipped": True, "reason": "no_picks"}
    picks = picks_block["picks"]
    print(f"[E] enriching {len(picks)} picks with live quotes/news", file=sys.stderr)
    block = enrich.build_enrichment(picks, text)
    if not block:
        return {"skipped": True, "reason": "no_data"}
    target_path.write_text(enrich.inject_top(text, block), encoding="utf-8")
    print("[E] enrichment block prepended to report", file=sys.stderr)
    return {"ok": True, "picks_enriched": len(picks)}


# ---------- Phase F: HTML dashboard (light-mode, GH Pages) ----------


def phase_f_dashboard(target_path: Path, audit_iterations: int = 1,
                      final_blockers: int = 0) -> dict:
    text = target_path.read_text(encoding="utf-8")
    picks_block = archiver.extract_json(text)
    if not picks_block or "picks" not in picks_block:
        print("[F] no picks JSON, skipping dashboard", file=sys.stderr)
        return {"skipped": True, "reason": "no_picks"}
    picks = picks_block["picks"]
    date_str = target_path.stem
    print(f"[F] rendering HTML dashboard for {date_str}", file=sys.stderr)
    out = dashboard.write_dashboard(
        picks, text, date_str, DOCS_DIR,
        audit_iterations=audit_iterations,
        final_blockers=final_blockers,
    )
    print(f"[F] wrote docs/{out.name} and docs/index.html", file=sys.stderr)
    return {"ok": True, "path": str(out.name)}


# ---------- commands ----------


def cmd_loop(_args) -> int:
    summary = {"date": _today(), "phases": {}}
    summary["phases"]["A"] = phase_a_review()
    summary["phases"]["B"] = phase_b_distill()
    report_text, usages, target = phase_c_scan()
    summary["phases"]["C"] = {"ok": True, "path": str(target.name)}
    d_result = phase_d_audit_loop(report_text, target)
    summary["phases"]["D"] = d_result
    # Re-read after possible regeneration in Phase D
    summary["phases"]["E"] = phase_e_enrich(target)
    summary["phases"]["F"] = phase_f_dashboard(
        target,
        audit_iterations=d_result.get("iterations", 1),
        final_blockers=d_result.get("final_blockers", 0),
    )
    summary["ledger_stats"] = ledger.stats_summary()
    print(json.dumps(summary, ensure_ascii=False, indent=2, default=str), file=sys.stderr)
    return 0


def cmd_daily(_args) -> int:
    phase_c_scan()
    return 0


def cmd_review(_args) -> int:
    phase_a_review()
    phase_b_distill()
    return 0


def cmd_critic(args) -> int:
    target = archiver.ARCHIVE_DIR / args.file
    if not target.exists():
        print(f"file not found: {target}", file=sys.stderr)
        return 1
    phase_d_critic(target.read_text(encoding="utf-8"), target)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("loop", help="完整 4 阶段自进化循环（推荐）")
    sub.add_parser("daily", help="只跑 Phase C（今日扫描）")
    sub.add_parser("review", help="只跑 Phase A+B（复盘 + 蒸馏）")
    cr = sub.add_parser("critic", help="只跑 Phase D（红队审计指定报告）")
    cr.add_argument("--file", required=True, help="YYYY-MM-DD.md")

    args = parser.parse_args()
    handlers = {
        "loop": cmd_loop,
        "daily": cmd_daily,
        "review": cmd_review,
        "critic": cmd_critic,
    }
    return handlers[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())

"""Deterministic hard audit — pure code rules, no LLM, no judgment.

These are the BLOCKERS that math can verify. The LLM critic (Phase D₂) is
*forbidden* from raising findings already covered here (told via prompt).

Rules implemented (matches 00-框架与方法论.md → Layer 5 风险预算):
- 单标的 ≤ 15%
- 单板块 ≤ 35%
- R:R ≥ 1.5（WARNING only — not BLOCKER）
- 必填字段完整：reasoning + scorecard 7 维度
- 当前价 vs 入场区合理性
"""

from __future__ import annotations
import re
from collections import defaultdict
from typing import Any

POSITION_LIMIT_SINGLE = 15.0   # %
POSITION_LIMIT_SECTOR = 35.0   # %
RR_MIN = 1.5

REQUIRED_SCORECARD_KEYS = [
    "shears", "substitutability", "valuation", "financials",
    "technicals", "options", "attention_inverse",
]
REQUIRED_REASONING_KEYS = [
    "catalyst", "supply_chain_node", "social_signal", "failure_signal",
]


def _finding(severity: str, category: str, tickers: list[str],
             title: str, detail: str, actionable: str) -> dict:
    return {
        "severity": severity,
        "category": category,
        "affected_tickers": tickers,
        "title": title,
        "detail": detail,
        "actionable": actionable,
        "source": "hard_audit",
    }


def _parse_num(s: Any) -> float | None:
    if isinstance(s, (int, float)):
        return float(s)
    m = re.search(r"\d+(?:\.\d+)?", str(s) if s else "")
    return float(m.group()) if m else None


def _parse_zone(s: Any) -> tuple[float | None, float | None]:
    nums = re.findall(r"\d+(?:\.\d+)?", str(s) if s else "")
    if len(nums) < 2:
        return None, None
    a, b = float(nums[0]), float(nums[1])
    return min(a, b), max(a, b)


# ---- Individual checks ----


def check_position_limits(picks: list[dict]) -> list[dict]:
    findings: list[dict] = []
    sector_totals: dict[str, float] = defaultdict(float)
    sector_tickers: dict[str, list[str]] = defaultdict(list)

    for p in picks:
        ticker = p.get("ticker", "?")
        pos = p.get("position_pct")
        sector = p.get("sector") or "Unspecified"

        if pos is None or not isinstance(pos, (int, float)):
            findings.append(_finding(
                "BLOCKER", "THESIS_WEAKNESS",
                [ticker],
                "缺 position_pct 字段",
                "Phase C 必须输出明确的单标的仓位百分比（≤15）",
                "在 picks JSON 中加 position_pct: 数字",
            ))
            continue

        if pos > POSITION_LIMIT_SINGLE:
            findings.append(_finding(
                "BLOCKER", "RISK_BUDGET",
                [ticker],
                f"单标的 {pos:.1f}% 超 {POSITION_LIMIT_SINGLE:.0f}% 硬上限",
                f"{ticker} 触犯 Layer 5 风控（单标的 ≤{POSITION_LIMIT_SINGLE:.0f}%）",
                f"减仓至 ≤{POSITION_LIMIT_SINGLE:.0f}%",
            ))

        sector_totals[sector] += float(pos)
        sector_tickers[sector].append(ticker)

    for sec, total in sector_totals.items():
        if total > POSITION_LIMIT_SECTOR:
            findings.append(_finding(
                "BLOCKER", "RISK_BUDGET",
                sector_tickers[sec],
                f"板块「{sec}」累计 {total:.1f}% 超 {POSITION_LIMIT_SECTOR:.0f}% 上限",
                f"{', '.join(sector_tickers[sec])} 同属一个板块",
                f"减少该板块敞口至 ≤{POSITION_LIMIT_SECTOR:.0f}%",
            ))

    return findings


def check_risk_reward(picks: list[dict]) -> list[dict]:
    findings: list[dict] = []
    for p in picks:
        ticker = p.get("ticker", "?")
        lo, hi = _parse_zone(p.get("entry_zone"))
        stop = _parse_num(p.get("stop"))
        target = _parse_num(p.get("target"))
        if not all([lo, hi, stop, target]):
            continue
        entry_mid = (lo + hi) / 2
        risk = abs(entry_mid - stop)
        reward = abs(target - entry_mid)
        if risk <= 0:
            continue
        rr = reward / risk
        if rr < RR_MIN:
            findings.append(_finding(
                "WARNING", "RISK_BUDGET",
                [ticker],
                f"R:R={rr:.2f}（< {RR_MIN}）",
                f"入场≈${entry_mid:.2f} · 止损${stop} · 目标${target}",
                "调整止损/目标价以达到 ≥1.5:1",
            ))
    return findings


def check_required_fields(picks: list[dict]) -> list[dict]:
    findings: list[dict] = []
    for p in picks:
        ticker = p.get("ticker", "?")
        reasoning = p.get("reasoning")

        if not reasoning or not isinstance(reasoning, dict):
            findings.append(_finding(
                "BLOCKER", "THESIS_WEAKNESS",
                [ticker],
                "缺 reasoning 字段",
                "Phase C 未输出 5 层推理链",
                "完整输出 reasoning 对象（含 scorecard）",
            ))
            continue

        scorecard = reasoning.get("scorecard") or {}
        missing_scores = [k for k in REQUIRED_SCORECARD_KEYS if scorecard.get(k) is None]
        if missing_scores:
            findings.append(_finding(
                "WARNING", "THESIS_WEAKNESS",
                [ticker],
                f"7 维评分缺 {len(missing_scores)} 项",
                f"缺失维度: {', '.join(missing_scores)}",
                "补全所有维度评分（0-10 整数）",
            ))

        missing_text = [k for k in REQUIRED_REASONING_KEYS if not reasoning.get(k)]
        if missing_text:
            findings.append(_finding(
                "WARNING", "THESIS_WEAKNESS",
                [ticker],
                f"5 层推理缺 {len(missing_text)} 项文字",
                f"缺失字段: {', '.join(missing_text)}",
                "补充上述字段（每项 ≤40 字）",
            ))
    return findings


def check_entry_sanity(picks: list[dict], quotes: dict[str, dict]) -> list[dict]:
    findings: list[dict] = []
    for p in picks:
        ticker = p.get("ticker", "?")
        norm = ticker.lstrip("$").strip().upper()
        lo, hi = _parse_zone(p.get("entry_zone"))
        if not lo or not hi:
            continue
        q = quotes.get(norm) or {}
        cur = q.get("price")
        if cur is None:
            continue
        if cur < lo * 0.5 or cur > hi * 1.5:
            findings.append(_finding(
                "WARNING", "BLIND_SPOT",
                [ticker],
                f"当前价 ${cur:.2f} 距入场区 [${lo:g}, ${hi:g}] 过远",
                "入场区已不再相关，或趋势已破坏",
                "重新评估入场区间或剔除此推荐",
            ))
    return findings


# ---- Orchestrator ----


def run_all(picks: list[dict], report_text: str = "",
            quotes: dict[str, dict] | None = None) -> list[dict]:
    """Run all hard checks. Returns findings in same shape as LLM critic."""
    quotes = quotes or {}
    out: list[dict] = []
    out.extend(check_position_limits(picks))
    out.extend(check_risk_reward(picks))
    out.extend(check_required_fields(picks))
    out.extend(check_entry_sanity(picks, quotes))
    return out


def count_blockers(findings: list[dict]) -> int:
    """Real blockers = severity BLOCKER + category not DATA_LIMITATION."""
    return sum(
        1 for f in findings
        if f.get("severity") == "BLOCKER" and f.get("category") != "DATA_LIMITATION"
    )


def format_blocker_feedback(findings: list[dict]) -> str:
    """Markdown summary of blockers — to feed back into LLM for regeneration."""
    blockers = [
        f for f in findings
        if f.get("severity") == "BLOCKER" and f.get("category") != "DATA_LIMITATION"
    ]
    if not blockers:
        return ""
    lines = ["# 必须修复的 BLOCKER（来自上一轮审计）\n"]
    for i, f in enumerate(blockers, 1):
        tickers = ", ".join(f.get("affected_tickers") or [])
        lines.append(
            f"## #{i} · {f.get('title','?')}\n"
            f"- 类别：{f.get('category','?')}（来源：{f.get('source','llm')}）\n"
            f"- 影响标的：{tickers}\n"
            f"- 详情：{f.get('detail','')}\n"
            f"- 你必须做的：{f.get('actionable','')}\n"
        )
    return "\n".join(lines)

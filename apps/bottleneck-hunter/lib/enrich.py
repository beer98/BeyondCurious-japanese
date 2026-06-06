"""Post-Phase-D enrichment: inject fresh prices, trend, news, and a verdict
card at the TOP of the report.

This guarantees the report has accurate real-time data regardless of what the
LLM saw during Phase C. Also produces an at-a-glance summary so the user
doesn't have to read all 300 lines to decide what to do.
"""

from __future__ import annotations
import re
from typing import Any

from . import archiver, market


# ---------- Critic findings (structured) ----------


def _norm_ticker(t: str) -> str:
    return (t or "").lstrip("$").strip().upper()


def get_blocking_findings(report_text: str) -> list[dict]:
    """Return findings that are BLOCKER and not DATA_LIMITATION.

    These are the only ones that downgrade a pick to AVOID. Data-limitation
    findings (Nitter down, search rate-limited, etc.) are system problems
    NOT investment problems — they never block.
    """
    block = archiver.extract_critic_findings(report_text)
    if not block:
        return []
    out = []
    for f in block.get("findings", []):
        if f.get("severity") != "BLOCKER":
            continue
        if f.get("category") == "DATA_LIMITATION":
            continue
        out.append(f)
    return out


def get_all_findings(report_text: str) -> list[dict]:
    """All findings for display."""
    block = archiver.extract_critic_findings(report_text)
    return block.get("findings", []) if block else []


def ticker_has_blocker(ticker: str, blockers: list[dict]) -> tuple[bool, str | None]:
    norm = _norm_ticker(ticker)
    for b in blockers:
        tickers = b.get("affected_tickers") or []
        if any(t == "*" for t in tickers):
            return True, b.get("title")
        if any(_norm_ticker(t) == norm for t in tickers):
            return True, b.get("title")
    return False, None


# ---------- Pick parsing & verdict logic ----------


def _parse_entry_zone(text: str) -> tuple[float | None, float | None]:
    """Extract (low, high) from a string like '$70-75', '70.10 - 75.50', '$X.XX-$X.XX'."""
    if not text:
        return None, None
    # Find all numbers (incl. decimals)
    nums = re.findall(r"\d+(?:\.\d+)?", text)
    if len(nums) >= 2:
        try:
            a, b = float(nums[0]), float(nums[1])
            return (min(a, b), max(a, b))
        except ValueError:
            pass
    return None, None


def _parse_stop(text: str) -> float | None:
    if not text:
        return None
    m = re.search(r"\d+(?:\.\d+)?", text)
    return float(m.group()) if m else None


def _verdict(pick: dict, quote: dict, blocker_title: str | None) -> tuple[str, str]:
    """Return (emoji, reason).

    Rules:
    - 🔴 AVOID: this ticker has a BLOCKER finding (non-DATA_LIMITATION),
                quote unavailable, or stop already triggered
    - 🟢 BUY: current price within entry zone
    - 🟡 WATCH: outside entry zone (too high or too low)
    """
    if blocker_title:
        return "🔴 AVOID", f"红队 BLOCKER: {blocker_title}"

    price = quote.get("price")
    if price is None:
        return "🔴 AVOID", "拿不到当前价"

    direction = (pick.get("direction") or "long").lower()
    stop = _parse_stop(pick.get("stop", ""))
    lo, hi = _parse_entry_zone(pick.get("entry_zone", ""))

    # Stop already triggered (long: price < stop ; short: price > stop)
    if stop is not None:
        if direction == "long" and price < stop:
            return "🔴 AVOID", f"已破止损 ${stop}"
        if direction == "short" and price > stop:
            return "🔴 AVOID", f"已破止损 ${stop}"

    if lo is not None and hi is not None:
        if lo <= price <= hi:
            return "🟢 BUY", "区间内，可执行"
        if price < lo:
            margin = round((lo - price) / lo * 100, 1)
            return "🟡 WATCH", f"低于入场区 {margin}%"
        margin = round((price - hi) / hi * 100, 1)
        return "🟡 WATCH", f"高于入场区 {margin}%，等回踩"

    return "🟡 WATCH", "入场区间未指定"


def _critic_has_critical(report_text: str) -> bool:
    """Legacy fallback for old reports that have 🚨 emoji but no structured findings."""
    return "🚨" in report_text or "CRITICAL ISSUES FOUND" in report_text


# ---------- Markdown rendering ----------


def _verdict_table(rows: list[dict]) -> str:
    lines = [
        "| 标的 | 方向 | 建议 | 当前价 | 今日 | 入场区间 | 一句话 |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        change = r["quote"].get("change_pct")
        change_str = (
            f"{'🟢' if change >= 0 else '🔴'} {change:+.2f}%" if change is not None else "?"
        )
        price = r["quote"].get("price")
        price_str = f"${price}" if price is not None else "?"
        lines.append(
            f"| {r['pick'].get('ticker','?')} | {r['pick'].get('direction','?')} "
            f"| {r['verdict']} | {price_str} | {change_str} "
            f"| {r['pick'].get('entry_zone','-')} | {r['reason']} |"
        )
    return "\n".join(lines)


def _snapshot_table(rows: list[dict]) -> str:
    lines = [
        "| 标的 | 当前 | 5 日趋势 | 区间 | 成交量 |",
        "|---|---|---|---|---|",
    ]
    for r in rows:
        q = r["quote"]
        c = r["chart"]
        price = f"${q.get('price')}" if q.get("price") else "?"
        spark = c.get("sparkline", "")
        trend = c.get("trend_pct")
        trend_str = f"{spark} {trend:+.1f}%" if trend is not None else spark or "?"
        rng = (
            f"L ${c.get('low','?')} - H ${c.get('high','?')}"
            if c.get("low") and c.get("high")
            else "?"
        )
        vol = q.get("volume")
        vol_str = f"{vol/1e6:.1f}M" if isinstance(vol, int) else "?"
        lines.append(f"| {r['pick'].get('ticker','?')} | {price} | {trend_str} | {rng} | {vol_str} |")
    return "\n".join(lines)


def _news_block(rows: list[dict]) -> str:
    out = []
    for r in rows:
        t = r["pick"].get("ticker", "?")
        if not r["news"]:
            continue
        out.append(f"\n**{t}**")
        for n in r["news"]:
            if "error" in n:
                out.append(f"- ⚠️ {n['error']}")
                continue
            title = (n.get("title") or "?").replace("\n", " ")
            pub = n.get("publisher") or "?"
            url = n.get("url") or "#"
            out.append(f"- [{title}]({url}) — *{pub}*")
    return "\n".join(out) if out else "_(无）_"


# ---------- Entry point ----------


def fetch_rows(picks: list[dict], report_text: str) -> list[dict]:
    """Fetch fresh quote/chart/news data for each pick and compute verdict.

    Verdict downgrade uses structured critic findings (BLOCKER + non-DATA_LIMITATION).
    Falls back to the legacy 🚨 emoji scan for old reports that lack the JSON block.
    """
    if not picks:
        return []
    blockers = get_blocking_findings(report_text)
    # Legacy fallback: if no structured findings JSON, use 🚨 emoji scan.
    legacy_flag = (
        not archiver.extract_critic_findings(report_text)
        and _critic_has_critical(report_text)
    )
    rows: list[dict] = []
    for p in picks:
        ticker = (p.get("ticker") or "").lstrip("$").strip()
        if not ticker:
            continue
        quote = market.get_quote(ticker)
        chart = market.get_chart_summary(ticker, days=5)
        news = market.get_ticker_news(ticker, limit=3)
        has_block, block_title = ticker_has_blocker(ticker, blockers)
        if legacy_flag and not has_block:
            has_block, block_title = True, "legacy CRITICAL flag"
        emoji_label, reason = _verdict(p, quote, block_title if has_block else None)
        rows.append(
            {
                "pick": p,
                "quote": quote,
                "chart": chart,
                "news": news,
                "verdict": emoji_label,
                "reason": reason,
                "blocker_title": block_title if has_block else None,
            }
        )
    return rows


def build_enrichment(picks: list[dict], report_text: str) -> str:
    """Build the markdown block to prepend to the report."""
    rows = fetch_rows(picks, report_text)
    if not rows:
        return ""

    # Build summary at the top
    buy_count = sum(1 for r in rows if r["verdict"].startswith("🟢"))
    watch_count = sum(1 for r in rows if r["verdict"].startswith("🟡"))
    avoid_count = sum(1 for r in rows if r["verdict"].startswith("🔴"))

    blocker_count = sum(1 for r in rows if r.get("blocker_title"))
    critic_note = (
        f"\n> 🛑 **红队 {blocker_count} 项 BLOCKER**，影响标的已降级为 AVOID。详见自审批注。\n"
        if blocker_count
        else ""
    )

    enrichment = f"""# 🎯 今日最终建议

> 🟢 BUY: **{buy_count}**  ·  🟡 WATCH: **{watch_count}**  ·  🔴 AVOID: **{avoid_count}**
{critic_note}
{_verdict_table(rows)}

## 📊 实时快照 + 5 日趋势

{_snapshot_table(rows)}

> 数据来源：Yahoo Finance（约 15 分钟延迟）

## 📰 各标的最新新闻

{_news_block(rows)}

---

"""
    return enrichment


def inject_top(report_text: str, enrichment: str) -> str:
    """Prepend enrichment block, keep the rest of the report intact."""
    if not enrichment:
        return report_text
    return enrichment + report_text

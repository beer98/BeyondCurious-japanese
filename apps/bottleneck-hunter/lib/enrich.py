"""Post-Phase-D enrichment: inject fresh prices, trend, news, and a verdict
card at the TOP of the report.

This guarantees the report has accurate real-time data regardless of what the
LLM saw during Phase C. Also produces an at-a-glance summary so the user
doesn't have to read all 300 lines to decide what to do.
"""

from __future__ import annotations
import re
from typing import Any

from . import market


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


def _verdict(pick: dict, quote: dict, critic_flagged: bool) -> tuple[str, str]:
    """Return (emoji, label, one-line reason).

    Rules:
    - 🔴 AVOID: critic flagged CRITICAL OR quote unavailable OR triggered stop
    - 🟢 BUY: current price within entry zone
    - 🟡 WATCH: outside entry zone (too high or too low)
    """
    if critic_flagged:
        return "🔴 AVOID", "红队发现 CRITICAL 问题"

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


def build_enrichment(picks: list[dict], report_text: str) -> str:
    """Fetch fresh data for each pick and build the top-of-report card."""
    if not picks:
        return ""

    critic_flagged = _critic_has_critical(report_text)
    rows: list[dict] = []

    for p in picks:
        ticker = (p.get("ticker") or "").lstrip("$").strip()
        if not ticker:
            continue
        quote = market.get_quote(ticker)
        chart = market.get_chart_summary(ticker, days=5)
        news = market.get_ticker_news(ticker, limit=3)
        emoji_label, reason = _verdict(p, quote, critic_flagged)
        rows.append(
            {
                "pick": p,
                "quote": quote,
                "chart": chart,
                "news": news,
                "verdict": emoji_label,
                "reason": reason,
            }
        )

    if not rows:
        return ""

    # Build summary at the top
    buy_count = sum(1 for r in rows if r["verdict"].startswith("🟢"))
    watch_count = sum(1 for r in rows if r["verdict"].startswith("🟡"))
    avoid_count = sum(1 for r in rows if r["verdict"].startswith("🔴"))

    critic_note = (
        "\n> 🚨 **红队发现 CRITICAL 问题**，所有推荐已自动降级为 AVOID。详见报告底部「自审批注」。\n"
        if critic_flagged
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

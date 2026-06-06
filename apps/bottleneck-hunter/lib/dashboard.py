"""Generate a light-mode HTML dashboard from enriched picks data.

Output: a single self-contained HTML file (no external CSS/JS dependencies
beyond a tiny inline SVG sparkline generator).

Color palette: warm off-white background, near-black text, semantic green /
amber / red for verdicts. Sans-serif system font stack. Mobile-responsive.
"""

from __future__ import annotations
import html
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import enrich

# ---- SVG sparkline ----


def svg_sparkline(values: list[float], width: int = 140, height: int = 40,
                  stroke: str = "#374151") -> str:
    if not values or len(values) < 2:
        return ""
    lo, hi = min(values), max(values)
    if hi == lo:
        hi = lo + 1
    pts = []
    for i, v in enumerate(values):
        x = i * width / (len(values) - 1)
        y = height - (v - lo) / (hi - lo) * (height - 4) - 2
        pts.append(f"{x:.1f},{y:.1f}")
    path = "M " + " L ".join(pts)
    # area fill under line
    area = path + f" L {width},{height} L 0,{height} Z"
    return (
        f'<svg viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
        f'xmlns="http://www.w3.org/2000/svg" class="sparkline">'
        f'<path d="{area}" fill="{stroke}" fill-opacity="0.08"/>'
        f'<path d="{path}" fill="none" stroke="{stroke}" stroke-width="1.8" '
        f'stroke-linecap="round" stroke-linejoin="round"/>'
        f"</svg>"
    )


# ---- Entry-zone number-line viz ----


def entry_zone_bar(pick: dict, current_price: float | None) -> str:
    """A tiny visualization showing where current price sits relative to stop /
    entry zone / target."""
    lo, hi = enrich._parse_entry_zone(pick.get("entry_zone", ""))
    stop = enrich._parse_stop(pick.get("stop", ""))
    target = enrich._parse_stop(pick.get("target", ""))
    if current_price is None or lo is None or hi is None:
        return ""
    candidates = [v for v in [stop, lo, hi, target, current_price] if v is not None]
    if not candidates:
        return ""
    p_min, p_max = min(candidates), max(candidates)
    if p_max == p_min:
        return ""
    span = p_max - p_min
    p_min -= span * 0.08
    p_max += span * 0.08
    span = p_max - p_min

    def pct(v: float) -> float:
        return (v - p_min) / span * 100

    zone_left = pct(lo)
    zone_width = pct(hi) - zone_left
    cur_left = pct(current_price)
    stop_left = pct(stop) if stop else None
    tgt_left = pct(target) if target else None

    markers = []
    if stop_left is not None:
        markers.append(
            f'<div class="marker stop" style="left:{stop_left:.1f}%" title="止损 ${stop}"></div>'
            f'<div class="marker-label stop-label" style="left:{stop_left:.1f}%">stop ${stop:g}</div>'
        )
    if tgt_left is not None:
        markers.append(
            f'<div class="marker target" style="left:{tgt_left:.1f}%" title="止盈 ${target}"></div>'
            f'<div class="marker-label target-label" style="left:{tgt_left:.1f}%">target ${target:g}</div>'
        )
    markers.append(
        f'<div class="marker current" style="left:{cur_left:.1f}%" title="当前 ${current_price}"></div>'
        f'<div class="marker-label current-label" style="left:{cur_left:.1f}%">${current_price:g}</div>'
    )

    return f"""
    <div class="zone-bar-wrap">
      <div class="zone-bar">
        <div class="zone-entry" style="left:{zone_left:.1f}%;width:{zone_width:.1f}%" title="入场区 ${lo:g}-${hi:g}"></div>
        {''.join(markers)}
      </div>
    </div>
    """


# ---- Helpers ----


def _esc(s: Any) -> str:
    return html.escape(str(s)) if s is not None else ""


def _verdict_class(label: str) -> str:
    if label.startswith("🟢"):
        return "buy"
    if label.startswith("🟡"):
        return "watch"
    return "avoid"


def _verdict_text(label: str) -> str:
    """Strip emoji, return english text."""
    if label.startswith("🟢"):
        return "BUY"
    if label.startswith("🟡"):
        return "WATCH"
    return "AVOID"


def _format_volume(v: int | None) -> str:
    if not isinstance(v, int) or v <= 0:
        return "—"
    if v >= 1_000_000:
        return f"{v/1_000_000:.1f}M"
    if v >= 1_000:
        return f"{v/1_000:.1f}K"
    return str(v)


def _format_cap(v: int | None) -> str:
    if not isinstance(v, int) or v <= 0:
        return "—"
    if v >= 1_000_000_000:
        return f"${v/1_000_000_000:.1f}B"
    if v >= 1_000_000:
        return f"${v/1_000_000:.1f}M"
    return f"${v}"


# ---- Reasoning chain (5-layer thinking funnel) ----

SCORECARD_LABELS = {
    "shears": "产能/需求剪刀差",
    "substitutability": "替代难度",
    "valuation": "估值安全垫",
    "financials": "财务质量",
    "technicals": "技术形态",
    "options": "期权链流动性",
    "attention_inverse": "反向关注度",
}


def _scorecard_bars(scorecard: dict) -> str:
    """Render the 7-dim scorecard as horizontal bars (light mode)."""
    if not scorecard:
        return ""
    rows = []
    total = 0
    count = 0
    for key, label in SCORECARD_LABELS.items():
        raw = scorecard.get(key)
        try:
            val = float(raw) if raw is not None else None
        except (TypeError, ValueError):
            val = None
        if val is None:
            display = "—"
            width = 0
            color = "var(--text-dim)"
        else:
            val = max(0, min(10, val))
            total += val
            count += 1
            display = f"{val:.0f}"
            width = val * 10  # %
            if val >= 7:
                color = "var(--buy)"
            elif val >= 4:
                color = "var(--watch)"
            else:
                color = "var(--avoid)"
        rows.append(
            f'<div class="score-row">'
            f'<span class="score-label">{label}</span>'
            f'<span class="score-track"><span class="score-fill" style="width:{width:.0f}%;background:{color}"></span></span>'
            f'<span class="score-val">{display}</span>'
            f'</div>'
        )
    avg = total / count if count else 0
    summary = f'<div class="score-avg">总分 <strong>{avg:.1f}</strong> / 10</div>'
    return f'<div class="scorecard">{summary}{"".join(rows)}</div>'


def _reasoning_section(pick: dict) -> str:
    """Per-pick 'why this stock' showing the 5-layer thinking chain."""
    r = pick.get("reasoning") or {}
    # Backward compat for old reports
    catalyst = _esc(r.get("catalyst") or "—")
    node = _esc(r.get("supply_chain_node") or "—")
    social = _esc(r.get("social_signal") or "—")
    options_play = _esc(r.get("options_play") or pick.get("structure") or "—")
    failure = _esc(r.get("failure_signal") or "—")
    scorecard = r.get("scorecard") or {}
    bars = _scorecard_bars(scorecard)
    return f"""
    <details class="reasoning">
      <summary>🔬 为什么这只票（5 层思考漏斗）</summary>
      <div class="reasoning-body">
        <div class="layer-row"><span class="layer-tag">L1 催化剂</span><span>{catalyst}</span></div>
        <div class="layer-row"><span class="layer-tag">L2 供应链节点</span><span>{node}</span></div>
        <div class="layer-section"><span class="layer-tag">L3 7 维度打分</span>{bars}</div>
        <div class="layer-row"><span class="layer-tag">L4 社交信号</span><span>{social}</span></div>
        <div class="layer-row"><span class="layer-tag">L5 期权结构</span><span>{options_play}</span></div>
        <div class="layer-row failure"><span class="layer-tag">⚠ 失败信号</span><span>{failure}</span></div>
      </div>
    </details>
    """


# ---- Findings (severity-graded red team) ----


SEVERITY_META = {
    "BLOCKER": {"color": "var(--avoid)", "soft": "var(--avoid-soft)", "icon": "🛑"},
    "WARNING": {"color": "var(--watch)", "soft": "var(--watch-soft)", "icon": "⚠️"},
    "INFO":    {"color": "var(--text-dim)", "soft": "#F1F0EB", "icon": "ℹ"},
}


def _findings_section(findings: list[dict]) -> str:
    if not findings:
        return ""
    # Sort: BLOCKER first, then WARNING, then INFO
    sev_order = {"BLOCKER": 0, "WARNING": 1, "INFO": 2}
    findings = sorted(findings, key=lambda f: sev_order.get(f.get("severity"), 3))
    items = []
    for f in findings:
        sev = f.get("severity", "INFO")
        meta = SEVERITY_META.get(sev, SEVERITY_META["INFO"])
        cat = f.get("category", "")
        is_data_lim = cat == "DATA_LIMITATION"
        tickers = ", ".join(f.get("affected_tickers") or [])
        if tickers == "*":
            tickers = "全部"
        title = _esc(f.get("title") or "")
        detail = _esc(f.get("detail") or "")
        actionable = _esc(f.get("actionable") or "")
        non_blocking_note = ""
        if sev == "BLOCKER" and is_data_lim:
            non_blocking_note = ' <span class="data-lim-tag">系统问题·不阻止</span>'
        src = f.get("source", "llm_critic")
        src_label = "🔧 代码" if src == "hard_audit" else "🤖 LLM"
        items.append(
            f'<div class="finding finding-{sev.lower()}" '
            f'style="border-left-color:{meta["color"]};background:{meta["soft"]}">'
            f'<div class="finding-head">'
            f'<span class="finding-sev">{meta["icon"]} {sev}</span>'
            f'<span class="finding-cat">{_esc(cat)}</span>'
            f'<span class="finding-tickers">{tickers}</span>'
            f'<span class="finding-source">{src_label}</span>'
            f'{non_blocking_note}'
            f'</div>'
            f'<div class="finding-title"><strong>{title}</strong></div>'
            f'<div class="finding-detail">{detail}</div>'
            f'<div class="finding-action">→ {actionable}</div>'
            f'</div>'
        )
    return f"""
    <section class="section">
      <h2>🛡️ 红队审计（按严重级别分级）</h2>
      <div class="findings">{"".join(items)}</div>
    </section>
    """


# ---- Card components ----


def _pick_card(row: dict) -> str:
    pick = row["pick"]
    quote = row["quote"]
    chart = row["chart"]
    verdict_cls = _verdict_class(row["verdict"])
    verdict_text = _verdict_text(row["verdict"])

    ticker = _esc(pick.get("ticker", "?"))
    direction = _esc(pick.get("direction", "?"))
    price = quote.get("price")
    change_pct = quote.get("change_pct")
    change_cls = "up" if (change_pct is not None and change_pct >= 0) else "down"
    change_str = f"{change_pct:+.2f}%" if change_pct is not None else "—"
    price_str = f"${price}" if price is not None else "—"
    entry = _esc(pick.get("entry_zone", "—"))

    chart_color_map = {"buy": "#15803D", "watch": "#B45309", "avoid": "#B91C1C"}
    spark = svg_sparkline(chart.get("closes") or [],
                         stroke=chart_color_map.get(verdict_cls, "#374151"))
    trend_pct = chart.get("trend_pct")
    trend_str = f"5日 {trend_pct:+.1f}%" if trend_pct is not None else ""
    zone_viz = entry_zone_bar(pick, price)
    structure = _esc(pick.get("structure", ""))
    thesis = _esc(pick.get("thesis_summary", ""))

    return f"""
    <article class="pick-card verdict-{verdict_cls}">
      <div class="pick-ribbon">{verdict_text}</div>
      <div class="pick-head">
        <div>
          <div class="ticker">{ticker}</div>
          <div class="direction">{direction.upper()}</div>
        </div>
        <div class="price-block">
          <div class="price">{price_str}</div>
          <div class="change {change_cls}">{change_str}</div>
        </div>
      </div>
      <div class="pick-trend">
        {spark}
        <div class="trend-label">{trend_str}</div>
      </div>
      {zone_viz}
      <div class="pick-meta">
        <div class="meta-row"><span class="meta-key">入场区间</span><span class="meta-val">{entry}</span></div>
        <div class="meta-row"><span class="meta-key">结构</span><span class="meta-val">{structure}</span></div>
      </div>
      <div class="pick-thesis">{thesis}</div>
      <div class="pick-reason"><span class="reason-icon">{'⚠️' if verdict_cls == 'avoid' else '✓'}</span> {_esc(row['reason'])}</div>
      {_reasoning_section(pick)}
    </article>
    """


def _news_section(rows: list[dict]) -> str:
    items: list[str] = []
    for r in rows:
        pick = r["pick"]
        ticker = _esc(pick.get("ticker", "?"))
        news = r.get("news") or []
        if not news:
            continue
        news_items = []
        for n in news:
            if "error" in n:
                continue
            title = _esc(n.get("title") or "")
            pub = _esc(n.get("publisher") or "")
            url = _esc(n.get("url") or "#")
            if not title:
                continue
            news_items.append(
                f'<li><a href="{url}" target="_blank" rel="noopener">{title}</a>'
                f' <span class="news-pub">{pub}</span></li>'
            )
        if not news_items:
            continue
        items.append(
            f'<div class="news-card"><h3>{ticker}</h3><ul>{"".join(news_items)}</ul></div>'
        )
    if not items:
        return ""
    return f"""
    <section class="section">
      <h2>📰 最新新闻</h2>
      <div class="news-grid">{"".join(items)}</div>
    </section>
    """


def _critic_section(report_text: str) -> str:
    """Extract the critic block from the report (between '## 自审批注' and the footer)."""
    m = re.search(r"## 自审批注.*?(?=\n---\n\n<sub>|$)", report_text, re.DOTALL)
    if not m:
        return ""
    body = m.group(0)
    body = re.sub(r"^## 自审批注.*?\n", "", body, count=1)
    # Convert minimal markdown
    body_html = _esc(body)
    body_html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", body_html)
    body_html = body_html.replace("\n\n", "</p><p>")
    return f"""
    <section class="section">
      <details class="critic">
        <summary>🛡️ 红队自审批注（点击展开）</summary>
        <div class="critic-body"><p>{body_html}</p></div>
      </details>
    </section>
    """


# ---- Top verdict banner ----


def _verdict_banner(rows: list[dict], blocker_count: int = 0,
                    audit_iterations: int = 1, final_blockers: int = 0) -> str:
    buy = sum(1 for r in rows if r["verdict"].startswith("🟢"))
    watch = sum(1 for r in rows if r["verdict"].startswith("🟡"))
    avoid = sum(1 for r in rows if r["verdict"].startswith("🔴"))

    if buy > 0:
        headline = f"今天可以下手 {buy} 只"
        mood = "buy"
    elif watch > 0 and avoid == 0:
        headline = f"今天观察 {watch} 只，等回踩"
        mood = "watch"
    else:
        headline = "今天什么都不要做"
        mood = "avoid"

    warning = ""
    if blocker_count:
        warning = f'<div class="warning">🛑 红队 {blocker_count} 项 BLOCKER 触发，受影响标的已降级 AVOID（下方审计区有详情）</div>'

    # Self-evolution stat: how many audit rounds it took
    audit_stat = ""
    if audit_iterations > 1:
        audit_stat = (
            f'<div class="audit-stat">🔁 系统自审 {audit_iterations} 轮（修复 BLOCKER 后重写）'
            + (f' · 仍有 {final_blockers} 项遗留' if final_blockers else ' · 全部通过')
            + "</div>"
        )
    elif audit_iterations == 1 and final_blockers == 0:
        audit_stat = '<div class="audit-stat">✓ 单轮审计通过，无 BLOCKER</div>'

    return f"""
    <section class="banner banner-{mood}">
      <div class="banner-head">今日核心判断</div>
      <div class="banner-headline">{headline}</div>
      <div class="banner-counts">
        <span class="count-buy">🟢 BUY <strong>{buy}</strong></span>
        <span class="count-watch">🟡 WATCH <strong>{watch}</strong></span>
        <span class="count-avoid">🔴 AVOID <strong>{avoid}</strong></span>
      </div>
      {audit_stat}
      {warning}
    </section>
    """


# ---- CSS (inlined for self-containment) ----

CSS = """
:root {
  --bg: #F8F6F1;
  --card: #FFFFFF;
  --border: #E8E5DE;
  --text: #1F2937;
  --text-dim: #6B7280;
  --buy: #15803D;
  --buy-soft: #DCFCE7;
  --watch: #B45309;
  --watch-soft: #FEF3C7;
  --avoid: #B91C1C;
  --avoid-soft: #FEE2E2;
  --accent: #1D4ED8;
}
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; }
body {
  background: var(--bg);
  color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
               "Microsoft YaHei", "Noto Sans CJK SC", Roboto, "Helvetica Neue",
               Arial, sans-serif;
  line-height: 1.5;
  font-size: 15px;
  -webkit-font-smoothing: antialiased;
}
.container { max-width: 920px; margin: 0 auto; padding: 24px 18px 80px; }
header.app-head {
  display: flex; justify-content: space-between; align-items: baseline;
  margin-bottom: 20px; padding-bottom: 16px; border-bottom: 1px solid var(--border);
}
header.app-head h1 { font-size: 20px; margin: 0; font-weight: 700; letter-spacing: -0.01em; }
header.app-head .date { color: var(--text-dim); font-size: 14px; font-variant-numeric: tabular-nums; }
header.app-head .subtitle { color: var(--text-dim); font-size: 13px; margin-top: 4px; }

.banner {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 24px 24px 20px;
  margin-bottom: 24px;
  position: relative;
  overflow: hidden;
}
.banner::before {
  content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 5px;
  background: var(--text-dim);
}
.banner-buy::before { background: var(--buy); }
.banner-watch::before { background: var(--watch); }
.banner-avoid::before { background: var(--avoid); }
.banner-head { font-size: 13px; color: var(--text-dim); margin-bottom: 8px; letter-spacing: 0.04em; text-transform: uppercase; }
.banner-headline { font-size: 26px; font-weight: 700; letter-spacing: -0.015em; line-height: 1.25; margin-bottom: 14px; }
.banner-counts { display: flex; gap: 18px; flex-wrap: wrap; font-size: 14px; color: var(--text-dim); }
.banner-counts strong { color: var(--text); margin-left: 4px; font-variant-numeric: tabular-nums; }
.warning {
  margin-top: 14px; padding: 10px 14px;
  background: var(--avoid-soft); color: var(--avoid);
  border-radius: 8px; font-weight: 600; font-size: 13px;
}

.section { margin-bottom: 28px; }
.section h2 { font-size: 16px; font-weight: 600; margin: 0 0 14px; color: var(--text); }

.picks-grid { display: grid; gap: 14px; grid-template-columns: 1fr; }
@media (min-width: 720px) { .picks-grid { grid-template-columns: 1fr 1fr; } }

.pick-card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 18px;
  position: relative;
}
.pick-ribbon {
  position: absolute; top: 0; right: 18px;
  padding: 4px 10px;
  font-size: 11px; font-weight: 700; letter-spacing: 0.08em;
  border-radius: 0 0 6px 6px;
  color: white;
}
.verdict-buy .pick-ribbon { background: var(--buy); }
.verdict-watch .pick-ribbon { background: var(--watch); }
.verdict-avoid .pick-ribbon { background: var(--avoid); }
.verdict-buy { border-left: 3px solid var(--buy); }
.verdict-watch { border-left: 3px solid var(--watch); }
.verdict-avoid { border-left: 3px solid var(--avoid); }

.pick-head { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 14px; }
.ticker { font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace; font-weight: 700; font-size: 18px; }
.direction { color: var(--text-dim); font-size: 11px; letter-spacing: 0.06em; margin-top: 2px; }
.price-block { text-align: right; }
.price { font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace; font-size: 18px; font-weight: 700; }
.change { font-size: 13px; font-weight: 600; font-variant-numeric: tabular-nums; }
.change.up { color: var(--buy); }
.change.down { color: var(--avoid); }

.pick-trend { display: flex; align-items: center; gap: 12px; margin: 10px 0; }
.sparkline { display: block; }
.trend-label { font-size: 12px; color: var(--text-dim); font-variant-numeric: tabular-nums; }

.zone-bar-wrap { padding: 16px 0 30px; position: relative; }
.zone-bar { position: relative; height: 4px; background: #EEE9DF; border-radius: 2px; }
.zone-entry { position: absolute; top: 0; height: 100%; background: var(--accent); opacity: 0.5; border-radius: 2px; }
.marker {
  position: absolute; top: 50%; transform: translate(-50%, -50%);
  width: 10px; height: 10px; border-radius: 50%;
  border: 2px solid white; box-shadow: 0 0 0 1px var(--text-dim);
}
.marker.stop { background: var(--avoid); box-shadow: 0 0 0 1px var(--avoid); }
.marker.target { background: var(--buy); box-shadow: 0 0 0 1px var(--buy); }
.marker.current { background: var(--text); box-shadow: 0 0 0 1px var(--text); width: 14px; height: 14px; }
.marker-label {
  position: absolute; top: 14px; transform: translateX(-50%);
  font-size: 10px; color: var(--text-dim);
  font-variant-numeric: tabular-nums; white-space: nowrap;
}
.current-label { top: 18px; color: var(--text); font-weight: 600; }

.pick-meta { font-size: 13px; }
.meta-row { display: flex; justify-content: space-between; padding: 4px 0; border-top: 1px dashed var(--border); }
.meta-row:first-child { border-top: none; }
.meta-key { color: var(--text-dim); }
.meta-val { font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace; font-size: 12px; }

.pick-thesis { margin-top: 12px; padding: 10px 12px; background: #FBFAF6; border-radius: 8px; font-size: 13px; color: var(--text-dim); line-height: 1.55; }
.pick-reason { margin-top: 10px; font-size: 13px; font-weight: 500; }
.verdict-buy .pick-reason { color: var(--buy); }
.verdict-watch .pick-reason { color: var(--watch); }
.verdict-avoid .pick-reason { color: var(--avoid); }
.reason-icon { margin-right: 4px; }

.news-grid { display: grid; gap: 12px; grid-template-columns: 1fr; }
@media (min-width: 720px) { .news-grid { grid-template-columns: 1fr 1fr; } }
.news-card { background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 14px 16px; }
.news-card h3 { margin: 0 0 8px; font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace; font-size: 14px; }
.news-card ul { list-style: none; padding: 0; margin: 0; }
.news-card li { padding: 6px 0; border-top: 1px dashed var(--border); font-size: 13px; line-height: 1.45; }
.news-card li:first-child { border-top: none; }
.news-card a { color: var(--accent); text-decoration: none; }
.news-card a:hover { text-decoration: underline; }
.news-pub { color: var(--text-dim); font-size: 11px; margin-left: 6px; }

.critic { background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 0; }
.critic summary { padding: 14px 18px; cursor: pointer; font-weight: 600; font-size: 14px; user-select: none; list-style: none; }
.critic summary::-webkit-details-marker { display: none; }
.critic summary::before { content: "▸ "; color: var(--text-dim); }
.critic[open] summary::before { content: "▾ "; }
.critic-body { padding: 0 18px 16px; font-size: 13px; color: var(--text-dim); line-height: 1.7; }
.critic-body p { margin: 0 0 10px; }

/* Reasoning chain (5-layer thinking funnel) */
.reasoning { margin-top: 14px; border-top: 1px dashed var(--border); padding-top: 12px; }
.reasoning summary { cursor: pointer; font-size: 13px; font-weight: 600; color: var(--accent); list-style: none; padding: 4px 0; user-select: none; }
.reasoning summary::-webkit-details-marker { display: none; }
.reasoning summary::before { content: "▸ "; color: var(--text-dim); }
.reasoning[open] summary::before { content: "▾ "; }
.reasoning-body { padding-top: 10px; }
.layer-row { display: flex; gap: 10px; align-items: flex-start; padding: 6px 0; font-size: 13px; }
.layer-row.failure { color: var(--watch); border-top: 1px dashed var(--border); margin-top: 6px; padding-top: 8px; }
.layer-section { padding: 8px 0; }
.layer-tag { flex-shrink: 0; min-width: 88px; font-size: 11px; color: var(--text-dim); padding-top: 2px; font-weight: 600; letter-spacing: 0.02em; }
.scorecard { margin-top: 6px; }
.score-avg { font-size: 12px; color: var(--text-dim); margin-bottom: 8px; }
.score-avg strong { color: var(--text); font-size: 13px; }
.score-row { display: grid; grid-template-columns: 100px 1fr 28px; gap: 8px; align-items: center; padding: 3px 0; font-size: 12px; }
.score-label { color: var(--text-dim); }
.score-track { background: #EEE9DF; height: 8px; border-radius: 4px; overflow: hidden; }
.score-fill { display: block; height: 100%; border-radius: 4px; transition: width 0.4s ease; }
.score-val { text-align: right; font-family: ui-monospace, "SF Mono", monospace; color: var(--text); font-weight: 600; }

/* Findings (severity-graded red team) */
.findings { display: grid; gap: 10px; }
.finding { border-left: 4px solid; border-radius: 8px; padding: 12px 14px; }
.finding-head { display: flex; gap: 8px; flex-wrap: wrap; font-size: 11px; align-items: center; margin-bottom: 6px; }
.finding-sev { font-weight: 700; letter-spacing: 0.04em; }
.finding-cat { color: var(--text-dim); font-family: ui-monospace, "SF Mono", monospace; }
.finding-tickers { color: var(--text-dim); font-family: ui-monospace, "SF Mono", monospace; }
.data-lim-tag { background: var(--card); color: var(--text-dim); padding: 1px 6px; border-radius: 4px; border: 1px solid var(--border); font-weight: 600; }
.finding-title { font-size: 14px; margin-bottom: 4px; }
.finding-detail { font-size: 13px; color: var(--text); line-height: 1.55; margin-bottom: 6px; }
.finding-action { font-size: 12px; color: var(--text-dim); font-style: italic; }
.finding-source { font-size: 10px; padding: 1px 5px; border-radius: 3px; background: var(--card); border: 1px solid var(--border); color: var(--text-dim); font-family: ui-monospace, "SF Mono", monospace; }

/* Audit stat (self-evolution counter) */
.audit-stat { margin-top: 10px; padding: 8px 12px; background: #F1F0EB; color: var(--text-dim); border-radius: 6px; font-size: 12px; font-weight: 500; }

footer.app-foot { margin-top: 32px; padding-top: 16px; border-top: 1px solid var(--border); color: var(--text-dim); font-size: 12px; text-align: center; }
footer.app-foot a { color: var(--text-dim); }
"""


# ---- Main render ----


def render(picks: list[dict], report_text: str, date_str: str,
           audit_iterations: int = 1, final_blockers: int = 0) -> str:
    """Render the dashboard HTML. Refetches data from yfinance."""
    rows = enrich.fetch_rows(picks, report_text)
    findings = enrich.get_all_findings(report_text)
    blocker_count = sum(1 for r in rows if r.get("blocker_title"))
    banner = _verdict_banner(rows, blocker_count=blocker_count,
                             audit_iterations=audit_iterations,
                             final_blockers=final_blockers)
    cards = "".join(_pick_card(r) for r in rows) or '<p class="text-dim">无候选标的</p>'
    news = _news_section(rows)
    findings_html = _findings_section(findings)
    critic = _critic_section(report_text)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>瓶颈猎手 · {date_str}</title>
<style>{CSS}</style>
</head>
<body>
<div class="container">
  <header class="app-head">
    <div>
      <h1>瓶颈猎手</h1>
      <div class="subtitle">美股每日扫描 · Serenity 思维原型</div>
    </div>
    <div class="date">{date_str}</div>
  </header>
  {banner}
  <section class="section">
    <h2>📊 持仓建议</h2>
    <div class="picks-grid">{cards}</div>
  </section>
  {news}
  {findings_html}
  {critic}
  <footer class="app-foot">
    生成时间 {now} · 数据来源 Yahoo Finance (~15分钟延迟) ·
    <a href="https://github.com/beer98/pipboy-ai-vault">GitHub</a>
  </footer>
</div>
</body>
</html>
"""


def write_dashboard(picks: list[dict], report_text: str, date_str: str,
                    docs_dir: Path, audit_iterations: int = 1,
                    final_blockers: int = 0) -> Path:
    """Write to docs/YYYY-MM-DD.html and also update docs/index.html."""
    docs_dir.mkdir(parents=True, exist_ok=True)
    html_str = render(picks, report_text, date_str,
                      audit_iterations=audit_iterations,
                      final_blockers=final_blockers)
    dated = docs_dir / f"{date_str}.html"
    index = docs_dir / "index.html"
    dated.write_text(html_str, encoding="utf-8")
    index.write_text(html_str, encoding="utf-8")
    return dated

"""Real-time market data via yfinance (free, no API key).

Used by:
- Phase C tool calling: the LLM can call get_quote/get_chart/get_ticker_news as
  function tools while building its analysis
- Post-Phase-D enrichment: orchestrator fetches fresh quotes for every pick
  and builds the "📊 实时快照" table at the top of the report (guaranteeing
  freshness regardless of what the LLM saw earlier)
"""

from __future__ import annotations
from typing import Any

try:
    import yfinance as yf
except ImportError:  # surfaced at runtime as tool error
    yf = None


def _strip(ticker: str) -> str:
    return ticker.lstrip("$").strip().upper()


def get_quote(ticker: str) -> dict[str, Any]:
    """Latest quote (~15 min delayed from Yahoo Finance)."""
    if yf is None:
        return {"error": "yfinance not installed"}
    sym = _strip(ticker)
    try:
        t = yf.Ticker(sym)
        fi = t.fast_info
        price = float(fi.last_price) if fi.last_price is not None else None
        prev = float(fi.previous_close) if fi.previous_close is not None else None
        change_pct = ((price / prev - 1) * 100) if (price and prev) else None
        return {
            "ticker": sym,
            "price": round(price, 2) if price else None,
            "previous_close": round(prev, 2) if prev else None,
            "change_pct": round(change_pct, 2) if change_pct is not None else None,
            "day_high": round(float(fi.day_high), 2) if fi.day_high else None,
            "day_low": round(float(fi.day_low), 2) if fi.day_low else None,
            "volume": int(fi.last_volume) if fi.last_volume else None,
            "market_cap": int(fi.market_cap) if fi.market_cap else None,
            "currency": fi.currency,
        }
    except Exception as e:  # noqa: BLE001
        return {"ticker": sym, "error": f"quote failed: {e}"}


def get_chart_summary(ticker: str, days: int = 5) -> dict[str, Any]:
    """OHLC + trend % for the last N trading days."""
    if yf is None:
        return {"error": "yfinance not installed"}
    sym = _strip(ticker)
    try:
        t = yf.Ticker(sym)
        # Pad to capture weekends/holidays
        hist = t.history(period=f"{max(days * 2, 10)}d")
        if hist.empty:
            return {"ticker": sym, "error": "no history"}
        hist = hist.tail(days)
        closes = [round(float(c), 2) for c in hist["Close"].tolist()]
        if not closes:
            return {"ticker": sym, "error": "no closes"}
        trend_pct = round((closes[-1] / closes[0] - 1) * 100, 2)
        return {
            "ticker": sym,
            "days": len(closes),
            "closes": closes,
            "trend_pct": trend_pct,
            "high": round(float(hist["High"].max()), 2),
            "low": round(float(hist["Low"].min()), 2),
            "sparkline": sparkline(closes),
        }
    except Exception as e:  # noqa: BLE001
        return {"ticker": sym, "error": f"chart failed: {e}"}


def get_ticker_news(ticker: str, limit: int = 5) -> list[dict[str, Any]]:
    """Recent news headlines from Yahoo Finance."""
    if yf is None:
        return [{"error": "yfinance not installed"}]
    sym = _strip(ticker)
    try:
        t = yf.Ticker(sym)
        items = (t.news or [])[:limit]
        out: list[dict] = []
        for n in items:
            # yfinance changed the schema; handle both old & new
            content = n.get("content") or n
            title = content.get("title") or n.get("title")
            url = (
                (content.get("canonicalUrl") or {}).get("url")
                or content.get("url")
                or n.get("link")
            )
            provider = (
                (content.get("provider") or {}).get("displayName")
                or n.get("publisher")
            )
            published = content.get("pubDate") or n.get("providerPublishTime")
            out.append(
                {
                    "title": title,
                    "url": url,
                    "publisher": provider,
                    "published": str(published) if published else None,
                }
            )
        return out
    except Exception as e:  # noqa: BLE001
        return [{"ticker": sym, "error": f"news failed: {e}"}]


def sparkline(values: list[float]) -> str:
    """Render a list of numbers as Unicode block-chars sparkline."""
    if not values:
        return ""
    blocks = "▁▂▃▄▅▆▇█"
    lo, hi = min(values), max(values)
    if hi == lo:
        return blocks[3] * len(values)
    return "".join(blocks[int((v - lo) / (hi - lo) * (len(blocks) - 1))] for v in values)


# ---------- Tool schemas (OpenAI / DeepSeek function-calling format) ----------

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "get_quote",
            "description": (
                "Get the latest stock quote (price, % change today, day range, volume, market cap). "
                "~15 min delay. Use this for any ticker you're analyzing — DO NOT rely on web_search for prices."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "Ticker symbol e.g. 'LITE' or '$LITE'"},
                },
                "required": ["ticker"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_chart_summary",
            "description": (
                "Get N-day OHLC summary and trend % for a ticker. "
                "Use for: trend direction, recent high/low, where current price sits in the range."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string"},
                    "days": {"type": "integer", "minimum": 2, "maximum": 60, "description": "default 5"},
                },
                "required": ["ticker"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_ticker_news",
            "description": (
                "Recent news headlines for a ticker from Yahoo Finance. "
                "Use for the LATEST company-specific news affecting your thesis."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 10},
                },
                "required": ["ticker"],
            },
        },
    },
]

DISPATCH = {
    "get_quote": get_quote,
    "get_chart_summary": get_chart_summary,
    "get_ticker_news": get_ticker_news,
}

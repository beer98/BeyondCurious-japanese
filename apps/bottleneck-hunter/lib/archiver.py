"""Write reports to 07-每日复盘归档 + append rules / ledger entries."""

from __future__ import annotations
import json
import re
from datetime import datetime, timezone
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_DIR = APP_ROOT / "07-每日复盘归档"
RULES_PATH = APP_ROOT / "08-知识沉淀" / "规则库.md"


def archive_report(filename: str, body: str, usage: list[dict] | dict) -> Path:
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    target = ARCHIVE_DIR / filename
    target.write_text(body.rstrip() + "\n\n" + _footer(usage), encoding="utf-8")
    return target


def _footer(usage: list[dict] | dict) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    if isinstance(usage, dict):
        usage = [usage]
    rows = []
    for i, u in enumerate(usage, 1):
        rows.append(
            f"- 阶段 {i} · 模型 `{u.get('model','?')}` · "
            f"prompt {u.get('prompt_tokens','?')} tok · "
            f"completion {u.get('completion_tokens','?')} tok · "
            f"iters {u.get('iterations','-')} · stop={u.get('stop_reason','?')}"
        )
    return "---\n\n<sub>自动生成 · " + now + "</sub>\n\n" + "\n".join(rows) + "\n"


def append_rules(markdown_snippet: str) -> None:
    """Append candidate rules to the 候选区 section of 规则库.md."""
    if not markdown_snippet.strip():
        return
    if not RULES_PATH.exists():
        return
    text = RULES_PATH.read_text(encoding="utf-8")
    marker = "## 三、候选区（验证中）"
    if marker not in text:
        # fallback: just append
        with RULES_PATH.open("a", encoding="utf-8") as f:
            f.write("\n\n" + markdown_snippet + "\n")
        return
    # Insert after the marker section heading and any intro lines (before next "## ")
    head, rest = text.split(marker, 1)
    # rest starts with the section content; find next "## " heading
    next_section = re.search(r"\n## ", rest)
    if next_section:
        section_body = rest[: next_section.start()]
        after = rest[next_section.start() :]
    else:
        section_body = rest
        after = ""
    new_text = head + marker + section_body.rstrip() + "\n\n" + markdown_snippet.strip() + "\n" + after
    RULES_PATH.write_text(new_text, encoding="utf-8")


JSON_BLOCK_RE = re.compile(r"```json\s*(\{.*?\}|\[.*?\])\s*```", re.DOTALL)


def _all_json_blocks(text: str) -> list:
    out = []
    for m in JSON_BLOCK_RE.finditer(text):
        try:
            out.append(json.loads(m.group(1)))
        except json.JSONDecodeError:
            continue
    return out


def extract_json(text: str) -> dict | list | None:
    """Pull the first JSON block. For backward compat, picks-shaped blocks
    are preferred even if a critic-findings block appears earlier."""
    blocks = _all_json_blocks(text)
    if not blocks:
        return None
    # Prefer picks block (has "picks" key) when multiple are present
    for b in blocks:
        if isinstance(b, dict) and "picks" in b:
            return b
    return blocks[0]


def extract_critic_findings(text: str) -> dict | None:
    """Find the critic findings JSON block (has 'findings' key)."""
    for b in _all_json_blocks(text):
        if isinstance(b, dict) and "findings" in b:
            return b
    return None


def find_yesterday_report() -> tuple[Path, str] | None:
    """Return the most recent dated report file ('YYYY-MM-DD.md') and its text."""
    if not ARCHIVE_DIR.exists():
        return None
    dated = sorted(
        [
            p
            for p in ARCHIVE_DIR.glob("*.md")
            if re.match(r"\d{4}-\d{2}-\d{2}\.md$", p.name)
        ]
    )
    if not dated:
        return None
    last = dated[-1]
    return last, last.read_text(encoding="utf-8")

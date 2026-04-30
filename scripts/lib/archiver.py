"""Write the report to disk under 07-每日复盘归档/ and emit a usage footer."""

from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ARCHIVE_DIR = (
    REPO_ROOT
    / "04-AI工具箱"
    / "提示词与工作流"
    / "瓶颈猎手-美股每日进化系统"
    / "07-每日复盘归档"
)


def archive(filename: str, body: str, usage: dict) -> Path:
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    target = ARCHIVE_DIR / filename

    footer = _build_footer(usage)
    target.write_text(body.rstrip() + "\n\n" + footer, encoding="utf-8")
    return target


def _build_footer(usage: dict) -> str:
    if not usage:
        return ""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return (
        "---\n\n"
        f"<sub>自动生成 · {now} · 模型：`{usage.get('model','?')}` · "
        f"输入 {usage.get('input_tokens','?')} tok（缓存读 "
        f"{usage.get('cache_read_input_tokens',0)}） · "
        f"输出 {usage.get('output_tokens','?')} tok · "
        f"stop={usage.get('stop_reason','?')}</sub>\n"
    )

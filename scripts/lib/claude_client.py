"""Claude API wrapper.

- Opus 4.7 with adaptive thinking (default)
- Prompt caching on the system prompt (90% read discount on repeated runs)
- Server-side web_search_20260209 + web_fetch_20260209 (dynamic filtering enabled)
- Streaming required for max_tokens > ~16000
- Uses .get_final_message() helper to collect the full response
"""

from __future__ import annotations
import os
import sys
from typing import Iterable

import anthropic

DEFAULT_MODEL = os.environ.get("CLAUDE_MODEL", "claude-opus-4-7")
DEFAULT_MAX_TOKENS = int(os.environ.get("CLAUDE_MAX_TOKENS", "32000"))
DEFAULT_EFFORT = os.environ.get("CLAUDE_EFFORT", "high")


def run(
    system_prompt: str,
    user_message: str,
    *,
    model: str = DEFAULT_MODEL,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    effort: str = DEFAULT_EFFORT,
    stream_to_stderr: bool = True,
) -> tuple[str, dict]:
    """Run a single Claude call with web_search + adaptive thinking.

    Returns (final_text, usage_dict).
    """
    client = anthropic.Anthropic()

    # System prompt is cached — system_prompt is the stable methodology block.
    system = [
        {
            "type": "text",
            "text": system_prompt,
            "cache_control": {"type": "ephemeral"},
        }
    ]

    tools = [
        {"type": "web_search_20260209", "name": "web_search"},
        {"type": "web_fetch_20260209", "name": "web_fetch"},
    ]

    messages = [{"role": "user", "content": user_message}]

    collected_text: list[str] = []
    usage: dict = {}

    with client.messages.stream(
        model=model,
        max_tokens=max_tokens,
        system=system,
        tools=tools,
        messages=messages,
        thinking={"type": "adaptive"},
        output_config={"effort": effort},
    ) as stream:
        # Surface progress while running so logs aren't silent for ~minutes.
        for event in stream:
            if (
                stream_to_stderr
                and event.type == "content_block_delta"
                and getattr(event.delta, "type", None) == "text_delta"
            ):
                sys.stderr.write(event.delta.text)
                sys.stderr.flush()

        final = stream.get_final_message()

    for block in final.content:
        if block.type == "text":
            collected_text.append(block.text)

    if final.usage:
        usage = {
            "input_tokens": final.usage.input_tokens,
            "output_tokens": final.usage.output_tokens,
            "cache_creation_input_tokens": getattr(
                final.usage, "cache_creation_input_tokens", 0
            ),
            "cache_read_input_tokens": getattr(
                final.usage, "cache_read_input_tokens", 0
            ),
            "stop_reason": final.stop_reason,
            "model": final.model,
        }

    if stream_to_stderr:
        sys.stderr.write("\n")

    return "\n\n".join(collected_text).strip(), usage

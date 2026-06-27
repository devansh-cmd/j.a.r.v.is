"""Claude API agentic loop — wires tools.py to anthropic.Anthropic()."""
from __future__ import annotations

import json
import os
from datetime import datetime

from anthropic import Anthropic
from colorama import Fore, Style

from config import JARVIS_PERSONA, MAX_TOKENS, MAX_TOOL_ITERATIONS, MODEL
from core import memory, tools


class Brain:
    def __init__(self) -> None:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY not set. Copy .env.example to .env and fill it in."
            )
        self.client = Anthropic(api_key=api_key)
        self.messages: list[dict] = []

    def _system_blocks(self) -> list[dict]:
        recent = memory.list_recent(limit=12)
        memory_summary = (
            "\n".join(f"- ({m['category']}) {m['content']}" for m in recent) or "(empty)"
        )
        context = (
            f"Current date and time: {datetime.now().isoformat(timespec='seconds')}\n"
            f"Total memories stored: {memory.count()}\n"
            f"Most recent memories:\n{memory_summary}"
        )
        return [
            {
                "type": "text",
                "text": JARVIS_PERSONA,
                "cache_control": {"type": "ephemeral"},
            },
            {"type": "text", "text": context},
        ]

    def respond(self, user_text: str, on_tool: callable | None = None) -> str:
        """Run one user turn through the agentic loop. Returns final assistant text."""
        self.messages.append({"role": "user", "content": user_text})

        for _ in range(MAX_TOOL_ITERATIONS):
            response = self.client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=self._system_blocks(),
                tools=tools.TOOLS,
                messages=self.messages,
            )

            self.messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason == "end_turn":
                return self._extract_text(response.content)

            if response.stop_reason == "tool_use":
                tool_results = []
                for block in response.content:
                    if block.type != "tool_use":
                        continue
                    if on_tool:
                        on_tool(block.name, block.input)
                    print(
                        f"{Fore.CYAN}  ↳ {block.name}({_short_args(block.input)}){Style.RESET_ALL}"
                    )
                    result, is_error = tools.run_tool(block.name, block.input)
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                            "is_error": is_error,
                        }
                    )
                self.messages.append({"role": "user", "content": tool_results})
                continue

            if response.stop_reason == "max_tokens":
                return (
                    self._extract_text(response.content)
                    or "(response cut off — hit max tokens)"
                )

            return self._extract_text(response.content) or f"(stopped: {response.stop_reason})"

        return "(too many tool iterations)"

    @staticmethod
    def _extract_text(blocks) -> str:
        return "\n".join(b.text for b in blocks if getattr(b, "type", None) == "text").strip()


def _short_args(args: dict, max_len: int = 80) -> str:
    s = json.dumps(args, ensure_ascii=False)
    if len(s) > max_len:
        s = s[: max_len - 1] + "…"
    return s

"""Agentic loop — routes each turn to a model backend (Claude, Gemini, local…).

The brain no longer talks to one SDK directly. It keeps a provider-neutral
history (core.llm.Turn) and, each turn, asks core.router which backend+model
fits the task, then runs the tool-use loop against it. Every turn is journaled
to the diary for perpetual memory.
"""
from __future__ import annotations

import json
from datetime import datetime

from colorama import Fore, Style

from config import JARVIS_PERSONA, MAX_TOKENS, MAX_TOOL_ITERATIONS
from core import diary, llm, memory, router, tools


class Brain:
    def __init__(self) -> None:
        self.history: list[llm.Turn] = []
        # Boundary between prior sessions (recalled from the diary) and this live
        # session. Diary timestamps are local naive ISO, so this string compares
        # correctly against them.
        self._session_start = datetime.now().isoformat(timespec="seconds")
        self.last_route: tuple[str, str, str] = ("", "", "")  # (provider, model, tier)

    def _system_text(self) -> str:
        recent = memory.list_recent(limit=10)
        memory_summary = (
            "\n".join(f"- ({m['category']}) {m['content']}" for m in recent) or "(none saved yet)"
        )
        digest = diary.context_digest(max_turns=20, before=self._session_start)
        context = (
            f"Current date and time: {datetime.now().isoformat(timespec='seconds')}\n"
            f"Memories on file: {memory.count()}\n\n"
            f"## What you remember about the user (curated long-term memory)\n"
            f"{memory_summary}\n\n"
            f"## Your diary — what happened in earlier sessions\n"
            f"This is your perpetual memory across restarts. Use it to recognise the user, "
            f"recall ongoing threads, and maintain continuity — don't act like you're meeting "
            f"them for the first time if there's history here.\n\n"
            f"{digest}"
        )
        return f"{JARVIS_PERSONA}\n\n{context}"

    def respond(self, user_text: str, on_tool=None) -> str:
        """Run one user turn through the routed agentic loop. Returns final text."""
        self.history.append(llm.Turn(role="user", text=user_text))
        diary.start_turn(user_text)

        backend, model, provider, tier = router.resolve(user_text)
        self.last_route = (provider, model, tier)
        print(f"{Fore.LIGHTBLACK_EX}  [route: {tier} → {provider}/{model}]{Style.RESET_ALL}")
        system = self._system_text()

        final = "(no response)"
        for _ in range(MAX_TOOL_ITERATIONS):
            try:
                resp = backend.complete(system, self.history, tools.TOOLS, model, MAX_TOKENS)
            except Exception as e:  # network / auth / provider error — surface, don't crash
                final = f"(model error on {provider}/{model}: {e})"
                break

            self.history.append(
                llm.Turn(role="assistant", text=resp.text, tool_calls=resp.tool_calls)
            )

            if resp.stop_reason == "tool_use" and resp.tool_calls:
                for call in resp.tool_calls:
                    if on_tool:
                        on_tool(call.name, call.input)
                    print(f"{Fore.CYAN}  ↳ {call.name}({_short_args(call.input)}){Style.RESET_ALL}")
                    result, is_error = tools.run_tool(call.name, call.input)
                    diary.record_action(call.name, call.input, result, is_error)
                    self.history.append(
                        llm.Turn(role="tool", tool_call_id=call.id, text=result, is_error=is_error)
                    )
                continue

            final = resp.text
            if not final:
                final = (
                    "(response cut off — hit max tokens)"
                    if resp.stop_reason == "max_tokens"
                    else "(no reply)"
                )
            break
        else:
            final = "(too many tool iterations)"

        diary.end_turn(final)
        return final


def _short_args(args: dict, max_len: int = 80) -> str:
    s = json.dumps(args, ensure_ascii=False)
    if len(s) > max_len:
        s = s[: max_len - 1] + "…"
    return s

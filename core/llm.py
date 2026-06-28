"""Pluggable LLM backends with a neutral message/tool format.

Jarvis routes each turn to a different model (Gemini, Claude, local Ollama, …),
so the conversation history and tool schemas must be provider-neutral. This
module defines that neutral format and two backends:

  - AnthropicBackend       → native `anthropic` SDK (best tool reliability)
  - OpenAICompatBackend    → `openai` SDK pointed at any OpenAI-compatible
                             endpoint: Gemini, Groq, Ollama, OpenRouter, …

brain.py keeps the agentic loop; it speaks Turn / LLMResponse and lets the
router pick which backend+model handles each step.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field


# ── Neutral data types ───────────────────────────────────────────────────────


@dataclass
class ToolCall:
    id: str
    name: str
    input: dict


@dataclass
class Turn:
    """One conversation turn in provider-neutral form."""
    role: str                                   # "user" | "assistant" | "tool"
    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)  # assistant turns
    tool_call_id: str | None = None             # tool-result turns
    is_error: bool = False


@dataclass
class LLMResponse:
    text: str
    tool_calls: list[ToolCall]
    stop_reason: str                            # "end" | "tool_use" | "max_tokens" | "other"
    model: str = ""


class BackendError(RuntimeError):
    pass


# ── Backend interface ────────────────────────────────────────────────────────


class Backend:
    kind = "base"

    def complete(
        self,
        system: str,
        history: list[Turn],
        tools: list[dict],
        model: str,
        max_tokens: int,
    ) -> LLMResponse:
        raise NotImplementedError


# ── Anthropic (native) ───────────────────────────────────────────────────────


class AnthropicBackend(Backend):
    kind = "anthropic"

    def __init__(self, api_key: str | None = None) -> None:
        from anthropic import Anthropic

        self._client = Anthropic(api_key=api_key or os.getenv("ANTHROPIC_API_KEY"))

    def complete(self, system, history, tools, model, max_tokens) -> LLMResponse:
        messages = [self._to_anthropic(t) for t in history]
        resp = self._client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            tools=tools,  # already in Anthropic format
            messages=messages,
        )
        text_parts, calls = [], []
        for block in resp.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                calls.append(ToolCall(id=block.id, name=block.name, input=dict(block.input)))
        stop = {"end_turn": "end", "tool_use": "tool_use", "max_tokens": "max_tokens"}.get(
            resp.stop_reason, "other"
        )
        return LLMResponse("\n".join(text_parts).strip(), calls, stop, model)

    @staticmethod
    def _to_anthropic(t: Turn) -> dict:
        if t.role == "tool":
            return {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": t.tool_call_id,
                        "content": t.text,
                        "is_error": t.is_error,
                    }
                ],
            }
        if t.role == "assistant":
            content: list[dict] = []
            if t.text:
                content.append({"type": "text", "text": t.text})
            for c in t.tool_calls:
                content.append({"type": "tool_use", "id": c.id, "name": c.name, "input": c.input})
            return {"role": "assistant", "content": content or t.text}
        return {"role": "user", "content": t.text}


# ── OpenAI-compatible (Gemini / Groq / Ollama / OpenRouter) ───────────────────


class OpenAICompatBackend(Backend):
    kind = "openai"

    def __init__(self, base_url: str, api_key: str | None = None) -> None:
        from openai import OpenAI

        # Ollama needs no key; OpenAI client requires a non-empty string.
        self._client = OpenAI(base_url=base_url, api_key=api_key or "not-needed")

    def complete(self, system, history, tools, model, max_tokens) -> LLMResponse:
        messages = [{"role": "system", "content": system}]
        for t in history:
            messages.extend(self._to_openai(t))
        oa_tools = [self._tool_to_openai(td) for td in tools] if tools else None
        resp = self._client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            messages=messages,
            tools=oa_tools,
        )
        choice = resp.choices[0]
        msg = choice.message
        calls = []
        for tc in (msg.tool_calls or []):
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            calls.append(ToolCall(id=tc.id, name=tc.function.name, input=args))
        stop = {"tool_calls": "tool_use", "stop": "end", "length": "max_tokens"}.get(
            choice.finish_reason, "tool_use" if calls else "end"
        )
        return LLMResponse((msg.content or "").strip(), calls, stop, model)

    @staticmethod
    def _tool_to_openai(td: dict) -> dict:
        return {
            "type": "function",
            "function": {
                "name": td["name"],
                "description": td.get("description", ""),
                "parameters": td.get("input_schema", {"type": "object", "properties": {}}),
            },
        }

    @staticmethod
    def _to_openai(t: Turn) -> list[dict]:
        if t.role == "tool":
            return [{"role": "tool", "tool_call_id": t.tool_call_id, "content": t.text}]
        if t.role == "assistant":
            m: dict = {"role": "assistant", "content": t.text or None}
            if t.tool_calls:
                m["tool_calls"] = [
                    {
                        "id": c.id,
                        "type": "function",
                        "function": {"name": c.name, "arguments": json.dumps(c.input)},
                    }
                    for c in t.tool_calls
                ]
            return [m]
        return [{"role": "user", "content": t.text}]

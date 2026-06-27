"""Action diary — JSONL per turn + daily Markdown digest.

Records everything Jarvis does: user inputs, tool calls (with args + result
snippets), final responses. Two surfaces:

  diary/YYYY-MM-DD.jsonl  — one JSON object per event, machine-readable
  diary/YYYY-MM-DD.md     — human-readable daily journal, append-only
"""
from __future__ import annotations

import json
import os
import re
import tempfile
import threading
import uuid
from datetime import datetime
from pathlib import Path

from config import ROOT

DIARY_DIR = ROOT / "diary"
_lock = threading.Lock()
_current_turn: dict | None = None


def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _ts() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _ensure_dir() -> None:
    DIARY_DIR.mkdir(parents=True, exist_ok=True)


def _append_jsonl(event: dict) -> None:
    _ensure_dir()
    path = DIARY_DIR / f"{_today()}.jsonl"
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def _append_md(text: str) -> None:
    _ensure_dir()
    path = DIARY_DIR / f"{_today()}.md"
    new_file = not path.exists()
    with open(path, "a", encoding="utf-8") as f:
        if new_file:
            f.write(f"# Jarvis diary — {_today()}\n\n")
        f.write(text)


def _truncate(s: str, n: int = 400) -> str:
    s = re.sub(r"\s+", " ", str(s)).strip()
    return s if len(s) <= n else s[: n - 1] + "…"


def start_turn(user_text: str) -> str:
    """Begin a new turn. Returns a turn id used by subsequent calls."""
    global _current_turn
    turn_id = uuid.uuid4().hex[:8]
    with _lock:
        _current_turn = {
            "turn_id": turn_id,
            "started_at": _ts(),
            "user_text": user_text,
            "actions": [],
            "response": None,
        }
        _append_jsonl(
            {"type": "turn_start", "turn_id": turn_id, "timestamp": _ts(), "user_text": user_text}
        )
        _append_md(f"## {_ts()} — _user_\n\n> {user_text}\n\n")
    return turn_id


def record_action(name: str, args: dict, result: str, is_error: bool) -> None:
    """Log one tool invocation."""
    with _lock:
        event = {
            "type": "tool_call",
            "turn_id": _current_turn["turn_id"] if _current_turn else None,
            "timestamp": _ts(),
            "tool": name,
            "args": args,
            "result_preview": _truncate(result, 600),
            "is_error": is_error,
        }
        _append_jsonl(event)
        if _current_turn is not None:
            _current_turn["actions"].append(event)
        arg_str = _truncate(json.dumps(args, ensure_ascii=False), 120)
        icon = "❌" if is_error else "⚙️ "
        _append_md(f"- {icon} `{name}({arg_str})`\n  - → {_truncate(result, 240)}\n")


def end_turn(response: str) -> None:
    """Close out the current turn with Jarvis's final reply."""
    global _current_turn
    with _lock:
        turn_id = _current_turn["turn_id"] if _current_turn else None
        _append_jsonl(
            {
                "type": "turn_end",
                "turn_id": turn_id,
                "timestamp": _ts(),
                "response": response,
                "action_count": len(_current_turn["actions"]) if _current_turn else 0,
            }
        )
        _append_md(f"\n_jarvis_: {response}\n\n---\n\n")
        _current_turn = None


def recent_entries(limit: int = 50) -> list[dict]:
    """Return the last N JSONL events across all days, newest last."""
    _ensure_dir()
    files = sorted(DIARY_DIR.glob("*.jsonl"))
    events: list[dict] = []
    for fp in files[-5:]:
        with open(fp, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return events[-limit:]


def _one_line(s: str, n: int = 150) -> str:
    s = re.sub(r"\s+", " ", str(s or "")).strip()
    return s if len(s) <= n else s[: n - 1] + "…"


def context_digest(max_turns: int = 20, before: str | None = None) -> str:
    """Reconstruct recent turns into a compact digest for Jarvis's context.

    This is the read side of the perpetual-memory loop: it lets Jarvis recall
    what happened in earlier sessions. Pass `before` (an ISO timestamp, e.g. the
    current session's start) to exclude the live session — those turns already
    live in the in-memory message history, so we only want *prior* context here.
    """
    events = recent_entries(limit=max(max_turns * 8, 80))
    turns: dict[str, dict] = {}
    order: list[str] = []
    for ev in events:
        tid = ev.get("turn_id")
        if not tid:
            continue
        if tid not in turns:
            turns[tid] = {"user": None, "tools": [], "response": None, "ts": ev.get("timestamp", "")}
            order.append(tid)
        t = turns[tid]
        et = ev.get("type")
        if et == "turn_start":
            t["user"] = ev.get("user_text")
            t["ts"] = ev.get("timestamp", t["ts"])
        elif et == "tool_call":
            tool = ev.get("tool")
            if tool:
                t["tools"].append(tool)
        elif et == "turn_end":
            t["response"] = ev.get("response")

    selected = []
    for tid in order:
        t = turns[tid]
        if before and t["ts"] and t["ts"] >= before:
            continue  # belongs to the current session — skip, it's in live context
        selected.append(t)
    selected = selected[-max_turns:]

    if not selected:
        return "(no earlier sessions on record yet — this is a fresh start)"

    lines = []
    for t in selected:
        ts = (t["ts"] or "")[:16].replace("T", " ")
        line = f"[{ts}] you: {_one_line(t['user'])}"
        if t["response"]:
            line += f"\n    jarvis: {_one_line(t['response'])}"
        if t["tools"]:
            uniq = ", ".join(dict.fromkeys(t["tools"]))
            line += f"  [used: {uniq}]"
        lines.append(line)
    return "\n".join(lines)

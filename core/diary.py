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
    for fp in files[-3:]:
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

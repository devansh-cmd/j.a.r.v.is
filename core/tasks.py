"""On-screen to-do list that Jarvis manages. JSON-backed, like memory.

This is the user's task list — Jarvis adds/completes items via tools, the HUD
renders them live. Distinct from long-term memory: tasks are actionable and
have a done/pending state.
"""
from __future__ import annotations

import json
import os
import tempfile
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

from config import MEMORY_DIR

TASKS_FILE = MEMORY_DIR / "tasks.json"
_lock = threading.Lock()

PRIORITIES = ("low", "normal", "high")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _load() -> list[dict]:
    if not TASKS_FILE.exists():
        return []
    try:
        return json.loads(TASKS_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []


def _save(entries: list[dict]) -> None:
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(MEMORY_DIR), suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2, ensure_ascii=False)
        os.replace(tmp, TASKS_FILE)
    except Exception:
        Path(tmp).unlink(missing_ok=True)
        raise


def _find(query: str, entries: list[dict]) -> dict | None:
    """Match by exact id, then case-insensitive substring. Prefer pending."""
    for e in entries:
        if e["id"] == query:
            return e
    q = query.lower().strip()
    matches = [e for e in entries if q in e["text"].lower()]
    pending = [e for e in matches if e["status"] == "pending"]
    if pending:
        return pending[0]
    return matches[0] if matches else None


def add(text: str, priority: str = "normal") -> dict:
    priority = priority if priority in PRIORITIES else "normal"
    entry = {
        "id": uuid.uuid4().hex[:6],
        "text": text.strip(),
        "status": "pending",
        "priority": priority,
        "created_at": _now_iso(),
        "done_at": None,
    }
    with _lock:
        entries = _load()
        entries.append(entry)
        _save(entries)
    return entry


def complete(query: str) -> dict | None:
    with _lock:
        entries = _load()
        entry = _find(query, entries)
        if entry is None:
            return None
        entry["status"] = "done"
        entry["done_at"] = _now_iso()
        _save(entries)
        return entry


def reopen(query: str) -> dict | None:
    with _lock:
        entries = _load()
        entry = _find(query, entries)
        if entry is None:
            return None
        entry["status"] = "pending"
        entry["done_at"] = None
        _save(entries)
        return entry


def remove(query: str) -> dict | None:
    with _lock:
        entries = _load()
        entry = _find(query, entries)
        if entry is None:
            return None
        entries = [e for e in entries if e["id"] != entry["id"]]
        _save(entries)
        return entry


def clear_done() -> int:
    with _lock:
        entries = _load()
        kept = [e for e in entries if e["status"] != "done"]
        removed = len(entries) - len(kept)
        _save(kept)
        return removed


def _prio_rank(p: str) -> int:
    return {"high": 0, "normal": 1, "low": 2}.get(p, 1)


def list_all(include_done: bool = True) -> list[dict]:
    """Pending first (by priority, then age), then done (most recent first)."""
    entries = _load()
    pending = [e for e in entries if e["status"] == "pending"]
    done = [e for e in entries if e["status"] == "done"]
    pending.sort(key=lambda e: (_prio_rank(e["priority"]), e["created_at"]))
    done.sort(key=lambda e: e.get("done_at") or "", reverse=True)
    return pending + (done if include_done else [])


def count_pending() -> int:
    return sum(1 for e in _load() if e["status"] == "pending")

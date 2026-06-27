"""DSA problem tracker. JSON-backed, grouped by difficulty.

Tracks LeetCode-style problems with easy/medium/hard difficulty and a
solved/todo status. The HUD surfaces solved counts per difficulty.
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

DSA_FILE = MEMORY_DIR / "dsa.json"
_lock = threading.Lock()

DIFFICULTIES = ("easy", "medium", "hard")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _load() -> list[dict]:
    if not DSA_FILE.exists():
        return []
    try:
        return json.loads(DSA_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []


def _save(entries: list[dict]) -> None:
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(MEMORY_DIR), suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2, ensure_ascii=False)
        os.replace(tmp, DSA_FILE)
    except Exception:
        Path(tmp).unlink(missing_ok=True)
        raise


def _norm_difficulty(d: str) -> str:
    d = (d or "").lower().strip()
    if d in ("e", "ez"):
        return "easy"
    if d in ("m", "med"):
        return "medium"
    if d in ("h",):
        return "hard"
    return d if d in DIFFICULTIES else "medium"


def _find(query: str, entries: list[dict]) -> dict | None:
    for e in entries:
        if e["id"] == query:
            return e
    q = query.lower().strip()
    matches = [e for e in entries if q in e["title"].lower()]
    todo = [e for e in matches if e["status"] != "solved"]
    if todo:
        return todo[0]
    return matches[0] if matches else None


def add(
    title: str,
    difficulty: str = "medium",
    topic: str = "",
    url: str = "",
    solved: bool = False,
) -> dict:
    entry = {
        "id": uuid.uuid4().hex[:6],
        "title": title.strip(),
        "difficulty": _norm_difficulty(difficulty),
        "topic": topic.strip(),
        "url": url.strip(),
        "status": "solved" if solved else "todo",
        "created_at": _now_iso(),
        "solved_at": _now_iso() if solved else None,
    }
    with _lock:
        entries = _load()
        entries.append(entry)
        _save(entries)
    return entry


def solve(query: str) -> dict | None:
    with _lock:
        entries = _load()
        entry = _find(query, entries)
        if entry is None:
            return None
        entry["status"] = "solved"
        entry["solved_at"] = _now_iso()
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


def list_all(difficulty: str | None = None, status: str | None = None) -> list[dict]:
    entries = _load()
    if difficulty:
        d = _norm_difficulty(difficulty)
        entries = [e for e in entries if e["difficulty"] == d]
    if status:
        entries = [e for e in entries if e["status"] == status]
    rank = {"easy": 0, "medium": 1, "hard": 2}
    entries.sort(key=lambda e: (e["status"] == "solved", rank.get(e["difficulty"], 1), e["title"].lower()))
    return entries


def stats() -> dict:
    """Per-difficulty solved/total + overall totals."""
    entries = _load()
    out = {d: {"solved": 0, "total": 0} for d in DIFFICULTIES}
    for e in entries:
        d = e["difficulty"]
        if d in out:
            out[d]["total"] += 1
            if e["status"] == "solved":
                out[d]["solved"] += 1
    out["total_solved"] = sum(out[d]["solved"] for d in DIFFICULTIES)
    out["total"] = len(entries)
    return out


def recent_solved(limit: int = 6) -> list[dict]:
    solved = [e for e in _load() if e["status"] == "solved"]
    solved.sort(key=lambda e: e.get("solved_at") or "", reverse=True)
    return solved[:limit]

"""Persistent JSON memory store with substring + tag search."""
from __future__ import annotations

import json
import os
import re
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

from config import MEMORY_DIR

MEMORY_FILE = MEMORY_DIR / "memories.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _load() -> list[dict]:
    if not MEMORY_FILE.exists():
        return []
    try:
        return json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        backup = MEMORY_FILE.with_suffix(".corrupt.json")
        MEMORY_FILE.rename(backup)
        return []


def _save(entries: list[dict]) -> None:
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=str(MEMORY_DIR), suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, MEMORY_FILE)
    except Exception:
        Path(tmp_path).unlink(missing_ok=True)
        raise


def save(content: str, category: str = "general", tags: list[str] | None = None) -> dict:
    entry = {
        "id": uuid.uuid4().hex[:12],
        "timestamp": _now_iso(),
        "category": category,
        "content": content,
        "tags": tags or [],
    }
    entries = _load()
    entries.append(entry)
    _save(entries)
    return entry


def search(query: str, limit: int = 10) -> list[dict]:
    """Substring + tag match. Case-insensitive. Newest first."""
    query_lower = query.lower()
    terms = [t for t in re.split(r"\s+", query_lower) if t]
    if not terms:
        return list(reversed(_load()))[:limit]

    scored: list[tuple[int, dict]] = []
    for entry in _load():
        hay = (
            entry["content"].lower()
            + " "
            + entry["category"].lower()
            + " "
            + " ".join(entry["tags"]).lower()
        )
        score = sum(hay.count(t) for t in terms)
        if score > 0:
            scored.append((score, entry))
    scored.sort(key=lambda x: (x[0], x[1]["timestamp"]), reverse=True)
    return [e for _, e in scored[:limit]]


def list_recent(limit: int = 10) -> list[dict]:
    return list(reversed(_load()))[:limit]


def delete(memory_id: str) -> bool:
    entries = _load()
    new_entries = [e for e in entries if e["id"] != memory_id]
    if len(new_entries) == len(entries):
        return False
    _save(new_entries)
    return True


def count() -> int:
    return len(_load())

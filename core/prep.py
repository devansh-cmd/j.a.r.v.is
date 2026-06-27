"""SWE / MLE job-prep tracker. JSON-backed checklist grouped by category.

Seeded on first run with a sensible MLE/SWE interview-prep curriculum. Jarvis
and the user add/complete items; the HUD shows per-category progress.
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

PREP_FILE = MEMORY_DIR / "prep.json"
_lock = threading.Lock()

# Ordered so the HUD renders categories in a sensible sequence.
CATEGORIES = (
    "Coding",
    "System Design",
    "ML System Design",
    "ML Theory",
    "Behavioral",
    "Applications",
)

# Seeded once on first run. The user can add/remove freely afterwards.
DEFAULT_CURRICULUM: list[tuple[str, str]] = [
    ("Coding", "Arrays, hashing & two-pointer patterns"),
    ("Coding", "Sliding window & prefix sums"),
    ("Coding", "Trees & graphs — BFS / DFS"),
    ("Coding", "Dynamic programming patterns"),
    ("Coding", "Heaps, intervals & greedy"),
    ("System Design", "Fundamentals — caching, load balancing, sharding"),
    ("System Design", "Design a URL shortener"),
    ("System Design", "Design a news feed"),
    ("System Design", "Design a chat / messaging system"),
    ("System Design", "Design a rate limiter"),
    ("ML System Design", "Recommendation system"),
    ("ML System Design", "Feed / search ranking"),
    ("ML System Design", "Ad click-through-rate prediction"),
    ("ML System Design", "Fraud / anomaly detection"),
    ("ML System Design", "ML pipeline: data → train → serve → monitor"),
    ("ML Theory", "Bias-variance, regularization, overfitting"),
    ("ML Theory", "Gradient descent & optimizers"),
    ("ML Theory", "Transformers & attention"),
    ("ML Theory", "Metrics — precision/recall, AUC, F1"),
    ("ML Theory", "Embeddings & similarity search"),
    ("Behavioral", "Prepare 5 STAR stories"),
    ("Behavioral", '"Tell me about yourself" pitch'),
    ("Behavioral", "Conflict / failure / leadership stories"),
    ("Applications", "Resume polished & ATS-friendly"),
    ("Applications", "LinkedIn & GitHub updated"),
    ("Applications", "Target company list + referrals"),
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _load() -> list[dict]:
    if not PREP_FILE.exists():
        return []
    try:
        return json.loads(PREP_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []


def _save(entries: list[dict]) -> None:
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(MEMORY_DIR), suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2, ensure_ascii=False)
        os.replace(tmp, PREP_FILE)
    except Exception:
        Path(tmp).unlink(missing_ok=True)
        raise


def ensure_seeded() -> None:
    """Seed the default curriculum exactly once (when the file doesn't exist)."""
    if PREP_FILE.exists():
        return
    with _lock:
        if PREP_FILE.exists():
            return
        entries = []
        for category, title in DEFAULT_CURRICULUM:
            entries.append(
                {
                    "id": uuid.uuid4().hex[:6],
                    "title": title,
                    "category": category,
                    "status": "todo",
                    "created_at": _now_iso(),
                    "done_at": None,
                }
            )
        _save(entries)


def _norm_category(c: str) -> str:
    c = (c or "").strip()
    for known in CATEGORIES:
        if c.lower() == known.lower():
            return known
    return c or "Other"


def _find(query: str, entries: list[dict]) -> dict | None:
    for e in entries:
        if e["id"] == query:
            return e
    q = query.lower().strip()
    matches = [e for e in entries if q in e["title"].lower()]
    todo = [e for e in matches if e["status"] != "done"]
    if todo:
        return todo[0]
    return matches[0] if matches else None


def add(title: str, category: str = "Other", done: bool = False) -> dict:
    entry = {
        "id": uuid.uuid4().hex[:6],
        "title": title.strip(),
        "category": _norm_category(category),
        "status": "done" if done else "todo",
        "created_at": _now_iso(),
        "done_at": _now_iso() if done else None,
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
        entry["status"] = "todo"
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


def _cat_rank(c: str) -> int:
    try:
        return CATEGORIES.index(c)
    except ValueError:
        return len(CATEGORIES)


def list_all(category: str | None = None) -> list[dict]:
    entries = _load()
    if category:
        c = _norm_category(category)
        entries = [e for e in entries if e["category"] == c]
    entries.sort(key=lambda e: (_cat_rank(e["category"]), e["status"] == "done", e["created_at"]))
    return entries


def stats() -> dict:
    """Per-category {done,total} in canonical order, plus overall."""
    entries = _load()
    cats: dict[str, dict] = {}
    for e in entries:
        c = e["category"]
        cats.setdefault(c, {"done": 0, "total": 0})
        cats[c]["total"] += 1
        if e["status"] == "done":
            cats[c]["done"] += 1
    ordered = {c: cats[c] for c in CATEGORIES if c in cats}
    for c in cats:
        if c not in ordered:
            ordered[c] = cats[c]
    done = sum(c["done"] for c in cats.values())
    total = len(entries)
    return {"by_category": ordered, "done": done, "total": total}

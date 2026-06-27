"""Tool definitions exposed to Claude and the dispatcher that executes them."""
from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

import pyautogui
import requests
from bs4 import BeautifulSoup

from config import (
    DOWNLOADS_DIR,
    IS_MAC,
    IS_WINDOWS,
    ROOT,
    SHELL_MAX_OUTPUT_CHARS,
    SHELL_NAME,
    SHELL_TIMEOUT_SECONDS,
)
from core import dsa, memory, prep, tasks

pyautogui.FAILSAFE = True


TOOLS: list[dict] = [
    {
        "name": "shell",
        "description": (
            f"Run a {SHELL_NAME} command on the user's machine and return its stdout/stderr. "
            "Use for filesystem ops, checking system state, git, running scripts, CLI tools. "
            f"Times out after {SHELL_TIMEOUT_SECONDS}s. Output truncated to {SHELL_MAX_OUTPUT_CHARS} chars. "
            "Confirm with the user before destructive commands (rm, overwrite, sudo, etc.)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": f"The {SHELL_NAME} command to execute.",
                },
                "cwd": {
                    "type": "string",
                    "description": "Working directory (optional).",
                },
            },
            "required": ["command"],
        },
    },
    {
        "name": "applescript",
        "description": (
            "macOS only. Run an AppleScript via osascript — the best way to control Mac apps: "
            "Music, Safari, Mail, Calendar, Reminders, Notes, Finder, System Events (UI scripting), "
            "set volume/brightness, etc. Prefer this over `shell` for anything app-related on a Mac. "
            "Confirm before actions that send, delete, or change settings."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "script": {
                    "type": "string",
                    "description": 'AppleScript source, e.g. \'tell application "Music" to play\'.',
                },
            },
            "required": ["script"],
        },
    },
    {
        "name": "read_file",
        "description": "Read a text file from disk. Returns content as a string.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "max_chars": {"type": "integer", "description": "Optional cap, default 20000."},
            },
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": "Write (or overwrite) a text file. Creates parent directories.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
                "append": {"type": "boolean", "description": "Append instead of overwrite. Default false."},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "list_directory",
        "description": "List entries in a directory. Returns names + types + sizes.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    },
    {
        "name": "web_fetch",
        "description": (
            "Fetch a URL and return the readable text content (HTML stripped). "
            "Use for reading article pages, docs, blog posts, etc."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string"},
                "max_chars": {"type": "integer", "description": "Cap on returned text. Default 8000."},
            },
            "required": ["url"],
        },
    },
    {
        "name": "web_search",
        "description": "Search the web via DuckDuckGo. Returns top result titles, URLs, and snippets.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "max_results": {"type": "integer", "description": "Default 6."},
            },
            "required": ["query"],
        },
    },
    {
        "name": "youtube_search",
        "description": "Search YouTube for videos matching a query. Returns titles, URLs, channels, durations.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "max_results": {"type": "integer", "description": "Default 5."},
            },
            "required": ["query"],
        },
    },
    {
        "name": "youtube_info",
        "description": "Get metadata for a YouTube video (title, channel, views, description, transcript if available).",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "YouTube URL or video ID."},
                "include_transcript": {"type": "boolean", "description": "Default true."},
            },
            "required": ["url"],
        },
    },
    {
        "name": "instagram_profile",
        "description": "Get public info for an Instagram username (followers, bio, recent posts).",
        "input_schema": {
            "type": "object",
            "properties": {
                "username": {"type": "string"},
                "max_posts": {"type": "integer", "description": "Default 5."},
            },
            "required": ["username"],
        },
    },
    {
        "name": "screenshot",
        "description": "Take a screenshot of the user's primary monitor and save it. Returns the saved path.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {"type": "string", "description": "Optional. Defaults to a timestamped name."},
            },
        },
    },
    {
        "name": "type_text",
        "description": "Type text via the keyboard at the current focus. Use sparingly — affects what's on screen.",
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "interval": {"type": "number", "description": "Seconds between keystrokes. Default 0.02."},
            },
            "required": ["text"],
        },
    },
    {
        "name": "key_press",
        "description": "Press a key or key combination, e.g. 'win', 'enter', 'ctrl+c', 'alt+tab'.",
        "input_schema": {
            "type": "object",
            "properties": {"keys": {"type": "string"}},
            "required": ["keys"],
        },
    },
    {
        "name": "mouse_click",
        "description": "Click at given screen coordinates. Defaults to a left click.",
        "input_schema": {
            "type": "object",
            "properties": {
                "x": {"type": "integer"},
                "y": {"type": "integer"},
                "button": {"type": "string", "description": "left | right | middle. Default left."},
                "double": {"type": "boolean", "description": "Double-click. Default false."},
            },
            "required": ["x", "y"],
        },
    },
    {
        "name": "open_app",
        "description": "Launch an application by name (e.g. 'notepad', 'chrome', 'code', 'spotify').",
        "input_schema": {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        },
    },
    {
        "name": "memory_save",
        "description": (
            "Save something to long-term memory. Use for facts about the user, preferences, "
            "ongoing projects, learned facts. Be selective — only save what's worth remembering."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "The fact or note to remember."},
                "category": {
                    "type": "string",
                    "description": "user | preference | project | fact | task | general",
                },
                "tags": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["content"],
        },
    },
    {
        "name": "memory_search",
        "description": "Search long-term memory by keywords. Returns matching entries newest-first.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer", "description": "Default 8."},
            },
            "required": ["query"],
        },
    },
    {
        "name": "memory_list_recent",
        "description": "List the most recently saved memories. No query needed.",
        "input_schema": {
            "type": "object",
            "properties": {"limit": {"type": "integer", "description": "Default 10."}},
        },
    },
    {
        "name": "task_add",
        "description": (
            "Add an item to the user's on-screen to-do list (shown live in the HUD). "
            "Use whenever the user asks to remember to do something, add a task, or note a reminder."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "The task description."},
                "priority": {
                    "type": "string",
                    "description": "low | normal | high. Default normal.",
                },
            },
            "required": ["text"],
        },
    },
    {
        "name": "task_complete",
        "description": (
            "Mark a to-do item as done. Match by its id or by a few words of its text "
            "(e.g. 'email john'). The HUD shows it checked off."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Task id or part of its text."},
            },
            "required": ["query"],
        },
    },
    {
        "name": "task_remove",
        "description": "Delete a to-do item entirely (not just complete it). Match by id or text.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Task id or part of its text."},
            },
            "required": ["query"],
        },
    },
    {
        "name": "task_list",
        "description": "List the user's current to-do items (pending first, then done).",
        "input_schema": {
            "type": "object",
            "properties": {
                "include_done": {"type": "boolean", "description": "Include completed. Default true."},
            },
        },
    },
    {
        "name": "task_clear_done",
        "description": "Remove all completed to-do items, clearing them from the list.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "dsa_add",
        "description": (
            "Add a DSA / LeetCode problem to the tracker. Set solved=true if the user has "
            "already solved it (e.g. 'I just solved Two Sum, easy')."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Problem name, e.g. 'Two Sum'."},
                "difficulty": {"type": "string", "description": "easy | medium | hard."},
                "topic": {"type": "string", "description": "Optional, e.g. 'arrays', 'graphs', 'dp'."},
                "url": {"type": "string", "description": "Optional problem URL."},
                "solved": {"type": "boolean", "description": "Mark solved immediately. Default false."},
            },
            "required": ["title", "difficulty"],
        },
    },
    {
        "name": "dsa_solve",
        "description": "Mark a tracked DSA problem as solved. Match by id or part of the title.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
    {
        "name": "dsa_remove",
        "description": "Remove a DSA problem from the tracker. Match by id or title.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
    {
        "name": "dsa_stats",
        "description": (
            "Get DSA progress: how many solved by difficulty (easy/medium/hard) and totals. "
            "Use when the user asks how many problems they've done."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "dsa_list",
        "description": "List tracked DSA problems, optionally filtered by difficulty or status (solved/todo).",
        "input_schema": {
            "type": "object",
            "properties": {
                "difficulty": {"type": "string", "description": "easy | medium | hard (optional)."},
                "status": {"type": "string", "description": "solved | todo (optional)."},
            },
        },
    },
    {
        "name": "prep_add",
        "description": (
            "Add an item to the SWE/MLE job-prep tracker under a category "
            "(Coding, System Design, ML System Design, ML Theory, Behavioral, Applications)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "category": {"type": "string", "description": "One of the prep categories."},
                "done": {"type": "boolean", "description": "Mark done immediately. Default false."},
            },
            "required": ["title", "category"],
        },
    },
    {
        "name": "prep_complete",
        "description": "Mark a job-prep item as done. Match by id or part of its text.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
    {
        "name": "prep_remove",
        "description": "Remove a job-prep item. Match by id or text.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
    {
        "name": "prep_stats",
        "description": "Get job-prep progress: done/total per category and overall. Use when asked about prep progress.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "prep_list",
        "description": "List job-prep items, optionally filtered by category.",
        "input_schema": {
            "type": "object",
            "properties": {"category": {"type": "string", "description": "Optional category filter."}},
        },
    },
]


def _truncate(s: str, n: int) -> str:
    if len(s) <= n:
        return s
    return s[:n] + f"\n…[truncated, {len(s) - n} more chars]"


def _shell_argv(command: str) -> list[str]:
    """Build the argv to run a command in the platform's shell."""
    if IS_WINDOWS:
        return ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command]
    # macOS / Linux — login shell so Homebrew/user PATH is available.
    shell = shutil.which("zsh") or shutil.which("bash") or "/bin/sh"
    return [shell, "-lc", command]


def t_shell(command: str, cwd: str | None = None) -> str:
    workdir = cwd or str(ROOT)
    try:
        result = subprocess.run(
            _shell_argv(command),
            capture_output=True,
            text=True,
            timeout=SHELL_TIMEOUT_SECONDS,
            cwd=workdir,
        )
    except subprocess.TimeoutExpired:
        return f"[timeout after {SHELL_TIMEOUT_SECONDS}s]"
    except FileNotFoundError as e:
        return f"[shell not found: {e}]"
    parts = []
    if result.stdout:
        parts.append("STDOUT:\n" + result.stdout.rstrip())
    if result.stderr:
        parts.append("STDERR:\n" + result.stderr.rstrip())
    parts.append(f"[exit code: {result.returncode}]")
    return _truncate("\n\n".join(parts), SHELL_MAX_OUTPUT_CHARS)


def t_read_file(path: str, max_chars: int = 20000) -> str:
    p = Path(path)
    if not p.exists():
        return f"File not found: {path}"
    if not p.is_file():
        return f"Not a file: {path}"
    try:
        content = p.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return f"Error reading: {e}"
    return _truncate(content, max_chars)


def t_write_file(path: str, content: str, append: bool = False) -> str:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if append else "w"
    try:
        with open(p, mode, encoding="utf-8") as f:
            f.write(content)
    except Exception as e:
        return f"Error writing: {e}"
    return f"Wrote {len(content)} chars to {p}"


def t_list_directory(path: str) -> str:
    p = Path(path)
    if not p.exists():
        return f"Not found: {path}"
    if not p.is_dir():
        return f"Not a directory: {path}"
    lines = []
    for entry in sorted(p.iterdir(), key=lambda e: (e.is_file(), e.name.lower())):
        if entry.is_dir():
            lines.append(f"<DIR>  {entry.name}/")
        else:
            try:
                size = entry.stat().st_size
                lines.append(f"{size:>9}  {entry.name}")
            except OSError:
                lines.append(f"        ?  {entry.name}")
    return "\n".join(lines) if lines else "(empty directory)"


def t_web_fetch(url: str, max_chars: int = 8000) -> str:
    try:
        r = requests.get(
            url,
            timeout=15,
            headers={"User-Agent": "Mozilla/5.0 (Jarvis)"},
        )
        r.raise_for_status()
    except Exception as e:
        return f"Fetch failed: {e}"
    soup = BeautifulSoup(r.text, "lxml")
    for tag in soup(["script", "style", "noscript", "iframe"]):
        tag.decompose()
    text = "\n".join(line.strip() for line in soup.get_text("\n").splitlines() if line.strip())
    return _truncate(f"[{url}]\n\n{text}", max_chars)


def t_web_search(query: str, max_results: int = 6) -> str:
    try:
        from ddgs import DDGS
    except ImportError:
        return "ddgs library not installed. Install with: pip install ddgs"
    results = []
    try:
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append(
                    f"• {r.get('title', '')}\n  {r.get('href', '')}\n  {r.get('body', '')}"
                )
    except Exception as e:
        return f"Search failed: {e}"
    return "\n\n".join(results) if results else "No results."


def t_youtube_search(query: str, max_results: int = 5) -> str:
    try:
        import yt_dlp
    except ImportError:
        return "yt-dlp not installed."
    opts = {"quiet": True, "no_warnings": True, "skip_download": True, "extract_flat": True}
    with yt_dlp.YoutubeDL(opts) as ydl:
        try:
            info = ydl.extract_info(f"ytsearch{max_results}:{query}", download=False)
        except Exception as e:
            return f"YouTube search failed: {e}"
    entries = info.get("entries", []) if info else []
    lines = []
    for e in entries:
        title = e.get("title", "?")
        url = e.get("url") or f"https://youtube.com/watch?v={e.get('id')}"
        channel = e.get("channel") or e.get("uploader", "?")
        dur = e.get("duration") or 0
        m, s = divmod(int(dur), 60) if dur else (0, 0)
        lines.append(f"• {title}\n  {channel} — {m}:{s:02d}\n  {url}")
    return "\n\n".join(lines) if lines else "No videos found."


def t_youtube_info(url: str, include_transcript: bool = True) -> str:
    try:
        import yt_dlp
    except ImportError:
        return "yt-dlp not installed."
    if not url.startswith("http"):
        url = f"https://youtube.com/watch?v={url}"
    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "writesubtitles": include_transcript,
        "writeautomaticsub": include_transcript,
        "subtitleslangs": ["en"],
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
        except Exception as e:
            return f"YouTube fetch failed: {e}"
    title = info.get("title", "?")
    channel = info.get("channel") or info.get("uploader", "?")
    views = info.get("view_count", "?")
    desc = (info.get("description") or "")[:1500]
    out = [
        f"Title: {title}",
        f"Channel: {channel}",
        f"Views: {views}",
        f"Duration: {info.get('duration_string', '?')}",
        f"URL: {info.get('webpage_url', url)}",
        f"\nDescription:\n{desc}",
    ]
    if include_transcript:
        subs = info.get("subtitles", {}) or info.get("automatic_captions", {})
        en_subs = subs.get("en", []) if subs else []
        if en_subs:
            sub_url = next(
                (s["url"] for s in en_subs if s.get("ext") in ("vtt", "ttml", "srv3")),
                en_subs[0].get("url"),
            )
            if sub_url:
                try:
                    sub_text = requests.get(sub_url, timeout=10).text
                    cleaned = _clean_vtt(sub_text)
                    out.append(f"\nTranscript:\n{cleaned[:6000]}")
                except Exception as e:
                    out.append(f"\nTranscript fetch failed: {e}")
    return "\n".join(out)


def _clean_vtt(text: str) -> str:
    import re

    lines = []
    for line in text.splitlines():
        if (
            not line.strip()
            or line.startswith(("WEBVTT", "NOTE", "Kind:", "Language:"))
            or "-->" in line
            or re.fullmatch(r"\d+", line.strip())
        ):
            continue
        cleaned = re.sub(r"<[^>]+>", "", line).strip()
        if cleaned and (not lines or lines[-1] != cleaned):
            lines.append(cleaned)
    return "\n".join(lines)


def t_instagram_profile(username: str, max_posts: int = 5) -> str:
    try:
        import instaloader
    except ImportError:
        return "instaloader not installed."
    L = instaloader.Instaloader(
        download_pictures=False,
        download_videos=False,
        download_video_thumbnails=False,
        download_geotags=False,
        download_comments=False,
        save_metadata=False,
        compress_json=False,
        quiet=True,
    )
    try:
        profile = instaloader.Profile.from_username(L.context, username)
    except Exception as e:
        return f"Instagram lookup failed: {e}"
    out = [
        f"Username: @{profile.username}",
        f"Full name: {profile.full_name}",
        f"Followers: {profile.followers}",
        f"Following: {profile.followees}",
        f"Posts: {profile.mediacount}",
        f"Bio: {profile.biography}",
        f"External URL: {profile.external_url or '(none)'}",
        f"Private: {profile.is_private}",
        f"Verified: {profile.is_verified}",
    ]
    if not profile.is_private:
        out.append("\nRecent posts:")
        try:
            for i, post in enumerate(profile.get_posts()):
                if i >= max_posts:
                    break
                caption = (post.caption or "")[:200].replace("\n", " ")
                out.append(
                    f"  [{post.date_utc:%Y-%m-%d}] likes={post.likes} comments={post.comments} — {caption}"
                )
        except Exception as e:
            out.append(f"  (could not fetch posts: {e})")
    return "\n".join(out)


def t_screenshot(filename: str | None = None) -> str:
    DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
    if not filename:
        filename = f"screenshot_{int(time.time())}.png"
    path = DOWNLOADS_DIR / filename
    pyautogui.screenshot(str(path))
    w, h = pyautogui.size()
    return f"Saved screenshot to {path} ({w}×{h})"


def t_type_text(text: str, interval: float = 0.02) -> str:
    pyautogui.typewrite(text, interval=interval)
    return f"Typed {len(text)} characters."


def t_key_press(keys: str) -> str:
    parts = [k.strip().lower() for k in keys.replace(" ", "").split("+")]
    if len(parts) == 1:
        pyautogui.press(parts[0])
    else:
        pyautogui.hotkey(*parts)
    return f"Pressed: {keys}"


def t_mouse_click(x: int, y: int, button: str = "left", double: bool = False) -> str:
    if double:
        pyautogui.doubleClick(x=x, y=y, button=button)
    else:
        pyautogui.click(x=x, y=y, button=button)
    return f"Clicked ({x}, {y}) [{button}{', double' if double else ''}]"


def t_open_app(name: str) -> str:
    if IS_WINDOWS:
        argv = ["powershell.exe", "-NoProfile", "-Command", f"Start-Process '{name}'"]
    elif IS_MAC:
        argv = ["open", "-a", name]
    else:
        argv = ["xdg-open", name]
    try:
        subprocess.Popen(argv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return f"Launched: {name}"
    except Exception as e:
        return f"Could not launch {name}: {e}"


def t_applescript(script: str) -> str:
    if not IS_MAC:
        return "applescript is only available on macOS."
    try:
        result = subprocess.run(
            ["osascript", "-"],
            input=script,
            capture_output=True,
            text=True,
            timeout=SHELL_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return f"[timeout after {SHELL_TIMEOUT_SECONDS}s]"
    except FileNotFoundError:
        return "[osascript not found — are you on macOS?]"
    out = (result.stdout or "").strip()
    err = (result.stderr or "").strip()
    if result.returncode != 0:
        return f"AppleScript error: {err or out or '(no output)'}"
    return out or "(ok)"


def t_memory_save(content: str, category: str = "general", tags: list[str] | None = None) -> str:
    entry = memory.save(content, category=category, tags=tags)
    return f"Saved [{entry['id']}] in '{entry['category']}': {entry['content']}"


def t_memory_search(query: str, limit: int = 8) -> str:
    results = memory.search(query, limit=limit)
    if not results:
        return f"No memories matched '{query}'."
    return "\n".join(
        f"[{r['id']}] {r['timestamp'][:10]} ({r['category']}): {r['content']}" for r in results
    )


def t_memory_list_recent(limit: int = 10) -> str:
    results = memory.list_recent(limit=limit)
    if not results:
        return "No memories saved yet."
    return "\n".join(
        f"[{r['id']}] {r['timestamp'][:10]} ({r['category']}): {r['content']}" for r in results
    )


def t_task_add(text: str, priority: str = "normal") -> str:
    entry = tasks.add(text, priority=priority)
    tag = f" ({entry['priority']})" if entry["priority"] != "normal" else ""
    return f"Added to-do [{entry['id']}]{tag}: {entry['text']}"


def t_task_complete(query: str) -> str:
    entry = tasks.complete(query)
    if entry is None:
        return f"No matching to-do for '{query}'."
    return f"Completed [{entry['id']}]: {entry['text']}"


def t_task_remove(query: str) -> str:
    entry = tasks.remove(query)
    if entry is None:
        return f"No matching to-do for '{query}'."
    return f"Removed [{entry['id']}]: {entry['text']}"


def t_task_list(include_done: bool = True) -> str:
    items = tasks.list_all(include_done=include_done)
    if not items:
        return "To-do list is empty."
    lines = []
    for t in items:
        box = "✓" if t["status"] == "done" else "○"
        tag = f" ({t['priority']})" if t["priority"] != "normal" else ""
        lines.append(f"{box} [{t['id']}]{tag} {t['text']}")
    return "\n".join(lines)


def t_task_clear_done(**_) -> str:
    n = tasks.clear_done()
    return f"Cleared {n} completed to-do{'s' if n != 1 else ''}."


def t_dsa_add(
    title: str, difficulty: str, topic: str = "", url: str = "", solved: bool = False
) -> str:
    e = dsa.add(title, difficulty=difficulty, topic=topic, url=url, solved=solved)
    state = "solved" if e["status"] == "solved" else "added"
    return f"DSA [{e['id']}] {state}: {e['title']} ({e['difficulty']})"


def t_dsa_solve(query: str) -> str:
    e = dsa.solve(query)
    if e is None:
        return f"No matching DSA problem for '{query}'."
    s = dsa.stats()
    return (
        f"Solved [{e['id']}]: {e['title']} ({e['difficulty']}). "
        f"Totals — E:{s['easy']['solved']} M:{s['medium']['solved']} H:{s['hard']['solved']}"
    )


def t_dsa_remove(query: str) -> str:
    e = dsa.remove(query)
    if e is None:
        return f"No matching DSA problem for '{query}'."
    return f"Removed [{e['id']}]: {e['title']}"


def t_dsa_stats(**_) -> str:
    s = dsa.stats()
    return (
        f"DSA solved — Easy: {s['easy']['solved']}/{s['easy']['total']}, "
        f"Medium: {s['medium']['solved']}/{s['medium']['total']}, "
        f"Hard: {s['hard']['solved']}/{s['hard']['total']}. "
        f"Total solved: {s['total_solved']} of {s['total']} tracked."
    )


def t_dsa_list(difficulty: str | None = None, status: str | None = None) -> str:
    items = dsa.list_all(difficulty=difficulty, status=status)
    if not items:
        return "No DSA problems match."
    lines = []
    for e in items:
        box = "✓" if e["status"] == "solved" else "○"
        topic = f" — {e['topic']}" if e["topic"] else ""
        lines.append(f"{box} [{e['id']}] ({e['difficulty']}) {e['title']}{topic}")
    return "\n".join(lines)


def t_prep_add(title: str, category: str, done: bool = False) -> str:
    e = prep.add(title, category=category, done=done)
    return f"Prep [{e['id']}] added under {e['category']}: {e['title']}"


def t_prep_complete(query: str) -> str:
    e = prep.complete(query)
    if e is None:
        return f"No matching prep item for '{query}'."
    return f"Done [{e['id']}] ({e['category']}): {e['title']}"


def t_prep_remove(query: str) -> str:
    e = prep.remove(query)
    if e is None:
        return f"No matching prep item for '{query}'."
    return f"Removed [{e['id']}]: {e['title']}"


def t_prep_stats(**_) -> str:
    s = prep.stats()
    parts = [f"{cat}: {v['done']}/{v['total']}" for cat, v in s["by_category"].items()]
    return f"Prep progress — {'; '.join(parts)}. Overall: {s['done']}/{s['total']}."


def t_prep_list(category: str | None = None) -> str:
    items = prep.list_all(category=category)
    if not items:
        return "No prep items match."
    lines = []
    current = None
    for e in items:
        if e["category"] != current:
            current = e["category"]
            lines.append(f"— {current} —")
        box = "✓" if e["status"] == "done" else "○"
        lines.append(f"  {box} [{e['id']}] {e['title']}")
    return "\n".join(lines)


DISPATCH: dict[str, Any] = {
    "shell": t_shell,
    "read_file": t_read_file,
    "write_file": t_write_file,
    "list_directory": t_list_directory,
    "web_fetch": t_web_fetch,
    "web_search": t_web_search,
    "youtube_search": t_youtube_search,
    "youtube_info": t_youtube_info,
    "instagram_profile": t_instagram_profile,
    "screenshot": t_screenshot,
    "type_text": t_type_text,
    "key_press": t_key_press,
    "mouse_click": t_mouse_click,
    "open_app": t_open_app,
    "applescript": t_applescript,
    "memory_save": t_memory_save,
    "memory_search": t_memory_search,
    "memory_list_recent": t_memory_list_recent,
    "task_add": t_task_add,
    "task_complete": t_task_complete,
    "task_remove": t_task_remove,
    "task_list": t_task_list,
    "task_clear_done": t_task_clear_done,
    "dsa_add": t_dsa_add,
    "dsa_solve": t_dsa_solve,
    "dsa_remove": t_dsa_remove,
    "dsa_stats": t_dsa_stats,
    "dsa_list": t_dsa_list,
    "prep_add": t_prep_add,
    "prep_complete": t_prep_complete,
    "prep_remove": t_prep_remove,
    "prep_stats": t_prep_stats,
    "prep_list": t_prep_list,
}


def run_tool(name: str, kwargs: dict) -> tuple[str, bool]:
    """Execute a tool by name with kwargs. Returns (result_text, is_error)."""
    fn = DISPATCH.get(name)
    if fn is None:
        return f"Unknown tool: {name}", True
    try:
        result = fn(**kwargs)
        return str(result), False
    except TypeError as e:
        return f"Bad arguments for {name}: {e}", True
    except Exception as e:
        return f"{name} raised {type(e).__name__}: {e}", True

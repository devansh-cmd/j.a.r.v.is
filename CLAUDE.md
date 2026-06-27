# CLAUDE.md — project context for Claude Code

This file orients any Claude Code session working on Jarvis. Read it first.

## What this is

**Jarvis** — a local, voice-driven personal assistant with a holographic PySide6 HUD,
powered by the Anthropic API (`claude-opus-4-8`). Voice in → Claude agentic tool-use
loop → voice out. It controls the machine, browses/scrapes the web, manages trackers,
and keeps a perpetual diary memory.

Public repo: https://github.com/devansh-cmd/j.a.r.v.is — shared on the owner's
LinkedIn, so it **must stay secret-free** (see Conventions).

## ⚠️ Deployment reality — READ THIS

- The app is **developed on a Windows 11 machine** but the **real target is the
  owner's Apple Mac Mini.** It is cross-platform by OS detection.
- The macOS code paths (zsh shell, `open -a`, the `applescript`/osascript tool) were
  written and verified *structurally* on Windows but have **NOT been run on real Mac
  hardware yet.** When this session is on the Mac, that first-run shakeout is the job:
  test the shell + AppleScript tools, fix any PATH/permission quirks, then launch.
- macOS needs **Privacy permissions** or the control tools silently fail: System
  Settings → Privacy & Security → grant the terminal/Python **Accessibility,
  Screen Recording, Automation, Microphone** (and Full Disk Access if touching
  protected folders).
- macOS `pip3` often errors with `externally-managed-environment` — use a venv:
  `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`.
  The mic needs `brew install portaudio` before PyAudio builds.

## Architecture

```
jarvis_hud.py     # graphical entry point (PySide6 HUD)
jarvis.py         # terminal entry point (no GUI)
config.py         # settings + OS detection (IS_MAC/IS_WINDOWS/SHELL_NAME) + persona
core/
  brain.py        # Claude agentic loop; injects memory + diary digest into system prompt
  tools.py        # ALL tools + DISPATCH. Add new capabilities HERE, not scattered.
  voice.py        # STT (SpeechRecognition/Google) + TTS (edge-tts + pygame)
  memory.py       # curated long-term memory (memory_store/memories.json)
  diary.py        # perpetual diary: write every turn + read recent back into context
  tasks.py        # on-screen TO-DO tracker
  dsa.py          # DSA problem tracker (easy/medium/hard solved counts)
  prep.py         # SWE/MLE interview-prep tracker (seeded curriculum)
hud/
  window.py       # JarvisHUD: MAIN view + JOB PREP view (QStackedWidget), render logic
  widgets.py      # ArcReactor, Panel, TabbedPanel, JobPrepView, TitleBar, StatusBar
  worker.py       # JarvisWorker QThread — owns Voice+Brain, emits Qt signals
  style.py        # theme + QSS
```

## Key design decisions

- **Cross-platform via `config.py`**: OS detected at runtime. `tools.t_shell` runs
  login zsh on macOS / PowerShell on Windows; `t_open_app` uses `open -a` / Start-Process;
  `applescript` tool is macOS-only (returns a clear message off-Mac). Keep all
  OS-specific behavior behind this layer — never hardcode one OS.
- **Guarded autonomy**: the persona instructs Jarvis to act freely on safe/read-only
  actions but confirm before destructive/irreversible ones. Enforced at the model level.
- **Two memories**: `diary.py` is the perpetual auto-log fed back into context each
  session (continuity / recognising the user); `memory.py` is curated durable facts
  (`memory_save`). Both gitignored.
- **Two HUD views**: MAIN (assistant) and JOB PREP (DSA + interview dashboard), switched
  from the title bar (`Ctrl+1`/`Ctrl+2`).
- The HUD `worker.py` runs Brain/Voice off the UI thread; the window renders via signals.

## Conventions

- **Secrets**: never hardcode. `ANTHROPIC_API_KEY` (and future `ELEVENLABS_API_KEY`)
  load only via `os.getenv` from a local, gitignored `.env`. A pre-commit secret guard
  is active via `git config core.hooksPath scripts/git-hooks`. See SECURITY.md.
- **Gitignored runtime data**: `memory_store/`, `logs/`, `diary/`, `downloads/`, `.env`.
- **Adding a tool**: define it in `core/tools.py` (TOOLS list + a `t_*` function +
  DISPATCH entry). The brain's loop picks it up automatically.
- **Testing the HUD headless**: render offscreen with `QT_QPA_PLATFORM=offscreen` and
  `window.grab().save(...)`. Text shows as boxes in headless renders (no font DB) — that
  is NOT a bug; it's crisp on a real display.

## Running

```bash
# macOS (use a venv — see Deployment reality above)
python3 jarvis_hud.py        # HUD    |  python3 jarvis.py  # terminal
```
Needs `ANTHROPIC_API_KEY` in `.env`. Without it the HUD opens but the reactor goes red
and ACTIONS shows "Brain init failed".

## Status / where we are

Living checklist is in **TODO.md**. Done: scaffold, brain+tools, voice, trackers
(to-do/DSA/prep), MAIN+JOB-PREP views, diary perpetual memory, security audit + hooks,
cross-platform layer, README. Open: recommended MCPs doc, HUD visual polish pass (match
`design/hud_mockup.html`), ElevenLabs British voice (needs key). Check TODO.md for the
current state before starting work.

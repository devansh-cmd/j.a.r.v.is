# Jarvis — TODO

Living checklist. Mirrors the in-session task tracker. Check things off as we go.

## ✅ Done
- [x] Project scaffold at `C:\Jarvis` (config, core package, entrypoint)
- [x] Claude brain — agentic tool-use loop (`core/brain.py`)
- [x] 17 tools — shell, files, web, YouTube, Instagram, PC control, memory (`core/tools.py`)
- [x] Persistent memory store — atomic JSON + search (`core/memory.py`)
- [x] Voice I/O — SpeechRecognition (STT) + edge-tts (TTS) (`core/voice.py`)
- [x] Action diary module — JSONL + daily markdown (`core/diary.py`)
- [x] Base HUD — PySide6 frameless window, arc reactor, 4 panels (`hud/`)
- [x] HTML aesthetic mockup (`design/hud_mockup.html`)
- [x] On-screen TO-DO list Jarvis manages — store + tools + live HUD panel
      (`core/tasks.py`, `task_add/complete/remove/list/clear_done`)
- [x] DSA tracker — easy/medium/hard with solved counts (`core/dsa.py`)
- [x] SWE/MLE prep tracker — seeded curriculum, per-category progress (`core/prep.py`)
- [x] MAIN / JOB PREP view switcher — title-bar nav; JOB PREP = full DSA +
      prep dashboard (`JobPrepView`); MAIN keeps TO-DO + glanceable summary

- [x] Diary wired as perpetual memory — journals every turn AND feeds recent
      history back into context so Jarvis recognises the user across sessions
      (`core/diary.py` + `core/brain.py`)
- [x] `.gitignore` + secret-scan audit + pre-commit secret guard + SECURITY.md
- [x] Cross-platform (macOS + Windows) — OS-aware shell/persona, `applescript`
      tool for Mac control, guarded autonomy, README with Mac setup + permissions
- [x] Proper README (features, both views, macOS/Windows setup, architecture)

- [x] HUD visual glow-up — grid+vignette background, scan line, corner brackets,
      translucent glowing panels, richer reactor (60-tick ring + crosshairs)

- [x] Theming spine (UI spec phase 1) — ThemeState + build_stylesheet(accent);
      apply_mode recolours the whole HUD; Ctrl+Shift+1-4 → default/chill/work/creative

## 🔵 In progress / next — J.A.R.V.I.S. modes system (design/UI_SPEC.md)
- [x] Phase 1 — theming spine
- [x] Phase 2 — mode selector UI + `set_mode` voice tool (switch via keyboard/click/voice)
- [x] Phase 3 — orb upgrade (1.5s breathing, puff+ripple, intensity hue-shift, 3 data rings)
- [ ] Phase 4 — Chill layout (clock, now-playing, ambient bg)
- [ ] Phase 5 — Creative layout (idea canvas / spawnable cards)
- [ ] Phase 6 — Work data (CS/world/India news feeds)
- [ ] Phase 7 — sound bed + ElevenLabs British voice
- [ ] Phase 8 — data-viz (real mic waveform, gauges, weather radar)
- [ ] (optional) status pills (BRAIN/VOICE/NET)

## 📋 Backlog
- [ ] README + `.gitignore`
- [ ] `git init` + first commit
- [ ] Push to GitHub (gh CLI not installed — need remote URL / repo name)
- [ ] Document recommended MCPs (`docs/MCPS.md`)
- [ ] ElevenLabs British Jarvis voice (deferred — needs API key)

## 💡 Ideas / later
- [ ] Wake word ("Jarvis…") instead of always-listening
- [ ] Streaming responses to HUD token-by-token
- [ ] System tray + global hotkey to summon
- [ ] Conversation history persistence across restarts
- [ ] MCP client support inside Jarvis itself (so Jarvis can use MCP servers)

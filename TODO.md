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

## 🔵 In progress / next
- [ ] **Port mockup aesthetic into Qt HUD** — translucent panels, glow, richer reactor
      (60 ticks, 8 notches, 4 rings), scan line, corner brackets, status pills,
      stat bars, audio waveform panel
- [ ] **Wire diary into brain loop** — record every turn + tool call + response

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

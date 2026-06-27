# J.A.R.V.I.S. — UI Specification

The target design for the HUD. This is the north star; it extends the current
PySide6 interface (orb/reactor + panels + MAIN/JOB-PREP views) toward a fully
themed, mode-driven, cinematic system. Each section gives the **visual**, the
**behavior/animation**, **Qt implementation notes**, and **Status** against the
code that exists today.

Status legend:  ✅ built · 🔶 partial · 🆕 new

---

## 0. Shared design language

- **Material**: transparent glass — translucent panels (`rgba`), thin cyan/mode-accent
  borders with a brighter glowing top edge, soft outer glow halos (`QGraphicsDropShadowEffect`).
- **Motion**: nothing snaps. All state changes ease over 200–800 ms (`QVariantAnimation`,
  `QPropertyAnimation`, eased timers). 30–60 fps custom painting for the orb/rings/overlay.
- **Type**: geometric mono/sans — Consolas now; ship with a bundled geometric face
  (e.g. *Rajdhani* / *Orbitron* / *JetBrains Mono*) so it's identical on Mac & Windows.
- **Accent**: a single mode accent colour drives orb, rings, panels, and glow. Default
  cyan `#00d4ff`; overridden per mode (see §7).
- **Layers (back → front)**: `HudBackground` (grid + vignette) → mode layout (orb + panels)
  → `HudOverlay` (scan line, corner brackets). ✅ this stack exists.

---

## 1. Central Core — the Orb

**Visual**
- Perfect circle, ~45–55% of the shorter screen dimension, centered.
- Glassy crystal: bright white-hot core → mode-accent mid → transparent rim, with a
  faint specular metallic gleam arc near the top.
- Neon filament lines along the rim drifting *inward* toward the core.

**Behavior & animation**
- **Idle**: soft breathing pulse on a **1.5 s** cycle; gentle rim-filament drift.
- **Active / task intensity**: brightness rises; base hue shifts along
  cyan → violet → yellow as `intensity` (0–1) climbs (token rate / tool activity).
- **Command received ("puff")**: quick scale-up (1.0 → 1.12 → 1.0 over ~450 ms,
  ease-out-back) + an energy ring rippling outward from the core to the rim.
- **Listening**: the waveform ring reacts to mic amplitude.
- Mode sets the *base* colour; intensity/ state modulate from there.

**Qt implementation**
- Extend `hud/widgets.py::ArcReactor`. Add: `set_intensity(float)`, `pulse_puff()`
  (kicks a one-shot scale+ripple animation), `set_accent(QColor)` (mode base).
- Core = multi-stop `QRadialGradient` (white → accent → transparent), pulse via a
  sine on a 1.5 s period. Filaments = short curved strokes on the rim, phase-animated.
- Ripple = an expanding alpha-fading ring tracked as a 0→1 animation value.

**Status** — 🔶 reactor exists with state colours, rotating rings, waveform, pulsing
core, 60-tick ring. Missing: 1.5 s breathing cadence, intensity hue-shift
(violet/yellow), puff+ripple, inward rim filaments, accent-from-mode.

---

## 2. Holographic Data Rings

**Visual** — three concentric rings around the orb:
| Ring | Speed | Carries |
|------|-------|---------|
| Inner | slow | low-level system stats (CPU, RAM, uptime) |
| Middle | medium | data processing / environment (weather, network) |
| Outer | fast | critical data & alerts |

**Behavior & animation**
- Each ring rotates independently; speed scales with that tier's activity.
- **Data-flow pulses** travel center → edge along radial spokes to show throughput.
- Gradient colour shifts with complexity (accent → yellow/orange when busy/critical).
- **Idle**: gentle rotation, faint accent glow.
- Voice/touch reactive (a spoken command sends a visible pulse around the outer ring).

**Qt implementation**
- New `RingSystem` widget (or fold into `ArcReactor`): three `drawArc` ring groups at
  radii r1<r2<r3, each with its own rotation accumulator and segment pattern.
- Pulses = small bright arcs spawned at the core, animated outward and faded.
- Feed real values: inner ring ticks from `psutil`, middle from a weather/net poller,
  outer from an alert queue.

**Status** — 🔶 reactor has two counter-rotating rings + tick ring. Missing: three
*distinct* data-bound rings, center→edge data pulses, complexity-driven colour/speed.

---

## 3. Floating Text Panels & Data Blocks

**Visual** — translucent glass rectangles in a loose grid around the orb; geometric
font in white/accent; thin glowing borders.

**Behavior & animation**
- **Float**: each panel drifts on a slow lissajous (±3–5 px, 6–12 s period) so the field
  feels alive without distracting.
- **Hover**: a status/detail bar slides in; border brightens.
- **Alert**: error/warn panels turn yellow→red with an animated border-pulse.
- **Enter/exit**: fade + slight scale when panels appear/disappear (mode changes,
  spawned cards).

**Qt implementation**
- `Panel` already supports header + body + glow. Add: a float driver (one `QTimer`
  nudging `move()` on a per-panel phase), `set_alert(level)` (swaps border colour +
  starts a pulse animation), opacity via `QGraphicsOpacityEffect` for fades.
- Keep float subtle — disable it in dense Work mode if it harms readability.

**Status** — ✅ translucent glowing panels, headers, live data. 🔶 float motion,
hover detail bar, alert pulse, fade in/out are new.

---

## 4. Voice & Sound Feedback

**Voice** — calm, authoritative, British. → **ElevenLabs** (planned, `core/voice.py`
already abstracts TTS; swap edge-tts backend for an ElevenLabs British voice).

**Sound design** (new, via `pygame.mixer` channels):
- **Harmonic hum** under responses, amplitude tracking the orb pulse.
- **Success chime** — short rising major triad on confirmation.
- **Error buzz** — low detuned tone synced with a red orb pulse.
- **Listen cue** — soft blip when the mic opens.

**Synchronization** — drive audio from the same state the orb reads, so a "thinking"
state raises both hum intensity and orb brightness together. Route through the
`JarvisWorker` state signals so UI + sound + voice stay in lockstep.

**Status** — 🔶 TTS (edge-tts) + STT live. 🆕 British ElevenLabs voice, hum/chime/buzz
sound bed, audio↔visual sync.

---

## 5. Real-Time Data Visualization

**Visual** — animated graphs/metrics: energy/CPU, "health" diagnostics, environment.
Cyan/accent when healthy → orange/red with warning pulse when degraded.

**Behavior**
- **Listening waveform** reacts to live mic amplitude (today it's simulated).
- Graphs update on a poll + on command ("show CPU" spikes the relevant graph).
- **Weather as radar** — a sweeping radar icon on the middle ring; precip blips.

**Qt implementation**
- Small custom spark-line / radial-gauge widgets painted from rolling `deque`s.
- A `Telemetry` poller (psutil + weather API) emits values on a timer; widgets subscribe.
- Wire the real mic level from `core/voice.py` into the orb's waveform.

**Status** — 🔶 SYSTEMS panel (CPU/RAM/uptime), reactor waveform (simulated). 🆕 real
mic-driven waveform, sparkline graphs, health colour-coding, weather radar.

---

## 6. Modes — global state layer

One active mode at a time. A mode sets **accent colour + HUD density + layout +
which data shows**. The **orb persists across all modes**, adapting colour/behavior.
Mode is switchable via an always-present selector and by voice ("Jarvis, chill mode").

### 6a. Chill — white `#e8f4f8`
- Minimal, ambient, console-idle feel. Rings + dense panels **fade out**.
- **Background**: looping ambient video (fireplace), swappable. (`QMediaPlayer` + `QVideoWidget`.)
- **Foreground**: large clock + a now-playing card (album art, track, progress).
  - Now-playing source: macOS via AppleScript to Music/Spotify; Windows via SMTC.
- **Orb**: slow **white breathing** pulse, quiet.

### 6b. Work — red `#ff3b3b`
- Dense, focused HUD: full rings + all panels active. Alert, sharp, urgent motion.
- **Panels**: job-prep stats, to-do, CS news, world news, India news. (folds in today's
  MAIN + JOB-PREP data; add news via a feeds poller.)
- **Orb/rings**: red theme, crisper/faster motion.

### 6c. Creative — green `#3effa3`
- Open, conversational, lots of breathing room. Dense data → a central **idea canvas /
  running brainstorm thread**.
- **Panels** become spawnable **idea cards**: create, group, expand.
- **Orb**: green, fluid, playful pulse.

### Mode transitions (cinematic)
1. Orb **puff** + brighten.
2. New accent **bleeds outward** from the core across rings → panels → glow
   (animate a `QColor` interpolation over ~0.8 s; regenerate QSS with the new accent).
3. Panels **rearrange** into the new layout (old fade/scale out, new fade in).
4. Background + sound bed crossfade.

**Status** — 🔶 two views (MAIN, JOB-PREP) ≈ a proto of Work. 🆕 the mode system,
Chill + Creative, accent theming, cinematic transitions.

---

## 7. Theming & Mode architecture (the technical spine)

Everything above hangs off one new system. Build this first.

- **`hud/theme.py`** — a `Theme` dataclass per mode: `accent`, `accent_bright`,
  `secondary`, `text`, `density` (`minimal|dense|open`), `layout_id`, `background`.
  Registry: `MODES = {"chill": ..., "work": ..., "creative": ...}`.
- **`ThemeState(QObject)`** — holds the active mode; `mode_changed = Signal(str)`;
  `accent_changed = Signal(QColor)` fired continuously during a transition tween.
- **Propagation** — on mode change:
  - `ArcReactor.set_accent()` + ring colours tween via a `QVariantAnimation` over QColor.
  - `style.build_stylesheet(accent)` regenerates QSS; `app.setStyleSheet(...)` re-applies
    (panels, borders, tabs all key off the accent).
  - `HudBackground`/`HudOverlay` repaint with the new accent.
  - Panel glow effects recoloured.
- **Layout switching** — a top-level `QStackedWidget` with one page per mode
  (`ChillView`, `WorkView`, `CreativeView`). The **orb is a single persistent widget**
  rendered in a centered overlay above the stack so it survives page swaps and animates
  through the transition.
- **Voice control** — add a `set_mode` tool so the brain can switch modes
  ("chill mode" → `set_mode("chill")`), and a mode selector widget in the title bar.

Refactor note: today colours are hardcoded in `hud/style.py` and `hud/widgets.py`.
Step one is routing them all through `ThemeState.accent` so a single source drives the
whole HUD.

---

## 8. Build phases (mapped to the codebase)

1. **Theming spine** — `theme.py` + `ThemeState`, route existing cyan through it,
   `build_stylesheet(accent)`. No visible change yet; everything becomes themeable.
2. **Mode shell** — `QStackedWidget` of WorkView (current HUD) + stub Chill/Creative;
   mode selector + `set_mode` voice tool + cinematic accent-bleed transition.
3. **Orb upgrade** — persistent centered orb, 1.5 s breathing, intensity hue-shift,
   puff+ripple, rim filaments, three data-bound rings with center→edge pulses.
4. **Chill mode** — ambient video bg, big clock, now-playing card.
5. **Creative mode** — idea canvas + spawnable cards.
6. **Work mode data** — news feeds (CS/world/India) + fold in job-prep/to-do.
7. **Sound + voice** — ElevenLabs British voice, hum/chime/buzz sound bed, audio↔orb sync.
8. **Data-viz** — real mic waveform, sparkline gauges, health colour-coding, weather radar.

Each phase is independently shippable and leaves the HUD working.

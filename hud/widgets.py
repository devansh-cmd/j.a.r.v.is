"""Custom HUD widgets: ArcReactor, Panel, TitleBar, StatusBar, WaveformRing."""
from __future__ import annotations

import math
from datetime import datetime

from PySide6.QtCore import (
    QPoint,
    QPointF,
    QRectF,
    QSize,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QRadialGradient,
)
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from hud.style import (
    ACCENT,
    ACCENT_AMBER,
    ACCENT_GREEN,
    ACCENT_RED,
    BG_DARK,
    BG_DARKEST,
    BORDER_BRIGHT,
    TEXT,
    TEXT_BRIGHT,
    TEXT_DIM,
)
from hud.theme import MODES


# ─────────────────────────────────────────────────────────────────────────────
# Arc Reactor — the centerpiece. State-driven concentric rings + pulse + waveform.
# ─────────────────────────────────────────────────────────────────────────────

STATE_IDLE = "IDLE"
STATE_LISTENING = "LISTENING"
STATE_THINKING = "THINKING"
STATE_SPEAKING = "SPEAKING"
STATE_ERROR = "ERROR"

_STATE_COLORS = {
    STATE_IDLE: QColor(0, 212, 255),
    STATE_LISTENING: QColor(95, 239, 255),
    STATE_THINKING: QColor(255, 170, 60),
    STATE_SPEAKING: QColor(62, 255, 163),
    STATE_ERROR: QColor(255, 48, 112),
}

_STATE_RATES = {
    STATE_IDLE: 0.4,
    STATE_LISTENING: 1.4,
    STATE_THINKING: 2.5,
    STATE_SPEAKING: 1.8,
    STATE_ERROR: 1.0,
}


def _lerp(c1: QColor, c2: QColor, t: float) -> QColor:
    return QColor(
        int(c1.red() + (c2.red() - c1.red()) * t),
        int(c1.green() + (c2.green() - c1.green()) * t),
        int(c1.blue() + (c2.blue() - c1.blue()) * t),
    )


def _warm(base: QColor, intensity: float) -> QColor:
    """Shift a colour toward violet (mid intensity) then yellow (high)."""
    if intensity <= 0.01:
        return QColor(base)
    violet = QColor(165, 95, 255)
    yellow = QColor(255, 215, 80)
    if intensity <= 0.5:
        return _lerp(base, violet, intensity / 0.5)
    return _lerp(violet, yellow, (intensity - 0.5) / 0.5)


class HudBackground(QWidget):
    """Painted backdrop — deep radial wash + faint tech grid that fades at the edges.

    Sits behind the content (which is transparent / translucent), so the grid shows
    through the gaps and through the panels.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._accent = QColor(21, 232, 255)

    def set_accent(self, color) -> None:
        self._accent = QColor(color)
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        a = self._accent

        # Deep noir base wash
        base = QRadialGradient(w / 2, h * 0.42, max(w, h) * 0.85)
        base.setColorAt(0.0, QColor(11, 15, 32))
        base.setColorAt(1.0, QColor(3, 4, 12))
        p.fillRect(self.rect(), QBrush(base))

        # Neon city glows — accent (cyan) from the top, magenta from the bottom
        cyan = QRadialGradient(w * 0.5, h * 0.16, max(w, h) * 0.6)
        cyan.setColorAt(0.0, QColor(a.red(), a.green(), a.blue(), 34))
        cyan.setColorAt(1.0, QColor(a.red(), a.green(), a.blue(), 0))
        p.fillRect(self.rect(), QBrush(cyan))
        mag = QRadialGradient(w * 0.5, h * 1.02, max(w, h) * 0.62)
        mag.setColorAt(0.0, QColor(255, 45, 149, 42))
        mag.setColorAt(1.0, QColor(255, 45, 149, 0))
        p.fillRect(self.rect(), QBrush(mag))

        # Tech grid
        pen = QPen(QColor(a.red(), a.green(), a.blue(), 14))
        pen.setWidth(1)
        p.setPen(pen)
        step = 42
        for x in range(0, w, step):
            p.drawLine(x, 0, x, h)
        for y in range(0, h, step):
            p.drawLine(0, y, w, y)

        # Vignette to deepen the noir toward the edges
        vig = QRadialGradient(w / 2, h / 2, max(w, h) * 0.62)
        vig.setColorAt(0.0, QColor(3, 4, 12, 0))
        vig.setColorAt(0.62, QColor(3, 4, 12, 0))
        vig.setColorAt(1.0, QColor(3, 4, 12, 215))
        p.fillRect(self.rect(), QBrush(vig))
        p.end()


class HudOverlay(QWidget):
    """Transparent top layer: a scan line sweeping down + corner brackets.

    Drawn above everything (panels, bars) so the scan line passes over the whole
    HUD like the concept. Transparent to mouse so it never intercepts clicks.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self._accent = QColor(21, 232, 255)
        self._scan = -0.05
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(33)

    def set_accent(self, color) -> None:
        self._accent = QColor(color)

    def _tick(self) -> None:
        self._scan += 0.0018
        if self._scan > 1.1:
            self._scan = -0.08
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        a = self._accent

        # Scan line
        y = self._scan * h
        if 0 <= y <= h:
            grad = QLinearGradient(0, y, w, y)
            grad.setColorAt(0.0, QColor(a.red(), a.green(), a.blue(), 0))
            grad.setColorAt(0.5, QColor(a.red(), a.green(), a.blue(), 110))
            grad.setColorAt(1.0, QColor(a.red(), a.green(), a.blue(), 0))
            pen = QPen(QBrush(grad), 2)
            p.setPen(pen)
            p.drawLine(0, int(y), w, int(y))

        # Corner brackets — hot magenta for the cyberpunk dual-tone
        pen = QPen(QColor(255, 45, 149, 210))
        pen.setWidth(2)
        p.setPen(pen)
        seg, m = 22, 9
        p.drawLine(m, m, m + seg, m); p.drawLine(m, m, m, m + seg)               # TL
        p.drawLine(w - m - seg, m, w - m, m); p.drawLine(w - m, m, w - m, m + seg)  # TR
        p.drawLine(m, h - m, m + seg, h - m); p.drawLine(m, h - m, m, h - m - seg)  # BL
        p.drawLine(w - m - seg, h - m, w - m, h - m); p.drawLine(w - m, h - m, w - m, h - m - seg)  # BR
        p.end()


class ArcReactor(QWidget):
    """Central animated reactor. Concentric rings, pulsing core, waveform ring.

    State drives color + animation speed. Rendered with QPainter; ~60fps.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumSize(380, 380)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._state = STATE_IDLE
        self._accent = QColor(21, 232, 255)
        self._phase = 0.0
        self._elapsed = 0.0          # seconds, for the 1.5s breathing cadence
        self._rotation = 0.0
        self._intensity = 0.0        # 0..1 task intensity → hue warmth + brightness
        self._puff = 0.0             # 0..1 one-shot "puff" on command
        self._ripples: list[float] = []      # expanding energy rings (progress 0..1)
        self._data_pulses: list[list[float]] = []  # [angle, progress] center→edge
        self._pulse_accum = 0
        self._wave = [0.0] * 48
        self._wave_targets = [0.0] * 48
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(33)

    def set_state(self, state: str) -> None:
        if state == self._state:
            return
        self._state = state
        self.update()

    def set_accent(self, color) -> None:
        self._accent = QColor(color)
        self.update()

    def set_intensity(self, value: float) -> None:
        self._intensity = max(0.0, min(1.0, float(value)))

    def pulse_puff(self) -> None:
        """Kick a one-shot expand + energy ripple (call when a command lands)."""
        self._puff = 1.0
        self._ripples.append(0.0)
        self.update()

    def _tick(self) -> None:
        import random

        rate = _STATE_RATES.get(self._state, 1.0)
        self._phase += 0.06 * rate
        self._elapsed += 0.033
        self._rotation += 0.4 * rate
        if self._rotation > 360:
            self._rotation -= 360

        if self._puff > 0:
            self._puff = max(0.0, self._puff - 0.045)
        self._ripples = [r + 0.018 for r in self._ripples if r < 1.0]

        self._pulse_accum += 1
        if self._pulse_accum >= max(4, int(14 / rate)):
            self._pulse_accum = 0
            self._data_pulses.append([random.uniform(0, 2 * math.pi), 0.0])
        nxt = []
        for ang, prog in self._data_pulses:
            prog += 0.03 * (0.6 + rate * 0.5)
            if prog < 1.0:
                nxt.append([ang, prog])
        self._data_pulses = nxt

        self._update_wave()
        self.update()

    def _update_wave(self) -> None:
        import random

        state = self._state
        for i in range(len(self._wave)):
            if state == STATE_LISTENING:
                base = 0.4 + 0.4 * abs(math.sin(self._phase * 1.2 + i * 0.3))
                target = base + random.uniform(-0.15, 0.15)
            elif state == STATE_SPEAKING:
                base = 0.5 + 0.4 * abs(math.sin(self._phase * 1.8 + i * 0.5))
                target = base + random.uniform(-0.1, 0.1)
            elif state == STATE_THINKING:
                base = 0.3 + 0.2 * math.sin(self._phase * 0.8 + i * 0.4)
                target = max(0.1, base)
            elif state == STATE_ERROR:
                base = 0.6 + 0.3 * math.sin(self._phase * 3.0)
                target = base
            else:  # IDLE
                target = 0.15 + 0.08 * math.sin(self._phase * 0.4 + i * 0.2)
            self._wave_targets[i] = max(0.0, min(1.0, target))
            self._wave[i] += (self._wave_targets[i] - self._wave[i]) * 0.25

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        side = min(self.width(), self.height())
        cx = self.width() / 2
        cy = self.height() / 2
        r_outer = side * 0.46
        r_wave_inner = side * 0.38
        r_ring = side * 0.30
        r_core = side * 0.16

        if self._state == STATE_THINKING:
            color = QColor(255, 170, 60)   # amber — universal "busy"
        elif self._state == STATE_ERROR:
            color = QColor(255, 48, 112)   # red — universal "error"
        else:
            color = QColor(self._accent)   # idle / listening / speaking → mode accent

        # Outermost faint ring
        pen = QPen(QColor(color.red(), color.green(), color.blue(), 50))
        pen.setWidth(1)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QPointF(cx, cy), r_outer, r_outer)

        # Fine tick ring — 60 ticks, every 5th brighter, slow drift
        p.save()
        p.translate(cx, cy)
        p.rotate(self._rotation * 0.25)
        for i in range(60):
            ang = (i / 60) * 2 * math.pi
            major = i % 5 == 0
            r1 = r_outer * 0.92
            r2 = r_outer * (0.80 if major else 0.86)
            tick_pen = QPen(
                QColor(color.red(), color.green(), color.blue(), 210 if major else 90)
            )
            tick_pen.setWidth(2 if major else 1)
            p.setPen(tick_pen)
            p.drawLine(
                QPointF(r1 * math.cos(ang), r1 * math.sin(ang)),
                QPointF(r2 * math.cos(ang), r2 * math.sin(ang)),
            )
        p.restore()

        # Crosshair stubs at N / E / S / W
        ch_pen = QPen(QColor(color.red(), color.green(), color.blue(), 70))
        ch_pen.setWidth(1)
        p.setPen(ch_pen)
        gap = r_ring * 1.18
        reach = r_outer * 0.96
        p.drawLine(QPointF(cx - reach, cy), QPointF(cx - gap, cy))
        p.drawLine(QPointF(cx + gap, cy), QPointF(cx + reach, cy))
        p.drawLine(QPointF(cx, cy - reach), QPointF(cx, cy - gap))
        p.drawLine(QPointF(cx, cy + gap), QPointF(cx, cy + reach))

        # Waveform ring (bars radiating from center)
        bars = len(self._wave)
        for i in range(bars):
            angle = (i / bars) * 2 * math.pi - math.pi / 2
            amp = self._wave[i]
            inner_r = r_wave_inner * 0.9
            outer_r = r_wave_inner * (0.9 + amp * 0.18)
            x1 = cx + inner_r * math.cos(angle)
            y1 = cy + inner_r * math.sin(angle)
            x2 = cx + outer_r * math.cos(angle)
            y2 = cy + outer_r * math.sin(angle)
            alpha = int(120 + 135 * amp)
            bar_color = QColor(color.red(), color.green(), color.blue(), alpha)
            pen = QPen(bar_color)
            pen.setWidth(2)
            pen.setCapStyle(Qt.RoundCap)
            p.setPen(pen)
            p.drawLine(QPointF(x1, y1), QPointF(x2, y2))

        # Three concentric data rings — inner (slow), middle (medium), outer (fast)
        col = (color.red(), color.green(), color.blue())
        for r_mul, segs, span_div, spd, width, alpha in (
            (0.78, 8, 3.0, 0.5, 1, 130),    # inner  — slow, low-level system stats
            (1.00, 12, 2.4, 1.0, 2, 190),   # middle — medium, data processing
            (1.22, 16, 4.0, 1.8, 2, 230),   # outer  — fast, critical / alerts
        ):
            p.save()
            p.translate(cx, cy)
            p.rotate(self._rotation * spd)
            pen = QPen(QColor(*col, alpha))
            pen.setWidth(width)
            p.setPen(pen)
            r = r_ring * r_mul
            for i in range(segs):
                start = (i / segs) * 360 * 16
                span = (360 / segs / span_div) * 16
                p.drawArc(QRectF(-r, -r, 2 * r, 2 * r), int(start), int(span))
            p.restore()

        # Data pulses travelling from the core out to the rings
        r_pulse_max = r_ring * 1.22
        for ang, prog in self._data_pulses:
            rr = r_core + (r_pulse_max - r_core) * prog
            px = cx + rr * math.cos(ang)
            py = cy + rr * math.sin(ang)
            a = int(230 * (1.0 - prog * 0.5))
            tr = max(r_core, rr - 9)
            tx = cx + tr * math.cos(ang)
            ty = cy + tr * math.sin(ang)
            trail = QPen(QColor(*col, max(0, a // 2)))
            trail.setWidth(2)
            trail.setCapStyle(Qt.RoundCap)
            p.setPen(trail)
            p.drawLine(QPointF(tx, ty), QPointF(px, py))
            head = QPen(QColor(255, 255, 255, a))
            head.setWidth(3)
            head.setCapStyle(Qt.RoundCap)
            p.setPen(head)
            p.drawPoint(QPointF(px, py))

        # Core glow — 1.5s breathing + puff expansion + intensity warmth
        breath = math.sin(2 * math.pi * self._elapsed / 1.5)
        pulse = 1.0 + 0.05 * breath + self._puff * 0.18
        hot = _warm(color, self._intensity)  # accent → violet → yellow with intensity
        r_glow = r_core * pulse * (1.6 + 0.35 * self._intensity)
        glow = QRadialGradient(QPointF(cx, cy), r_glow)
        glow.setColorAt(0.0, QColor(255, 255, 255, 235))
        glow.setColorAt(0.22, QColor(hot.red(), hot.green(), hot.blue(), 210))
        glow.setColorAt(0.6, QColor(hot.red(), hot.green(), hot.blue(), 80))
        glow.setColorAt(1.0, QColor(hot.red(), hot.green(), hot.blue(), 0))
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(glow))
        p.drawEllipse(QPointF(cx, cy), r_glow, r_glow)

        # Energy ripples from a puff
        for prog in self._ripples:
            rr = r_core + (r_outer - r_core) * prog
            a = int(170 * (1.0 - prog))
            rp = QPen(QColor(color.red(), color.green(), color.blue(), a))
            rp.setWidth(2)
            p.setPen(rp)
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(QPointF(cx, cy), rr, rr)

        # Inner core ring
        r_inner_ring = r_core * pulse
        pen = QPen(QColor(255, 255, 255, 220))
        pen.setWidth(2)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QPointF(cx, cy), r_inner_ring, r_inner_ring)

        # Tiny inner notches around the core
        p.save()
        p.translate(cx, cy)
        p.rotate(self._rotation * 1.4)
        pen = QPen(QColor(color.red(), color.green(), color.blue(), 220))
        pen.setWidth(2)
        p.setPen(pen)
        notches = 6
        for i in range(notches):
            a = (i / notches) * 2 * math.pi
            x1 = (r_inner_ring * 0.55) * math.cos(a)
            y1 = (r_inner_ring * 0.55) * math.sin(a)
            x2 = (r_inner_ring * 0.85) * math.cos(a)
            y2 = (r_inner_ring * 0.85) * math.sin(a)
            p.drawLine(QPointF(x1, y1), QPointF(x2, y2))
        p.restore()

        # State label below the reactor
        p.setFont(QFont("Consolas", 9, QFont.Bold))
        p.setPen(QColor(color.red(), color.green(), color.blue(), 220))
        label_rect = QRectF(cx - 100, cy + r_outer + 8, 200, 18)
        p.drawText(label_rect, Qt.AlignCenter, f"◇  {self._state}  ◇")

        p.end()


# ─────────────────────────────────────────────────────────────────────────────
# Panel — bordered card with header + scrollable body
# ─────────────────────────────────────────────────────────────────────────────


class Panel(QFrame):
    def __init__(self, title: str, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("panel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QLabel(f"◇  {title}")
        header.setObjectName("panelHeader")
        layout.addWidget(header)

        self.body = QTextEdit()
        self.body.setObjectName("panelBody")
        self.body.setReadOnly(True)
        self.body.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.body.setFrameStyle(QFrame.NoFrame)
        layout.addWidget(self.body, 1)

    def append_line(self, text: str, color: str | None = None, indent: int = 0) -> None:
        prefix = "&nbsp;" * (indent * 2)
        if color:
            html = f'<div style="margin: 2px 0;">{prefix}<span style="color:{color};">{_html(text)}</span></div>'
        else:
            html = f'<div style="margin: 2px 0;">{prefix}{_html(text)}</div>'
        self.body.append(html)
        bar = self.body.verticalScrollBar()
        bar.setValue(bar.maximum())

    def set_text(self, text: str, color: str | None = None) -> None:
        if color:
            self.body.setHtml(f'<div style="color:{color}; line-height: 1.6;">{_html(text)}</div>')
        else:
            self.body.setHtml(f'<div style="line-height: 1.6;">{_html(text)}</div>')

    def clear(self) -> None:
        self.body.clear()


def _html(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\n", "<br>")
    )


class TabbedPanel(QFrame):
    """A panel with a row of switchable tabs, each holding a scrollable body.

    Used for the right-column trackers (TO-DO / DSA / PREP). Each tab button
    can carry a small badge (e.g. a count). `body(name)` returns the QTextEdit
    for a tab so the window can set HTML into it.
    """

    def __init__(self, tabs: list[str], parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("panel")
        self._names = list(tabs)
        self._base = {name: name for name in tabs}
        self._buttons: dict[str, QPushButton] = {}
        self._bodies: dict[str, QTextEdit] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QWidget()
        header.setObjectName("tabHeader")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(0)

        self._stack = QStackedWidget()

        for i, name in enumerate(tabs):
            btn = QPushButton(name)
            btn.setObjectName("tabBtn")
            btn.setCheckable(True)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            btn.clicked.connect(lambda _checked=False, idx=i: self._switch(idx))
            hl.addWidget(btn, 1)
            self._buttons[name] = btn

            body = QTextEdit()
            body.setObjectName("panelBody")
            body.setReadOnly(True)
            body.setFrameStyle(QFrame.NoFrame)
            self._bodies[name] = body
            self._stack.addWidget(body)

        layout.addWidget(header)
        layout.addWidget(self._stack, 1)
        self._switch(0)

    def _switch(self, idx: int) -> None:
        self._stack.setCurrentIndex(idx)
        for i, name in enumerate(self._names):
            self._buttons[name].setChecked(i == idx)

    def body(self, name: str) -> QTextEdit:
        return self._bodies[name]

    def set_badge(self, name: str, badge: str) -> None:
        base = self._base[name]
        self._buttons[name].setText(f"{base}  {badge}" if badge else base)


class JobPrepView(QWidget):
    """Full-screen dashboard combining the DSA tracker and interview-prep checklist.

    Brought up from the title-bar nav. `dsa` and `prep` are Panels whose bodies
    the window renders detailed HTML into.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        banner = QLabel("⬡  JOB PREP  ·  DSA GRIND & INTERVIEW READINESS")
        banner.setObjectName("viewBanner")
        layout.addWidget(banner)

        cols = QHBoxLayout()
        cols.setSpacing(10)
        self.dsa = Panel("DSA · PROBLEM TRACKER")
        self.prep = Panel("INTERVIEW PREP CHECKLIST")
        cols.addWidget(self.dsa, 1)
        cols.addWidget(self.prep, 1)
        layout.addLayout(cols, 1)


# ─────────────────────────────────────────────────────────────────────────────
# Title bar — draggable, with clock and window controls
# ─────────────────────────────────────────────────────────────────────────────


class TitleBar(QFrame):
    minimize_clicked = Signal()
    close_clicked = Signal()
    view_changed = Signal(str)   # "main" | "jobprep"
    mode_selected = Signal(str)  # "default" | "chill" | "work" | "creative"

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("titleBar")
        self.setFixedHeight(44)
        self._drag_offset: QPoint | None = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        title = QLabel("◆  J . A . R . V . I . S")
        title.setObjectName("title")
        layout.addWidget(title)

        # View navigation
        self._nav: dict[str, QPushButton] = {}
        for key, label in (("main", "◆ MAIN"), ("jobprep", "⬡ JOB PREP")):
            btn = QPushButton(label)
            btn.setObjectName("navBtn")
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _checked=False, k=key: self.set_view(k))
            layout.addWidget(btn)
            self._nav[key] = btn
        self._nav["main"].setChecked(True)

        layout.addStretch(1)

        # Mode selector — switches theme / density / layout
        self._mode_btns: dict[str, QPushButton] = {}
        for key, theme in MODES.items():
            btn = QPushButton(theme.label)
            btn.setObjectName("modeBtn")
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(
                f"QPushButton#modeBtn:checked {{ color: {theme.accent}; "
                f"border: 1px solid {theme.accent}; }}"
            )
            btn.clicked.connect(lambda _c=False, k=key: self.mode_selected.emit(k))
            layout.addWidget(btn)
            self._mode_btns[key] = btn
        self._mode_btns["default"].setChecked(True)

        self.clock = QLabel("--:--:--")
        self.clock.setObjectName("clock")
        layout.addWidget(self.clock)

        min_btn = QPushButton("—")
        min_btn.setObjectName("winBtn")
        min_btn.clicked.connect(self.minimize_clicked.emit)
        layout.addWidget(min_btn)

        close_btn = QPushButton("✕")
        close_btn.setObjectName("winBtn")
        close_btn.setProperty("class", "close")
        close_btn.setStyleSheet("QPushButton:hover { background-color: " + ACCENT_RED + "; color: white; }")
        close_btn.clicked.connect(self.close_clicked.emit)
        layout.addWidget(close_btn)

        timer = QTimer(self)
        timer.timeout.connect(self._tick_clock)
        timer.start(1000)
        self._tick_clock()

    def _tick_clock(self) -> None:
        self.clock.setText(datetime.now().strftime("%H : %M : %S"))

    def set_view(self, key: str) -> None:
        for k, btn in self._nav.items():
            btn.setChecked(k == key)
        self.view_changed.emit(key)

    def set_active_mode(self, key: str) -> None:
        for k, btn in self._mode_btns.items():
            btn.setChecked(k == key)

    # Drag the window
    def mousePressEvent(self, event):  # noqa: N802
        if event.button() == Qt.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.window().frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):  # noqa: N802
        if self._drag_offset is not None and event.buttons() & Qt.LeftButton:
            self.window().move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()

    def mouseReleaseEvent(self, event):  # noqa: N802
        self._drag_offset = None


# ─────────────────────────────────────────────────────────────────────────────
# Status bar — current state + listening indicator
# ─────────────────────────────────────────────────────────────────────────────


class StatusBar(QFrame):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("statusBar")
        self.setFixedHeight(36)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.label = QLabel("▸ READY")
        self.label.setObjectName("statusLabel")
        layout.addWidget(self.label)
        layout.addStretch(1)
        self.hint = QLabel("[ Esc to quit ]")
        self.hint.setObjectName("statusLabel")
        self.hint.setStyleSheet(f"color: {TEXT_DIM}; padding: 8px 18px;")
        layout.addWidget(self.hint)

    def set_state(self, state: str) -> None:
        colors = {
            STATE_IDLE: ACCENT,
            STATE_LISTENING: "#5fefff",
            STATE_THINKING: ACCENT_AMBER,
            STATE_SPEAKING: ACCENT_GREEN,
            STATE_ERROR: ACCENT_RED,
        }
        c = colors.get(state, ACCENT)
        self.label.setStyleSheet(f"color: {c}; padding: 8px 18px;")
        self.label.setText(f"▸ {state}")

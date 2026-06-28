"""Mode / theme state — the single source of truth for the HUD's accent colour.

A *mode* sets the accent colour (and, later, density + layout). Everything that
paints — the orb, background, overlay, panels, QSS chrome — keys off the active
mode's accent, so switching modes recolours the whole HUD. Layout swapping per
mode (Chill clock, Creative canvas, etc.) is built on top of this in later phases.
"""
from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QColor


@dataclass(frozen=True)
class Theme:
    name: str
    label: str
    accent: str         # primary accent hex
    accent_bright: str  # brighter accent hex
    density: str        # "minimal" | "dense" | "open"


# Mode registry. `default` is the standard cyan JARVIS look; the three named
# modes match the UI spec (Chill / Work / Creative).
MODES: dict[str, Theme] = {
    "default":  Theme("default",  "JARVIS",   "#00d4ff", "#5fefff", "dense"),
    "chill":    Theme("chill",    "CHILL",    "#cfe8f5", "#ffffff", "minimal"),
    "work":     Theme("work",     "WORK",     "#ff3b3b", "#ff8a8a", "dense"),
    "creative": Theme("creative", "CREATIVE", "#3effa3", "#9bffd0", "open"),
}

DEFAULT_MODE = "default"


class ThemeState(QObject):
    """Holds the active mode and notifies listeners when it changes."""

    mode_changed = Signal(str)        # mode name
    accent_changed = Signal(QColor)   # new accent colour

    def __init__(self, mode: str = DEFAULT_MODE) -> None:
        super().__init__()
        self._mode = mode if mode in MODES else DEFAULT_MODE

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def theme(self) -> Theme:
        return MODES[self._mode]

    def accent(self) -> QColor:
        return QColor(self.theme.accent)

    def accent_bright(self) -> QColor:
        return QColor(self.theme.accent_bright)

    def set_mode(self, name: str) -> bool:
        """Switch mode. Returns True if it actually changed."""
        if name not in MODES or name == self._mode:
            return False
        self._mode = name
        self.mode_changed.emit(name)
        self.accent_changed.emit(self.accent())
        return True

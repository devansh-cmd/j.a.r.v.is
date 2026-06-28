"""HUD theme — palette + a themeable QSS generator.

`build_stylesheet(accent, accent_bright)` regenerates the whole stylesheet around a
given accent colour, so a mode switch can recolour the entire chrome. The module-level
constants below are the cyan defaults used when no mode override is active.
"""

# Fixed palette (mode-independent) — cyberpunk noir
BG_DARKEST = "#04060e"   # deep noir blue-black
BG_DARK = "#080b18"
BG_PANEL = "rgba(10, 14, 28, 205)"

TEXT_DIM = "#5a7a92"
TEXT = "#bfe9f5"
TEXT_BRIGHT = "#ffffff"

# Universal signal colours (used inside panels regardless of mode)
ACCENT_AMBER = "#ffb13c"
ACCENT_GREEN = "#2bf0b0"
ACCENT_RED = "#ff2d6b"

# Cyberpunk dual-tone — electric cyan primary, hot magenta secondary
NEON_MAGENTA = "#ff2d95"

# Default accent (electric cyan) — mode themes override these at runtime
ACCENT = "#15e8ff"
ACCENT_BRIGHT = "#7df9ff"
BORDER = "rgba(21, 232, 255, 70)"
BORDER_BRIGHT = "#15e8ff"
BORDER_DIM = "rgba(21, 232, 255, 40)"

FONT_MAIN = "Consolas"
FONT_DISPLAY = "Consolas"


def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _rgba(hexcolor: str, alpha: int) -> str:
    r, g, b = _hex_to_rgb(hexcolor)
    return f"rgba({r}, {g}, {b}, {alpha})"


def build_stylesheet(accent: str = ACCENT, accent_bright: str = ACCENT_BRIGHT) -> str:
    """Generate the full QSS around an accent colour."""
    border = _rgba(accent, 70)
    border_dim = _rgba(accent, 40)
    a18 = _rgba(accent, 18)
    a16 = _rgba(accent, 16)
    a14 = _rgba(accent, 14)
    a22 = _rgba(accent, 22)
    a28 = _rgba(accent, 28)
    a30 = _rgba(accent, 30)
    return f"""
QWidget {{
    background-color: transparent;
    color: {TEXT};
    font-family: {FONT_MAIN};
    font-size: 13px;
}}

QMainWindow, #rootBg {{
    background-color: {BG_DARKEST};
}}

#panel {{
    background-color: rgba(9, 13, 26, 175);
    border: 1px solid {border_dim};
    border-top: 2px solid {accent_bright};
    border-radius: 4px;
}}

#panelHeader {{
    color: {accent};
    font-size: 11px;
    font-weight: bold;
    letter-spacing: 3px;
    padding: 8px 14px;
    border-bottom: 1px solid {border_dim};
    background-color: {a18};
}}

#panelBody {{
    padding: 10px 14px;
    background-color: transparent;
}}

QTextEdit, QPlainTextEdit, QListWidget {{
    background-color: transparent;
    border: none;
    color: {TEXT};
    font-family: {FONT_MAIN};
    font-size: 12px;
    selection-background-color: {accent};
    selection-color: {BG_DARKEST};
}}

QScrollBar:vertical {{
    background: transparent;
    width: 6px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {border};
    border-radius: 3px;
    min-height: 24px;
}}
QScrollBar::handle:vertical:hover {{
    background: {accent};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}

#titleBar {{
    background-color: {BG_DARK};
    border-bottom: 1px solid {border};
}}

#title {{
    color: {accent};
    font-size: 14px;
    font-weight: bold;
    letter-spacing: 6px;
    padding: 0 18px;
}}

QPushButton#navBtn {{
    color: {TEXT_DIM};
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 3px;
    padding: 5px 16px;
    margin: 0 3px;
    font-size: 11px;
    font-weight: bold;
    letter-spacing: 3px;
}}
QPushButton#navBtn:hover {{
    color: {TEXT};
    background-color: {a16};
}}
QPushButton#navBtn:checked {{
    color: {accent_bright};
    border: 1px solid {border};
    background-color: {a28};
}}

QPushButton#modeBtn {{
    color: {TEXT_DIM};
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 3px;
    padding: 4px 11px;
    margin: 0 2px;
    font-size: 10px;
    font-weight: bold;
    letter-spacing: 2px;
}}
QPushButton#modeBtn:hover {{
    color: {TEXT};
    background-color: {a16};
}}
QPushButton#modeBtn:checked {{
    border: 1px solid {border};
    background-color: {a22};
}}

#viewBanner {{
    color: {accent};
    font-size: 12px;
    font-weight: bold;
    letter-spacing: 5px;
    padding: 6px 4px 10px;
}}

#clock {{
    color: {TEXT};
    font-size: 14px;
    letter-spacing: 2px;
    padding: 0 18px;
}}

QPushButton#winBtn {{
    color: {TEXT_DIM};
    background-color: transparent;
    border: none;
    font-size: 14px;
    min-width: 32px;
    min-height: 28px;
}}
QPushButton#winBtn:hover {{
    color: {accent};
    background-color: {a30};
}}
QPushButton#winBtnClose:hover {{
    color: {TEXT_BRIGHT};
    background-color: {ACCENT_RED};
}}

#statusBar {{
    background-color: {BG_DARK};
    border-top: 1px solid {border};
}}

#statusLabel {{
    color: {accent};
    font-size: 12px;
    letter-spacing: 4px;
    font-weight: bold;
    padding: 8px 18px;
}}

#inputBar {{
    background-color: {BG_PANEL};
    border-top: 1px solid {border_dim};
}}

QLineEdit#textInput {{
    background-color: rgba(0, 0, 0, 100);
    border: 1px solid {border_dim};
    border-radius: 4px;
    padding: 8px 14px;
    color: {TEXT_BRIGHT};
    font-family: {FONT_MAIN};
    font-size: 13px;
    selection-background-color: {accent};
}}
QLineEdit#textInput:focus {{
    border: 1px solid {accent};
}}

#tabHeader {{
    background-color: {a16};
    border-bottom: 1px solid {border_dim};
}}

QPushButton#tabBtn {{
    color: {TEXT_DIM};
    background-color: transparent;
    border: none;
    border-bottom: 2px solid transparent;
    padding: 8px 4px;
    font-size: 10px;
    font-weight: bold;
    letter-spacing: 2px;
}}
QPushButton#tabBtn:hover {{
    color: {TEXT};
    background-color: {a14};
}}
QPushButton#tabBtn:checked {{
    color: {accent};
    border-bottom: 2px solid {accent};
    background-color: {a22};
}}
"""


# Default cyan stylesheet (back-compat for code that imports STYLESHEET)
STYLESHEET = build_stylesheet()

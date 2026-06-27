"""HUD theme — color palette, fonts, QSS stylesheet."""

# Core palette
BG_DARKEST = "#01080d"
BG_DARK = "#02141c"
BG_PANEL = "rgba(8, 26, 36, 220)"
BG_PANEL_HOVER = "rgba(14, 36, 50, 230)"

BORDER = "rgba(0, 212, 255, 70)"
BORDER_BRIGHT = "#00d4ff"
BORDER_DIM = "rgba(0, 212, 255, 40)"

TEXT_DIM = "#4a7886"
TEXT = "#a8e8f0"
TEXT_BRIGHT = "#ffffff"

ACCENT = "#00d4ff"
ACCENT_BRIGHT = "#5fefff"
ACCENT_AMBER = "#ffaa3c"
ACCENT_GREEN = "#3effa3"
ACCENT_RED = "#ff3070"

FONT_MAIN = "Consolas"
FONT_DISPLAY = "Consolas"


STYLESHEET = f"""
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
    background-color: rgba(6, 22, 32, 160);
    border: 1px solid {BORDER_DIM};
    border-top: 2px solid {BORDER_BRIGHT};
    border-radius: 4px;
}}

#panelHeader {{
    color: {ACCENT};
    font-size: 11px;
    font-weight: bold;
    letter-spacing: 3px;
    padding: 8px 14px;
    border-bottom: 1px solid {BORDER_DIM};
    background-color: rgba(0, 212, 255, 18);
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
    selection-background-color: {ACCENT};
    selection-color: {BG_DARKEST};
}}

QScrollBar:vertical {{
    background: transparent;
    width: 6px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {BORDER};
    border-radius: 3px;
    min-height: 24px;
}}
QScrollBar::handle:vertical:hover {{
    background: {ACCENT};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}

#titleBar {{
    background-color: {BG_DARK};
    border-bottom: 1px solid {BORDER};
}}

#title {{
    color: {ACCENT};
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
    background-color: rgba(0, 212, 255, 16);
}}
QPushButton#navBtn:checked {{
    color: {ACCENT_BRIGHT};
    border: 1px solid {BORDER};
    background-color: rgba(0, 212, 255, 28);
}}

#viewBanner {{
    color: {ACCENT};
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
    color: {ACCENT};
    background-color: rgba(0, 212, 255, 30);
}}
QPushButton#winBtnClose:hover {{
    color: {TEXT_BRIGHT};
    background-color: {ACCENT_RED};
}}

#statusBar {{
    background-color: {BG_DARK};
    border-top: 1px solid {BORDER};
}}

#statusLabel {{
    color: {ACCENT};
    font-size: 12px;
    letter-spacing: 4px;
    font-weight: bold;
    padding: 8px 18px;
}}

#inputBar {{
    background-color: {BG_PANEL};
    border-top: 1px solid {BORDER_DIM};
}}

QLineEdit#textInput {{
    background-color: rgba(0, 0, 0, 100);
    border: 1px solid {BORDER_DIM};
    border-radius: 4px;
    padding: 8px 14px;
    color: {TEXT_BRIGHT};
    font-family: {FONT_MAIN};
    font-size: 13px;
    selection-background-color: {ACCENT};
}}
QLineEdit#textInput:focus {{
    border: 1px solid {ACCENT};
}}

#tabHeader {{
    background-color: rgba(0, 212, 255, 16);
    border-bottom: 1px solid {BORDER_DIM};
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
    background-color: rgba(0, 212, 255, 14);
}}
QPushButton#tabBtn:checked {{
    color: {ACCENT};
    border-bottom: 2px solid {ACCENT};
    background-color: rgba(0, 212, 255, 22);
}}
"""

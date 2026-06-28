"""Jarvis HUD — graphical voice assistant interface. Run: python jarvis_hud.py"""
from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from hud.window import JarvisHUD


def main() -> int:
    # Force UTF-8 console so debug prints with unicode never crash a turn on Windows.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    load_dotenv(Path(__file__).resolve().parent / ".env")  # works from any cwd
    app = QApplication(sys.argv)
    app.setApplicationName("Jarvis")
    app.setFont(QFont("Consolas", 10))
    window = JarvisHUD()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())

"""Jarvis HUD — graphical voice assistant interface. Run: python jarvis_hud.py"""
from __future__ import annotations

import sys

from dotenv import load_dotenv
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from hud.window import JarvisHUD


def main() -> int:
    load_dotenv()
    app = QApplication(sys.argv)
    app.setApplicationName("Jarvis")
    app.setFont(QFont("Consolas", 10))
    window = JarvisHUD()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())

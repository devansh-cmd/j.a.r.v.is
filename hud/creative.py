"""Creative mode layout — an open brainstorm canvas with spawnable idea cards.

Distinct from the dense Work/default layout: the orb sits up top, and the body is
a free canvas of idea cards you (or Jarvis) can add and clear. Green, breezy.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from hud.style import TEXT_BRIGHT, TEXT_DIM
from hud.widgets import ArcReactor


class IdeaCard(QFrame):
    def __init__(self, text: str, on_remove) -> None:
        super().__init__()
        self.setObjectName("panel")
        self.setMinimumSize(170, 78)
        v = QVBoxLayout(self)
        v.setContentsMargins(12, 9, 12, 11)
        v.setSpacing(6)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        tag = QLabel("◆ IDEA")
        tag.setStyleSheet(f"color:{TEXT_DIM}; font-size:9px; letter-spacing:2px; font-weight:bold;")
        row.addWidget(tag)
        row.addStretch(1)
        close = QPushButton("✕")
        close.setObjectName("winBtn")
        close.setFixedSize(20, 18)
        close.setCursor(Qt.PointingHandCursor)
        close.clicked.connect(lambda: on_remove(self))
        row.addWidget(close)
        v.addLayout(row)

        body = QLabel(text)
        body.setWordWrap(True)
        body.setStyleSheet(f"color:{TEXT_BRIGHT}; font-size:13px;")
        v.addWidget(body, 1)


class CreativeView(QWidget):
    """Brainstorm canvas: orb on top, a wrapping grid of idea cards below."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._cards: list[IdeaCard] = []
        self._cols = 3

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 14)
        root.setSpacing(10)

        banner = QLabel("✦  CREATIVE  ·  BRAINSTORM CANVAS")
        banner.setObjectName("viewBanner")
        root.addWidget(banner)

        # Persistent orb, sized modestly so the canvas has room
        self.reactor = ArcReactor()
        self.reactor.setMinimumSize(190, 190)
        self.reactor.setMaximumHeight(220)
        self.reactor.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        root.addWidget(self.reactor)

        # Scrollable canvas of idea cards
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._canvas = QWidget()
        self._grid = QGridLayout(self._canvas)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setSpacing(10)
        self._grid.setAlignment(Qt.AlignTop)
        scroll.setWidget(self._canvas)
        root.addWidget(scroll, 1)

        # Add-idea input
        self._input = QLineEdit()
        self._input.setObjectName("textInput")
        self._input.setPlaceholderText("drop an idea and press Enter…")
        self._input.returnPressed.connect(self._on_add)
        root.addWidget(self._input)

        for seed in (
            "Voice-switch modes hands-free",
            "Weather radar sweeping the rings",
            "Now-playing card for Chill mode",
        ):
            self.add_idea(seed)

    def _on_add(self) -> None:
        text = self._input.text().strip()
        if text:
            self.add_idea(text)
            self._input.clear()

    def add_idea(self, text: str) -> None:
        card = IdeaCard(text, self._remove)
        self._cards.append(card)
        self._relayout()

    def _remove(self, card: IdeaCard) -> None:
        if card in self._cards:
            self._cards.remove(card)
            card.setParent(None)
            self._relayout()

    def _relayout(self) -> None:
        while self._grid.count():
            self._grid.takeAt(0)
        for i, card in enumerate(self._cards):
            self._grid.addWidget(card, i // self._cols, i % self._cols)

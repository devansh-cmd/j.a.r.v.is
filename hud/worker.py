"""Background thread that owns Voice + Brain, emits Qt signals for the HUD.

Typed text and spoken speech both feed a single inbox queue. The mic runs on its
own daemon thread, so typing is never blocked by waiting on speech (the original
bug). While Jarvis is speaking, the mic is suppressed so it doesn't hear itself.
"""
from __future__ import annotations

import queue
import threading
import time
import traceback

from PySide6.QtCore import QThread, Signal

from core.brain import Brain
from core.voice import Voice
from hud.widgets import (
    STATE_ERROR,
    STATE_IDLE,
    STATE_SPEAKING,
    STATE_THINKING,
)


class JarvisWorker(QThread):
    state_changed = Signal(str)
    transcript = Signal(str)          # user input (typed or spoken)
    tool_started = Signal(str, dict)  # tool name, args
    response = Signal(str)            # final assistant text
    error = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._stop = False
        self.brain: Brain | None = None
        self.voice: Voice | None = None
        self._inbox: queue.Queue[str] = queue.Queue()
        self._speaking = False

    def submit_text(self, text: str) -> None:
        """Inject a typed message from the HUD input box."""
        self._inbox.put(text)

    def stop(self) -> None:
        self._stop = True
        self._inbox.put("__STOP__")

    def run(self) -> None:
        try:
            self.brain = Brain()
        except Exception as e:
            self.error.emit(f"Brain init failed: {e}")
            self.state_changed.emit(STATE_ERROR)
            return

        try:
            self.voice = Voice()
        except Exception as e:
            self.error.emit(f"Voice unavailable ({e}) — text-only mode")
            self.voice = None

        # Mic on its own thread, feeding the same inbox as typed text.
        if self.voice is not None:
            threading.Thread(target=self._voice_loop, daemon=True).start()

        self.state_changed.emit(STATE_IDLE)

        while not self._stop:
            user_text = self._inbox.get()
            if user_text == "__STOP__" or self._stop:
                return
            user_text = (user_text or "").strip()
            if not user_text:
                continue

            try:
                self.transcript.emit(user_text)
                self.state_changed.emit(STATE_THINKING)
                reply = self.brain.respond(user_text, on_tool=self._on_tool)
                self.response.emit(reply)
                if self.voice is not None:
                    self.state_changed.emit(STATE_SPEAKING)
                    self._speaking = True
                    try:
                        self.voice.speak(reply)
                    finally:
                        self._speaking = False
                self.state_changed.emit(STATE_IDLE)
            except Exception as e:
                self.error.emit(f"{type(e).__name__}: {e}\n{traceback.format_exc()}")
                self.state_changed.emit(STATE_ERROR)

    def _on_tool(self, name: str, args: dict) -> None:
        self.tool_started.emit(name, args)

    def _voice_loop(self) -> None:
        """Continuously listen on the mic; push recognized speech to the inbox."""
        while not self._stop:
            if self._speaking:
                time.sleep(0.2)
                continue
            try:
                text = self.voice.listen(timeout=4)
            except Exception:
                time.sleep(0.5)
                continue
            if text and not self._stop and not self._speaking:
                self._inbox.put(text)

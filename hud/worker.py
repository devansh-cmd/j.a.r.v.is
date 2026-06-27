"""Background thread that owns Voice + Brain, emits Qt signals for the HUD."""
from __future__ import annotations

import queue
import traceback

from PySide6.QtCore import QThread, Signal

from core.brain import Brain
from core.voice import Voice
from hud.widgets import (
    STATE_ERROR,
    STATE_IDLE,
    STATE_LISTENING,
    STATE_SPEAKING,
    STATE_THINKING,
)


class JarvisWorker(QThread):
    state_changed = Signal(str)
    transcript = Signal(str)         # user said text
    tool_started = Signal(str, dict)  # tool name, args
    response = Signal(str)            # final assistant text
    error = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._stop = False
        self.brain: Brain | None = None
        self.voice: Voice | None = None
        self._text_queue: queue.Queue[str] = queue.Queue()

    def submit_text(self, text: str) -> None:
        """Inject a text message instead of waiting on the mic."""
        self._text_queue.put(text)

    def stop(self) -> None:
        self._stop = True
        self._text_queue.put("__STOP__")  # unblock listen loop

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
            self.error.emit(f"Voice init failed: {e} — text-only mode")
            self.voice = None

        while not self._stop:
            try:
                user_text = self._wait_for_input()
                if user_text is None:
                    continue
                if self._stop:
                    return

                self.transcript.emit(user_text)
                self.state_changed.emit(STATE_THINKING)

                def on_tool(name: str, args: dict) -> None:
                    self.tool_started.emit(name, args)

                reply = self.brain.respond(user_text, on_tool=on_tool)
                self.response.emit(reply)

                if self.voice is not None:
                    self.state_changed.emit(STATE_SPEAKING)
                    self.voice.speak(reply)

                self.state_changed.emit(STATE_IDLE)
            except Exception as e:
                self.error.emit(f"{type(e).__name__}: {e}\n{traceback.format_exc()}")
                self.state_changed.emit(STATE_ERROR)

    def _wait_for_input(self) -> str | None:
        """Wait for either a voice phrase OR an injected text message."""
        # Check text queue first (non-blocking)
        try:
            text = self._text_queue.get_nowait()
            if text == "__STOP__":
                return None
            return text
        except queue.Empty:
            pass

        # If no voice, block on text queue
        if self.voice is None:
            text = self._text_queue.get()
            return None if text == "__STOP__" else text

        # Voice mode — listen with a short timeout so we can check the text queue
        self.state_changed.emit(STATE_LISTENING)
        text = self.voice.listen()
        return text  # may be None if STT didn't recognize

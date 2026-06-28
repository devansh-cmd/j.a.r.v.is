"""Speech-to-text (Google via SpeechRecognition) + text-to-speech (edge-tts + pygame)."""
from __future__ import annotations

import asyncio
import os
import tempfile
import threading
from contextlib import suppress

import edge_tts
import pygame
import speech_recognition as sr

from config import (
    AMBIENT_CALIBRATION_SECONDS,
    LISTEN_PHRASE_TIME_LIMIT,
    TTS_RATE,
    TTS_VOICE,
)


class Voice:
    def __init__(self) -> None:
        self.recognizer = sr.Recognizer()
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.9
        try:
            self.mic = sr.Microphone()
        except OSError as e:
            raise RuntimeError(
                "No microphone detected. Install PyAudio and check your input device."
            ) from e
        with self.mic as source:
            self.recognizer.adjust_for_ambient_noise(
                source, duration=AMBIENT_CALIBRATION_SECONDS
            )
        pygame.mixer.init()
        self._lock = threading.Lock()

    def listen(self, timeout: float | None = None) -> str | None:
        """Listen for a phrase. Returns transcribed text, or None on timeout/failure.

        `timeout` caps how long to wait for speech to *start* — pass a few seconds
        so a background listener can poll and re-check its stop flag.
        """
        try:
            with self.mic as source:
                audio = self.recognizer.listen(
                    source,
                    timeout=timeout,
                    phrase_time_limit=LISTEN_PHRASE_TIME_LIMIT,
                )
        except sr.WaitTimeoutError:
            return None
        try:
            return self.recognizer.recognize_google(audio)
        except sr.UnknownValueError:
            return None
        except sr.RequestError as e:
            print(f"[voice] STT request error: {e}")
            return None

    def speak(self, text: str) -> None:
        """Synthesize and play back text. Blocks until playback completes."""
        if not text.strip():
            return
        with self._lock:
            tmp_path = self._synthesize(text)
            try:
                pygame.mixer.music.load(tmp_path)
                pygame.mixer.music.play()
                clock = pygame.time.Clock()
                while pygame.mixer.music.get_busy():
                    clock.tick(20)
            finally:
                with suppress(Exception):
                    pygame.mixer.music.unload()
                with suppress(OSError):
                    os.unlink(tmp_path)

    @staticmethod
    def _synthesize(text: str) -> str:
        fd, path = tempfile.mkstemp(suffix=".mp3")
        os.close(fd)

        async def _run() -> None:
            communicate = edge_tts.Communicate(text, TTS_VOICE, rate=TTS_RATE)
            await communicate.save(path)

        asyncio.run(_run())
        return path

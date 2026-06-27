"""Render HUD offscreen with demo content and save a PNG."""
import os
import sys

os.environ["ANTHROPIC_API_KEY"] = "fake-for-screenshot"

from PySide6.QtCore import QCoreApplication, QEventLoop, Qt, QTimer
from PySide6.QtGui import QFont, QPixmap
from PySide6.QtWidgets import QApplication

app = QApplication(sys.argv)
app.setFont(QFont("Cascadia Code", 10))

from hud.window import JarvisHUD
from hud.widgets import STATE_LISTENING, STATE_THINKING

window = JarvisHUD()
window.show()

# Demo content
window.transcript.append_line("[14:32]  ▸ what's the weather in london", color="#ffffff")
window.transcript.append_line("[14:34]  ▸ open spotify and play something chill", color="#ffffff")
window.transcript.append_line("[14:37]  ▸ search youtube for veritasium new video", color="#ffffff")
window.transcript.append_line("[14:39]  ▸ remember that I prefer dark mode in everything", color="#ffffff")

window.actions.append_line("⚙ web_search", color="#00d4ff")
window.actions.append_line('{"query":"weather london"}', color="#4a7886", indent=2)
window.actions.append_line("⚙ shell", color="#00d4ff")
window.actions.append_line('{"command":"Start-Process spotify"}', color="#4a7886", indent=2)
window.actions.append_line("⚙ youtube_search", color="#00d4ff")
window.actions.append_line('{"query":"veritasium","max_results":3}', color="#4a7886", indent=2)
window.actions.append_line("⚙ memory_save", color="#00d4ff")
window.actions.append_line('{"content":"prefers dark mode","category":"preference"}', color="#4a7886", indent=2)

window.response.set_text(
    "Currently 12°C and overcast in London — light rain expected by evening. "
    "Spotify is launching now, queuing up your Lo-Fi playlist. "
    "The newest Veritasium upload is 'The Universe is Hostile to Computers' from 3 days ago. "
    "I've noted your preference for dark mode.",
    color="#a8e8f0",
)

# Force state for visual interest
window.reactor.set_state(STATE_LISTENING)
window.status.set_state(STATE_LISTENING)

# Let the event loop tick a few frames so animation reaches steady state
loop = QEventLoop()
QTimer.singleShot(500, loop.quit)
loop.exec()

# Grab and save
pixmap = window.grab()
out = "C:/Jarvis/_hud_preview.png"
pixmap.save(out)
print(f"saved {out}  ({pixmap.width()}x{pixmap.height()})")

window.worker.stop()
window.worker.wait(500)

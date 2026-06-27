"""Main HUD window — frameless dark grid with arc reactor centered, panels around."""
from __future__ import annotations

import json
import os
import time
from datetime import datetime

import psutil
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLineEdit,
    QMainWindow,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

import config
from core import dsa, memory, prep, tasks as task_store
from hud.style import (
    ACCENT,
    ACCENT_AMBER,
    ACCENT_BRIGHT,
    ACCENT_GREEN,
    ACCENT_RED,
    STYLESHEET,
    TEXT,
    TEXT_DIM,
    TEXT_BRIGHT,
)
from hud.widgets import (
    STATE_IDLE,
    STATE_LISTENING,
    STATE_THINKING,
    STATE_SPEAKING,
    STATE_ERROR,
    ArcReactor,
    JobPrepView,
    Panel,
    StatusBar,
    TitleBar,
)
from hud.worker import JarvisWorker


def _esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _bar(pct: int, fill: str, track: str = "rgba(0,212,255,28)") -> str:
    """A thin horizontal progress bar rendered as a 2-cell HTML table."""
    pct = max(0, min(100, int(pct)))
    if pct <= 0:
        cells = f'<td width="100%" style="background-color:{track}; font-size:1px;">&nbsp;</td>'
    elif pct >= 100:
        cells = f'<td width="100%" style="background-color:{fill}; font-size:1px;">&nbsp;</td>'
    else:
        cells = (
            f'<td width="{pct}%" style="background-color:{fill}; font-size:1px;">&nbsp;</td>'
            f'<td width="{100 - pct}%" style="background-color:{track}; font-size:1px;">&nbsp;</td>'
        )
    return (
        f'<table width="100%" cellspacing="0" cellpadding="0" style="margin-top:2px;">'
        f"<tr>{cells}</tr></table>"
    )


class JarvisHUD(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Jarvis")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowSystemMenuHint)
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.resize(1280, 820)
        self.setStyleSheet(STYLESHEET)

        self._started_at = time.time()
        self._tool_count = 0
        prep.ensure_seeded()

        root = QWidget()
        root.setObjectName("rootBg")
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Title bar
        self.title_bar = TitleBar()
        self.title_bar.close_clicked.connect(self.close)
        self.title_bar.minimize_clicked.connect(self.showMinimized)
        outer.addWidget(self.title_bar)

        # ── Stacked views: MAIN (assistant) + JOB PREP (dashboard) ──────────
        self.views = QStackedWidget()
        outer.addWidget(self.views, 1)
        self.title_bar.view_changed.connect(self._switch_view)

        # MAIN view — 3-column grid with reactor centered
        main_view = QWidget()
        grid = QGridLayout(main_view)
        grid.setContentsMargins(12, 12, 12, 12)
        grid.setSpacing(10)

        self.transcript = Panel("TRANSCRIPT")
        self.actions = Panel("ACTIONS")
        self.response = Panel("RESPONSE")
        self.systems = Panel("SYSTEMS")
        self.todo = Panel("TO-DO")
        self.reactor = ArcReactor()

        # ┌─────────────┬─────────────┬─────────────┐
        # │ TRANSCRIPT  │             │ TO-DO       │
        # ├─────────────┤   REACTOR   ├─────────────┤
        # │ ACTIONS     │             │ SYSTEMS     │
        # ├─────────────┴─────────────┴─────────────┤
        # │ RESPONSE  (full-width strip)            │
        # └─────────────────────────────────────────┘
        grid.addWidget(self.transcript, 0, 0)
        grid.addWidget(self.actions, 1, 0)
        grid.addWidget(self.reactor, 0, 1, 2, 1)
        grid.addWidget(self.todo, 0, 2)
        grid.addWidget(self.systems, 1, 2)
        grid.addWidget(self.response, 2, 0, 1, 3)
        grid.setColumnStretch(0, 3)
        grid.setColumnStretch(1, 4)
        grid.setColumnStretch(2, 3)
        grid.setRowStretch(0, 4)
        grid.setRowStretch(1, 2)
        grid.setRowStretch(2, 2)
        self.views.addWidget(main_view)

        # JOB PREP view — dedicated DSA + interview-prep dashboard
        self.jobprep = JobPrepView()
        self.views.addWidget(self.jobprep)

        # Text input fallback (always available)
        input_bar = QWidget()
        input_bar.setObjectName("inputBar")
        input_bar.setFixedHeight(54)
        input_layout = QHBoxLayout(input_bar)
        input_layout.setContentsMargins(14, 10, 14, 10)
        self.text_input = QLineEdit()
        self.text_input.setObjectName("textInput")
        self.text_input.setPlaceholderText("speak or type and press Enter…")
        self.text_input.returnPressed.connect(self._on_text_submit)
        input_layout.addWidget(self.text_input)
        outer.addWidget(input_bar)

        # Status bar
        self.status = StatusBar()
        outer.addWidget(self.status)

        # Start the worker
        self.worker = JarvisWorker()
        self.worker.state_changed.connect(self._on_state)
        self.worker.transcript.connect(self._on_transcript)
        self.worker.tool_started.connect(self._on_tool)
        self.worker.response.connect(self._on_response)
        self.worker.error.connect(self._on_error)
        self.worker.start()

        # Periodic system stats refresh
        self.stats_timer = QTimer(self)
        self.stats_timer.timeout.connect(self._refresh_systems)
        self.stats_timer.start(2000)
        self._refresh_systems()

        # Keyboard shortcuts
        QShortcut(QKeySequence("Esc"), self, activated=self.close)
        QShortcut(QKeySequence("Ctrl+1"), self, activated=lambda: self.title_bar.set_view("main"))
        QShortcut(QKeySequence("Ctrl+2"), self, activated=lambda: self.title_bar.set_view("jobprep"))
        QShortcut(QKeySequence("Ctrl+J"), self, activated=lambda: self.title_bar.set_view("jobprep"))

        # Boot message
        self.response.set_text(
            "Online and ready.\n\nSpeak into your microphone, or type below.",
            color=TEXT,
        )

    # ── Signal handlers ─────────────────────────────────────────────────────

    def _on_state(self, state: str) -> None:
        self.reactor.set_state(state)
        self.status.set_state(state)

    def _on_transcript(self, text: str) -> None:
        timestamp = datetime.now().strftime("%H:%M")
        self.transcript.append_line(f"[{timestamp}]  ▸ {text}", color=TEXT_BRIGHT)

    def _on_tool(self, name: str, args: dict) -> None:
        self._tool_count += 1
        arg_str = json.dumps(args, ensure_ascii=False)
        if len(arg_str) > 70:
            arg_str = arg_str[:69] + "…"
        self.actions.append_line(f"⚙ {name}", color=ACCENT)
        self.actions.append_line(arg_str, color=TEXT_DIM, indent=2)

    def _on_response(self, text: str) -> None:
        self.response.set_text(text, color=TEXT)
        self._refresh_trackers()

    def _on_error(self, msg: str) -> None:
        self.actions.append_line(f"✕ ERROR: {msg.splitlines()[0]}", color=ACCENT_RED)

    def _on_text_submit(self) -> None:
        text = self.text_input.text().strip()
        if not text:
            return
        self.text_input.clear()
        self.worker.submit_text(text)

    # ── System stats ────────────────────────────────────────────────────────

    def _refresh_systems(self) -> None:
        cpu = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory()
        mem_used_gb = mem.used / (1024**3)
        mem_total_gb = mem.total / (1024**3)
        uptime = int(time.time() - self._started_at)
        h, rem = divmod(uptime, 3600)
        m, s = divmod(rem, 60)

        ds = dsa.stats()
        ps = prep.stats()
        rows = [
            ("CPU", f"{cpu:5.1f} %"),
            ("RAM", f"{mem_used_gb:.1f} / {mem_total_gb:.0f} GB"),
            ("MODEL", config.MODEL.replace("claude-", "")),
            ("MEMORIES", str(memory.count())),
            ("TO-DO", f"{task_store.count_pending()} pending"),
            ("DSA", f"{ds['easy']['solved']}E {ds['medium']['solved']}M {ds['hard']['solved']}H"),
            ("PREP", f"{ps['done']}/{ps['total']}"),
            ("TOOLS RUN", str(self._tool_count)),
            ("UPTIME", f"{h:02d}:{m:02d}:{s:02d}"),
        ]
        body = "<br>".join(
            f'<span style="color:{TEXT_DIM};">{label:<10}</span> '
            f'<span style="color:{TEXT_BRIGHT};">{value}</span>'
            for label, value in rows
        )
        self.systems.body.setHtml(
            f'<div style="font-family: Consolas; line-height: 1.9; '
            f'letter-spacing: 1px;">{body}</div>'
        )
        self._refresh_trackers()

    # ── View switching ──────────────────────────────────────────────────────

    def _switch_view(self, key: str) -> None:
        self.views.setCurrentIndex(1 if key == "jobprep" else 0)

    # ── Trackers: TO-DO (main view) + DSA/PREP (job-prep view) ──────────────

    def _refresh_trackers(self) -> None:
        self._render_todo()
        self._render_jobprep_dsa()
        self._render_jobprep_prep()

    def _render_todo(self) -> None:
        items = task_store.list_all(include_done=True)
        if not items:
            self.todo.body.setHtml(
                f'<div style="color:{TEXT_DIM}; padding-top:4px;">'
                f'list is empty — ask Jarvis to add something</div>'
            )
            return
        rows = []
        for t in items:
            done = t["status"] == "done"
            if done:
                box, box_color, color, deco = "✓", ACCENT_GREEN, TEXT_DIM, "text-decoration: line-through;"
            else:
                box, box_color, deco = "○", ACCENT, ""
                color = (
                    ACCENT_AMBER if t["priority"] == "high"
                    else TEXT_DIM if t["priority"] == "low"
                    else TEXT_BRIGHT
                )
            flag = " ▲" if (not done and t["priority"] == "high") else ""
            rows.append(
                f'<div style="margin:5px 0; {deco}">'
                f'<span style="color:{box_color};">{box}</span> '
                f'<span style="color:{color};">{_esc(t["text"])}</span>'
                f'<span style="color:{ACCENT_AMBER};">{flag}</span>'
                f"</div>"
            )
        self.todo.body.setHtml(f'<div style="line-height:1.4;">{"".join(rows)}</div>')

    def _render_jobprep_dsa(self) -> None:
        s = dsa.stats()

        def block(solved: int, total: int, label: str, color: str) -> str:
            return (
                f'<td align="center" width="33%">'
                f'<span style="font-size:40px; font-weight:bold; color:{color};">{solved}</span><br>'
                f'<span style="font-size:10px; letter-spacing:2px; color:{TEXT_DIM};">{label}</span><br>'
                f'<span style="font-size:10px; color:{TEXT_DIM};">of {total}</span></td>'
            )

        html = (
            '<table width="100%" cellspacing="0" cellpadding="6"><tr>'
            + block(s["easy"]["solved"], s["easy"]["total"], "EASY", ACCENT_GREEN)
            + block(s["medium"]["solved"], s["medium"]["total"], "MEDIUM", ACCENT_AMBER)
            + block(s["hard"]["solved"], s["hard"]["total"], "HARD", ACCENT_RED)
            + "</tr></table>"
        )
        html += (
            f'<div style="text-align:center; margin:8px 0 4px; color:{TEXT};">'
            f'<span style="color:{ACCENT_BRIGHT}; font-size:20px; font-weight:bold;">{s["total_solved"]}</span>'
            f' solved · {s["total"]} tracked</div>'
        )

        dot = {"easy": ACCENT_GREEN, "medium": ACCENT_AMBER, "hard": ACCENT_RED}
        any_problems = False
        for diff in ("easy", "medium", "hard"):
            probs = dsa.list_all(difficulty=diff)
            if not probs:
                continue
            any_problems = True
            d = s[diff]
            html += (
                f'<div style="color:{dot[diff]}; font-size:10px; letter-spacing:2px; '
                f'margin:12px 0 4px;">{diff.upper()}  '
                f'<span style="color:{TEXT_DIM};">{d["solved"]}/{d["total"]}</span></div>'
            )
            for p in probs:
                solved = p["status"] == "solved"
                box = "✓" if solved else "○"
                box_color = ACCENT_GREEN if solved else TEXT_DIM
                title_color = TEXT if solved else TEXT_BRIGHT
                topic = (
                    f' <span style="color:{TEXT_DIM};">· {_esc(p["topic"])}</span>'
                    if p["topic"] else ""
                )
                html += (
                    f'<div style="margin:3px 0;">'
                    f'<span style="color:{box_color};">{box}</span> '
                    f'<span style="color:{title_color};">{_esc(p["title"])}</span>{topic}</div>'
                )
        if not any_problems:
            html += (
                f'<div style="color:{TEXT_DIM}; margin-top:14px;">'
                f'No problems tracked yet. Tell Jarvis when you solve one — '
                f'e.g. "I solved Two Sum, easy".</div>'
            )
        self.jobprep.dsa.body.setHtml(html)

    def _render_jobprep_prep(self) -> None:
        s = prep.stats()
        total = s["total"]
        done = s["done"]
        pct = int(round(100 * done / total)) if total else 0

        html = (
            f'<div style="color:{TEXT}; font-size:12px; margin-bottom:2px;">'
            f'<span style="color:{ACCENT_BRIGHT}; font-weight:bold;">{done}</span> / {total} complete '
            f'<span style="color:{TEXT_DIM};">({pct}%)</span></div>'
        )
        html += _bar(pct, ACCENT_GREEN if pct >= 100 else ACCENT)

        if not total:
            html += f'<div style="color:{TEXT_DIM}; margin-top:10px;">no prep items</div>'
            self.jobprep.prep.body.setHtml(html)
            return

        items = prep.list_all()
        by_cat: dict[str, list[dict]] = {}
        for it in items:
            by_cat.setdefault(it["category"], []).append(it)

        for cat, v in s["by_category"].items():
            cpct = int(round(100 * v["done"] / v["total"])) if v["total"] else 0
            fill = ACCENT_GREEN if cpct >= 100 else ACCENT
            html += (
                f'<div style="margin:12px 0 2px;">'
                f'<table width="100%" cellspacing="0" cellpadding="0"><tr>'
                f'<td style="color:{TEXT_BRIGHT}; font-size:11px; font-weight:bold; '
                f'letter-spacing:1px;">{_esc(cat)}</td>'
                f'<td align="right" style="color:{TEXT_DIM}; font-size:10px;">{v["done"]}/{v["total"]}</td>'
                f"</tr></table>{_bar(cpct, fill)}</div>"
            )
            for it in by_cat.get(cat, []):
                done_it = it["status"] == "done"
                box = "✓" if done_it else "○"
                box_color = ACCENT_GREEN if done_it else TEXT_DIM
                color = TEXT_DIM if done_it else TEXT
                deco = "text-decoration: line-through;" if done_it else ""
                html += (
                    f'<div style="margin:2px 0 2px 6px; {deco}">'
                    f'<span style="color:{box_color};">{box}</span> '
                    f'<span style="color:{color}; font-size:11px;">{_esc(it["title"])}</span></div>'
                )
        self.jobprep.prep.body.setHtml(html)

    # ── Cleanup ─────────────────────────────────────────────────────────────

    def closeEvent(self, event) -> None:  # noqa: N802
        self.worker.stop()
        self.worker.wait(2000)
        event.accept()

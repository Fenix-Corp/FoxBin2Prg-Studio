"""Lector incremental de events.jsonl.

Se sirve del QProcess `readyReadStandardOutput` para el heartbeat, pero la
verdad esta en el archivo JSONL: leemos desde el ultimo offset conocido,
parseamos linea por linea, y emitimos senales tipadas.
"""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QObject, QTimer, Signal

from fb2p_studio.core.job import (
    CancelledEvent,
    DriverErrorEvent,
    Event,
    FileProcessedEvent,
    JobDoneEvent,
    JobStartEvent,
    OpDoneEvent,
    OpErrorEvent,
    OpStartEvent,
    parse_event,
)


class EventStream(QObject):
    """Poll periodico del JSONL. Emite senales tipadas por cada evento nuevo."""

    job_started = Signal(JobStartEvent)
    op_started = Signal(OpStartEvent)
    file_processed = Signal(FileProcessedEvent)
    op_done = Signal(OpDoneEvent)
    op_error = Signal(OpErrorEvent)
    job_done = Signal(JobDoneEvent)
    driver_error = Signal(DriverErrorEvent)
    cancelled = Signal(CancelledEvent)
    raw_line = Signal(str)

    def __init__(self, path: Path, parent: QObject | None = None, interval_ms: int = 100) -> None:
        super().__init__(parent)
        self._path = path
        self._offset = 0
        self._buffer = b""
        self._timer = QTimer(self)
        self._timer.setInterval(interval_ms)
        self._timer.timeout.connect(self._drain)

    def start(self) -> None:
        self._timer.start()

    def stop(self) -> None:
        self._timer.stop()
        self._drain()

    def _drain(self) -> None:
        if not self._path.exists():
            return
        try:
            with self._path.open("rb") as f:
                f.seek(self._offset)
                chunk = f.read()
                self._offset = f.tell()
        except OSError:
            return
        if not chunk:
            return
        self._buffer += chunk
        while b"\n" in self._buffer:
            line, self._buffer = self._buffer.split(b"\n", 1)
            text = line.rstrip(b"\r").decode("utf-8", errors="replace").strip()
            if not text:
                continue
            self.raw_line.emit(text)
            self._dispatch(text)

    def _dispatch(self, line: str) -> None:
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            return
        event: Event | None = parse_event(payload)
        if event is None:
            return
        if isinstance(event, JobStartEvent):
            self.job_started.emit(event)
        elif isinstance(event, OpStartEvent):
            self.op_started.emit(event)
        elif isinstance(event, FileProcessedEvent):
            self.file_processed.emit(event)
        elif isinstance(event, OpDoneEvent):
            self.op_done.emit(event)
        elif isinstance(event, OpErrorEvent):
            self.op_error.emit(event)
        elif isinstance(event, JobDoneEvent):
            self.job_done.emit(event)
        elif isinstance(event, DriverErrorEvent):
            self.driver_error.emit(event)
        elif isinstance(event, CancelledEvent):
            self.cancelled.emit(event)

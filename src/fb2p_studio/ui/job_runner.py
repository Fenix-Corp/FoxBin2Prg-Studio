"""Ejecuta un `Job` contra el bridge VFP y vuelca sus eventos en el log.

Lo comparten las pestanas Convertir y Proyecto. Antes esta logica vivia dentro
de `ConvertTab`; al aparecer la segunda pestana que ejecuta jobs, duplicarla
habria significado dos copias de los ocho handlers de eventos.

Los nombres de evento (`job_start`, `op_done`, ...) son tokens del protocolo
JSONL y NO se traducen; sólo la prosa que los acompana.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QMessageBox, QWidget

from fb2p_studio.core.bridge import Bridge, BridgeLaunchError
from fb2p_studio.core.discovery import Paths
from fb2p_studio.core.job import (
    CancelledEvent,
    DriverErrorEvent,
    FileProcessedEvent,
    Job,
    JobDoneEvent,
    JobStartEvent,
    OpDoneEvent,
    OpErrorEvent,
    OpStartEvent,
)
from fb2p_studio.ui.widgets.log_view import LogView
from fb2p_studio.ui.widgets.results_view import ResultsView


class JobRunner(QObject):
    """Un job por vez. `busy` dice si hay uno corriendo."""

    started = Signal()
    finished = Signal()

    def __init__(
        self,
        log: LogView,
        dialog_parent: QWidget,
        results: ResultsView | None = None,
    ) -> None:
        super().__init__(dialog_parent)
        self._log = log
        self._results = results
        self._parent = dialog_parent
        self._bridge: Bridge | None = None
        # Lo que FoxBin2Prg escribe en stderr durante la operacion en curso.
        # Ahi viaja la explicacion de casi todos los fallos: los que no llegan
        # a ser una excepcion VFP salen por aca y sólo dejan un rc distinto de
        # cero en `op_done`.
        self._stderr: list[str] = []

    # ------------------------------------------------------------------ api
    @property
    def busy(self) -> bool:
        return self._bridge is not None

    def run(self, paths: Paths, job: Job) -> bool:
        """Lanza el job. Devuelve False si no se pudo (ya avisó por diálogo)."""
        if self.busy:
            return False

        try:
            bridge = Bridge(paths, self)
        except Exception as exc:  # noqa: BLE001 — cualquier fallo de construccion
            QMessageBox.critical(self._parent, self.tr("Error"), str(exc))
            return False

        try:
            bridge.start(job)
        except BridgeLaunchError as exc:
            QMessageBox.critical(self._parent, self.tr("No se pudo lanzar el bridge"), str(exc))
            return False

        self._bridge = bridge
        if self._results is not None:
            self._results.clear()
        assert bridge.events is not None
        bridge.events.job_started.connect(self._on_job_started)
        bridge.events.op_started.connect(self._on_op_started)
        bridge.events.file_processed.connect(self._on_file_processed)
        bridge.events.op_done.connect(self._on_op_done)
        bridge.events.op_error.connect(self._on_op_error)
        bridge.events.job_done.connect(self._on_job_done)
        bridge.events.driver_error.connect(self._on_driver_error)
        bridge.events.cancelled.connect(self._on_cancelled)
        bridge.stderr_line.connect(self._on_stderr)
        bridge.stdout_line.connect(lambda line: self._log.append(f"[stdout] {line}", severity="muted"))
        bridge.finished.connect(self._on_process_finished)

        self.started.emit()
        return True

    def cancel(self) -> None:
        if self._bridge is not None:
            self._bridge.cancel()
            self._log.append(
                self.tr("» Cancelacion solicitada (se aplica entre operaciones)"), severity="warn"
            )

    # ------------------------------------------------------------------ handlers
    def _on_job_started(self, ev: JobStartEvent) -> None:
        self._log.append(
            "job_start · "
            + self.tr("VFP {0} · FoxBin2Prg {1} · {2} op(s) · dryRun={3}").format(
                ev.vfp_version, ev.fb2p_version or "?", ev.total, ev.dry_run
            ),
            severity="muted",
        )

    def _on_stderr(self, line: str) -> None:
        self._stderr.append(line)
        self._log.append(f"[stderr] {line}", severity="warn")

    def _on_op_started(self, ev: OpStartEvent) -> None:
        self._stderr.clear()
        self._log.append(f"→ op_start [{ev.op_id}] {ev.direction} · {ev.file}", severity="info")
        if self._results is not None:
            self._results.start_op(ev)

    def _on_file_processed(self, ev: FileProcessedEvent) -> None:
        tag = "OK " if not ev.has_errors else "ERR"
        sev = "ok" if not ev.has_errors else "error"
        arrow = "in " if ev.in_out == "I" else "out"
        self._log.append(f"  · [{tag}] {arrow} {ev.file}", severity=sev)
        if self._results is not None:
            self._results.add_file(ev)

    def _on_op_done(self, ev: OpDoneEvent) -> None:
        sev = "ok" if ev.return_code == 0 else "error"
        self._log.append(
            f"← op_done [{ev.op_id}] rc={ev.return_code} · {ev.elapsed_ms} ms", severity=sev
        )
        if self._results is not None:
            self._results.finish_op(ev, "\n".join(self._stderr))

    def _on_op_error(self, ev: OpErrorEvent) -> None:
        self._log.append(
            f"× op_error [{ev.op_id}] "
            + self.tr("#{0} en linea {1}: {2}").format(ev.error_no, ev.line_no, ev.message),
            severity="error",
        )
        if ev.line_contents:
            self._log.append(self.tr("    codigo: {0}").format(ev.line_contents), severity="muted")
        if ev.details:
            self._log.append(self.tr("    detalle: {0}").format(ev.details), severity="muted")
        if self._results is not None:
            self._results.fail_op(ev, "\n".join(self._stderr))

    def _on_job_done(self, ev: JobDoneEvent) -> None:
        sev = "ok" if ev.err_count == 0 else "error"
        self._log.append(
            f"= job_done · ok={ev.ok_count} err={ev.err_count} · {ev.elapsed_ms} ms", severity=sev
        )
        if self._results is not None:
            self._results.finish_job(ev)

    def _on_cancelled(self, ev: CancelledEvent) -> None:
        self._log.append(
            self.tr("= cancelado tras {0} operacion(es)").format(ev.ops_processed), severity="warn"
        )

    def _on_driver_error(self, ev: DriverErrorEvent) -> None:
        self._log.append(f"!! DRIVER_ERROR [{ev.stage}]: {ev.message}", severity="error")
        if self._results is not None:
            self._results.driver_error(ev)

    def _on_process_finished(self, exit_code: int) -> None:
        self._log.append(
            self.tr("» vfp9.exe termino con exit code {0}").format(exit_code), severity="muted"
        )
        self._bridge = None
        self.finished.emit()

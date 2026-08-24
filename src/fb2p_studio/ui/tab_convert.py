"""Tab: Convertir un archivo (BIN2PRG / PRG2BIN / auto por extension)."""

from __future__ import annotations

from pathlib import Path
from typing import cast

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from fb2p_studio.core.bridge import Bridge, BridgeLaunchError
from fb2p_studio.core.discovery import Paths, resolve
from fb2p_studio.core.extensions import direction_from_ext, is_supported
from fb2p_studio.core.job import (
    DriverErrorEvent,
    FileProcessedEvent,
    Job,
    JobDoneEvent,
    JobStartEvent,
    OpDoneEvent,
    OpErrorEvent,
    OpStartEvent,
    Operation,
    OperationOptions,
)
from fb2p_studio.core.settings import Settings
from fb2p_studio.ui.theme import LogColors
from fb2p_studio.ui.widgets.command_preview import CommandPreview
from fb2p_studio.ui.widgets.log_view import LogView
from fb2p_studio.ui.widgets.path_picker import PathPicker


class ConvertTab(QWidget):
    def __init__(self, settings: Settings, log_colors: LogColors, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._settings = settings
        self._log_colors = log_colors
        self._bridge: Bridge | None = None

        # --- top: origen + operacion + opciones ---
        self._source = PathPicker(mode="file", placeholder="Ruta al archivo binario o de texto",
                                  file_filter="FoxBin2Prg (*.scx *.vcx *.pjx *.frx *.lbx *.mnx *.dbc *.dbf "
                                              "*.sc2 *.vc2 *.pj2 *.fr2 *.lb2 *.mn2 *.dc2 *.db2);;Todos (*.*)")
        self._source.path_changed.connect(self._on_source_changed)

        self._rb_auto = QRadioButton("Auto (por extension)")
        self._rb_bin = QRadioButton("Bin -> Prg")
        self._rb_prg = QRadioButton("Prg -> Bin")
        self._rb_auto.setChecked(True)
        for rb in (self._rb_auto, self._rb_bin, self._rb_prg):
            rb.toggled.connect(self._refresh_preview)
        op_row = QHBoxLayout()
        op_row.addWidget(self._rb_auto)
        op_row.addWidget(self._rb_bin)
        op_row.addWidget(self._rb_prg)
        op_row.addStretch(1)

        source_form = QFormLayout()
        source_form.addRow("Archivo:", self._source)
        source_form.addRow("Operacion:", self._wrap(op_row))

        # --- avanzadas ---
        self._chk_no_timestamps = QCheckBox("Limpiar timestamps (recomendado)")
        self._chk_no_timestamps.setChecked(True)
        self._chk_clear_uid = QCheckBox("Limpiar UniqueID")
        self._chk_clear_uid.setChecked(True)
        self._chk_recompile = QCheckBox("Recompilar tras generar binario")
        self._chk_recompile.setChecked(True)
        self._chk_dry_run = QCheckBox("Solo simular (dry-run)")
        self._sp_backup = QSpinBox()
        self._sp_backup.setRange(0, 10)
        self._sp_backup.setValue(1)
        self._cb_debug = QComboBox()
        self._cb_debug.addItems(["0 - sin debug", "1 - log por archivo", "2 - log extendido"])

        for w in (self._chk_no_timestamps, self._chk_clear_uid, self._chk_recompile, self._chk_dry_run):
            w.toggled.connect(self._refresh_preview)
        self._sp_backup.valueChanged.connect(lambda _: self._refresh_preview())
        self._cb_debug.currentIndexChanged.connect(lambda _: self._refresh_preview())

        adv_form = QFormLayout()
        adv_form.addRow(self._chk_no_timestamps)
        adv_form.addRow(self._chk_clear_uid)
        adv_form.addRow(self._chk_recompile)
        adv_form.addRow(self._chk_dry_run)
        adv_form.addRow("Backups (n .bak):", self._sp_backup)
        adv_form.addRow("Debug:", self._cb_debug)

        gb_adv = QGroupBox("Opciones avanzadas")
        gb_adv.setCheckable(True)
        gb_adv.setChecked(False)
        gb_adv.setLayout(adv_form)

        # --- preview + boton ejecutar ---
        self._preview = CommandPreview()
        self._btn_run = QPushButton("Ejecutar")
        self._btn_run.clicked.connect(self._run)
        self._btn_cancel = QPushButton("Cancelar")
        self._btn_cancel.setEnabled(False)
        self._btn_cancel.clicked.connect(self._cancel)

        run_row = QHBoxLayout()
        run_row.addStretch(1)
        run_row.addWidget(self._btn_cancel)
        run_row.addWidget(self._btn_run)

        # --- log ---
        self._log = LogView(self._log_colors)

        # --- layout con splitter ---
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        top_layout.addLayout(source_form)
        top_layout.addWidget(gb_adv)
        top_layout.addWidget(QLabel("job.ini (preview):"))
        top_layout.addWidget(self._preview, 1)
        top_layout.addLayout(run_row)

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(top_widget)
        splitter.addWidget(self._log)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        root = QVBoxLayout(self)
        root.addWidget(splitter, 1)

        self._refresh_preview()

    # ---------------------------------------------------------------- helpers
    @staticmethod
    def _wrap(layout) -> QWidget:
        w = QWidget()
        w.setLayout(layout)
        return w

    def _current_direction(self) -> str:
        if self._rb_bin.isChecked():
            return "BIN2PRG"
        if self._rb_prg.isChecked():
            return "PRG2BIN"
        return direction_from_ext(self._source.value())

    def _build_operation(self) -> Operation:
        return Operation(
            id="op1",
            file=self._source.value(),
            type=cast(str, self._current_direction()),
            options=OperationOptions(
                no_timestamps=int(self._chk_no_timestamps.isChecked()),
                clear_unique_id=int(self._chk_clear_uid.isChecked()),
                recompile=int(self._chk_recompile.isChecked()),
                backup_levels=self._sp_backup.value(),
                debug=self._cb_debug.currentIndex(),
            ),
        )

    def _build_job(self, paths: Paths) -> Job:
        return Job(
            foxbin2prg_home=str(paths.fb2p_home) if paths.fb2p_home else "",
            event_stream=Path("<workdir>/events.jsonl"),
            operations=[self._build_operation()],
            dry_run=self._chk_dry_run.isChecked(),
        )

    def _refresh_preview(self) -> None:
        paths = resolve(self._settings.vfp_exe or None, self._settings.fb2p_home or None)
        job = self._build_job(paths)
        self._preview.set_text(job.to_ini())

    # ---------------------------------------------------------------- events
    def _on_source_changed(self, text: str) -> None:
        if text and self._rb_auto.isChecked():
            if not is_supported(text):
                self._log.append(f"Extension no reconocida: {text}", severity="warn")
        self._refresh_preview()

    # ---------------------------------------------------------------- run
    def _run(self) -> None:
        if not self._source.value():
            QMessageBox.warning(self, "Falta origen", "Seleccioná un archivo de origen.")
            return
        if not Path(self._source.value()).exists():
            QMessageBox.warning(self, "Origen inexistente", f"No existe:\n{self._source.value()}")
            return
        if self._current_direction() == "":
            QMessageBox.warning(self, "Direccion desconocida",
                                "La extension no permite decidir auto. Elegí Bin->Prg o Prg->Bin.")
            return

        paths = resolve(self._settings.vfp_exe or None, self._settings.fb2p_home or None)
        try:
            self._bridge = Bridge(paths, self)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error", str(exc))
            return

        job = self._build_job(paths)
        self._log.append(f"» Ejecutando {job.operations[0].type} sobre {job.operations[0].file}", severity="muted")

        try:
            self._bridge.start(job)
        except BridgeLaunchError as exc:
            QMessageBox.critical(self, "No se pudo lanzar el bridge", str(exc))
            self._bridge = None
            return

        assert self._bridge.events is not None
        self._bridge.events.job_started.connect(self._on_job_started)
        self._bridge.events.op_started.connect(self._on_op_started)
        self._bridge.events.file_processed.connect(self._on_file_processed)
        self._bridge.events.op_done.connect(self._on_op_done)
        self._bridge.events.op_error.connect(self._on_op_error)
        self._bridge.events.job_done.connect(self._on_job_done)
        self._bridge.events.driver_error.connect(self._on_driver_error)
        self._bridge.stderr_line.connect(lambda l: self._log.append(f"[stderr] {l}", severity="warn"))
        self._bridge.stdout_line.connect(lambda l: self._log.append(f"[stdout] {l}", severity="muted"))
        self._bridge.finished.connect(self._on_process_finished)

        self._btn_run.setEnabled(False)
        self._btn_cancel.setEnabled(True)

    def _cancel(self) -> None:
        if self._bridge is not None:
            self._bridge.cancel()
            self._log.append("» Cancelacion solicitada (se aplica entre operaciones)", severity="warn")

    # ---------------------------------------------------------------- handlers
    def _on_job_started(self, ev: JobStartEvent) -> None:
        self._log.append(
            f"job_start · VFP {ev.vfp_version} · FoxBin2Prg {ev.fb2p_version or '?'} · "
            f"{ev.total} op(s) · dryRun={ev.dry_run}",
            severity="muted",
        )

    def _on_op_started(self, ev: OpStartEvent) -> None:
        self._log.append(f"→ op_start [{ev.op_id}] {ev.direction} · {ev.file}", severity="info")

    def _on_file_processed(self, ev: FileProcessedEvent) -> None:
        tag = "OK " if not ev.has_errors else "ERR"
        sev = "ok" if not ev.has_errors else "error"
        arrow = "in " if ev.in_out == "I" else "out"
        self._log.append(f"  · [{tag}] {arrow} {ev.file}", severity=sev)

    def _on_op_done(self, ev: OpDoneEvent) -> None:
        sev = "ok" if ev.return_code == 0 else "error"
        self._log.append(f"← op_done [{ev.op_id}] rc={ev.return_code} · {ev.elapsed_ms} ms", severity=sev)

    def _on_op_error(self, ev: OpErrorEvent) -> None:
        self._log.append(
            f"× op_error [{ev.op_id}] #{ev.error_no} en linea {ev.line_no}: {ev.message}",
            severity="error",
        )
        if ev.line_contents:
            self._log.append(f"    codigo: {ev.line_contents}", severity="muted")
        if ev.details:
            self._log.append(f"    detalle: {ev.details}", severity="muted")

    def _on_job_done(self, ev: JobDoneEvent) -> None:
        sev = "ok" if ev.err_count == 0 else "error"
        self._log.append(
            f"= job_done · ok={ev.ok_count} err={ev.err_count} · {ev.elapsed_ms} ms",
            severity=sev,
        )
        self._settings.push_recent(self._source.value())

    def _on_driver_error(self, ev: DriverErrorEvent) -> None:
        self._log.append(f"!! DRIVER_ERROR [{ev.stage}]: {ev.message}", severity="error")

    def _on_process_finished(self, exit_code: int) -> None:
        self._log.append(f"» vfp9.exe termino con exit code {exit_code}", severity="muted")
        self._btn_run.setEnabled(True)
        self._btn_cancel.setEnabled(False)

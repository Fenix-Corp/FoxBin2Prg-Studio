"""Tab: Convertir un archivo (BIN2PRG / PRG2BIN / auto por extension).

Para un proyecto entero (.pjx / .pj2 con todos sus archivos) esta la pestana
Proyecto: ver `tab_project.py`.
"""

from __future__ import annotations

from pathlib import Path
from typing import cast

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from fb2p_studio.core.discovery import Paths, resolve
from fb2p_studio.core.extensions import direction_from_ext, is_supported, supports
from fb2p_studio.core.job import Job, Operation
from fb2p_studio.core.settings import Settings
from fb2p_studio.ui.job_runner import JobRunner
from fb2p_studio.ui.theme import LogColors
from fb2p_studio.ui.widgets.advanced_options import AdvancedOptions
from fb2p_studio.ui.widgets.command_preview import CommandPreview
from fb2p_studio.ui.widgets.log_view import LogView
from fb2p_studio.ui.widgets.path_picker import PathPicker
from fb2p_studio.ui.widgets.results_view import ResultsView


class ConvertTab(QWidget):
    def __init__(self, settings: Settings, log_colors: LogColors, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._settings = settings

        # --- top: origen + operacion + opciones ---
        self._source = PathPicker(
            mode="file",
            placeholder=self.tr("Ruta al archivo binario o de texto"),
            file_filter=self.tr(
                "FoxBin2Prg (*.scx *.vcx *.pjx *.frx *.lbx *.mnx *.dbc *.dbf "
                "*.sc2 *.vc2 *.pj2 *.fr2 *.lb2 *.mn2 *.dc2 *.db2);;Todos (*.*)"
            ),
        )
        self._source.path_changed.connect(self._on_source_changed)

        self._rb_auto = QRadioButton(self.tr("Auto (por extension)"))
        self._rb_bin = QRadioButton(self.tr("Bin -> Prg"))
        self._rb_prg = QRadioButton(self.tr("Prg -> Bin"))
        self._rb_auto.setChecked(True)
        for rb in (self._rb_auto, self._rb_bin, self._rb_prg):
            rb.toggled.connect(self._refresh_preview)
        op_row = QHBoxLayout()
        op_row.addWidget(self._rb_auto)
        op_row.addWidget(self._rb_bin)
        op_row.addWidget(self._rb_prg)
        op_row.addStretch(1)

        source_form = QFormLayout()
        source_form.addRow(self.tr("Archivo:"), self._source)
        source_form.addRow(self.tr("Operacion:"), self._wrap(op_row))

        self._adv = AdvancedOptions()
        self._adv.changed.connect(self._refresh_preview)

        # --- preview + botones ---
        self._preview = CommandPreview()
        self._btn_run = QPushButton(self.tr("Ejecutar"))
        self._btn_run.setObjectName("accionPrincipal")  # lo destaca el tema ADS
        self._btn_run.clicked.connect(self._run)
        self._btn_cancel = QPushButton(self.tr("Cancelar"))
        self._btn_cancel.setEnabled(False)

        run_row = QHBoxLayout()
        run_row.addStretch(1)
        run_row.addWidget(self._btn_cancel)
        run_row.addWidget(self._btn_run)

        # --- log + runner ---
        self._log = LogView(log_colors)
        self._results = ResultsView(log_colors)
        # Resultados primero: es lo que se mira. El log queda al lado para
        # diagnosticar (stdout/stderr de VFP, eventos crudos).
        self._salida = QTabWidget()
        self._salida.addTab(self._results, self.tr("Resultados"))
        self._salida.addTab(self._log, self.tr("Log"))
        self._runner = JobRunner(self._log, self, self._results)
        self._btn_cancel.clicked.connect(self._runner.cancel)
        self._runner.started.connect(lambda: self._set_running(True))
        self._runner.finished.connect(lambda: self._set_running(False))

        # --- layout con splitter ---
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        top_layout.addLayout(source_form)
        top_layout.addWidget(self._adv)
        top_layout.addWidget(QLabel(self.tr("job.ini (preview):")))
        top_layout.addWidget(self._preview, 1)
        top_layout.addLayout(run_row)

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(top_widget)
        splitter.addWidget(self._salida)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        root = QVBoxLayout(self)
        root.addWidget(splitter, 1)

        self._refresh_preview()

    # ---------------------------------------------------------------- helpers
    def set_log_colors(self, colors: LogColors) -> None:
        """Cambio de tema en caliente (lo llama `MainWindow`)."""
        self._log.set_colors(colors)
        self._results.set_colors(colors)

    @staticmethod
    def _wrap(layout) -> QWidget:
        w = QWidget()
        w.setLayout(layout)
        return w

    def _set_running(self, running: bool) -> None:
        self._btn_run.setEnabled(not running)
        self._btn_cancel.setEnabled(running)

    def _current_direction(self) -> str:
        if self._rb_bin.isChecked():
            return "BIN2PRG"
        if self._rb_prg.isChecked():
            return "PRG2BIN"
        return direction_from_ext(self._source.value())

    def _build_job(self, paths: Paths) -> Job:
        operation = Operation(
            id="op1",
            file=self._source.value(),
            type=cast(str, self._current_direction()),
            options=self._adv.to_options(),
        )
        return Job(
            foxbin2prg_home=str(paths.fb2p_home) if paths.fb2p_home else "",
            event_stream=Path("<workdir>/events.jsonl"),
            operations=[operation],
            dry_run=self._adv.dry_run(),
        )

    def _refresh_preview(self) -> None:
        paths = resolve(self._settings.vfp_exe or None, self._settings.fb2p_home or None)
        self._preview.set_text(self._build_job(paths).to_ini())

    # ---------------------------------------------------------------- events
    def _on_source_changed(self, text: str) -> None:
        if text and self._rb_auto.isChecked() and not is_supported(text):
            self._log.append(self.tr("Extension no reconocida: {0}").format(text), severity="warn")
        self._refresh_preview()

    # ---------------------------------------------------------------- run
    def _run(self) -> None:
        if not self._source.value():
            QMessageBox.warning(
                self, self.tr("Falta origen"), self.tr("Seleccioná un archivo de origen.")
            )
            return
        if not Path(self._source.value()).exists():
            QMessageBox.warning(
                self,
                self.tr("Origen inexistente"),
                self.tr("No existe:\n{0}").format(self._source.value()),
            )
            return
        direccion = self._current_direction()
        if direccion == "":
            QMessageBox.warning(
                self,
                self.tr("Direccion desconocida"),
                self.tr("La extension no permite decidir auto. Elegí Bin->Prg o Prg->Bin."),
            )
            return
        # FoxBin2Prg no convierte todo en las dos direcciones: un .dbf se
        # vuelca a texto, pero el .db2 no se reconstruye salvo que el .cfg lo
        # habilite. Sin este aviso, Ejecutar no haria nada y no se sabria por que.
        if not supports(self._source.value(), direccion):
            QMessageBox.warning(
                self,
                self.tr("Conversion no soportada"),
                self.tr(
                    "FoxBin2Prg no convierte este archivo en esa direccion, asi que lo "
                    "saltearia sin avisar.\n\n{0}\n\nSi es un .db2 / .fk2 / .me2, se "
                    "habilita poniendo n_XXX_Conversion_Support=2 en el foxbin2prg.cfg."
                ).format(Path(self._source.value()).name),
            )
            return

        paths = resolve(self._settings.vfp_exe or None, self._settings.fb2p_home or None)
        job = self._build_job(paths)
        self._log.append(
            self.tr("» Ejecutando {0} sobre {1}").format(
                job.operations[0].type, job.operations[0].file
            ),
            severity="muted",
        )
        if self._runner.run(paths, job):
            self._settings.push_recent(self._source.value())

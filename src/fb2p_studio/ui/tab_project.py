"""Tab: Proyecto — convierte un `.pjx`/`.pj2` con todos sus archivos.

Corresponde al modo `*` / `*-` del Usage 1 de FoxBin2Prg, que es como se
trabaja de verdad: un desarrollador VFP rara vez convierte un archivo suelto,
casi siempre el proyecto entero.

Dos cosas de este modo que condicionan la UI:

1. **La direccion no se elige.** FoxBin2Prg entra al modo proyecto cuando el
   `cType` empieza con `*` y el archivo es un `.pjx`/`.pj2`; ahi la direccion
   la decide la extension (`.pjx` -> texto, `.pj2` -> binario). Ofrecer un
   selector de direccion seria mentir: FoxBin2Prg lo ignoraria.
2. **`*` incluye el propio archivo de proyecto y `*-` lo excluye.** Excluirlo
   sirve cuando el `.pjx` cambia en cada compilacion (fechas, contadores) y no
   se lo quiere en cada commit, pero se quiere el texto del resto al dia.
"""

from __future__ import annotations

from pathlib import Path
from typing import cast

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from fb2p_studio.core.discovery import Paths, resolve
from fb2p_studio.core.extensions import (
    PROJECT_BIN,
    PROJECT_TEXT,
    ext_of,
    is_project,
    project_ctype,
)
from fb2p_studio.core.job import Job, Operation
from fb2p_studio.core.project_reader import ProjectReadError, read_project
from fb2p_studio.core.settings import Settings
from fb2p_studio.core.validators import ProjectPreflight, preflight
from fb2p_studio.ui.job_runner import JobRunner
from fb2p_studio.ui.theme import LogColors
from fb2p_studio.ui.widgets.advanced_options import AdvancedOptions
from fb2p_studio.ui.widgets.command_preview import CommandPreview
from fb2p_studio.ui.widgets.log_view import LogView
from fb2p_studio.ui.widgets.path_picker import PathPicker
from fb2p_studio.ui.widgets.project_contents import ProjectContentsView


class ProjectTab(QWidget):
    def __init__(self, settings: Settings, log_colors: LogColors, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._settings = settings
        self._preflight: ProjectPreflight | None = None

        # Leer el proyecto toca disco (el DBF, mas un stat por archivo). Con la
        # ruta escribiendose a mano eso son N lecturas por tecleo, y en una
        # carpeta de red se nota. Se relee cuando la ruta deja de cambiar.
        self._recheck = QTimer(self)
        self._recheck.setSingleShot(True)
        self._recheck.setInterval(250)
        self._recheck.timeout.connect(self._reload_contents)

        self._project = PathPicker(
            mode="file",
            placeholder=self.tr("Ruta al .pjx (a texto) o al .pj2 (a binario)"),
            file_filter=self.tr("Proyecto VFP (*.pjx *.pj2);;Todos (*.*)"),
        )
        self._project.path_changed.connect(self._on_project_changed)

        self._lbl_direction = QLabel()
        self._lbl_direction.setTextFormat(Qt.TextFormat.RichText)
        self._lbl_direction.setWordWrap(True)

        self._chk_include_pjx = QCheckBox(
            self.tr("Incluir el propio archivo de proyecto en el lote")
        )
        self._chk_include_pjx.setChecked(True)
        self._chk_include_pjx.setToolTip(
            self.tr(
                "Marcado envia cType «*»; desmarcado, «*-», que procesa los archivos "
                "del proyecto pero deja el .pjx/.pj2 sin tocar."
            )
        )
        self._chk_include_pjx.toggled.connect(self._refresh_preview)
        self._chk_include_pjx.toggled.connect(self._refresh_summary)

        self._chk_recompile_here = QCheckBox(
            self.tr("Recompilar desde la carpeta del proyecto")
        )
        self._chk_recompile_here.setChecked(True)
        self._chk_recompile_here.setToolTip(
            self.tr(
                "FoxBin2Prg recompila desde la carpeta de cada archivo, lo que rompe "
                "las rutas relativas (los #include, tipicamente). Con esto se le pasa "
                "la carpeta del proyecto como base."
            )
        )
        self._chk_recompile_here.toggled.connect(self._refresh_preview)

        form = QFormLayout()
        form.addRow(self.tr("Proyecto:"), self._project)
        form.addRow(self.tr("Operacion:"), self._lbl_direction)
        form.addRow("", self._chk_include_pjx)
        form.addRow("", self._chk_recompile_here)

        self._adv = AdvancedOptions()
        self._adv.changed.connect(self._refresh_preview)

        self._contents = ProjectContentsView(log_colors)
        self._preview = CommandPreview()

        self._views = QTabWidget()
        self._views.addTab(self._contents, self.tr("Contenido"))
        self._views.addTab(self._preview, self.tr("job.ini"))

        self._btn_run = QPushButton(self.tr("Ejecutar"))
        self._btn_run.clicked.connect(self._run)
        self._btn_cancel = QPushButton(self.tr("Cancelar"))
        self._btn_cancel.setEnabled(False)

        run_row = QHBoxLayout()
        run_row.addStretch(1)
        run_row.addWidget(self._btn_cancel)
        run_row.addWidget(self._btn_run)

        self._log = LogView(log_colors)
        self._runner = JobRunner(self._log, self)
        self._btn_cancel.clicked.connect(self._runner.cancel)
        self._runner.started.connect(lambda: self._set_running(True))
        self._runner.finished.connect(lambda: self._set_running(False))

        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        top_layout.addLayout(form)
        top_layout.addWidget(self._adv)
        top_layout.addWidget(self._views, 1)
        top_layout.addLayout(run_row)

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(top_widget)
        splitter.addWidget(self._log)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        root = QVBoxLayout(self)
        root.addWidget(splitter, 1)

        self._on_project_changed(self._project.value())

    # ---------------------------------------------------------------- helpers
    def _set_running(self, running: bool) -> None:
        self._btn_run.setEnabled(not running)
        self._btn_cancel.setEnabled(running)

    def _direction_text(self, path: str) -> str:
        """Que va a hacer FoxBin2Prg, deducido de la extension."""
        if not path.strip():
            return self.tr("<i>Elegí un proyecto para ver la operacion.</i>")
        ext = ext_of(path)
        if ext == PROJECT_BIN:
            return self.tr("<b>Bin → Prg</b> — el proyecto y sus archivos pasan a texto.")
        if ext == PROJECT_TEXT:
            return self.tr("<b>Prg → Bin</b> — el texto del proyecto vuelve a binario.")
        return self.tr(
            "<b>No es un proyecto.</b> Este modo sólo acepta <code>.pjx</code> o "
            "<code>.pj2</code>; para un archivo suelto está la pestaña Convertir."
        )

    def _recompile_cwd(self) -> str:
        """Carpeta del proyecto, si se pidió recompilar desde ahí."""
        path = self._project.value().strip()
        if not path or not self._chk_recompile_here.isChecked() or not self._adv.recompile():
            return ""
        return str(Path(path).parent)

    def _build_job(self, paths: Paths) -> Job:
        ctype = project_ctype(include_project_file=self._chk_include_pjx.isChecked())
        operation = Operation(
            id="proyecto",
            file=self._project.value(),
            type=cast(str, ctype),
            options=self._adv.to_options(recompile_cwd=self._recompile_cwd()),
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

    # ---------------------------------------------------------------- contenido
    def _reload_contents(self) -> None:
        """Lee el proyecto y calcula el pre-flight. Nunca impide ejecutar."""
        path = self._project.value().strip()
        self._preflight = None

        if not path:
            self._contents.clear(self.tr("Elegí un proyecto para ver su contenido."))
            return
        if not is_project(path):
            self._contents.clear(self.tr("Sólo se puede listar un .pjx o un .pj2."))
            return
        if not Path(path).is_file():
            self._contents.clear(self.tr("El archivo todavía no existe."))
            return

        try:
            contenido = read_project(path)
        except ProjectReadError as e:
            # Informativo: FoxBin2Prg puede saber leerlo igual, asi que se avisa
            # y se deja ejecutar.
            self._contents.show_error(str(e))
            return

        self._preflight = preflight(
            contenido, include_project_file=self._chk_include_pjx.isChecked()
        )
        self._contents.show_preflight(self._preflight)

    def _refresh_summary(self) -> None:
        """Recalcula sólo el resumen (cambió incluir/excluir el proyecto)."""
        if self._preflight is None:
            return
        self._preflight = preflight(
            self._preflight.contents, include_project_file=self._chk_include_pjx.isChecked()
        )
        self._contents.show_preflight(self._preflight)

    # ---------------------------------------------------------------- events
    def _on_project_changed(self, text: str) -> None:
        self._lbl_direction.setText(self._direction_text(text))
        self._refresh_preview()
        self._recheck.start()  # relee el contenido cuando la ruta se asiente

    # ---------------------------------------------------------------- run
    def _run(self) -> None:
        path = self._project.value().strip()
        if not path:
            QMessageBox.warning(
                self, self.tr("Falta el proyecto"), self.tr("Seleccioná un .pjx o un .pj2.")
            )
            return
        if not Path(path).exists():
            QMessageBox.warning(
                self, self.tr("Proyecto inexistente"), self.tr("No existe:\n{0}").format(path)
            )
            return
        if not is_project(path):
            QMessageBox.warning(
                self,
                self.tr("No es un proyecto"),
                self.tr(
                    "FoxBin2Prg sólo procesa un lote completo cuando el archivo es un "
                    ".pjx o un .pj2.\n\nRecibido: {0}\n\nPara un archivo suelto, usá la "
                    "pestaña Convertir."
                ).format(Path(path).name),
            )
            return

        # El pre-flight ya sabe si faltan archivos. FoxBin2Prg los saltaria en
        # silencio, asi que se avisa ANTES en vez de despues.
        if not self._confirm_problems():
            return

        paths = resolve(self._settings.vfp_exe or None, self._settings.fb2p_home or None)
        job = self._build_job(paths)
        incluye = (
            self.tr("incluyendo el archivo de proyecto")
            if self._chk_include_pjx.isChecked()
            else self.tr("sin el archivo de proyecto")
        )
        self._log.append(
            self.tr("» Proyecto completo: {0} ({1})").format(path, incluye), severity="muted"
        )
        if self._preflight is not None:
            self._log.append(
                self.tr("» {0} archivo(s) a convertir de {1} en el proyecto").format(
                    self._preflight.total_to_convert, len(self._preflight.contents)
                ),
                severity="muted",
            )
            for check in self._preflight.missing:
                self._log.append(
                    self.tr("  · FALTA, se saltea: {0}").format(check.item.source), severity="warn"
                )

        if self._runner.run(paths, job):
            self._settings.push_recent(path)

    def _confirm_problems(self) -> bool:
        """Pide confirmacion si el pre-flight encontro archivos faltantes."""
        pf = self._preflight
        if pf is None or not pf.has_problems:
            return True

        faltan = [str(c.item.source) for c in pf.missing]
        muestra = "\n".join(f"  · {f}" for f in faltan[:10])
        if len(faltan) > 10:
            muestra += "\n" + self.tr("  · ... y {0} mas").format(len(faltan) - 10)

        respuesta = QMessageBox.warning(
            self,
            self.tr("Faltan archivos del proyecto"),
            self.tr(
                "{0} archivo(s) que el proyecto declara no están en disco. FoxBin2Prg "
                "los saltea sin avisar:\n\n{1}\n\n¿Convertir de todas formas los {2} "
                "que sí están?"
            ).format(len(faltan), muestra, pf.total_to_convert),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        return respuesta == QMessageBox.StandardButton.Yes

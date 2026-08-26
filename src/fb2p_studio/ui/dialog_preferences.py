"""Dialogo de Preferencias: rutas de vfp9.exe y FoxBin2Prg."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from fb2p_studio.core.discovery import find_fb2p_home, find_vfp_exe
from fb2p_studio.core.settings import Settings
from fb2p_studio.core.updates import DEFAULT_MANIFEST
from fb2p_studio.ui import theme
from fb2p_studio.ui.widgets.path_picker import PathPicker


def _auto_hint(detected: object | None, missing: str) -> str:
    """Texto del placeholder: que se va a usar si el campo queda vacio."""
    return f"(auto) {detected}" if detected else f"(auto) {missing}"


def _separador() -> QFrame:
    linea = QFrame()
    linea.setFrameShape(QFrame.Shape.HLine)
    linea.setFrameShadow(QFrame.Shadow.Sunken)
    return linea


class PreferencesDialog(QDialog):
    def __init__(self, settings: Settings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(self.tr("Preferencias — FoxBin2Prg-Studio"))
        self.setMinimumWidth(560)
        self._settings = settings

        self._vfp = PathPicker(
            mode="file",
            placeholder="C:\\...\\vfp9.exe",
            file_filter=self.tr("vfp9.exe (vfp9.exe);;Todos (*.*)"),
        )
        self._fb2p = PathPicker(
            mode="dir", placeholder=self.tr("Carpeta con FoxBin2Prg.EXE / .FXP")
        )

        # Los campos muestran SOLO el override guardado. Lo autodetectado va
        # como placeholder: si se escribiera como texto, un OK lo convertiria
        # en override y la ruta de esta maquina quedaria clavada en el .ini
        # (mortal si ese .ini viaja a otra maquina).
        self._vfp.set_value(settings.vfp_exe)
        self._fb2p.set_value(settings.fb2p_home)
        self._vfp.set_placeholder(_auto_hint(find_vfp_exe(), self.tr("no se encontro vfp9.exe")))
        self._fb2p.set_placeholder(
            _auto_hint(find_fb2p_home(), self.tr("no se encontro FoxBin2Prg"))
        )

        self._tema = QComboBox()
        for tema_id, nombre in theme.NOMBRES.items():
            self._tema.addItem(nombre, tema_id)
        actual = theme.normalize(settings.theme)
        self._tema.setCurrentIndex(max(0, self._tema.findData(actual)))

        self._manifest = PathPicker(
            mode="file",
            placeholder=self.tr("(por defecto) {0}").format(DEFAULT_MANIFEST),
            file_filter=self.tr("Manifiesto (*.json);;Todos (*.*)"),
        )
        self._manifest.set_value(settings.update_manifest)
        self._chk_updates = QCheckBox(self.tr("Buscar actualizaciones al arrancar"))
        self._chk_updates.setChecked(settings.check_updates_on_start)

        form = QFormLayout()
        form.addRow(self.tr("Tema:"), self._tema)
        form.addRow(_separador())
        form.addRow(self.tr("vfp9.exe:"), self._vfp)
        form.addRow(self.tr("FoxBin2Prg (carpeta):"), self._fb2p)
        form.addRow(_separador())
        form.addRow(self.tr("Manifiesto de versiones:"), self._manifest)
        form.addRow("", self._chk_updates)

        hint = QLabel(
            self.tr(
                "Dejar un campo <b>vacio</b> = autodeteccion (lo que muestra el texto gris): "
                "variables VFP_EXE / FB2P_HOME, rutas tipicas y, para FoxBin2Prg, el que "
                "viene embebido en el propio Studio.<br>"
                "Escribir una ruta la fija como override y la persiste en QSettings. "
                "Si mas adelante esa ruta no existe, se ignora y se vuelve a la autodeteccion.<br><br>"
                "El <b>manifiesto de versiones</b> es un JSON en la red que dice cual es la "
                "ultima version publicada. Studio sólo avisa: no descarga ni instala nada.<br><br>"
                "El <b>tema</b> se aplica al instante, sin reiniciar."
            )
        )
        hint.setTextFormat(Qt.TextFormat.RichText)
        hint.setWordWrap(True)
        hint.setObjectName("pista")
        hint.setStyleSheet(f"color: {theme.hint_color()};")

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(hint)
        layout.addWidget(buttons)

    def theme_id(self) -> str:
        """Tema elegido. Lo lee `MainWindow` para repintar sin reiniciar."""
        return str(self._tema.currentData())

    def _accept(self) -> None:
        self._settings.theme = self.theme_id()
        self._settings.vfp_exe = self._vfp.value()
        self._settings.fb2p_home = self._fb2p.value()
        self._settings.update_manifest = self._manifest.value()
        self._settings.check_updates_on_start = self._chk_updates.isChecked()
        self.accept()

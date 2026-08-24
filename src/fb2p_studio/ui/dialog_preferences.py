"""Dialogo de Preferencias: rutas de vfp9.exe y FoxBin2Prg."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from fb2p_studio.core.discovery import find_fb2p_home, find_vfp_exe
from fb2p_studio.core.settings import Settings
from fb2p_studio.ui.widgets.path_picker import PathPicker


class PreferencesDialog(QDialog):
    def __init__(self, settings: Settings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Preferencias — FoxBin2Prg-Studio")
        self.setMinimumWidth(560)
        self._settings = settings

        self._vfp = PathPicker(mode="file", placeholder="C:\\...\\vfp9.exe", file_filter="vfp9.exe (vfp9.exe);;Todos (*.*)")
        self._fb2p = PathPicker(mode="dir", placeholder="Carpeta con FoxBin2Prg.EXE / .FXP")

        cur_vfp = settings.vfp_exe or (str(find_vfp_exe()) if find_vfp_exe() else "")
        cur_fb2p = settings.fb2p_home or (str(find_fb2p_home()) if find_fb2p_home() else "")
        self._vfp.set_value(cur_vfp)
        self._fb2p.set_value(cur_fb2p)

        form = QFormLayout()
        form.addRow("vfp9.exe:", self._vfp)
        form.addRow("FoxBin2Prg (carpeta):", self._fb2p)

        hint = QLabel(
            "El valor detectado por defecto proviene de las variables VFP_EXE / FB2P_HOME "
            "o de rutas tipicas. Un override aqui se persiste en QSettings."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #666;")

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(hint)
        layout.addWidget(buttons)

    def _accept(self) -> None:
        self._settings.vfp_exe = self._vfp.value()
        self._settings.fb2p_home = self._fb2p.value()
        self.accept()

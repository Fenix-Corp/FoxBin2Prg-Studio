"""Grupo colapsable con las opciones que se pasan a `c_foxbin2prg.execute()`.

Lo comparten las pestanas Convertir y Proyecto: son las mismas opciones y no
tiene sentido mantener dos copias que se desincronicen.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QSpinBox,
    QWidget,
)

from fb2p_studio.core.job import OperationOptions


class AdvancedOptions(QGroupBox):
    """Checkable y colapsado por defecto: son opciones, no lo habitual."""

    changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setTitle(self.tr("Opciones avanzadas"))
        self.setCheckable(True)
        self.setChecked(False)

        self._chk_no_timestamps = QCheckBox(self.tr("Limpiar timestamps (recomendado)"))
        self._chk_no_timestamps.setChecked(True)
        self._chk_clear_uid = QCheckBox(self.tr("Limpiar UniqueID"))
        self._chk_clear_uid.setChecked(True)
        self._chk_recompile = QCheckBox(self.tr("Recompilar tras generar binario"))
        self._chk_recompile.setChecked(True)
        self._chk_dry_run = QCheckBox(self.tr("Solo simular (dry-run)"))

        self._sp_backup = QSpinBox()
        self._sp_backup.setRange(0, 10)
        self._sp_backup.setValue(1)

        self._cb_debug = QComboBox()
        self._cb_debug.addItems(
            [self.tr("0 - sin debug"), self.tr("1 - log por archivo"), self.tr("2 - log extendido")]
        )

        form = QFormLayout()
        form.addRow(self._chk_no_timestamps)
        form.addRow(self._chk_clear_uid)
        form.addRow(self._chk_recompile)
        form.addRow(self._chk_dry_run)
        form.addRow(self.tr("Backups (n .bak):"), self._sp_backup)
        form.addRow(self.tr("Debug:"), self._cb_debug)
        self.setLayout(form)

        for chk in (
            self._chk_no_timestamps,
            self._chk_clear_uid,
            self._chk_recompile,
            self._chk_dry_run,
        ):
            chk.toggled.connect(self.changed.emit)
        self._sp_backup.valueChanged.connect(lambda _: self.changed.emit())
        self._cb_debug.currentIndexChanged.connect(lambda _: self.changed.emit())

    # ------------------------------------------------------------------ api
    def to_options(self, *, recompile_cwd: str = "") -> OperationOptions:
        return OperationOptions(
            no_timestamps=int(self._chk_no_timestamps.isChecked()),
            clear_unique_id=int(self._chk_clear_uid.isChecked()),
            recompile=int(self._chk_recompile.isChecked()),
            backup_levels=self._sp_backup.value(),
            debug=self._cb_debug.currentIndex(),
            recompile_cwd=recompile_cwd,
        )

    def dry_run(self) -> bool:
        return self._chk_dry_run.isChecked()

    def recompile(self) -> bool:
        return self._chk_recompile.isChecked()

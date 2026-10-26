"""Barra de progreso de una corrida, con el archivo en curso al lado.

Nace indeterminada (animacion de "ocupado") en cuanto arranca el job, porque
al principio FoxBin2Prg todavia no dijo cuantos archivos son. Al llegar el
primer evento de progreso pasa a barra con porcentaje.
"""

from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QProgressBar, QWidget

from fb2p_studio.ui.widgets.elided_label import ElidedLabel


class RunProgress(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._bar = QProgressBar(self)
        self._bar.setTextVisible(True)
        self._bar.setMinimumWidth(220)
        self._file = ElidedLabel("", self)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._bar)
        layout.addWidget(self._file, 1)
        self.setVisible(False)

    def begin(self) -> None:
        """Arranca la corrida: barra indeterminada hasta saber el total."""
        self._bar.setRange(0, 0)
        self._file.setText("")
        self.setVisible(True)

    def update_progress(self, current: int, total: int, text: str) -> None:
        if total <= 0:
            return
        self._bar.setRange(0, total)
        self._bar.setValue(min(current, total))
        self._bar.setFormat(f"{current} / {total}  (%p%)")
        self._file.setText(text)

    def end(self) -> None:
        self.setVisible(False)

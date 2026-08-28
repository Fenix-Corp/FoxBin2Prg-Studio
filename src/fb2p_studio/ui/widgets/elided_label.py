"""Etiqueta para rutas: se acorta con puntos suspensivos en vez de estirar.

Un `QLabel` con una ruta larga le pone un ancho minimo enorme a toda la
ventana — `D:\\FenixPro\\Proyectos\\FoxBin2Prg-Studio\\bundled\\foxbin2prg`
pedia 1040 px, y con eso la ventana no bajaba de 1318 px de ancho. En una
pantalla de 1366 eso significa no poder achicarla ni poner dos ventanas al
lado.

`setWordWrap(True)` no alcanza: una ruta no tiene espacios, asi que para Qt es
una sola palabra y el minimo sigue siendo su ancho completo.

Se elide **en el medio**, que es lo util en una ruta: se ven la unidad y el
nombre del archivo, que es lo que identifica. El texto completo queda en el
tooltip y se puede seleccionar con el mouse.
"""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QPainter, QPaintEvent
from PySide6.QtWidgets import QLabel, QSizePolicy, QWidget


class ElidedLabel(QLabel):
    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self._completo = text
        self.setToolTip(text)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

    def setText(self, text: str) -> None:  # noqa: N802 — API de Qt
        self._completo = text
        self.setToolTip(text)
        super().setText(text)
        self.updateGeometry()

    def full_text(self) -> str:
        return self._completo

    # Un ancho minimo chico es justamente el objetivo: que la ventana pueda
    # encoger. El alto si tiene que respetar el de una linea de texto.
    def minimumSizeHint(self) -> QSize:  # noqa: N802 — API de Qt
        return QSize(60, super().minimumSizeHint().height())

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802 — API de Qt
        pintor = QPainter(self)
        metrica = self.fontMetrics()
        elidido = metrica.elidedText(
            self._completo, Qt.TextElideMode.ElideMiddle, self.width()
        )
        pintor.drawText(self.rect(), int(self.alignment()), elidido)

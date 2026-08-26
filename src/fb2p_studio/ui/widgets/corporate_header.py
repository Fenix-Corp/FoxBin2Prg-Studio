"""Banda corporativa del tema ADS.

No es adorno: es la misma banda azul que llevan las demas utilidades del
departamento y los PDF que produce `md2pdf`, asi que la persona reconoce la
herramienta como parte de la familia. Sólo aparece con el tema ADS; con el
tema Sistema la ventana se mimetiza con Windows y la banda estorbaria.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from fb2p_studio.core.discovery import resources_dir

TITULO = "FoxBin2Prg-Studio"
SUBTITULO = "ADS Software · Departamento de Desarrollo"


class CorporateHeader(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("bandaCorporativa")
        self.setFixedHeight(58)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(12)

        logo = self._logo()
        if logo is not None:
            layout.addWidget(logo)

        textos = QVBoxLayout()
        textos.setSpacing(0)
        titulo = QLabel(TITULO)
        titulo.setObjectName("bandaTitulo")
        subtitulo = QLabel(self.tr(SUBTITULO))
        subtitulo.setObjectName("bandaSubtitulo")
        textos.addWidget(titulo)
        textos.addWidget(subtitulo)
        layout.addLayout(textos)
        layout.addStretch(1)

    def _logo(self) -> QLabel | None:
        """El logo en blanco, pensado para fondo oscuro. Sin el, la banda sirve igual."""
        archivo = resources_dir() / "ads_logo.png"
        if not archivo.is_file():
            return None
        pixmap = QPixmap(str(archivo))
        if pixmap.isNull():
            return None
        etiqueta = QLabel()
        etiqueta.setPixmap(
            pixmap.scaledToHeight(30, Qt.TransformationMode.SmoothTransformation)
        )
        return etiqueta

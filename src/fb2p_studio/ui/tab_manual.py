"""Pagina del manual de usuario: el LEEME.md renderizado dentro de Studio.

Autor: AJACH
Fecha: 2026-10-28 17:05:00

El manual es el mismo `LEEME.md` que se reparte en el zip y el MSI (una sola
fuente: `release/_template/LEEME.md`); el `.spec` lo embebe en el `.exe`. Esta
pagina solo lo lee y se lo pasa al visor, asi que escribirlo en un lugar y
mostrarlo en otro no puede desfasarse.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from fb2p_studio.core import discovery
from fb2p_studio.ui.widgets.markdown_viewer import MarkdownViewer


class ManualTab(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._path = discovery.manual_path()

        self._viewer = MarkdownViewer()

        self._lbl_origen = QLabel()
        self._lbl_origen.setObjectName("pista")
        self._btn_carpeta = QPushButton(self.tr("Abrir carpeta del manual"))
        self._btn_carpeta.clicked.connect(self._open_folder)

        barra = QHBoxLayout()
        barra.addWidget(self._lbl_origen, 1)
        barra.addWidget(self._btn_carpeta)

        raiz = QVBoxLayout(self)
        raiz.addWidget(self._viewer, 1)
        raiz.addLayout(barra)

        self._load()

    def _load(self) -> None:
        """Lee el manual; si no esta o no se puede leer, lo dice en vez de quedar en blanco."""
        if self._path is None:
            self._viewer.set_markdown(self._missing_text(self.tr("No se encontró el archivo del manual.")))
            self._lbl_origen.setText("")
            self._btn_carpeta.setEnabled(False)
            return
        try:
            texto = self._path.read_text(encoding="utf-8")
        except OSError as e:
            self._viewer.set_markdown(self._missing_text(str(e)))
            return
        self._viewer.set_markdown(texto)
        self._lbl_origen.setText(str(self._path))
        self._lbl_origen.setToolTip(str(self._path))
        # Dentro del .exe vive en la carpeta temporal de PyInstaller: abrirla no
        # le sirve a nadie, asi que el boton solo se ofrece cuando es un archivo real.
        self._btn_carpeta.setEnabled(not _is_temp_bundle(self._path))

    def _missing_text(self, detalle: str) -> str:
        return (
            f"# {self.tr('Manual no disponible')}\n\n{detalle}\n\n"
            + self.tr("Revisa el **LEEME.md** que viene junto al ejecutable, o escribe a **desarrolloads@adsecuador.com**.")
        )

    def _open_folder(self) -> None:
        if self._path is not None:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._path.parent)))

    # -- lo que llama MainWindow ---------------------------------------------
    def focus_search(self) -> None:
        self._viewer.focus_search()

    def refresh_theme(self) -> None:
        """Cambio de tema en caliente: el documento se viste de nuevo."""
        self._viewer.refresh_theme()

    @property
    def viewer(self) -> MarkdownViewer:
        return self._viewer


def _is_temp_bundle(ruta: Path) -> bool:
    """True si el manual esta dentro del paquete temporal de PyInstaller."""
    base = getattr(sys, "_MEIPASS", None)
    return bool(base) and str(ruta).lower().startswith(str(base).lower())

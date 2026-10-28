"""Visor de Markdown con indice de encabezados y busqueda.

Autor: AJACH
Fecha: 2026-10-28 17:05:00

Muestra un `.md` **renderizado** (encabezados, listas, tablas, codigo) sin sumar
dependencias: se apoya en `QTextBrowser.setMarkdown` (dialecto GitHub, con
tablas). Lo usa la pagina del manual de usuario, pero no sabe nada de ella: solo
recibe texto.

Lo que agrega sobre un `QTextBrowser` pelado:

    - un **indice** (a la izquierda) armado con los encabezados del documento.
      `setMarkdown` no genera anclas, asi que los enlaces internos `#seccion`
      no funcionan; el indice salta al encabezado midiendo su bloque.
    - **enlaces internos** (`[texto](#seccion)`): se resuelven por el texto del
      encabezado, como en GitHub; los externos abren en el navegador.
    - **busqueda** con vuelta al principio, hacia adelante y hacia atras.
    - una hoja de estilo derivada del **tema aplicado** (ADS, Claro u Oscuro):
      tablas con borde y codigo sobre fondo tenue, legibles en los tres.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QPalette, QTextCursor, QTextDocument
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSplitter,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from fb2p_studio.ui import theme, theme_ads

#: Niveles de encabezado que entran al indice. El 4 en adelante son detalle.
MAX_TOC_LEVEL = 3

_MONO = "Consolas, 'Courier New', monospace"


def slugify(texto: str) -> str:
    """El ancla de un encabezado, como la arma GitHub.

    Minusculas, sin signos de puntuacion (conserva letras con tilde, digitos y
    guiones) y espacios como guiones: `Solución de problemas` -> `solución-de-problemas`.
    """
    limpio = re.sub(r"[^\w\- ]", "", texto.strip().lower())
    return limpio.replace(" ", "-")


@dataclass(frozen=True, slots=True)
class Heading:
    """Un encabezado del documento: su nivel (1 = `#`) y su texto."""

    level: int
    text: str


class MarkdownViewer(QWidget):
    """Indice + documento + barra de busqueda."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._markdown = ""
        self._headings: list[Heading] = []
        #: Posicion (bloque) de cada item del indice dentro del documento.
        self._toc_blocks: list[int] = []

        self._toc = QListWidget()
        self._toc.setObjectName("indiceManual")
        self._toc.setMinimumWidth(150)
        self._toc.setMaximumWidth(340)
        # Los titulos largos se cortan con «...» (el tooltip trae el completo), en
        # vez de abrir una barra horizontal que tapa el indice.
        self._toc.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._toc.setTextElideMode(Qt.TextElideMode.ElideRight)
        self._toc.currentRowChanged.connect(self._on_toc_row)

        self._browser = QTextBrowser()
        self._browser.setObjectName("documentoManual")
        # Los enlaces los decide `_on_link`: con `setOpenExternalLinks` los
        # internos (#seccion) no llevan a ningun lado, porque `setMarkdown` no
        # genera anclas.
        self._browser.setOpenLinks(False)
        self._browser.anchorClicked.connect(self._on_link)

        self._search = QLineEdit()
        self._search.setPlaceholderText(self.tr("Buscar en el manual..."))
        self._search.setClearButtonEnabled(True)
        self._search.returnPressed.connect(lambda: self.find_text(self._search.text()))
        self._btn_prev = QPushButton(self.tr("Anterior"))
        self._btn_prev.clicked.connect(lambda: self.find_text(self._search.text(), backwards=True))
        self._btn_next = QPushButton(self.tr("Siguiente"))
        self._btn_next.clicked.connect(lambda: self.find_text(self._search.text()))
        self._lbl_result = QLabel()
        self._lbl_result.setObjectName("pista")

        barra = QHBoxLayout()
        barra.addWidget(self._search, 1)
        barra.addWidget(self._btn_prev)
        barra.addWidget(self._btn_next)
        barra.addWidget(self._lbl_result)

        derecha = QWidget()
        col = QVBoxLayout(derecha)
        col.setContentsMargins(0, 0, 0, 0)
        col.addLayout(barra)
        col.addWidget(self._browser, 1)

        self._split = QSplitter(Qt.Orientation.Horizontal)
        self._split.addWidget(self._toc)
        self._split.addWidget(derecha)
        self._split.setStretchFactor(0, 0)
        self._split.setStretchFactor(1, 1)
        self._split.setSizes([230, 700])
        self._split.setChildrenCollapsible(False)

        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(0, 0, 0, 0)
        raiz.addWidget(self._split)

    # ------------------------------------------------------------- contenido
    def set_markdown(self, text: str) -> None:
        """Muestra el texto y rearma el indice."""
        self._markdown = text
        self._render()

    def markdown(self) -> str:
        return self._markdown

    def headings(self) -> list[Heading]:
        """Los encabezados del indice, en orden de aparicion."""
        return list(self._headings)

    def refresh_theme(self) -> None:
        """Vuelve a vestir el documento con el tema aplicado, sin perder el lugar."""
        barra = self._browser.verticalScrollBar()
        posicion = barra.value()
        self._render()
        barra.setValue(posicion)

    def _render(self) -> None:
        self._browser.document().setDefaultStyleSheet(self._css())
        self._browser.setMarkdown(self._markdown)
        self._build_toc()

    def _css(self) -> str:
        """Hoja del documento, derivada del tema aplicado.

        Tablas con borde y codigo sobre un fondo apenas distinto del base: se leen
        igual en claro y en oscuro. Con ADS los encabezados toman el azul de la
        casa; en los otros dos, el color de texto de la paleta.
        """
        paleta = self.palette()
        base = paleta.color(QPalette.ColorRole.Base)
        claro = base.lightness() > 128
        suave = (base.darker(112) if claro else base.lighter(135)).name()
        borde = (base.darker(140) if claro else base.lighter(170)).name()
        reglas = [
            f"code, pre {{ font-family: {_MONO}; background-color: {suave}; }}",
            f"th, td {{ border: 1px solid {borde}; padding: 3px 8px; }}",
            f"th {{ background-color: {suave}; }}",
        ]
        if theme.current() == theme.ADS:
            reglas.append(f"h1, h2, h3 {{ color: {theme_ads.PRIMARY}; }}")
        return "\n".join(reglas)

    # ---------------------------------------------------------------- indice
    def _build_toc(self) -> None:
        """Arma el indice leyendo los bloques con nivel de encabezado."""
        self._headings = []
        self._toc_blocks = []
        self._toc.blockSignals(True)
        self._toc.clear()

        bloque = self._browser.document().begin()
        while bloque.isValid():
            nivel = bloque.blockFormat().headingLevel()
            texto = bloque.text().strip()
            if 1 <= nivel <= MAX_TOC_LEVEL and texto:
                self._headings.append(Heading(nivel, texto))
                self._toc_blocks.append(bloque.blockNumber())
                item = QListWidgetItem(("    " * (nivel - 1)) + texto)
                item.setToolTip(texto)
                self._toc.addItem(item)
            bloque = bloque.next()

        self._toc.blockSignals(False)

    def _on_toc_row(self, fila: int) -> None:
        if 0 <= fila < len(self._toc_blocks):
            self.scroll_to_block(self._toc_blocks[fila])

    def scroll_to_heading(self, index: int) -> None:
        """Salta al encabezado `index` del indice (y lo marca en la lista)."""
        if 0 <= index < len(self._toc_blocks):
            self._toc.setCurrentRow(index)  # dispara _on_toc_row

    def scroll_to_slug(self, slug: str) -> bool:
        """Salta al primer encabezado cuyo ancla (`slugify`) es `slug`."""
        objetivo = slug.strip().lower()
        for i, h in enumerate(self._headings):
            if slugify(h.text) == objetivo:
                self.scroll_to_heading(i)
                return True
        return False

    def _on_link(self, url: QUrl) -> None:
        if url.scheme() in ("http", "https", "mailto"):
            QDesktopServices.openUrl(url)
        elif not url.scheme() and url.fragment():
            self.scroll_to_slug(url.fragment())

    def scroll_to_block(self, numero: int) -> None:
        """Deja el bloque `numero` arriba del area visible."""
        documento = self._browser.document()
        bloque = documento.findBlockByNumber(numero)
        if not bloque.isValid():
            return
        rect = documento.documentLayout().blockBoundingRect(bloque)
        self._browser.verticalScrollBar().setValue(int(rect.top()))

    # --------------------------------------------------------------- busqueda
    def focus_search(self) -> None:
        self._search.setFocus()
        self._search.selectAll()

    def find_text(self, texto: str, *, backwards: bool = False) -> bool:
        """Busca `texto` desde el cursor y, si llega al borde, da la vuelta.

        Devuelve si lo encontro; ademas lo dice en la etiqueta junto al buscador.
        """
        self._lbl_result.clear()
        if not texto:
            return False

        opciones = QTextDocument.FindFlag(0)
        if backwards:
            opciones |= QTextDocument.FindFlag.FindBackward

        if self._browser.find(texto, opciones):
            return True
        # Sin coincidencia hasta el final (o el principio): se reintenta desde el
        # otro extremo, una sola vez.
        cursor = self._browser.textCursor()
        cursor.movePosition(
            QTextCursor.MoveOperation.End if backwards else QTextCursor.MoveOperation.Start
        )
        self._browser.setTextCursor(cursor)
        if self._browser.find(texto, opciones):
            self._lbl_result.setText(self.tr("Volvió al inicio") if not backwards else self.tr("Volvió al final"))
            return True
        self._lbl_result.setText(self.tr("Sin resultados"))
        return False

    # ----------------------------------------------------------------- acceso
    @property
    def browser(self) -> QTextBrowser:
        return self._browser

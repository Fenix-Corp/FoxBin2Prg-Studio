"""Listado de lo que contiene un proyecto y que va a pasar con cada archivo.

Responde la pregunta que antes sólo se contestaba despues de ejecutar: *¿esto
va a convertir lo que creo que va a convertir?*
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QLabel,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from fb2p_studio.core.validators import CONVIERTE, FALTA, NO_CONVERTIBLE, ProjectPreflight
from fb2p_studio.ui.theme import LogColors


class ProjectContentsView(QWidget):
    """Arbol de archivos del proyecto + una linea de resumen."""

    #: Emitida cuando cambia el contenido mostrado, con el resumen ya armado.
    summary_changed = Signal(str)

    def __init__(self, colors: LogColors, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._colors = colors
        self._ultimo: ProjectPreflight | None = None

        self._summary = QLabel()
        self._summary.setWordWrap(True)
        self._summary.setTextFormat(Qt.TextFormat.RichText)

        self._tree = QTreeWidget(self)
        self._tree.setColumnCount(3)
        self._tree.setHeaderLabels([self.tr("Archivo"), self.tr("Tipo"), self.tr("Estado")])
        self._tree.setRootIsDecorated(False)
        self._tree.setAlternatingRowColors(True)
        self._tree.setUniformRowHeights(True)
        self._tree.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._tree.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        cabecera = self._tree.header()
        cabecera.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        cabecera.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        cabecera.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._summary)
        layout.addWidget(self._tree, 1)

        self.clear(self.tr("Elegí un proyecto para ver su contenido."))

    # ------------------------------------------------------------------ api
    def set_colors(self, colors: LogColors) -> None:
        """Cambio de tema en caliente: se repinta lo que haya en pantalla."""
        self._colors = colors
        if self._ultimo is not None:
            self.show_preflight(self._ultimo)

    def clear(self, mensaje: str = "") -> None:
        self._ultimo = None
        self._tree.clear()
        self._set_summary(mensaje, self._colors.muted)

    def show_error(self, mensaje: str) -> None:
        """No se pudo leer el proyecto. Es informativo: no impide ejecutar."""
        self._ultimo = None
        self._tree.clear()
        self._set_summary(
            self.tr("No se pudo leer el contenido: {0}").format(mensaje), self._colors.warn
        )

    def show_preflight(self, pf: ProjectPreflight) -> None:
        self._ultimo = pf
        self._tree.clear()

        for check in pf.checks:
            fila = QTreeWidgetItem(
                [check.item.listed, check.item.type_label, self._status_text(check)]
            )
            color = {
                CONVIERTE: self._colors.ok,
                FALTA: self._colors.error,
                NO_CONVERTIBLE: self._colors.muted,
            }.get(check.status, self._colors.info)
            for col in range(3):
                fila.setForeground(col, color)

            detalle = [self.tr("Se lee: {0}").format(check.item.source)]
            if check.reason:
                detalle.append(self.tr("No se convierte: {0}.").format(check.reason))
            if check.other_drive:
                detalle.append(self.tr("Está en otra unidad que el proyecto."))
            if check.item.excluded:
                detalle.append(self.tr("Excluido del build (no afecta a la conversión)."))
            if check.item.main:
                detalle.append(self.tr("Es el programa principal."))
            fila.setToolTip(0, "\n".join(detalle))

            self._tree.addTopLevelItem(fila)

        self._set_summary(*self._resumen(pf))

    # ------------------------------------------------------------------ interno
    def _status_text(self, check) -> str:  # noqa: ANN001 — ItemCheck, evita el import ciclico
        base = {
            CONVIERTE: self.tr("se convierte"),
            FALTA: self.tr("FALTA en disco"),
            NO_CONVERTIBLE: self.tr("no convertible"),
        }.get(check.status, check.status)
        marcas = []
        if check.item.main:
            marcas.append(self.tr("principal"))
        if check.item.excluded:
            marcas.append(self.tr("excluido"))
        if check.other_drive:
            marcas.append(self.tr("otra unidad"))
        return f"{base} ({', '.join(marcas)})" if marcas else base

    def _resumen(self, pf: ProjectPreflight) -> tuple[str, object]:
        partes = [
            self.tr("<b>{0}</b> archivo(s) a convertir").format(pf.total_to_convert),
        ]
        if pf.include_project_file:
            partes.append(self.tr("incluyendo el propio {0}").format(pf.contents.project.name))
        else:
            partes.append(self.tr("sin el propio {0}").format(pf.contents.project.name))

        texto = " — ".join(partes) + "."
        color = self._colors.info

        if pf.missing:
            texto += " " + self.tr(
                "<b>{0} no está(n) en disco</b> y se van a saltar en silencio."
            ).format(len(pf.missing))
            color = self._colors.error
        if pf.unsupported:
            texto += " " + self.tr(
                "{0} no se convierte(n) (pasá el mouse por la fila para ver por qué)."
            ).format(len(pf.unsupported))
        if pf.other_drive:
            texto += " " + self.tr("{0} vive(n) en otra unidad.").format(len(pf.other_drive))
        for aviso in pf.contents.warnings:
            texto += " " + self.tr("Aviso al leer el proyecto: {0}.").format(aviso)
            color = self._colors.warn

        if pf.unsupported:
            # No leemos los foxbin2prg.cfg del arbol (herencia incluida), asi
            # que el soporte se predice con los valores por defecto. Decirlo es
            # mas honesto que dar un numero como si fuera definitivo.
            texto += " " + self.tr(
                "<i>Calculado con la configuración por defecto de FoxBin2Prg; un "
                "foxbin2prg.cfg puede cambiarlo.</i>"
            )

        return texto, color

    def _set_summary(self, texto: str, color: object) -> None:
        self._summary.setText(texto)
        self._summary.setStyleSheet(f"color: {color.name()};")  # type: ignore[union-attr]
        self.summary_changed.emit(texto)

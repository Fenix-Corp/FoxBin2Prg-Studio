"""Arbol de resultados de una corrida, con el detalle del error a la vista.

El log lineal sirve para diagnosticar, pero no escala: convertir un proyecto
son decenas de lineas y encontrar el archivo que fallo obliga a leerlas todas.
Aca cada operacion es una fila con sus archivos colgando, se puede filtrar por
problemas, y al elegir una fila con error se ve la excepcion completa
(`Message`, `LineNo`, `LineContents`, `Details`, `ErrorNo`) en vez de mezclada
entre el resto.

**La jerarquia sale del protocolo, no de un capricho:** FoxBin2Prg reporta
tiempo por operacion (`op_done.elapsedMs`), no por archivo, asi que el tiempo
vive en la fila de la operacion. Inventar un tiempo por archivo seria mentir.
"""

from __future__ import annotations

import re

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPlainTextEdit,
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from fb2p_studio.core.job import (
    DriverErrorEvent,
    FileProcessedEvent,
    JobDoneEvent,
    OpDoneEvent,
    OpErrorEvent,
    OpStartEvent,
)
from fb2p_studio.ui.theme import LogColors

#: Rol donde se guarda el detalle del error de una fila.
_ROL_DETALLE = int(Qt.ItemDataRole.UserRole) + 1
#: Rol que marca una fila como problematica, para el filtro.
_ROL_PROBLEMA = int(Qt.ItemDataRole.UserRole) + 2

COL_ARCHIVO, COL_DIRECCION, COL_ESTADO, COL_TIEMPO, COL_ERROR = range(5)

#: `Error 1098, No se ha encontrado el marcador...` — asi encabeza FoxBin2Prg
#: el volcado a stderr cuando el fallo no llega a ser una excepcion VFP.
_RE_ERROR = re.compile(r"^Error\s+\d+\s*,", re.IGNORECASE)


class ResultsView(QWidget):
    def __init__(self, colors: LogColors, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._colors = colors
        self._ops: dict[str, QTreeWidgetItem] = {}

        self._tree = QTreeWidget(self)
        self._tree.setColumnCount(5)
        self._tree.setHeaderLabels(
            [
                self.tr("Archivo"),
                self.tr("Direccion"),
                self.tr("Estado"),
                self.tr("Tiempo"),
                self.tr("Error"),
            ]
        )
        self._tree.setAlternatingRowColors(True)
        self._tree.setUniformRowHeights(True)
        self._tree.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._tree.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        cabecera = self._tree.header()
        cabecera.setSectionResizeMode(COL_ARCHIVO, QHeaderView.ResizeMode.Stretch)
        for col in (COL_DIRECCION, COL_ESTADO, COL_TIEMPO):
            cabecera.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        cabecera.setSectionResizeMode(COL_ERROR, QHeaderView.ResizeMode.Interactive)
        self._tree.currentItemChanged.connect(self._on_current_changed)

        self._solo_problemas = QCheckBox(self.tr("Sólo lo que falló o no se proceso"))
        self._solo_problemas.toggled.connect(self._apply_filter)
        self._resumen = QLabel()
        self._resumen.setObjectName("pista")

        barra = QHBoxLayout()
        barra.setContentsMargins(0, 0, 0, 0)
        barra.addWidget(self._resumen, 1)
        barra.addWidget(self._solo_problemas)

        # Detalle: aparece sólo cuando hay una excepcion que mostrar. Un panel
        # vacio permanente ocuparia media pantalla para no decir nada.
        self._detalle = QPlainTextEdit(self)
        self._detalle.setObjectName("bitacora")
        self._detalle.setReadOnly(True)
        self._detalle.setVisible(False)
        self._detalle.setPlaceholderText(
            self.tr("Elegí una fila con error para ver la excepcion completa.")
        )

        self._splitter = QSplitter(Qt.Orientation.Vertical, self)
        self._splitter.addWidget(self._tree)
        self._splitter.addWidget(self._detalle)
        self._splitter.setStretchFactor(0, 3)
        self._splitter.setStretchFactor(1, 1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(barra)
        layout.addWidget(self._splitter, 1)

        self.clear()

    # ------------------------------------------------------------------ api
    def set_colors(self, colors: LogColors) -> None:
        self._colors = colors

    def clear(self) -> None:
        self._tree.clear()
        self._ops.clear()
        self._detalle.clear()
        self._detalle.setVisible(False)
        self._resumen.setText(self.tr("Sin corridas todavía."))

    def start_op(self, ev: OpStartEvent) -> None:
        fila = QTreeWidgetItem(
            [ev.file, _direccion_legible(ev.direction), self.tr("procesando..."), "", ""]
        )
        fila.setToolTip(COL_ARCHIVO, ev.file)
        self._pintar(fila, self._colors.info)
        self._tree.addTopLevelItem(fila)
        fila.setExpanded(True)
        self._ops[ev.op_id] = fila
        self._tree.scrollToItem(fila)

    def add_file(self, ev: FileProcessedEvent) -> None:
        padre = self._ops.get(ev.op_id)
        if padre is None:
            return

        if ev.has_errors:
            estado, color, problema = self.tr("con errores"), self._colors.error, True
        elif not ev.processed:
            estado, color, problema = self.tr("no procesado"), self._colors.muted, True
        else:
            estado, color, problema = self.tr("OK"), self._colors.ok, False

        hijo = QTreeWidgetItem(
            [ev.file, _entrada_salida(ev.in_out), estado, "", ""]
        )
        hijo.setToolTip(COL_ARCHIVO, ev.file)
        if not ev.supported:
            hijo.setToolTip(
                COL_ESTADO,
                self.tr("FoxBin2Prg no convierte este tipo de archivo en esta direccion."),
            )
        hijo.setData(0, _ROL_PROBLEMA, problema)
        self._pintar(hijo, color)
        padre.addChild(hijo)

    def finish_op(self, ev: OpDoneEvent, diagnostico: str = "") -> None:
        """`diagnostico` es lo que FoxBin2Prg escribio en stderr durante la operacion.

        Hace falta porque **la mayoria de los errores no son excepciones**: para
        un texto mal formado, `execute()` devuelve el codigo de error (1098, por
        ejemplo) y manda a stderr la explicacion legible ("no se encontro el
        marcador de fin [ENDDEFINE] de la linea 35..."). Sin esto, la fila diria
        `rc=1098` y la explicacion quedaria enterrada en el log.
        """
        fila = self._ops.get(ev.op_id)
        if fila is None:
            return
        ok = ev.return_code == 0
        fila.setText(COL_ESTADO, self.tr("OK") if ok else self.tr("rc={0}").format(ev.return_code))
        fila.setText(COL_TIEMPO, _ms(ev.elapsed_ms))
        fila.setData(0, _ROL_PROBLEMA, not ok)
        self._pintar(fila, self._colors.ok if ok else self._colors.error)

        if not ok and diagnostico and not fila.data(0, _ROL_DETALLE):
            resumen = resumen_de_stderr(diagnostico)
            fila.setText(COL_ERROR, resumen)
            fila.setToolTip(COL_ERROR, resumen)
            fila.setData(
                0,
                _ROL_DETALLE,
                "\n".join(
                    [
                        self.tr("Operacion : {0}").format(ev.op_id),
                        self.tr("Codigo    : {0}").format(ev.return_code),
                        self.tr("Tiempo    : {0}").format(_ms(ev.elapsed_ms)),
                        "",
                        self.tr("FoxBin2Prg reporto:"),
                        diagnostico,
                    ]
                ),
            )
            self._tree.setCurrentItem(fila)
        self._apply_filter()

    def fail_op(self, ev: OpErrorEvent, diagnostico: str = "") -> None:
        fila = self._ops.get(ev.op_id)
        if fila is None:
            return
        fila.setText(COL_ESTADO, self.tr("ERROR"))
        fila.setText(COL_TIEMPO, _ms(ev.elapsed_ms))
        fila.setText(COL_ERROR, ev.message)
        fila.setToolTip(COL_ERROR, ev.message)
        fila.setData(0, _ROL_PROBLEMA, True)
        detalle = _detalle_de_error(ev)
        if diagnostico:
            detalle += "\n\n" + self.tr("FoxBin2Prg reporto:") + "\n" + diagnostico
        fila.setData(0, _ROL_DETALLE, detalle)
        self._pintar(fila, self._colors.error)
        self._tree.setCurrentItem(fila)  # abre el detalle solo
        self._apply_filter()

    def driver_error(self, ev: DriverErrorEvent) -> None:
        fila = QTreeWidgetItem(
            [self.tr("(driver)"), ev.stage, self.tr("ERROR"), "", ev.message]
        )
        fila.setData(0, _ROL_PROBLEMA, True)
        fila.setData(
            0,
            _ROL_DETALLE,
            self.tr("Fallo el propio driver VFP, antes o fuera de una operacion.\n\n")
            + self.tr("Etapa:   {0}\n").format(ev.stage)
            + self.tr("Mensaje: {0}").format(ev.message),
        )
        self._pintar(fila, self._colors.error)
        self._tree.addTopLevelItem(fila)
        self._tree.setCurrentItem(fila)

    def finish_job(self, ev: JobDoneEvent) -> None:
        archivos = sum(
            self._tree.topLevelItem(i).childCount() for i in range(self._tree.topLevelItemCount())
        )
        self._resumen.setText(
            self.tr("{0} operacion(es), {1} archivo(s) · {2} con error · {3}").format(
                ev.ok_count + ev.err_count, archivos, ev.err_count, _ms(ev.elapsed_ms)
            )
        )

    # ------------------------------------------------------------------ interno
    def _pintar(self, fila: QTreeWidgetItem, color) -> None:  # noqa: ANN001 — QColor
        for col in range(5):
            fila.setForeground(col, color)

    def _on_current_changed(self, actual: QTreeWidgetItem | None, _anterior) -> None:  # noqa: ANN001
        detalle = actual.data(0, _ROL_DETALLE) if actual is not None else None
        if detalle:
            self._detalle.setPlainText(str(detalle))
            self._detalle.setVisible(True)
        else:
            self._detalle.clear()
            self._detalle.setVisible(False)

    def _apply_filter(self) -> None:
        """Con el filtro puesto, una operacion se ve si ella o algun hijo falló."""
        solo = self._solo_problemas.isChecked()
        for i in range(self._tree.topLevelItemCount()):
            op = self._tree.topLevelItem(i)
            hijos_con_problema = 0
            for j in range(op.childCount()):
                hijo = op.child(j)
                problema = bool(hijo.data(0, _ROL_PROBLEMA))
                hijo.setHidden(solo and not problema)
                hijos_con_problema += int(problema)
            propio = bool(op.data(0, _ROL_PROBLEMA))
            op.setHidden(solo and not propio and hijos_con_problema == 0)


def resumen_de_stderr(texto: str) -> str:
    """La linea que explica el fallo, para la columna Error.

    FoxBin2Prg encabeza el volcado con una linea de guiones y lo cierra con
    datos de contexto (version del EXE, rutas). La util es la que empieza con
    `Error NNNN,`; si no esta, la primera linea con contenido.
    """
    lineas = [ln.strip() for ln in texto.splitlines() if ln.strip().strip("-")]
    for linea in lineas:
        if _RE_ERROR.match(linea):
            return linea
    return lineas[0] if lineas else ""


def _direccion_legible(direction: str) -> str:
    return {
        "BIN2PRG": "Bin → Prg",
        "PRG2BIN": "Prg → Bin",
        "*": "Proyecto (con el .pjx)",
        "*-": "Proyecto (sin el .pjx)",
    }.get(direction, direction or "auto")


def _entrada_salida(in_out: str) -> str:
    return {"I": "lee", "O": "genera"}.get(in_out, in_out)


def _ms(valor: int) -> str:
    if valor >= 1000:
        return f"{valor / 1000:.2f} s"
    return f"{valor} ms"


def _detalle_de_error(ev: OpErrorEvent) -> str:
    """La excepcion completa, en el orden en que se lee para diagnosticar."""
    lineas = [
        f"Operacion : {ev.op_id}",
        f"ErrorNo   : {ev.error_no}",
        f"Mensaje   : {ev.message}",
        f"Linea     : {ev.line_no}",
    ]
    if ev.line_contents:
        lineas += ["", "Codigo de la linea:", ev.line_contents]
    if ev.details:
        lineas += ["", "Detalle:", ev.details]
    lineas += ["", f"Tiempo hasta el fallo: {_ms(ev.elapsed_ms)}"]
    return "\n".join(lineas)

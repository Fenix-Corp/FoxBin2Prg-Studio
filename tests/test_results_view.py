"""Arbol de resultados: lo que muestra y de donde saca el detalle del error.

El caso que motiva la mitad de estos tests aparecio corriendo una conversion
real sobre un `.sc2` truncado: **FoxBin2Prg no lanza una excepcion**, devuelve
`rc=1098` y escribe la explicacion legible en stderr. Sin recogerla, la fila
decia `rc=1098` y el motivo quedaba enterrado en el log.
"""

from __future__ import annotations

import pytest
from PySide6.QtGui import QColor

from fb2p_studio.core.job import (
    FileProcessedEvent,
    JobDoneEvent,
    OpDoneEvent,
    OpErrorEvent,
    OpStartEvent,
)
from fb2p_studio.ui.theme import LogColors
from fb2p_studio.ui.widgets.results_view import (
    COL_ERROR,
    COL_ESTADO,
    COL_TIEMPO,
    ResultsView,
    resumen_de_stderr,
)

#: Volcado real de FoxBin2Prg 1.21.05 ante un .sc2 cortado a la mitad.
STDERR_REAL = """\
----------------------------------------------------------------------------------------------------
Error 1098, No se ha encontrado el marcador de fin [ENDDEFINE] de la linea 35 para el identificador [formset]
analyzecodeblock_define_class, 11239
FoxBin2Prg: [D:\\FOXBIN2PRG\\FOXBIN2PRG.EXE] (EXE Version: v1.21.05)
tc_InputFile = [C:\\PROY\\ARTDETALLE.SC2]
Archivo origen: C:\\proy\\artdetalle.sc2"""


# --------------------------------------------------------------- resumen_de_stderr
def test_elige_la_linea_del_error() -> None:
    """De todo el volcado, la util es la que empieza con `Error NNNN,`."""
    assert resumen_de_stderr(STDERR_REAL).startswith("Error 1098, No se ha encontrado")


def test_ignora_la_linea_de_guiones() -> None:
    assert "---" not in resumen_de_stderr(STDERR_REAL)


def test_sin_linea_de_error_toma_la_primera_util() -> None:
    texto = "-------------\nAlgo salio mal\ncontexto irrelevante"
    assert resumen_de_stderr(texto) == "Algo salio mal"


@pytest.mark.parametrize("texto", ["", "   ", "-----\n-----"])
def test_sin_nada_que_resumir(texto: str) -> None:
    assert resumen_de_stderr(texto) == ""


# --------------------------------------------------------------------- el arbol
@pytest.fixture
def vista(qapp) -> ResultsView:  # noqa: ANN001, ARG001 — qapp lo da pytest-qt
    colores = LogColors(
        info=QColor("#000000"),
        ok=QColor("#1a6b3c"),
        warn=QColor("#8a5e00"),
        error=QColor("#9d2235"),
        muted=QColor("#5b6470"),
    )
    return ResultsView(colores)


def _op_start(op_id: str = "op1") -> OpStartEvent:
    return OpStartEvent(op_id=op_id, file=r"C:\proy\app.pjx", direction="*")


def _archivo(nombre: str, *, procesado=True, con_errores=False, soportado=True):
    return FileProcessedEvent(
        op_id="op1",
        file=nombre,
        in_out="I",
        processed=procesado,
        has_errors=con_errores,
        supported=soportado,
        expanded=True,
    )


def test_una_operacion_con_sus_archivos(vista: ResultsView) -> None:
    vista.start_op(_op_start())
    vista.add_file(_archivo(r"C:\proy\a.scx"))
    vista.add_file(_archivo(r"C:\proy\b.scx"))
    vista.finish_op(OpDoneEvent(op_id="op1", return_code=0, elapsed_ms=263))

    op = vista._tree.topLevelItem(0)  # noqa: SLF001
    assert op.childCount() == 2
    assert op.text(COL_ESTADO) == "OK"
    assert op.text(COL_TIEMPO) == "263 ms"


def test_el_tiempo_vive_en_la_operacion_no_en_el_archivo(vista: ResultsView) -> None:
    """FoxBin2Prg mide por operacion; poner un tiempo por archivo seria inventarlo."""
    vista.start_op(_op_start())
    vista.add_file(_archivo(r"C:\proy\a.scx"))
    vista.finish_op(OpDoneEvent(op_id="op1", return_code=0, elapsed_ms=500))

    op = vista._tree.topLevelItem(0)  # noqa: SLF001
    assert op.text(COL_TIEMPO) == "500 ms"
    assert op.child(0).text(COL_TIEMPO) == ""


def test_los_segundos_se_muestran_como_segundos(vista: ResultsView) -> None:
    vista.start_op(_op_start())
    vista.finish_op(OpDoneEvent(op_id="op1", return_code=0, elapsed_ms=2500))
    assert vista._tree.topLevelItem(0).text(COL_TIEMPO) == "2.50 s"  # noqa: SLF001


def test_un_rc_distinto_de_cero_trae_el_motivo_del_stderr(vista: ResultsView) -> None:
    """El caso real: sin excepcion, pero con explicacion en stderr."""
    vista.start_op(_op_start())
    vista.finish_op(
        OpDoneEvent(op_id="op1", return_code=1098, elapsed_ms=120), STDERR_REAL
    )

    op = vista._tree.topLevelItem(0)  # noqa: SLF001
    assert op.text(COL_ESTADO) == "rc=1098"
    assert op.text(COL_ERROR).startswith("Error 1098")
    assert "ENDDEFINE" in vista._detalle.toPlainText()  # noqa: SLF001
    assert "v1.21.05" in vista._detalle.toPlainText()  # noqa: SLF001


def test_sin_error_no_hay_panel_de_detalle(vista: ResultsView) -> None:
    vista.start_op(_op_start())
    vista.finish_op(OpDoneEvent(op_id="op1", return_code=0, elapsed_ms=10), STDERR_REAL)
    assert vista._detalle.toPlainText() == ""  # noqa: SLF001


def test_una_excepcion_muestra_los_campos_de_la_excepcion(vista: ResultsView) -> None:
    vista.start_op(_op_start())
    vista.fail_op(
        OpErrorEvent(
            op_id="op1",
            error_no=11,
            message="Function argument value, type, or count is invalid",
            line_no=842,
            line_contents="lcX = SUBSTR(lcY, 0)",
            details="detalle extra",
            elapsed_ms=90,
        )
    )
    detalle = vista._detalle.toPlainText()  # noqa: SLF001
    assert "ErrorNo   : 11" in detalle
    assert "842" in detalle
    assert "lcX = SUBSTR(lcY, 0)" in detalle
    assert "detalle extra" in detalle


def test_el_filtro_deja_sólo_lo_problematico(vista: ResultsView) -> None:
    vista.start_op(_op_start())
    vista.add_file(_archivo(r"C:\proy\ok.scx"))
    vista.add_file(_archivo(r"C:\proy\mal.scx", con_errores=True))
    vista.add_file(_archivo(r"C:\proy\saltado.txt", procesado=False, soportado=False))
    vista.finish_op(OpDoneEvent(op_id="op1", return_code=0, elapsed_ms=10))

    op = vista._tree.topLevelItem(0)  # noqa: SLF001
    vista._solo_problemas.setChecked(True)  # noqa: SLF001

    assert op.child(0).isHidden() is True  # el OK
    assert op.child(1).isHidden() is False  # el que fallo
    assert op.child(2).isHidden() is False  # el que no se proceso


def test_una_operacion_sin_problemas_se_esconde_entera(vista: ResultsView) -> None:
    vista.start_op(_op_start())
    vista.add_file(_archivo(r"C:\proy\ok.scx"))
    vista.finish_op(OpDoneEvent(op_id="op1", return_code=0, elapsed_ms=10))

    vista._solo_problemas.setChecked(True)  # noqa: SLF001
    assert vista._tree.topLevelItem(0).isHidden() is True  # noqa: SLF001


def test_el_resumen_cuenta_operaciones_y_archivos(vista: ResultsView) -> None:
    vista.start_op(_op_start())
    vista.add_file(_archivo(r"C:\proy\a.scx"))
    vista.add_file(_archivo(r"C:\proy\b.scx"))
    vista.finish_op(OpDoneEvent(op_id="op1", return_code=0, elapsed_ms=10))
    vista.finish_job(JobDoneEvent(ok_count=1, err_count=0, elapsed_ms=127))

    resumen = vista._resumen.text()  # noqa: SLF001
    assert "1 operacion(es)" in resumen
    assert "2 archivo(s)" in resumen
    assert "127 ms" in resumen


def test_una_corrida_nueva_limpia_la_anterior(vista: ResultsView) -> None:
    vista.start_op(_op_start())
    vista.finish_op(OpDoneEvent(op_id="op1", return_code=1, elapsed_ms=1), STDERR_REAL)
    vista.clear()

    assert vista._tree.topLevelItemCount() == 0  # noqa: SLF001
    assert vista._detalle.toPlainText() == ""  # noqa: SLF001

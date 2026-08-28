"""La ventana tiene que entrar en 1366x768 maximizada, sin montarse.

Es la resolucion mas chica en uso en el equipo. El defecto que motiva estos
tests: el preview del `job.ini` usaba `setFixedHeight()` y las opciones
avanzadas no colapsaban de verdad, asi que el **minimo** de la ventana trepaba
a 1013 px de alto. Como no entraba en la pantalla, Qt aplastaba los controles
por debajo de su minimo y se dibujaban unos sobre otros.

Un solapamiento se puede medir (dos hermanos visibles cuyos rectangulos se
intersectan), asi que esto no depende de mirar capturas.
"""

from __future__ import annotations

import pytest
from PySide6.QtCore import QCoreApplication, QEvent, QSettings
from PySide6.QtWidgets import QWidget

from fb2p_studio.ui import theme

#: Resolucion objetivo. El alto util descuenta la barra de tareas de Windows
#: (~40 px), que es lo que queda al maximizar.
ANCHO, ALTO = 1366, 768
ALTO_UTIL = ALTO - 40


@pytest.fixture(autouse=True, scope="module")
def _config_aislada(tmp_path_factory) -> None:  # noqa: ANN001
    """QSettings a un directorio temporal: no tocamos el .ini del usuario."""
    destino = tmp_path_factory.mktemp("qsettings")
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(destino))


@pytest.fixture
def ventana(qapp):  # noqa: ANN001, ANN201
    """Fabrica de ventanas por tema, ya dimensionadas.

    Las cierra al terminar: `theme.apply()` reestiliza TODAS las ventanas
    vivas de la aplicacion, asi que dejarlas acumular hace que cada test
    cueste mas que el anterior (medido: 0,2 s la primera, 2,6 s la tercera).
    """
    creadas = []

    def _crear(tema: str):  # noqa: ANN202
        from fb2p_studio.core.settings import Settings
        from fb2p_studio.ui.main_window import MainWindow

        # Sin chequeo al arrancar: este test no debe salir a la red.
        Settings().check_updates_on_start = False

        win = MainWindow(log_colors=theme.apply(qapp, tema))
        win._apply_theme(tema)  # noqa: SLF001
        win.resize(ANCHO, ALTO_UTIL)
        win.show()
        qapp.processEvents()
        creadas.append(win)
        return win

    yield _crear

    for win in creadas:
        win.close()
        win.deleteLater()
    # `processEvents()` NO entrega los DeferredDelete: hay que pedirlos. Sin
    # esto las ventanas siguen vivas, cada `theme.apply()` las reestila a
    # todas y los tests se vuelven cuadraticamente mas lentos.
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    qapp.processEvents()


def _visible(w: QWidget) -> bool:
    return w.isVisible() and w.width() > 0 and w.height() > 0


def _solapamientos(raiz: QWidget) -> list[str]:
    """Pares de hermanos directos visibles cuyos rectangulos se pisan."""
    choques: list[str] = []
    pila = [raiz]
    vistos: set[int] = set()
    while pila:
        padre = pila.pop()
        if id(padre) in vistos:
            continue
        vistos.add(id(padre))
        hijos = [h for h in padre.children() if isinstance(h, QWidget) and _visible(h)]
        for i, a in enumerate(hijos):
            for b in hijos[i + 1 :]:
                inter = a.geometry().intersected(b.geometry())
                if inter.width() > 1 and inter.height() > 1:
                    choques.append(
                        f"{type(a).__name__} y {type(b).__name__} se pisan en "
                        f"{inter.width()}x{inter.height()} px dentro de {type(padre).__name__}"
                    )
        pila += hijos
    return choques


@pytest.mark.parametrize("tema", [theme.SISTEMA, theme.ADS])
def test_la_ventana_entra_en_la_pantalla(ventana, tema: str) -> None:  # noqa: ANN001
    """Si el minimo no entra, Qt aplasta los controles y se montan."""
    win = ventana(tema)
    minimo = win.minimumSizeHint()

    assert minimo.height() <= ALTO_UTIL, (
        f"tema {tema}: la ventana pide {minimo.height()} px de alto y la pantalla "
        f"deja {ALTO_UTIL}"
    )
    assert minimo.width() <= ANCHO, (
        f"tema {tema}: la ventana pide {minimo.width()} px de ancho y la pantalla "
        f"tiene {ANCHO}"
    )


@pytest.mark.parametrize("tema", [theme.SISTEMA, theme.ADS])
def test_el_alto_pedido_se_respeta(ventana, tema: str) -> None:  # noqa: ANN001
    win = ventana(tema)
    assert win.height() == ALTO_UTIL


@pytest.mark.parametrize("tema", [theme.SISTEMA, theme.ADS])
def test_ninguna_pestana_se_monta(ventana, qapp, tema: str) -> None:  # noqa: ANN001
    win = ventana(tema)
    for i in range(win._tabs.count()):  # noqa: SLF001
        win._tabs.setCurrentIndex(i)  # noqa: SLF001
        qapp.processEvents()
        choques = _solapamientos(win._tabs.widget(i))  # noqa: SLF001
        assert not choques, f"tema {tema}, pestana {win._tabs.tabText(i)}: " + "; ".join(  # noqa: SLF001
            choques
        )


@pytest.mark.parametrize("tema", [theme.SISTEMA, theme.ADS])
def test_con_las_opciones_avanzadas_desplegadas_tampoco(ventana, qapp, tema: str) -> None:  # noqa: ANN001
    """El peor caso: el grupo colapsable abierto suma ~170 px."""
    win = ventana(tema)
    for tab in (win._tab_convert, win._tab_project):  # noqa: SLF001
        tab._adv.setChecked(True)  # noqa: SLF001
    qapp.processEvents()

    for i in range(win._tabs.count()):  # noqa: SLF001
        win._tabs.setCurrentIndex(i)  # noqa: SLF001
        qapp.processEvents()
        assert not _solapamientos(win._tabs.widget(i))  # noqa: SLF001


def test_las_opciones_avanzadas_colapsan_de_verdad(ventana, qapp) -> None:  # noqa: ANN001
    """Desmarcado tiene que OCULTAR, no sólo deshabilitar: un QGroupBox
    checkable deja a los hijos ocupando su lugar en gris."""
    win = ventana(theme.SISTEMA)
    adv = win._tab_convert._adv  # noqa: SLF001

    adv.setChecked(True)
    qapp.processEvents()
    desplegado = adv.sizeHint().height()

    adv.setChecked(False)
    qapp.processEvents()
    colapsado = adv.sizeHint().height()

    assert colapsado < desplegado / 2, (
        f"colapsado mide {colapsado} px y desplegado {desplegado}: no esta colapsando"
    )


def test_el_preview_puede_encoger_y_hacer_scroll(ventana) -> None:  # noqa: ANN001
    """Con altura fija nunca aparecia el scroll y no se llegaba al final."""
    win = ventana(theme.SISTEMA)
    edit = win._tab_convert._preview._edit  # noqa: SLF001

    assert edit.minimumHeight() < edit.maximumHeight(), (
        "el preview tiene altura fija: no puede ceder espacio ni mostrar scroll"
    )
    assert edit.verticalScrollBarPolicy().name == "ScrollBarAsNeeded"


def test_las_rutas_largas_no_estiran_la_ventana(ventana) -> None:  # noqa: ANN001
    """Una ruta larga en Acerca de le fijaba a la ventana 1318 px de ancho."""
    win = ventana(theme.SISTEMA)
    etiqueta = win._tab_about._lbl_fb2p  # noqa: SLF001

    etiqueta.setText(r"D:\una\ruta\absurdamente\larga\que\nadie\deberia\tener\pero\pasa\x.exe")
    assert etiqueta.minimumSizeHint().width() <= 100
    assert etiqueta.toolTip().endswith("x.exe"), "el texto completo tiene que quedar accesible"

"""El menu lateral: navegacion, colapso, pie de preferencias y atajos.

Autor: AJACH
Fecha: 2026-10-28 15:33:32

Cubre lo que reemplaza a la barra de menus y a la fila de pestanas. `SideNav`
solo navega (no conoce las paginas), asi que sus pruebas no necesitan una
ventana; las de `MainWindow` verifican el cableado.
"""

from __future__ import annotations

import pytest
from PySide6.QtCore import QCoreApplication, QEvent, QSettings
from PySide6.QtWidgets import QPushButton

from fb2p_studio.ui import sidenav, theme
from fb2p_studio.ui.sidenav import SideNav


@pytest.fixture(autouse=True, scope="module")
def _config_aislada(tmp_path_factory) -> None:  # noqa: ANN001
    """QSettings a un directorio temporal: no tocamos el .ini del usuario."""
    destino = tmp_path_factory.mktemp("qsettings_nav")
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(destino))


@pytest.fixture
def nav(qapp) -> SideNav:  # noqa: ANN001
    barra = SideNav()
    barra.add_group("Herramientas")
    barra.add_page("Uno", 0xE8AB)
    barra.add_page("Dos", 0xE838)
    barra.add_page("Tres", 0xE946)
    barra.add_group("Preferencias", footer=True)
    barra.add_action("Tema", sidenav.GLYPH_THEME)
    return barra


def test_la_primera_pagina_arranca_elegida(nav: SideNav) -> None:
    assert nav.count() == 3
    assert nav.current_index() == 0


def test_select_avisa_incluso_si_ya_estaba_elegida(nav: SideNav) -> None:
    avisos: list[int] = []
    nav.currentChanged.connect(avisos.append)

    nav.select(0)
    nav.select(2)

    assert avisos == [0, 2]
    assert nav.current_index() == 2


def test_select_ignora_indices_fuera_de_rango(nav: SideNav) -> None:
    nav.select(9)
    nav.select(-1)
    assert nav.current_index() == 0


def test_step_da_la_vuelta(nav: SideNav) -> None:
    nav.step(-1)
    assert nav.current_index() == 2
    nav.step(1)
    assert nav.current_index() == 0


def test_page_path_devuelve_grupo_y_titulo(nav: SideNav) -> None:
    assert nav.page_path(1) == ("Herramientas", "Dos")


def test_una_accion_del_pie_no_es_pagina(nav: SideNav) -> None:
    """«Tema» abre un menu o un dialogo: no puede quedar como pagina elegible."""
    assert nav.count() == 3


def test_colapsar_deja_solo_iconos_con_tooltip(nav: SideNav) -> None:
    nav.set_collapsed(True)

    assert nav.is_collapsed()
    assert nav.width() == sidenav.COLLAPSED_WIDTH
    botones = [b for b in nav.findChildren(QPushButton) if b.objectName() == "navItem"]
    assert botones
    for boton in botones:
        assert boton.text() == ""
        assert boton.toolTip() == boton.property("titulo")

    nav.set_collapsed(False)
    assert nav.width() == sidenav.EXPANDED_WIDTH
    for boton in botones:
        assert boton.text() == boton.property("titulo")
        assert boton.toolTip() == ""


def test_el_boton_de_colapsar_cambia_su_nombre(nav: SideNav) -> None:
    antes = nav.toggle_button.property("titulo")
    nav.toggle()
    assert nav.toggle_button.property("titulo") != antes
    nav.toggle()
    assert nav.toggle_button.property("titulo") == antes


@pytest.mark.parametrize("tema", [theme.CLARO, theme.OSCURO, theme.ADS])
def test_apply_theme_no_rompe_con_ningun_tema(qapp, nav: SideNav, tema: str) -> None:  # noqa: ANN001
    theme.apply(qapp, tema)
    nav.apply_theme(tema)
    # Con ADS la hoja es la global (la barra no pone una local); con los otros
    # dos, la barra arma la suya.
    assert (nav.styleSheet() == "") == (tema == theme.ADS)


# --- cableado en la ventana -------------------------------------------------


@pytest.fixture
def ventana(qapp):  # noqa: ANN001, ANN201
    from fb2p_studio.core.settings import Settings
    from fb2p_studio.ui.main_window import MainWindow

    Settings().check_updates_on_start = False  # sin salir a la red
    win = MainWindow(log_colors=theme.apply(qapp, theme.CLARO))
    win.show()
    qapp.processEvents()
    yield win
    win.close()
    win.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    qapp.processEvents()


def test_la_ventana_ya_no_tiene_barra_de_menus(ventana) -> None:  # noqa: ANN001
    assert ventana.menuBar().actions() == []


def test_elegir_una_opcion_muestra_su_pagina_y_encabezado(ventana) -> None:  # noqa: ANN001
    ventana._nav.select(1)  # noqa: SLF001

    assert ventana._pages.currentWidget() is ventana._tab_project  # noqa: SLF001
    assert ventana._section_title.text().endswith("Proyecto")  # noqa: SLF001


def test_ctrl_tab_recorre_las_paginas(ventana) -> None:  # noqa: ANN001
    from PySide6.QtGui import QShortcut

    atajos = {s.key().toString(): s for s in ventana.findChildren(QShortcut)}
    assert {"Ctrl+Tab", "Ctrl+Shift+Tab", "Ctrl+PgDown", "Ctrl+PgUp"} <= set(atajos)

    atajos["Ctrl+Tab"].activated.emit()
    assert ventana._pages.currentWidget() is ventana._tab_project  # noqa: SLF001
    atajos["Ctrl+Shift+Tab"].activated.emit()
    assert ventana._pages.currentWidget() is ventana._tab_convert  # noqa: SLF001


def test_el_menu_de_tema_cambia_y_recuerda_el_tema(ventana) -> None:  # noqa: ANN001
    from fb2p_studio.core.settings import Settings

    accion = next(
        a
        for a in ventana._acciones_tema.actions()  # noqa: SLF001
        if a.data() == theme.OSCURO
    )
    accion.trigger()

    assert theme.current() == theme.OSCURO
    assert Settings().theme == theme.OSCURO
    marcadas = [a.data() for a in ventana._acciones_tema.actions() if a.isChecked()]  # noqa: SLF001
    assert marcadas == [theme.OSCURO]

"""El visor de Markdown y el manual de usuario (LEEME.md) que muestra.

Autor: AJACH
Fecha: 2026-10-28 17:20:00

Dos cosas distintas, las dos con prueba:

- `MarkdownViewer`: indice de encabezados, enlaces internos, busqueda, tema.
- El manual real: que exista, que se renderice (tablas incluidas) y que no se
  quede atras del programa (cada pagina del menu lateral tiene su seccion).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from PySide6.QtCore import QCoreApplication, QEvent, QSettings

from fb2p_studio.core import discovery
from fb2p_studio.ui import theme
from fb2p_studio.ui.widgets.markdown_viewer import MarkdownViewer, slugify

RAIZ = Path(__file__).resolve().parents[1]

#: Un documento con los niveles que importan: 1-3 entran al indice, 4 no.
MUESTRA = """# Titulo

Texto del titulo.

## Primera seccion

| a | b |
|---|---|
| 1 | 2 |

### Detalle uno

#### Demasiado hondo

## Solución de problemas

Relleno.
""" + "\n".join(f"Linea de relleno numero {i}." for i in range(120)) + """

## Ultima seccion

Aqui termina. [Ir a problemas](#solución-de-problemas)
"""


@pytest.fixture(autouse=True, scope="module")
def _config_aislada(tmp_path_factory) -> None:  # noqa: ANN001
    """QSettings a un directorio temporal: no tocamos el .ini del usuario."""
    destino = tmp_path_factory.mktemp("qsettings_manual")
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(destino))


@pytest.fixture
def visor(qapp) -> MarkdownViewer:  # noqa: ANN001
    v = MarkdownViewer()
    v.resize(900, 500)
    v.set_markdown(MUESTRA)
    v.show()
    qapp.processEvents()
    yield v
    v.close()
    v.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


# ----------------------------------------------------------------- slugify
@pytest.mark.parametrize(
    ("texto", "ancla"),
    [
        ("Preferencias", "preferencias"),
        ("Solución de problemas", "solución-de-problemas"),
        ("  Pre-requisito: que VFP9 sea SP2 (build ≥ 3504)  ", "pre-requisito-que-vfp9-sea-sp2-build--3504"),
        ("La ventana", "la-ventana"),
    ],
)
def test_slugify_como_github(texto: str, ancla: str) -> None:
    assert slugify(texto) == ancla


# ------------------------------------------------------------------ indice
def test_el_indice_trae_los_niveles_1_a_3(visor: MarkdownViewer) -> None:
    niveles = [(h.level, h.text) for h in visor.headings()]
    assert niveles == [
        (1, "Titulo"),
        (2, "Primera seccion"),
        (3, "Detalle uno"),
        (2, "Solución de problemas"),
        (2, "Ultima seccion"),
    ]  # el de nivel 4 no entra


def test_el_indice_se_rearma_al_cambiar_el_texto(visor: MarkdownViewer) -> None:
    visor.set_markdown("# Otro\n\n## Uno\n")
    assert [h.text for h in visor.headings()] == ["Otro", "Uno"]


def test_elegir_un_encabezado_baja_hasta_el(visor: MarkdownViewer, qapp) -> None:  # noqa: ANN001
    barra = visor.browser.verticalScrollBar()
    assert barra.maximum() > 0, "el documento de prueba tiene que ser mas alto que el visor"
    arriba = barra.value()  # el margen del documento: unos pocos px, no necesariamente 0

    visor.scroll_to_heading(4)  # «Ultima seccion», al final
    qapp.processEvents()

    assert barra.value() > arriba + 100
    visor.scroll_to_heading(0)
    assert barra.value() <= arriba + 10


# ---------------------------------------------------------------- enlaces
def test_un_enlace_interno_lleva_al_encabezado(visor: MarkdownViewer) -> None:
    barra = visor.browser.verticalScrollBar()
    antes = barra.value()

    assert visor.scroll_to_slug("solución-de-problemas") is True
    assert barra.value() > antes + 20


def test_un_enlace_interno_inexistente_no_rompe(visor: MarkdownViewer) -> None:
    assert visor.scroll_to_slug("no-existe") is False


def test_los_enlaces_externos_abren_en_el_navegador(visor: MarkdownViewer, monkeypatch) -> None:  # noqa: ANN001
    from PySide6.QtCore import QUrl

    abiertos: list[str] = []
    monkeypatch.setattr(
        "fb2p_studio.ui.widgets.markdown_viewer.QDesktopServices.openUrl",
        lambda url: abiertos.append(url.toString()),
    )
    visor._on_link(QUrl("https://github.com/Fenix-Corp/Utilities-Dist"))  # noqa: SLF001
    visor._on_link(QUrl("#primera-seccion"))  # noqa: SLF001  (interno: no abre nada)

    assert abiertos == ["https://github.com/Fenix-Corp/Utilities-Dist"]


# --------------------------------------------------------------- busqueda
def test_buscar_encuentra_y_da_la_vuelta(visor: MarkdownViewer) -> None:
    assert visor.find_text("Ultima seccion") is True  # hacia adelante
    # Ya esta en el ultimo resultado: otra vez, vuelve al principio y lo reencuentra.
    assert visor.find_text("Ultima seccion") is True
    assert visor._lbl_result.text() != ""  # noqa: SLF001 — avisa que dio la vuelta


def test_buscar_hacia_atras(visor: MarkdownViewer) -> None:
    assert visor.find_text("Titulo", backwards=True) is True  # da la vuelta desde el inicio


def test_buscar_sin_resultados_lo_dice(visor: MarkdownViewer) -> None:
    assert visor.find_text("palabra-que-no-esta-en-ningun-lado") is False
    assert "Sin resultados" in visor._lbl_result.text()  # noqa: SLF001


def test_buscar_texto_vacio_no_hace_nada(visor: MarkdownViewer) -> None:
    assert visor.find_text("") is False


# ------------------------------------------------------------------- tema
def test_la_hoja_cambia_con_el_tema(visor: MarkdownViewer, qapp) -> None:  # noqa: ANN001
    theme.apply(qapp, theme.ADS)
    ads = visor._css()  # noqa: SLF001
    theme.apply(qapp, theme.OSCURO)
    oscuro = visor._css()  # noqa: SLF001
    theme.apply(qapp, theme.CLARO)

    assert "h1, h2, h3" in ads, "con ADS los encabezados llevan el azul de la casa"
    assert "h1, h2, h3" not in oscuro
    assert ads != oscuro


def test_refrescar_el_tema_conserva_el_lugar(visor: MarkdownViewer, qapp) -> None:  # noqa: ANN001
    visor.scroll_to_heading(3)
    qapp.processEvents()
    antes = visor.browser.verticalScrollBar().value()
    assert antes > 0

    visor.refresh_theme()

    assert visor.browser.verticalScrollBar().value() == antes


# ------------------------------------------------------------- el manual real
def test_el_manual_existe_y_discovery_lo_encuentra() -> None:
    ruta = discovery.manual_path()
    assert ruta is not None, "falta release/_template/LEEME.md"
    assert ruta.name == "LEEME.md"
    assert ruta.read_text(encoding="utf-8").startswith("# FoxBin2Prg-Studio")


def test_el_manual_se_renderiza_con_sus_tablas(visor: MarkdownViewer) -> None:
    visor.set_markdown(discovery.manual_path().read_text(encoding="utf-8"))  # type: ignore[union-attr]

    assert len(visor.headings()) >= 12
    assert "<table" in visor.browser.toHtml(), "las tablas del manual no se estan renderizando"


#: Cada pagina del menu lateral y cada funcion con atajo tiene que tener su
#: seccion: si se agrega una pagina o se renombra una, el manual no puede
#: quedarse atras sin que esta prueba lo diga.
SECCIONES_OBLIGATORIAS = [
    "La ventana",
    "Atajos de teclado",
    "Convertir un archivo",
    "Opciones avanzadas",
    "Convertir un proyecto",
    "Leer los resultados",
    "Preferencias",
    "Temas",
    "Actualizaciones",
    "Acerca de",
    "Solución de problemas",
    "Reportar problemas",
]


@pytest.mark.parametrize("titulo", SECCIONES_OBLIGATORIAS)
def test_el_manual_cubre_cada_pagina_y_funcion(visor: MarkdownViewer, titulo: str) -> None:
    visor.set_markdown(discovery.manual_path().read_text(encoding="utf-8"))  # type: ignore[union-attr]
    assert titulo in [h.text for h in visor.headings()]


def test_los_enlaces_internos_del_manual_apuntan_a_un_encabezado(visor: MarkdownViewer) -> None:
    """Un `[texto](#ancla)` sin encabezado destino seria un enlace muerto."""
    texto = discovery.manual_path().read_text(encoding="utf-8")  # type: ignore[union-attr]
    visor.set_markdown(texto)
    anclas = {slugify(h.text) for h in visor.headings()}

    for ancla in re.findall(r"\]\(#([^)]+)\)", texto):
        assert ancla in anclas, f"el manual enlaza a #{ancla}, que no es ningun encabezado"


def test_el_manual_no_cita_atajos_que_no_existen() -> None:
    """Los atajos del manual tienen que ser los que cablea la ventana."""
    manual = discovery.manual_path().read_text(encoding="utf-8")  # type: ignore[union-attr]
    ventana = (RAIZ / "src" / "fb2p_studio" / "ui" / "main_window.py").read_text(encoding="utf-8")

    for tecla in ("Ctrl+Tab", "Ctrl+Shift+Tab", "F1", "Ctrl+F", "Ctrl+Q"):
        assert tecla in manual, f"el manual no menciona {tecla}"
    for cableado in ("Ctrl+Tab", "Ctrl+Shift+Tab", "Key_F1", "StandardKey.Find", "StandardKey.Quit"):
        assert cableado in ventana, f"main_window ya no cablea {cableado}"


def test_el_spec_embebe_el_manual_en_el_exe() -> None:
    spec = (RAIZ / "build" / "fb2p_studio.spec").read_text(encoding="utf-8")
    assert "LEEME.md" in spec
    assert '"fb2p_studio/resources"' in spec


# ------------------------------------------------------- en la ventana
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


def test_el_manual_esta_en_el_grupo_ayuda(ventana) -> None:  # noqa: ANN001
    indice = ventana._pages.indexOf(ventana._tab_manual)  # noqa: SLF001
    assert ventana._nav.page_path(indice) == ("Ayuda", "Manual")  # noqa: SLF001


def test_f1_abre_el_manual(ventana, qapp) -> None:  # noqa: ANN001
    from PySide6.QtGui import QShortcut

    atajos = {s.key().toString(): s for s in ventana.findChildren(QShortcut)}
    assert "F1" in atajos

    atajos["F1"].activated.emit()
    qapp.processEvents()

    assert ventana._pages.currentWidget() is ventana._tab_manual  # noqa: SLF001
    assert ventana._section_title.text().endswith("Manual")  # noqa: SLF001


def test_ctrl_f_solo_busca_estando_en_el_manual(ventana, qapp) -> None:  # noqa: ANN001
    campo = ventana._tab_manual.viewer._search  # noqa: SLF001

    ventana._nav.select(0)  # noqa: SLF001
    ventana._search_manual()  # noqa: SLF001
    assert not campo.hasFocus()

    ventana.show_manual()
    qapp.processEvents()
    ventana._search_manual()  # noqa: SLF001
    qapp.processEvents()
    assert campo.hasFocus()


def test_cambiar_el_tema_revisten_el_manual(ventana) -> None:  # noqa: ANN001
    visor = ventana._tab_manual.viewer  # noqa: SLF001
    ventana._apply_theme(theme.ADS)  # noqa: SLF001
    assert "h1, h2, h3" in visor._css()  # noqa: SLF001
    ventana._apply_theme(theme.OSCURO)  # noqa: SLF001
    assert "h1, h2, h3" not in visor._css()  # noqa: SLF001


def test_la_ventana_muestra_el_manual_real(ventana) -> None:  # noqa: ANN001
    assert len(ventana._tab_manual.viewer.headings()) >= 12  # noqa: SLF001

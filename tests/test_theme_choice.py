"""Eleccion de tema: ADS, Claro y Oscuro, y el `sistema` de antes.

Autor: AJACH
Fecha: 2026-10-28 11:23:20

Hasta 2026-10-28 habia un unico tema «Sistema» que copiaba el modo de Windows.
Se separo en Claro y Oscuro, como en UtilitiesDevelopment. Lo que se cuida:

    · que se ofrezcan los tres, en el mismo orden que en UtilitiesDevelopment
    · que Oscuro sea oscuro aunque Windows este en claro (y al reves)
    · que el `sistema` de un .ini viejo, o nada, se resuelva a Claro u Oscuro
    · que Preferencias muestre el tema APLICADO: con `sistema` en el .ini el
      combo caia en la primera opcion y un OK cambiaba el tema sin pedirlo
"""

from __future__ import annotations

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtGui import QPalette

from fb2p_studio.ui import theme


@pytest.fixture(autouse=True, scope="module")
def _config_aislada(tmp_path_factory) -> None:  # noqa: ANN001
    """QSettings a un directorio temporal: no tocamos el .ini del usuario."""
    destino = tmp_path_factory.mktemp("qsettings")
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(destino))


def test_se_ofrecen_los_tres_en_orden() -> None:
    assert list(theme.NOMBRES) == [theme.ADS, theme.CLARO, theme.OSCURO]
    assert theme.SISTEMA not in theme.NOMBRES


def test_claro_usa_los_neutros_fenix_y_seleccion_clara(qapp) -> None:  # noqa: ANN001
    theme.apply(qapp, theme.CLARO)
    pal = qapp.palette()
    assert pal.color(QPalette.ColorRole.Window).name() == "#f7fafc"
    assert pal.color(QPalette.ColorRole.Highlight).name() == "#afc3dc"
    assert pal.color(QPalette.ColorRole.HighlightedText).name() == "#000000"
    assert qapp.styleSheet() == ""
    assert not theme.is_dark()


def test_oscuro_es_oscuro_aunque_windows_no_lo_este(qapp) -> None:  # noqa: ANN001
    theme.apply(qapp, theme.OSCURO)
    assert qapp.palette().color(QPalette.ColorRole.Window).lightness() < 80
    assert theme.is_dark()
    assert theme.hint_color() == "#9a9a9a"


@pytest.mark.parametrize("guardado", [theme.SISTEMA, "", None, "inventado"])
def test_lo_de_antes_se_resuelve_a_claro_u_oscuro(qapp, guardado) -> None:  # noqa: ANN001
    # is_dark_mode cae a mirar la paleta si Qt no informa el esquema de
    # Windows (offscreen): se parte de una paleta clara conocida y se calcula
    # lo esperado ANTES de aplicar, que es lo que hace `apply`.
    theme.apply(qapp, theme.ADS)
    esperado = theme.OSCURO if theme.is_dark_mode(qapp) else theme.CLARO
    theme.apply(qapp, guardado)
    assert theme.current() == esperado


def test_preferencias_muestra_el_tema_aplicado(qapp) -> None:  # noqa: ANN001
    from fb2p_studio.core.settings import Settings
    from fb2p_studio.ui.dialog_preferences import PreferencesDialog

    ajustes = Settings()
    ajustes.theme = theme.SISTEMA
    theme.apply(qapp, ajustes.theme)
    resuelto = theme.current()

    dlg = PreferencesDialog(ajustes)
    assert dlg.theme_id() == resuelto, (
        f"con `sistema` en el .ini el combo muestra {dlg.theme_id()!r} y el tema "
        f"aplicado es {resuelto!r}: un OK lo cambiaria sin pedirlo"
    )
    dlg.deleteLater()

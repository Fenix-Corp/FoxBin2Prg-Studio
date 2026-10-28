"""Aplicacion del estilo y paleta. Hay tres temas a elegir.

**Claro** y **Oscuro**: **Fusion**, el estilo mas neutro y consistente entre
versiones de Windows. Se eligen por separado, no segun Windows: quien quiere el
oscuro lo quiere aunque el escritorio este en claro. El claro usa los neutros
de la paleta corporativa Fenix (fondo #F7FAFC, texto #2D3748) y selecciona con
un azul CLARO (#AFC3DC) y texto negro, no con el azul saturado de Windows: asi
lo elegido se sigue leyendo sin esfuerzo.

**ADS corporativo**: la identidad de la casa — el mismo azul #1F3A5E y la
misma banda superior que el resto de las utilidades del departamento y que
los PDF que produce `md2pdf`. Sirve para que las herramientas se vean como
una familia. Es siempre claro: la identidad corporativa no tiene version
oscura.

Hasta 2026-10-28 habia un unico tema «Sistema» que tomaba claro u oscuro de
Windows. Su id (`sistema`) sigue siendo el de por defecto mientras nadie elija
otro, y el que puede haber en el .ini de alguien: al aplicarlo se resuelve a
Claro u Oscuro segun Windows, como hacia antes. Igual que en
`UtilitiesDevelopment/shell/theme.py`, de donde se porto la separacion.

En todos los casos se exponen los colores semanticos del log
(info/ok/warn/error/muted) para que cambien con el tema en vez de ser fijos.
"""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

from fb2p_studio.ui import theme_ads

#: Identificadores de tema. Se persisten en el .ini: no cambiarlos.
ADS = "ads"
CLARO = "claro"
OSCURO = "oscuro"
#: Ya no se ofrece, pero es el de por defecto (nada elegido todavia) y se
#: acepta del .ini: se resuelve a Claro u Oscuro segun Windows (ver `apply`).
SISTEMA = "sistema"
DEFAULT = SISTEMA

#: Nombre visible de cada tema, en el orden en que se ofrecen. El mismo orden
#: que en UtilitiesDevelopment: las dos herramientas se leen igual.
NOMBRES: dict[str, str] = {
    ADS: "ADS corporativo",
    CLARO: "Claro",
    OSCURO: "Oscuro",
}


@dataclass(frozen=True, slots=True)
class LogColors:
    info: QColor
    ok: QColor
    warn: QColor
    error: QColor
    muted: QColor


#: Sobre el fondo claro (#F7FAFC, el de los formularios Fenix).
_LIGHT = LogColors(
    info=QColor("#2D3748"),
    ok=QColor("#1b7f34"),
    warn=QColor("#a86500"),
    error=QColor("#c62828"),
    muted=QColor("#637083"),
)

_DARK = LogColors(
    info=QColor("#e6e6e6"),
    ok=QColor("#7bd88b"),
    warn=QColor("#ffb454"),
    error=QColor("#ff6b6b"),
    muted=QColor("#9a9a9a"),
)


def is_dark_mode(app: QApplication) -> bool:
    """Detecta si el OS/tema esta en dark mode.

    Qt 6.5+ expone `QStyleHints.colorScheme()`. En Windows 11 con tema
    oscuro devuelve `Qt.ColorScheme.Dark`. Si no esta disponible, cae a
    heuristica sobre la paleta actual.

    Solo sirve para resolver el id `sistema`. Para saber si el tema APLICADO
    es oscuro, `is_dark()`.
    """
    hints = app.styleHints()
    if hasattr(hints, "colorScheme"):
        scheme = hints.colorScheme()
        if scheme == Qt.ColorScheme.Dark:
            return True
        if scheme == Qt.ColorScheme.Light:
            return False
    # Heuristica: si el fondo de Window es mas oscuro que su texto, es dark.
    palette = app.palette()
    bg = palette.color(QPalette.ColorRole.Window)
    fg = palette.color(QPalette.ColorRole.WindowText)
    return bg.lightness() < fg.lightness()


_ADS = LogColors(
    info=QColor(theme_ads.INFO),
    ok=QColor(theme_ads.OK),
    warn=QColor(theme_ads.WARN),
    error=QColor(theme_ads.ERROR),
    muted=QColor(theme_ads.MUTED),
)


#: Tema aplicado ahora mismo, ya resuelto (nunca `sistema`). Lo consultan la
#: banda corporativa (que sólo existe con el tema ADS), Preferencias y los
#: textos de ayuda, que necesitan un gris que se lea en el tema puesto.
_current = CLARO


def current() -> str:
    return _current


def is_dark() -> bool:
    """Si el tema APLICADO es oscuro (no si Windows lo esta)."""
    return _current == OSCURO


def hint_color() -> str:
    """Gris de los textos de ayuda, acorde al tema aplicado.

    Un gris fijo pensado para fondo blanco es ilegible sobre el oscuro. En el
    claro es el gris pizarra de la paleta Fenix (#637083, 4,8:1 sobre el
    fondo): el «texto secundario» #718096 se queda en 3,8:1.
    """
    if _current == ADS:
        return theme_ads.TEXT_MUTED
    if _current == OSCURO:
        return "#9a9a9a"
    return "#637083"


def normalize(name: str | None) -> str:
    """Un tema desconocido en el .ini no rompe nada: cae al de siempre."""
    return name if name in NOMBRES or name == SISTEMA else DEFAULT


def apply(app: QApplication, name: str | None = None) -> LogColors:
    """Aplica el tema pedido y devuelve los colores del log.

    Se puede llamar en caliente: cambiar la hoja de estilo y la paleta
    repinta toda la aplicacion. Lo unico que no viaja solo son los colores
    del log, que los widgets guardaron al construirse — por eso se devuelven
    y `MainWindow` los reparte (`set_log_colors`).
    """
    global _current
    name = normalize(name)
    if name == SISTEMA:
        name = OSCURO if is_dark_mode(app) else CLARO
    _current = name
    if _current == ADS:
        return _apply_ads(app)
    return _apply_fusion(app, dark=_current == OSCURO)


def _apply_fusion(app: QApplication, dark: bool) -> LogColors:
    app.setStyleSheet("")
    app.setStyle("Fusion")
    app.setPalette(_dark_palette() if dark else _light_palette())
    return _DARK if dark else _LIGHT


def _apply_ads(app: QApplication) -> LogColors:
    # La paleta clara va igual: la hoja de estilo no cubre todos los widgets
    # (dialogos estandar, tooltips), y sin ella un Windows en modo oscuro
    # dejaria texto claro sobre los fondos blancos del QSS.
    app.setStyle("Fusion")
    app.setPalette(_ads_palette())
    app.setStyleSheet(theme_ads.stylesheet())
    return _ADS


# ---------------------------------------------------------------------------
# Paletas
# ---------------------------------------------------------------------------
def _ads_palette() -> QPalette:
    """La paleta de fondo del tema ADS: casi todo lo viste su hoja de estilo."""
    p = QPalette()
    p.setColor(QPalette.ColorRole.Window, QColor("#f3f3f3"))
    p.setColor(QPalette.ColorRole.WindowText, QColor("#1a1a1a"))
    p.setColor(QPalette.ColorRole.Base, QColor("#ffffff"))
    p.setColor(QPalette.ColorRole.AlternateBase, QColor("#f0f0f0"))
    p.setColor(QPalette.ColorRole.ToolTipBase, QColor("#ffffdc"))
    p.setColor(QPalette.ColorRole.ToolTipText, QColor("#1a1a1a"))
    p.setColor(QPalette.ColorRole.Text, QColor("#1a1a1a"))
    p.setColor(QPalette.ColorRole.Button, QColor("#e8e8e8"))
    p.setColor(QPalette.ColorRole.ButtonText, QColor("#1a1a1a"))
    p.setColor(QPalette.ColorRole.BrightText, QColor("#ff0000"))
    p.setColor(QPalette.ColorRole.Link, QColor("#0067c0"))
    p.setColor(QPalette.ColorRole.Highlight, QColor("#0067c0"))
    p.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    return p


def _light_palette() -> QPalette:
    """Tema Claro, con los neutros canonicos de la paleta corporativa Fenix.

    La seleccion (listas, arbol de resultados, menus) es el azul claro de
    «Bancos» (#AFC3DC) con texto negro, 11,7:1: se distingue del fondo y el
    texto elegido se lee sin esfuerzo, que con el azul saturado de Windows
    no pasaba.
    """
    p = QPalette()
    p.setColor(QPalette.ColorRole.Window, QColor("#F7FAFC"))
    p.setColor(QPalette.ColorRole.WindowText, QColor("#2D3748"))
    p.setColor(QPalette.ColorRole.Base, QColor("#FFFFFF"))
    p.setColor(QPalette.ColorRole.AlternateBase, QColor("#F4F6F9"))
    p.setColor(QPalette.ColorRole.ToolTipBase, QColor("#FFFFFF"))
    p.setColor(QPalette.ColorRole.ToolTipText, QColor("#2D3748"))
    p.setColor(QPalette.ColorRole.Text, QColor("#2D3748"))
    p.setColor(QPalette.ColorRole.Button, QColor("#F4F6F9"))
    p.setColor(QPalette.ColorRole.ButtonText, QColor("#2D3748"))
    p.setColor(QPalette.ColorRole.BrightText, QColor("#7F1D1D"))
    p.setColor(QPalette.ColorRole.Link, QColor("#325582"))
    p.setColor(QPalette.ColorRole.Highlight, QColor("#AFC3DC"))
    p.setColor(QPalette.ColorRole.HighlightedText, QColor("#000000"))
    p.setColor(QPalette.ColorRole.PlaceholderText, QColor("#637083"))
    for rol in (QPalette.ColorRole.WindowText, QPalette.ColorRole.Text,
                QPalette.ColorRole.ButtonText):
        p.setColor(QPalette.ColorGroup.Disabled, rol, QColor("#9AA4B2"))
    return p


def _dark_palette() -> QPalette:
    p = QPalette()
    p.setColor(QPalette.ColorRole.Window, QColor("#2b2b2b"))
    p.setColor(QPalette.ColorRole.WindowText, QColor("#e6e6e6"))
    p.setColor(QPalette.ColorRole.Base, QColor("#1e1e1e"))
    p.setColor(QPalette.ColorRole.AlternateBase, QColor("#2a2a2a"))
    p.setColor(QPalette.ColorRole.ToolTipBase, QColor("#3a3a3a"))
    p.setColor(QPalette.ColorRole.ToolTipText, QColor("#e6e6e6"))
    p.setColor(QPalette.ColorRole.Text, QColor("#e6e6e6"))
    p.setColor(QPalette.ColorRole.Button, QColor("#3a3a3a"))
    p.setColor(QPalette.ColorRole.ButtonText, QColor("#e6e6e6"))
    p.setColor(QPalette.ColorRole.BrightText, QColor("#ff6b6b"))
    p.setColor(QPalette.ColorRole.Link, QColor("#4ea1ff"))
    p.setColor(QPalette.ColorRole.Highlight, QColor("#3d6ea5"))
    p.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    p.setColor(QPalette.ColorRole.PlaceholderText, QColor("#8a8a8a"))
    # Estados deshabilitados
    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, QColor("#6a6a6a"))
    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor("#6a6a6a"))
    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor("#6a6a6a"))
    return p

"""Aplicacion del estilo y paleta. Hay dos temas a elegir.

**Sistema** (el de siempre, y el que sigue viniendo por defecto): **Fusion**,
el estilo mas neutro y consistente entre versiones de Windows, con la paleta
clara u oscura segun como este el OS. Se mimetiza con el escritorio.

**ADS corporativo**: la identidad de la casa — el mismo azul #1F3A5E y la
misma banda superior que el resto de las utilidades del departamento y que
los PDF que produce `md2pdf`. Sirve para que las herramientas se vean como
una familia. Es siempre claro: la identidad corporativa no tiene version
oscura.

En los dos casos se exponen los colores semanticos del log
(info/ok/warn/error/muted) para que cambien con el tema en vez de ser fijos.
"""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

from fb2p_studio.ui import theme_ads

#: Identificadores de tema. Se persisten en el .ini: no cambiarlos.
SISTEMA = "sistema"
ADS = "ads"
DEFAULT = SISTEMA

#: Nombre visible de cada tema, en el orden en que se ofrecen.
NOMBRES: dict[str, str] = {
    SISTEMA: "Sistema (claro/oscuro segun Windows)",
    ADS: "ADS corporativo",
}


@dataclass(frozen=True, slots=True)
class LogColors:
    info: QColor
    ok: QColor
    warn: QColor
    error: QColor
    muted: QColor


_LIGHT = LogColors(
    info=QColor("#212121"),
    ok=QColor("#1b7f34"),
    warn=QColor("#a86500"),
    error=QColor("#c62828"),
    muted=QColor("#6b6b6b"),
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


#: Tema aplicado ahora mismo. Lo consultan la banda corporativa (que sólo
#: existe con el tema ADS) y los textos de ayuda, que necesitan un gris que
#: se lea en el tema que este puesto.
_current = DEFAULT


def current() -> str:
    return _current


def hint_color() -> str:
    """Gris de los textos de ayuda, acorde al tema aplicado.

    Con el tema Sistema tiene que servir en claro Y en oscuro: un `#666` fijo
    (lo que habia) es ilegible sobre el fondo oscuro de Windows.
    """
    if _current == ADS:
        return theme_ads.TEXT_MUTED
    app = QApplication.instance()
    if isinstance(app, QApplication) and is_dark_mode(app):
        return "#9a9a9a"
    return "#666666"


def normalize(name: str | None) -> str:
    """Un tema desconocido en el .ini no rompe nada: cae al de siempre."""
    return name if name in NOMBRES else DEFAULT


def apply(app: QApplication, name: str | None = None) -> LogColors:
    """Aplica el tema pedido y devuelve los colores del log.

    Se puede llamar en caliente: cambiar la hoja de estilo y la paleta
    repinta toda la aplicacion. Lo unico que no viaja solo son los colores
    del log, que los widgets guardaron al construirse — por eso se devuelven
    y `MainWindow` los reparte (`set_log_colors`).
    """
    global _current
    _current = normalize(name)
    return _apply_ads(app) if _current == ADS else _apply_sistema(app)


def _apply_sistema(app: QApplication) -> LogColors:
    app.setStyleSheet("")
    app.setStyle("Fusion")
    dark = is_dark_mode(app)
    app.setPalette(_dark_palette() if dark else _light_palette())
    return _DARK if dark else _LIGHT


def _apply_ads(app: QApplication) -> LogColors:
    # La paleta clara va igual: la hoja de estilo no cubre todos los widgets
    # (dialogos estandar, tooltips), y sin ella un Windows en modo oscuro
    # dejaria texto claro sobre los fondos blancos del QSS.
    app.setStyle("Fusion")
    app.setPalette(_light_palette())
    app.setStyleSheet(theme_ads.stylesheet())
    return _ADS


# ---------------------------------------------------------------------------
# Paletas
# ---------------------------------------------------------------------------
def _light_palette() -> QPalette:
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

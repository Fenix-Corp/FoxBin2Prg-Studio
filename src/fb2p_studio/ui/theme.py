"""Aplicacion del estilo y paleta.

Usamos **Fusion** (el estilo mas neutro y consistente entre versiones de
Windows) y detectamos el modo (claro/oscuro) del sistema para poner una
paleta que combine con el resto del OS. Tambien exponemos los colores
semanticos del log (info/ok/warn/error/muted) para que cambien con el
tema en vez de ser fijos.
"""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication


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


def apply(app: QApplication) -> LogColors:
    """Aplica Fusion + paleta acorde al tema del OS. Devuelve los colores del log."""
    app.setStyle("Fusion")
    dark = is_dark_mode(app)
    app.setPalette(_dark_palette() if dark else _light_palette())
    return _DARK if dark else _LIGHT


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

"""Tema corporativo ADS: la misma identidad que el resto de las utilidades.

Portado de `UtilitiesDevelopment/shell/theme.py`, el "cajon de herramientas"
del departamento, para que las dos aplicaciones se vean como la misma familia.
Los colores son los de `templates/ads.css`, con lo que se imprimen los PDF: si
cambia la identidad corporativa se corrigen ahi y aca, y no en veinte widgets
sueltos.

**Los colores del log estan medidos, no elegidos a ojo.** Van sobre
`SURFACE_CODE`, que es su fondo, y cumplen el 4,5:1 de WCAG 2.1 AA — el ambar
"natural" (#9d6b00) daba 4,09:1 y no llegaba. `tests/test_theme_contrast.py`
lo verifica en cada corrida, para que un retoque no rompa la accesibilidad en
silencio.
"""

from __future__ import annotations

#: Azul corporativo de la banda. El mismo #1F3A5E del CSS.
PRIMARY = "#1F3A5E"
PRIMARY_DARK = "#14304f"
PRIMARY_MID = "#2d445f"

TEXT = "#22262b"
TEXT_MUTED = "#5b6470"
TEXT_ON_PRIMARY = "#ffffff"

BORDER = "#dde3ea"
SURFACE = "#ffffff"
SURFACE_ALT = "#f6f8fa"
SURFACE_CODE = "#eef1f5"

#: Colores de la bitacora, medidos contra SURFACE_CODE.
OK = "#1a6b3c"  # 5,77:1
WARN = "#8a5e00"  # 5,03:1
ERROR = "#9d2235"  # 6,83:1
INFO = TEXT
MUTED = TEXT_MUTED

#: Estados del arbol de contenido y de resultados. Mismo criterio.
HOVER_BG = "#e8eef6"
HOVER_BORDER = "#c3d2e4"
SELECTED_INACTIVE_BG = "#ccdaea"
ALT_ROW = "#fbfcfd"

FONT_UI = '"Segoe UI", "Calibri", system-ui, sans-serif'
FONT_MONO = '"Consolas", "Courier New", monospace'


def stylesheet() -> str:
    """Hoja de estilo de toda la aplicacion.

    Deliberadamente corta: sólo lo necesario para que los controles nativos de
    Windows se vean ordenados y lleven el azul corporativo. No se redisena
    cada widget — eso envejece mal y se rompe con cada version de Qt.

    De cada elemento seleccionable se declaran los CUATRO estados (reposo,
    raton encima, elegido con foco y elegido sin foco): el que se olvida es
    justo el que se ve mal, porque Qt sobre Windows cae al resaltado del
    sistema y deja texto oscuro sobre fondo azul oscuro.
    """
    return _QSS % {
        "font": FONT_UI,
        "mono": FONT_MONO,
        "text": TEXT,
        "muted": TEXT_MUTED,
        "primary": PRIMARY,
        "primary_dark": PRIMARY_DARK,
        "primary_mid": PRIMARY_MID,
        "on_primary": TEXT_ON_PRIMARY,
        "border": BORDER,
        "surface": SURFACE,
        "surface_alt": SURFACE_ALT,
        "surface_code": SURFACE_CODE,
        "hover": HOVER_BG,
        "hover_border": HOVER_BORDER,
        "sel_inactive": SELECTED_INACTIVE_BG,
        "alt_row": ALT_ROW,
    }


_QSS = """
QWidget {
    font-family: %(font)s;
    font-size: 10pt;
    color: %(text)s;
}
QMainWindow, QDialog { background: %(surface_alt)s; }

/* Banda superior: el mismo azul y la misma logica que la del PDF. */
#bandaCorporativa { background: %(primary)s; }
#bandaTitulo {
    color: %(on_primary)s;
    font-size: 13pt;
    font-weight: 600;
}
#bandaSubtitulo { color: #c8d4e4; font-size: 9pt; }

QTabBar { background: transparent; }
QTabWidget::pane {
    border: 1px solid %(border)s;
    background: %(surface)s;
    top: -1px;
}
QTabBar::tab {
    background: %(surface_alt)s;
    border: 1px solid %(border)s;
    border-bottom: none;
    padding: 7px 16px;
    margin-right: 2px;
    color: %(muted)s;
}
QTabBar::tab:selected {
    background: %(surface)s;
    color: %(primary)s;
    font-weight: 600;
    border-top: 2px solid %(primary)s;
}
QTabBar::tab:hover:!selected { color: %(primary_mid)s; }

QSplitter::handle { background: %(surface_alt)s; }
QSplitter::handle:horizontal { width: 8px; }
QSplitter::handle:vertical { height: 8px; }
QSplitter::handle:hover { background: %(border)s; }

QScrollBar:vertical {
    background: %(surface_alt)s;
    width: 11px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #c4ccd6;
    border-radius: 5px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover { background: #9aa7b8; }
QScrollBar:horizontal {
    background: %(surface_alt)s;
    height: 11px;
    margin: 0;
}
QScrollBar::handle:horizontal {
    background: #c4ccd6;
    border-radius: 5px;
    min-width: 30px;
}
QScrollBar::handle:horizontal:hover { background: #9aa7b8; }
QScrollBar::add-line, QScrollBar::sub-line { height: 0; width: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: none; }

QGroupBox {
    border: 1px solid %(border)s;
    border-radius: 3px;
    background: %(surface)s;
    margin-top: 14px;
    padding: 10px 9px 8px 9px;
    font-weight: 600;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 8px;
    padding: 0 4px;
    color: %(primary)s;
}

QLineEdit, QComboBox, QPlainTextEdit, QSpinBox, QTreeWidget {
    border: 1px solid %(border)s;
    border-radius: 3px;
    background: %(surface)s;
    padding: 4px 6px;
    selection-background-color: %(primary)s;
    selection-color: %(on_primary)s;
}
QLineEdit:focus, QComboBox:focus, QPlainTextEdit:focus, QTreeWidget:focus {
    border: 1px solid %(primary)s;
}
QLineEdit:hover:!focus, QComboBox:hover:!focus { border-color: #aebccd; }
QLineEdit:disabled, QComboBox:disabled {
    background: %(surface_alt)s;
    color: %(muted)s;
}
QComboBox::drop-down { border: none; width: 18px; }

/* El desplegable es una vista aparte y no hereda nada del combo: hay que
   vestirla por separado o sale con el tema del sistema. */
QComboBox QAbstractItemView {
    border: 1px solid %(primary)s;
    background: %(surface)s;
    outline: none;
    padding: 2px;
}
QComboBox QAbstractItemView::item { padding: 5px 6px; color: %(text)s; }
QComboBox QAbstractItemView::item:hover {
    background: %(hover)s;
    color: %(primary_dark)s;
}
QComboBox QAbstractItemView::item:selected {
    background: %(primary)s;
    color: %(on_primary)s;
}

QPushButton {
    border: 1px solid %(border)s;
    border-radius: 3px;
    background: %(surface)s;
    padding: 5px 14px;
}
QPushButton:hover { border-color: %(primary_mid)s; color: %(primary)s; }
QPushButton:pressed { background: %(surface_code)s; }
QPushButton:disabled { color: %(muted)s; background: %(surface_alt)s; }
QPushButton:focus {
    border: 1px solid %(primary)s;
    color: %(primary)s;
    outline: none;
}

/* Accion principal de la pestana: Ejecutar. */
QPushButton#accionPrincipal {
    background: %(primary)s;
    color: %(on_primary)s;
    border: 1px solid %(primary_dark)s;
    font-weight: 600;
    padding: 6px 22px;
}
QPushButton#accionPrincipal:hover { background: %(primary_mid)s; }
QPushButton#accionPrincipal:focus {
    border: 2px solid %(primary_dark)s;
    color: %(on_primary)s;
}
QPushButton#accionPrincipal:disabled {
    background: #cdd4de;
    border-color: #c2cad6;
    color: %(muted)s;
}

/* La bitacora y el preview del job.ini se ven como codigo, no como campos
   que inviten a escribir, pero siguen siendo seleccionables. */
QPlainTextEdit#bitacora, QPlainTextEdit#commandPreview {
    font-family: %(mono)s;
    font-size: 9pt;
    background: %(surface_code)s;
    border: 1px solid %(border)s;
}

/* Arbol de contenido / resultados: los cuatro estados. */
QTreeWidget {
    outline: none;
    alternate-background-color: %(alt_row)s;
    padding: 0;
}
QTreeWidget::item { padding: 4px 6px; border: 1px solid transparent; }
QTreeWidget::item:hover {
    background: %(hover)s;
    border-color: #c3d2e4;
}
QTreeWidget::item:selected {
    background: %(primary)s;
    border-color: %(primary_dark)s;
    color: %(on_primary)s;
}
QTreeWidget::item:selected:hover { background: %(primary_mid)s; }
/* Elegido pero sin el foco del teclado: es como queda mientras se tocan
   otros controles, asi que tiene que seguir diciendo cual esta elegido. */
QTreeWidget::item:selected:!active {
    background: %(sel_inactive)s;
    border-color: #a9c0d8;
    color: %(primary_dark)s;
}
QHeaderView::section {
    background: %(surface_alt)s;
    border: none;
    border-bottom: 1px solid %(border)s;
    border-right: 1px solid %(border)s;
    padding: 5px 6px;
    color: %(muted)s;
    font-weight: 600;
}

QRadioButton:hover, QCheckBox:hover { color: %(primary)s; }
QRadioButton:focus, QCheckBox:focus { color: %(primary_dark)s; }
QRadioButton:disabled, QCheckBox:disabled { color: %(muted)s; }

QLabel#pista { color: %(muted)s; font-size: 9pt; }
QLabel#datoClave { font-weight: 600; color: %(primary_dark)s; }

QStatusBar { background: %(surface_alt)s; color: %(muted)s; }
QStatusBar::item { border: none; }

QMenuBar { background: %(surface_alt)s; }
QMenuBar::item:selected { background: %(hover)s; color: %(primary_dark)s; }
/* Menus desplegables. La opcion bajo el raton va en un tono CLARO con texto
   azul marino (11,5:1), igual que el arbol y la barra de menus: el azul
   corporativo lleno se reserva para lo ELEGIDO, no para el paso del raton.
   Mismo criterio que UtilitiesDevelopment. */
QMenu { background: %(surface)s; border: 1px solid %(border)s; padding: 4px; }
QMenu::item {
    padding: 5px 22px;
    border: 1px solid transparent;
    border-radius: 3px;
    color: %(text)s;
    background: transparent;
}
QMenu::item:selected {
    background: %(hover)s;
    border-color: %(hover_border)s;
    color: %(primary_dark)s;
}
QMenu::item:disabled { color: %(muted)s; }
QMenu::separator { height: 1px; background: %(border)s; margin: 4px 6px; }
"""

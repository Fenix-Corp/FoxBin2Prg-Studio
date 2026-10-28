"""Menu lateral de la ventana, al estilo de los dashboards web de Fenix.

Autor: AJACH
Fecha: 2026-10-28 15:33:32

Reemplaza a la barra de menus y a la fila de pestanas: cada pagina es una
opcion con icono, agrupada bajo un titulo, igual que la barra de los dashboards
de Fenix. Es la misma navegacion que usa el Migrador VFP9 -> Fenix 360
(`fnxDbMigra/sidenav.py`), de donde esta portada.

Lo que copia del dashboard web:

    - grupos con titulo en versalitas y opciones con icono
    - la opcion activa resaltada
    - el boton que la colapsa a solo iconos, con el nombre en el tooltip
    - un pie fijo con las preferencias (tema, ajustes, actualizaciones)

Solo es la NAVEGACION: no sabe nada de las paginas. La ventana le pide una
opcion por pagina y escucha `currentChanged` para mostrar la que toca en su
`QStackedWidget`. Lo que no es pagina (abrir un dialogo, desplegar un menu) se
agrega con `add_action`.

Los iconos son glifos de Segoe Fluent Icons (Windows 11), con Segoe MDL2 Assets
(Windows 10) de respaldo: los dos traen los mismos codigos y vienen con Windows,
asi que no viaja ningun archivo de imagen.

Los colores del tema ADS viven en `theme_ads` (para que `test_theme_contrast` los
lea); con los temas Claro y Oscuro la barra arma su propia hoja local a partir de
la paleta aplicada, porque esos temas no tienen hoja global.
"""

from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QFontDatabase, QIcon, QPainter, QPalette, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QFrame,
    QLabel,
    QMenu,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from fb2p_studio.ui import theme, theme_ads

#: Fuentes de iconos, en orden de preferencia.
GLYPH_FONTS = ("Segoe Fluent Icons", "Segoe MDL2 Assets")
#: Archivo de cada fuente en %WINDIR%\Fonts, por si Qt no la ve sola.
GLYPH_FILES = ("SegoeIcons.ttf", "segmdl2.ttf")

#: Glifos de la barra misma. Los de cada pagina se declaran al construirla.
GLYPH_MENU = 0xE700
GLYPH_THEME = 0xE790

EXPANDED_WIDTH = 236
COLLAPSED_WIDTH = 56
ICON_SIZE = 16


def glyph_family() -> str | None:
    """La primera fuente de iconos disponible, o None si no hay ninguna.

    Con la plataforma `offscreen` (las pruebas) Qt no lee las fuentes del
    sistema: en ese caso se cargan desde la carpeta de fuentes de Windows.
    """
    familias = set(QFontDatabase.families())
    for familia in GLYPH_FONTS:
        if familia in familias:
            return familia
    carpeta = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
    for archivo in GLYPH_FILES:
        ruta = carpeta / archivo
        if ruta.is_file():
            ident = QFontDatabase.addApplicationFont(str(ruta))
            cargadas = QFontDatabase.applicationFontFamilies(ident)
            if cargadas:
                return cargadas[0]
    return None


def glyph_icon(code: int, normal: QColor, hover: QColor, checked: QColor) -> QIcon:
    """Un icono dibujado con un glifo, con un color por estado.

    `normal` es el de reposo, `hover` el del paso del raton (modo Active) y
    `checked` el de la opcion elegida (estado On). Se dibuja al doble de tamano
    para que se vea nitido en pantallas con escala de 150 o 200 %.
    """
    familia = glyph_family()
    icono = QIcon()
    if familia is None:
        return icono
    escala = 2
    lado = ICON_SIZE * escala

    def dibujar(color: QColor) -> QPixmap:
        pixmap = QPixmap(lado, lado)
        pixmap.fill(Qt.GlobalColor.transparent)
        pintor = QPainter(pixmap)
        pintor.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        fuente = QFont(familia)
        fuente.setPixelSize(int(lado * 0.85))
        pintor.setFont(fuente)
        pintor.setPen(color)
        pintor.drawText(QRectF(0, 0, lado, lado), Qt.AlignmentFlag.AlignCenter, chr(code))
        pintor.end()
        pixmap.setDevicePixelRatio(escala)
        return pixmap

    elegido = dibujar(checked)
    icono.addPixmap(dibujar(normal), QIcon.Mode.Normal, QIcon.State.Off)
    icono.addPixmap(dibujar(hover), QIcon.Mode.Active, QIcon.State.Off)
    icono.addPixmap(elegido, QIcon.Mode.Normal, QIcon.State.On)
    icono.addPixmap(elegido, QIcon.Mode.Active, QIcon.State.On)
    return icono


class SideNav(QFrame):
    """La barra lateral: grupos de opciones arriba, preferencias al pie."""

    #: Indice de la pagina elegida, en el orden en que se agregaron.
    currentChanged = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("menuLateral")
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        self.setFixedWidth(EXPANDED_WIDTH)

        self._collapsed = False
        #: (boton, glifo) de todo lo que lleva icono, para repintarlo al cambiar
        #: de tema.
        self._iconos: list[tuple[QPushButton, int]] = []
        #: (titulo visible, separador) de cada grupo: colapsada se ve el
        #: separador en lugar del titulo.
        self._grupos: list[tuple[QLabel, QFrame]] = []
        self._paginas: list[QPushButton] = []
        #: Grupo y titulo de cada pagina, para el encabezado de la seccion.
        self._rutas: list[tuple[str, str]] = []
        self._grupo_actual = ""
        self._botones = QButtonGroup(self)
        self._botones.setExclusive(True)

        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(8, 8, 8, 8)
        raiz.setSpacing(2)

        self._txt_contraer = self.tr("Contraer menu")
        self._txt_expandir = self.tr("Expandir menu")
        self.toggle_button = self._new_button(self._txt_contraer, GLYPH_MENU)
        self.toggle_button.clicked.connect(self.toggle)
        # Solo con el raton: si toma el foco, la ventana abre con su marco de
        # foco encendido (es el primer control).
        self.toggle_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        raiz.addWidget(self.toggle_button)

        # Las paginas van con scroll propio: con la ventana en su alto minimo no
        # caben todas, y el pie de preferencias no debe salirse de vista.
        self._area = QScrollArea()
        self._area.setObjectName("menuLateralArea")
        self._area.setWidgetResizable(True)
        self._area.setFrameShape(QFrame.Shape.NoFrame)
        self._area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        contenido = QWidget()
        contenido.setObjectName("menuLateralContenido")
        self._cuerpo = QVBoxLayout(contenido)
        self._cuerpo.setContentsMargins(0, 0, 0, 0)
        self._cuerpo.setSpacing(2)
        self._cuerpo.addStretch(1)
        self._area.setWidget(contenido)
        raiz.addWidget(self._area, 1)

        self._pie = QVBoxLayout()
        self._pie.setContentsMargins(0, 0, 0, 0)
        self._pie.setSpacing(2)
        raiz.addLayout(self._pie)

        self._destino = self._cuerpo

    # -- construccion -----------------------------------------------------

    def add_group(self, title: str, *, footer: bool = False) -> None:
        """Abre un grupo; lo que se agregue despues cae bajo su titulo.

        Con `footer` el grupo va al pie fijo de la barra, fuera del scroll.
        """
        self._destino = self._pie if footer else self._cuerpo
        self._grupo_actual = title
        titulo = QLabel(title.upper())
        titulo.setObjectName("navGrupo")
        separador = QFrame()
        separador.setObjectName("navSeparador")
        separador.setFrameShape(QFrame.Shape.HLine)
        # Plana: la hundida se pinta con la paleta e ignora el `color` del QSS.
        separador.setFrameShadow(QFrame.Shadow.Plain)
        separador.setVisible(self._collapsed)
        titulo.setVisible(not self._collapsed)
        self._add(separador)
        self._add(titulo)
        self._grupos.append((titulo, separador))

    def add_page(self, title: str, glyph: int) -> int:
        """Agrega una opcion que muestra una pagina; devuelve su indice."""
        boton = self._new_button(title, glyph)
        boton.setCheckable(True)
        indice = len(self._paginas)
        self._botones.addButton(boton, indice)
        boton.clicked.connect(lambda _=False, i=indice: self.select(i))
        self._paginas.append(boton)
        self._rutas.append((self._grupo_actual, title))
        self._add(boton)
        if indice == 0:
            boton.setChecked(True)
        return indice

    def add_action(
        self, title: str, glyph: int, *, slot=None, menu: QMenu | None = None
    ) -> QPushButton:
        """Agrega una opcion que NO es pagina: abre un dialogo o un menu."""
        boton = self._new_button(title, glyph)
        if menu is not None:
            boton.setMenu(menu)
        if slot is not None:
            boton.clicked.connect(slot)
        self._add(boton)
        return boton

    def _add(self, widget: QWidget) -> None:
        if self._destino is self._cuerpo:
            # Antes del estirador final, para que todo quede pegado arriba.
            self._cuerpo.insertWidget(self._cuerpo.count() - 1, widget)
        else:
            self._pie.addWidget(widget)

    def _new_button(self, title: str, glyph: int) -> QPushButton:
        boton = QPushButton(title)
        boton.setObjectName("navItem")
        boton.setProperty("titulo", title)
        boton.setIconSize(QSize(ICON_SIZE, ICON_SIZE))
        boton.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        boton.setCursor(Qt.CursorShape.PointingHandCursor)
        self._iconos.append((boton, glyph))
        return boton

    # -- navegacion -------------------------------------------------------

    def count(self) -> int:
        return len(self._paginas)

    def current_index(self) -> int:
        return self._botones.checkedId()

    def select(self, index: int) -> None:
        """Marca la pagina y avisa, aunque ya estuviera marcada.

        Avisar siempre es lo que espera la ventana: el clic sobre la opcion
        activa no cambia nada, y repetir `setCurrentIndex` no cuesta.
        """
        if not 0 <= index < len(self._paginas):
            return
        self._paginas[index].setChecked(True)
        self.currentChanged.emit(index)

    def step(self, delta: int) -> None:
        """Pasa a la pagina siguiente o anterior, dando la vuelta."""
        if self._paginas:
            self.select((self.current_index() + delta) % len(self._paginas))

    def page_path(self, index: int) -> tuple[str, str]:
        """(grupo, titulo) de la pagina, para el encabezado de la seccion."""
        return self._rutas[index]

    # -- colapsar ---------------------------------------------------------

    def is_collapsed(self) -> bool:
        return self._collapsed

    def toggle(self) -> None:
        self.set_collapsed(not self._collapsed)

    def set_collapsed(self, collapsed: bool) -> None:
        """Solo iconos (con el nombre en el tooltip) o iconos con texto.

        No se recuerda entre sesiones: la barra siempre abre desplegada.
        """
        self._collapsed = collapsed
        self.setFixedWidth(COLLAPSED_WIDTH if collapsed else EXPANDED_WIDTH)
        self.toggle_button.setProperty("titulo", self._txt_expandir if collapsed else self._txt_contraer)
        for boton, _ in self._iconos:
            titulo = boton.property("titulo")
            boton.setText("" if collapsed else titulo)
            boton.setToolTip(titulo if collapsed else "")
        for titulo, separador in self._grupos:
            titulo.setVisible(not collapsed)
            separador.setVisible(collapsed)
        self.setProperty("colapsada", collapsed)
        # Las reglas de la hoja que dependen de la propiedad se reevaluan solo si
        # se le pide al estilo que vuelva a pulir el widget.
        for widget in [self, *self.findChildren(QPushButton)]:
            widget.style().unpolish(widget)
            widget.style().polish(widget)

    # -- tema -------------------------------------------------------------

    def apply_theme(self, tema: str) -> None:
        """Repinta los iconos y, con Claro u Oscuro, pone la hoja local."""
        if tema == theme.ADS:
            self.setStyleSheet("")
            normal = QColor(theme_ads.SIDE_TEXT)
            hover = elegido = QColor(theme_ads.SIDE_TEXT_ACTIVE)
        else:
            colores = _system_colors()
            self.setStyleSheet(_system_stylesheet(colores))
            normal = hover = QColor(colores["text"])
            # La elegida va sobre el color de seleccion de la paleta.
            elegido = QColor(colores["on_sel"])
        for boton, glifo in self._iconos:
            boton.setIcon(glyph_icon(glifo, normal, hover, elegido))


def _system_colors() -> dict[str, str]:
    """Colores de la barra con los temas Claro/Oscuro, de la paleta aplicada.

    Se arman en Python y no con `palette(...)` dentro de la hoja: las paletas de
    `theme.py` fijan solo algunos roles (no `Midlight` ni `Mid`), y los que no se
    fijan caen a valores que no combinan con el fondo.
    """
    app = QApplication.instance()
    paleta = app.palette() if app is not None else QPalette()
    fondo = paleta.color(QPalette.ColorRole.Window)
    # El tema elegido, no el de Windows: se puede pedir Oscuro con el escritorio
    # en claro.
    oscuro = theme.is_dark()
    return {
        "bg": fondo.name(),
        "text": paleta.color(QPalette.ColorRole.WindowText).name(),
        "muted": theme.hint_color(),
        "hover": (fondo.lighter(135) if oscuro else fondo.darker(108)).name(),
        "border": (fondo.lighter(160) if oscuro else fondo.darker(118)).name(),
        "sel": paleta.color(QPalette.ColorRole.Highlight).name(),
        "on_sel": paleta.color(QPalette.ColorRole.HighlightedText).name(),
    }


#: Hoja local de la barra con Claro/Oscuro: los mismos cuatro estados que la del
#: tema ADS. Formato con `%` y no con `.format`: el QSS esta lleno de llaves.
_SYSTEM_QSS = """
    #menuLateral {
        background: %(bg)s;
        border-right: 1px solid %(border)s;
    }
    #menuLateralArea, #menuLateralContenido { background: transparent; }
    QLabel#navGrupo {
        color: %(muted)s;
        font-size: 8pt;
        font-weight: 700;
        padding: 12px 8px 4px 8px;
    }
    QFrame#navSeparador { color: %(border)s; margin: 6px 4px; }
    QPushButton#navItem {
        text-align: left;
        border: 1px solid transparent;
        border-radius: 6px;
        padding: 7px 9px;
        background: transparent;
        color: %(text)s;
    }
    QPushButton#navItem:hover { background: %(hover)s; }
    QPushButton#navItem:checked {
        background: %(sel)s;
        color: %(on_sel)s;
        font-weight: 600;
    }
    QPushButton#navItem:focus { border-color: %(sel)s; }
    QPushButton#navItem:checked:focus { border-color: %(on_sel)s; }
    QPushButton#navItem::menu-indicator { image: none; width: 0; }
    #menuLateral[colapsada="true"] QPushButton#navItem {
        text-align: center;
        padding: 7px 0;
    }
"""


def _system_stylesheet(c: dict[str, str]) -> str:
    """Hoja local de la barra con Claro/Oscuro, con los colores de la paleta."""
    return _SYSTEM_QSS % c  # noqa: UP031

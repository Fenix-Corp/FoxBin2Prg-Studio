"""Ventana principal: menu lateral (`SideNav`) y paginas apiladas.

La navegacion es la misma del Migrador VFP9 -> Fenix 360: grupos con icono a la
izquierda, preferencias fijas al pie y atajos Ctrl+Tab / Ctrl+RePag / Ctrl+AvPag.
Ya no hay barra de menus ni fila de pestanas: todo se alcanza desde la barra.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QActionGroup, QDesktopServices, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from fb2p_studio import __version__
from fb2p_studio.core.settings import Settings
from fb2p_studio.core.updates import DEFAULT_MANIFEST, UpdateChecker, UpdateInfo
from fb2p_studio.ui import sidenav, theme
from fb2p_studio.ui.dialog_preferences import PreferencesDialog
from fb2p_studio.ui.sidenav import SideNav
from fb2p_studio.ui.tab_about import AboutTab
from fb2p_studio.ui.tab_convert import ConvertTab
from fb2p_studio.ui.tab_project import ProjectTab
from fb2p_studio.ui.theme import LogColors
from fb2p_studio.ui.widgets.corporate_header import CorporateHeader
from fb2p_studio.ui.widgets.toast import Toast

#: Glifos de Segoe Fluent Icons / MDL2 de cada opcion del menu lateral.
GLYPH_CONVERT = 0xE8AB
GLYPH_PROJECT = 0xE838
GLYPH_ABOUT = 0xE946
GLYPH_PREFERENCES = 0xE713
GLYPH_UPDATES = 0xE895


class MainWindow(QMainWindow):
    def __init__(self, log_colors: LogColors) -> None:
        super().__init__()
        self.setWindowTitle(f"FoxBin2Prg-Studio {__version__}")
        # El menu lateral se lleva ~236 px del ancho: la ventana abre mas ancha
        # para que la pagina tenga el espacio de siempre.
        self.resize(1160, 700)

        self._settings = Settings()
        self._checker: UpdateChecker | None = None
        self._pending_update: UpdateInfo | None = None

        self._tab_convert = ConvertTab(self._settings, log_colors)
        self._tab_project = ProjectTab(self._settings, log_colors)
        self._tab_about = AboutTab(self._settings)

        # La banda corporativa sólo existe con el tema ADS; con Claro y Oscuro
        # la ventana se mimetiza con Windows y la banda estorbaria.
        central = QWidget()
        raiz = QVBoxLayout(central)
        raiz.setContentsMargins(0, 0, 0, 0)
        raiz.setSpacing(0)
        self._header = CorporateHeader()
        raiz.addWidget(self._header)

        cuerpo = QHBoxLayout()
        cuerpo.setContentsMargins(0, 0, 0, 0)
        cuerpo.setSpacing(0)
        self._nav = SideNav()
        cuerpo.addWidget(self._nav)

        # Una pagina por herramienta; la que se ve la elige el menu lateral.
        # Sobre ellas, el encabezado «Grupo › Pagina».
        self._pages = QStackedWidget()
        self._pages.setObjectName("paginas")
        self._section_title = QLabel()
        self._section_title.setObjectName("tituloSeccion")
        contenedor = QWidget()
        self._margen = QVBoxLayout(contenedor)
        self._margen.setSpacing(0)
        self._margen.addWidget(self._section_title)
        self._margen.addWidget(self._pages, 1)
        cuerpo.addWidget(contenedor, 1)
        raiz.addLayout(cuerpo, 1)
        self.setCentralWidget(central)

        # Aviso de version nueva: vive a la derecha de la barra de estado y
        # sólo aparece si hay algo que avisar.
        self._lbl_update = QLabel(self)
        self._lbl_update.setVisible(False)
        self._lbl_update.setOpenExternalLinks(False)
        self._lbl_update.linkActivated.connect(lambda _: self._show_update_dialog())
        self.statusBar().addPermanentWidget(self._lbl_update)

        self.statusBar().showMessage(self.tr("Listo"))

        self._nav.currentChanged.connect(self._show_page)
        self._mount_pages()
        self._build_preferences_menu()
        self._build_shortcuts()
        self._show_page(0)
        # El tema ya lo aplico `app.run`; aqui queda lo que depende de la
        # ventana: la banda, los margenes y el menu lateral.
        self._decorate(theme.current())

        if self._settings.check_updates_on_start:
            # Diferido sólo lo justo para que la ventana pinte primero. El
            # chequeo corre fuera del hilo de la UI y avisa con un toast, asi
            # que puede tardar lo que tarde el NAS sin demorar el arranque ni
            # interrumpir a quien ya empezo a trabajar.
            QTimer.singleShot(400, lambda: self._check_updates(quiet=True))

    # ------------------------------------------------------------ menu lateral
    def _mount_pages(self) -> None:
        """Arma las paginas y sus opciones en el menu lateral."""
        self._nav.add_group(self.tr("Herramientas"))
        for titulo, glifo, pagina in (
            (self.tr("Convertir"), GLYPH_CONVERT, self._tab_convert),
            (self.tr("Proyecto"), GLYPH_PROJECT, self._tab_project),
            (self.tr("Acerca de"), GLYPH_ABOUT, self._tab_about),
        ):
            self._pages.addWidget(pagina)
            self._nav.add_page(titulo, glifo)

    def _show_page(self, indice: int) -> None:
        """Muestra la pagina elegida en el menu lateral, con su encabezado."""
        if not 0 <= indice < self._pages.count():
            return
        self._pages.setCurrentIndex(indice)
        grupo, titulo = self._nav.page_path(indice)
        self._section_title.setText(f"{grupo}  ›  {titulo}")

    def _build_preferences_menu(self) -> None:
        """El grupo «Preferencias», fijo al pie del menu lateral.

        Reemplaza a la barra de menus (Archivo / Herramientas / Ayuda): como en
        una aplicacion web, todo se alcanza desde la misma barra. «Tema» abre un
        menu con los tres temas, exclusivos y marcables.
        """
        menu_tema = QMenu(self)
        self._acciones_tema = QActionGroup(self)
        self._acciones_tema.setExclusive(True)
        actual = theme.current()
        for tema_id, nombre in theme.NOMBRES.items():
            accion = menu_tema.addAction(nombre)
            accion.setCheckable(True)
            accion.setChecked(tema_id == actual)
            accion.setData(tema_id)
            self._acciones_tema.addAction(accion)
        self._acciones_tema.triggered.connect(lambda accion: self._set_theme_from_menu(accion.data()))

        self._nav.add_group(self.tr("Preferencias"), footer=True)
        self._nav.add_action(self.tr("Tema"), sidenav.GLYPH_THEME, menu=menu_tema)
        self._nav.add_action(
            self.tr("Preferencias..."), GLYPH_PREFERENCES, slot=self._open_preferences
        )
        self._nav.add_action(
            self.tr("Buscar actualizaciones..."),
            GLYPH_UPDATES,
            slot=lambda: self._check_updates(quiet=False),
        )

    def _build_shortcuts(self) -> None:
        """Ctrl+Tab y Ctrl+RePag/AvPag, como en la fila de pestanas de antes."""
        for teclas, paso in (
            ("Ctrl+Tab", 1),
            ("Ctrl+Shift+Tab", -1),
            ("Ctrl+PgDown", 1),
            ("Ctrl+PgUp", -1),
        ):
            atajo = QShortcut(QKeySequence(teclas), self)
            atajo.activated.connect(lambda p=paso: self._nav.step(p))
        # «Archivo > Salir» ya no existe: queda su atajo.
        salir = QShortcut(QKeySequence.StandardKey.Quit, self)
        salir.activated.connect(self.close)

    def _set_theme_from_menu(self, tema: str) -> None:
        """Elige tema desde el menu lateral: se aplica y se recuerda."""
        self._settings.theme = tema
        self._apply_theme(tema)
        self.statusBar().showMessage(self.tr("Tema: {0}").format(theme.NOMBRES[theme.current()]), 4000)

    def _open_preferences(self) -> None:
        dlg = PreferencesDialog(self._settings, self)
        if dlg.exec():
            self._apply_theme(dlg.theme_id())
            self._tab_convert._refresh_preview()  # noqa: SLF001
            self._tab_project._refresh_preview()  # noqa: SLF001
            self._tab_about.refresh()
            self.statusBar().showMessage(self.tr("Preferencias actualizadas"), 3000)

    def _apply_theme(self, name: str) -> None:
        """Cambia el tema sin reiniciar.

        La hoja de estilo y la paleta las repinta Qt solo. Lo unico que no
        viaja es el color del log, que los widgets guardaron al construirse:
        por eso se reparte a mano.
        """
        app = QApplication.instance()
        if not isinstance(app, QApplication):
            return
        colores = theme.apply(app, name)
        # El menu de Tema marca el aplicado aunque el cambio venga de Preferencias.
        for accion in self._acciones_tema.actions():
            accion.setChecked(accion.data() == theme.current())
        self._decorate(theme.current())
        self._tab_convert.set_log_colors(colores)
        self._tab_project.set_log_colors(colores)

    def _decorate(self, tema: str) -> None:
        """Lo que distingue visualmente a un tema del otro, fuera del QSS.

        Con Claro y Oscuro la ventana se ve como una de Windows: sin banda
        corporativa y con margenes mas ajustados. La banda tiene sentido con la
        identidad de la casa; sobre un fondo oscuro seria una franja azul sin
        relacion con nada.
        """
        es_ads = tema == theme.ADS
        self._header.setVisible(es_ads)
        self._nav.apply_theme(tema)
        # Sin hoja de estilo (Claro u Oscuro) el encabezado toma su tamano de
        # aqui; con la del tema ADS, la hoja manda sobre esta fuente.
        fuente = self._section_title.font()
        fuente.setPointSize(13)
        fuente.setBold(True)
        self._section_title.setFont(fuente)
        self._margen.setContentsMargins(*((12, 10, 12, 12) if es_ads else (6, 6, 6, 6)))

    # ------------------------------------------------------------ updates
    def _manifest_path(self) -> str:
        return self._settings.update_manifest or DEFAULT_MANIFEST

    def _check_updates(self, *, quiet: bool) -> None:
        """`quiet=True` (arranque): sólo habla si hay novedad.

        `quiet=False` (menu lateral): contesta siempre, incluso si el NAS no
        responde — si lo pediste a mano, querés una respuesta.
        """
        if self._checker is not None:
            return  # ya hay uno en curso

        checker = UpdateChecker(self._manifest_path(), __version__, self)
        checker.found.connect(lambda info: self._on_update_found(info, quiet=quiet))
        checker.up_to_date.connect(lambda v: self._on_up_to_date(v, quiet=quiet))
        checker.failed.connect(lambda motivo: self._on_update_failed(motivo, quiet=quiet))
        self._checker = checker

        if not quiet:
            self.statusBar().showMessage(self.tr("Buscando actualizaciones..."), 3000)
        checker.start()

    def _on_update_found(self, info: UpdateInfo, *, quiet: bool) -> None:
        self._checker = None
        self._pending_update = info
        self._lbl_update.setText(
            '<a href="#">' + self.tr("Hay una version nueva: {0}").format(info.version) + "</a>"
        )
        self._lbl_update.setVisible(True)

        if quiet:
            # Al arrancar no interrumpimos con un modal: un toast que se va
            # solo, mas el link permanente en la barra de estado por si el
            # aviso paso de largo.
            toast = Toast.show_message(
                self,
                self.tr("Hay una version nueva de FoxBin2Prg-Studio: {0}").format(info.version),
                level="info",
                action=self.tr("Ver"),
            )
            toast.clicked.connect(self._show_update_dialog)
        else:
            self._show_update_dialog()

    def _on_up_to_date(self, version: str, *, quiet: bool) -> None:
        self._checker = None
        if not quiet:
            QMessageBox.information(
                self,
                self.tr("Sin actualizaciones"),
                self.tr("Estas en la ultima version publicada ({0}).").format(version),
            )

    def _on_update_failed(self, motivo: str, *, quiet: bool) -> None:
        self._checker = None
        if quiet:
            return  # el NAS puede no estar disponible; no molestamos al arrancar
        QMessageBox.warning(
            self,
            self.tr("No se pudo verificar"),
            self.tr(
                "No se pudo leer el manifiesto de versiones.\n\n{0}\n\n"
                "Se puede cambiar su ubicacion en Preferencias, al pie del menu lateral."
            ).format(motivo),
        )

    def _show_update_dialog(self) -> None:
        info = self._pending_update
        if info is None:
            return

        texto = self.tr("Hay una version nueva: <b>{0}</b> (tenes la {1}).").format(
            info.version, __version__
        )
        if info.notes:
            texto += f"<br><br>{info.notes}"

        box = QMessageBox(self)
        box.setWindowTitle(self.tr("Actualizacion disponible"))
        box.setIcon(QMessageBox.Icon.Information)
        box.setTextFormat(Qt.TextFormat.RichText)
        box.setText(texto)

        carpeta = _carpeta_del_paquete(info.package)
        if carpeta is not None:
            box.setInformativeText(self.tr("Paquete:\n{0}").format(info.package))
            abrir = box.addButton(self.tr("Abrir carpeta"), QMessageBox.ButtonRole.AcceptRole)
        else:
            abrir = None
        box.addButton(self.tr("Cerrar"), QMessageBox.ButtonRole.RejectRole)
        box.exec()

        if abrir is not None and box.clickedButton() is abrir and carpeta is not None:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(carpeta)))


def _carpeta_del_paquete(package: str) -> Path | None:
    """Carpeta contenedora del paquete, si el manifiesto trae una ruta usable."""
    if not package.strip():
        return None
    p = Path(package)
    carpeta = p.parent if p.suffix else p
    return carpeta if str(carpeta) not in (".", "") else None

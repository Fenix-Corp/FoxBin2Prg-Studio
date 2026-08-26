"""Ventana principal con QTabWidget."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QAction, QDesktopServices, QKeySequence
from PySide6.QtWidgets import QLabel, QMainWindow, QMessageBox, QTabWidget

from fb2p_studio import __version__
from fb2p_studio.core.settings import Settings
from fb2p_studio.core.updates import DEFAULT_MANIFEST, UpdateChecker, UpdateInfo
from fb2p_studio.ui.dialog_preferences import PreferencesDialog
from fb2p_studio.ui.tab_about import AboutTab
from fb2p_studio.ui.tab_convert import ConvertTab
from fb2p_studio.ui.tab_project import ProjectTab
from fb2p_studio.ui.theme import LogColors


class MainWindow(QMainWindow):
    def __init__(self, log_colors: LogColors) -> None:
        super().__init__()
        self.setWindowTitle(f"FoxBin2Prg-Studio {__version__}")
        self.resize(940, 700)

        self._settings = Settings()
        self._checker: UpdateChecker | None = None
        self._pending_update: UpdateInfo | None = None

        self._tabs = QTabWidget(self)
        self._tab_convert = ConvertTab(self._settings, log_colors)
        self._tab_project = ProjectTab(self._settings, log_colors)
        self._tab_about = AboutTab(self._settings)
        self._tabs.addTab(self._tab_convert, self.tr("Convertir"))
        self._tabs.addTab(self._tab_project, self.tr("Proyecto"))
        self._tabs.addTab(self._tab_about, self.tr("Acerca de"))
        self.setCentralWidget(self._tabs)

        # Aviso de version nueva: vive a la derecha de la barra de estado y
        # sólo aparece si hay algo que avisar.
        self._lbl_update = QLabel(self)
        self._lbl_update.setVisible(False)
        self._lbl_update.setOpenExternalLinks(False)
        self._lbl_update.linkActivated.connect(lambda _: self._show_update_dialog())
        self.statusBar().addPermanentWidget(self._lbl_update)

        self._build_menu()
        self.statusBar().showMessage(self.tr("Listo"))

        if self._settings.check_updates_on_start:
            # Diferido: que la ventana pinte primero. El chequeo en si corre
            # fuera del hilo de la UI (el NAS puede tardar en responder).
            QTimer.singleShot(1500, lambda: self._check_updates(quiet=True))

    def _build_menu(self) -> None:
        menu = self.menuBar()
        m_file = menu.addMenu(self.tr("&Archivo"))
        act_quit = QAction(self.tr("Salir"), self)
        act_quit.setShortcut(QKeySequence.StandardKey.Quit)
        act_quit.triggered.connect(self.close)
        m_file.addAction(act_quit)

        m_tools = menu.addMenu(self.tr("&Herramientas"))
        act_prefs = QAction(self.tr("Preferencias..."), self)
        act_prefs.triggered.connect(self._open_preferences)
        m_tools.addAction(act_prefs)

        m_help = menu.addMenu(self.tr("A&yuda"))
        act_updates = QAction(self.tr("Buscar actualizaciones..."), self)
        act_updates.triggered.connect(lambda: self._check_updates(quiet=False))
        m_help.addAction(act_updates)

    def _open_preferences(self) -> None:
        dlg = PreferencesDialog(self._settings, self)
        if dlg.exec():
            self._tab_convert._refresh_preview()  # noqa: SLF001
            self._tab_project._refresh_preview()  # noqa: SLF001
            self._tab_about.refresh()
            self.statusBar().showMessage(self.tr("Preferencias actualizadas"), 3000)

    # ------------------------------------------------------------ updates
    def _manifest_path(self) -> str:
        return self._settings.update_manifest or DEFAULT_MANIFEST

    def _check_updates(self, *, quiet: bool) -> None:
        """`quiet=True` (arranque): sólo habla si hay novedad.

        `quiet=False` (menu Ayuda): contesta siempre, incluso si el NAS no
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
        # Al arrancar no interrumpimos con un modal: queda el link en la barra
        # de estado, que abre el detalle cuando la persona quiera.
        if not quiet:
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
                "Se puede cambiar su ubicacion en Herramientas > Preferencias."
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

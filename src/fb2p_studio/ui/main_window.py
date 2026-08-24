"""Ventana principal con QTabWidget."""

from __future__ import annotations

from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QMainWindow, QTabWidget

from fb2p_studio import __version__
from fb2p_studio.core.settings import Settings
from fb2p_studio.ui.dialog_preferences import PreferencesDialog
from fb2p_studio.ui.tab_about import AboutTab
from fb2p_studio.ui.tab_convert import ConvertTab


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"FoxBin2Prg-Studio {__version__}")
        self.resize(940, 700)

        self._settings = Settings()

        self._tabs = QTabWidget(self)
        self._tab_convert = ConvertTab(self._settings)
        self._tab_about = AboutTab(self._settings)
        self._tabs.addTab(self._tab_convert, "Convertir")
        self._tabs.addTab(self._tab_about, "Acerca de")
        self.setCentralWidget(self._tabs)

        self._build_menu()
        self.statusBar().showMessage("Listo")

    def _build_menu(self) -> None:
        menu = self.menuBar()
        m_file = menu.addMenu("&Archivo")
        act_quit = QAction("Salir", self)
        act_quit.setShortcut(QKeySequence.StandardKey.Quit)
        act_quit.triggered.connect(self.close)
        m_file.addAction(act_quit)

        m_tools = menu.addMenu("&Herramientas")
        act_prefs = QAction("Preferencias...", self)
        act_prefs.triggered.connect(self._open_preferences)
        m_tools.addAction(act_prefs)

    def _open_preferences(self) -> None:
        dlg = PreferencesDialog(self._settings, self)
        if dlg.exec():
            self._tab_convert._refresh_preview()  # noqa: SLF001
            self._tab_about.refresh()
            self.statusBar().showMessage("Preferencias actualizadas", 3000)

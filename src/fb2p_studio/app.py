"""QApplication + main window bootstrap."""

from __future__ import annotations

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication

from fb2p_studio import __version__
from fb2p_studio.ui.main_window import MainWindow


def run(argv: list[str]) -> int:
    QCoreApplication.setOrganizationName("ADS Software")
    QCoreApplication.setApplicationName("FoxBin2Prg-Studio")
    QCoreApplication.setApplicationVersion(__version__)

    app = QApplication(argv)
    window = MainWindow()
    window.show()
    return app.exec()

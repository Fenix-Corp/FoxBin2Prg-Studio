"""QApplication + main window bootstrap."""

from __future__ import annotations

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication

from fb2p_studio import __version__
from fb2p_studio.ui import theme
from fb2p_studio.ui.main_window import MainWindow


def run(argv: list[str]) -> int:
    QCoreApplication.setOrganizationName("ADS Software")
    QCoreApplication.setApplicationName("FoxBin2Prg-Studio")
    QCoreApplication.setApplicationVersion(__version__)

    app = QApplication(argv)
    log_colors = theme.apply(app)
    window = MainWindow(log_colors=log_colors)
    window.show()
    return app.exec()

"""QApplication + main window bootstrap."""

from __future__ import annotations

import sys

from PySide6.QtCore import QCoreApplication, QLocale, QTranslator
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from fb2p_studio import __version__
from fb2p_studio.core import discovery
from fb2p_studio.core.settings import Settings
from fb2p_studio.ui import theme
from fb2p_studio.ui.main_window import MainWindow

_APP_ID = "ADSSoftware.FoxBin2PrgStudio"


def _set_taskbar_identity() -> None:
    """Le da a la ventana su propia identidad en la barra de tareas de Windows.

    Sin esto, corriendo desde fuente Windows agrupa la ventana bajo el icono
    de `python.exe` y muestra ese icono en vez del nuestro.
    """
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(_APP_ID)
    except (OSError, AttributeError):
        pass  # cosmetico: si no se puede, seguimos igual


def _app_icon() -> QIcon:
    """Icono de la app; QIcon vacio si el .ico no esta (ver build/make_icon.py)."""
    path = discovery.app_icon_path()
    return QIcon(str(path)) if path is not None else QIcon()


def _install_translator(app: QApplication) -> QTranslator | None:
    """Carga la traduccion del idioma del sistema, si existe.

    El idioma fuente es el espanol: las cadenas estan en el codigo tal cual se
    muestran, asi que en una maquina en espanol no hay nada que cargar y esto
    devuelve None. Para el resto, `QTranslator.load()` con un QLocale prueba
    solo las variantes (`en_US` -> `en`) y cae con elegancia si no hay .qm.

    Los .ts/.qm se generan con `build\\i18n.bat`.

    Hay que conservar la referencia al traductor: si lo junta el GC, Qt lo
    desinstala y la UI vuelve al idioma fuente sin avisar. Por eso se devuelve
    y el llamador lo guarda.
    """
    carpeta = discovery.resources_dir() / "i18n"
    if not carpeta.is_dir():
        return None

    translator = QTranslator(app)
    if translator.load(QLocale.system(), "fb2p_studio", "_", str(carpeta), ".qm"):
        app.installTranslator(translator)
        return translator
    return None


def run(argv: list[str]) -> int:
    QCoreApplication.setOrganizationName("ADS Software")
    QCoreApplication.setApplicationName("FoxBin2Prg-Studio")
    QCoreApplication.setApplicationVersion(__version__)
    _set_taskbar_identity()

    app = QApplication(argv)
    app.setWindowIcon(_app_icon())
    translator = _install_translator(app)  # noqa: F841 — mantiene viva la referencia

    settings = Settings()
    log_colors = theme.apply(app, settings.theme)
    window = MainWindow(log_colors=log_colors)
    window.show()
    return app.exec()

"""Tab Acerca de: version + rutas detectadas."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFormLayout, QLabel, QVBoxLayout, QWidget

from fb2p_studio import __version__
from fb2p_studio.core.discovery import resolve
from fb2p_studio.core.settings import Settings


class AboutTab(QWidget):
    def __init__(self, settings: Settings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._settings = settings

        self._lbl_vfp = QLabel()
        self._lbl_fb2p = QLabel()
        self._lbl_bridge = QLabel()

        header = QLabel(f"<h2>FoxBin2Prg-Studio {__version__}</h2>"
                        "<p>GUI de administracion para <b>FoxBin2Prg</b> — utilitario generico para proyectos VFP9.</p>")
        header.setTextFormat(Qt.TextFormat.RichText)
        header.setWordWrap(True)

        form = QFormLayout()
        form.addRow("vfp9.exe:", self._lbl_vfp)
        form.addRow("FoxBin2Prg (home):", self._lbl_fb2p)
        form.addRow("Bridge PRG:", self._lbl_bridge)

        credits = QLabel(
            "<p>FoxBin2Prg es obra de <a href='https://github.com/fdbozzo/foxbin2prg'>Fernando D. Bozzo</a> "
            "y mantenido por <a href='https://github.com/lscheffler'>Lutz Scheffler</a>.</p>"
            "<p>Esta GUI la habla vía <b>Object API</b> (<code>c_foxbin2prg</code>) para reportar errores "
            "estructurados en vez del <code>ErrorLevel 0/1</code> del CLI.</p>"
        )
        credits.setTextFormat(Qt.TextFormat.RichText)
        credits.setOpenExternalLinks(True)
        credits.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.addWidget(header)
        layout.addLayout(form)
        layout.addWidget(credits)
        layout.addStretch(1)

        self.refresh()

    def refresh(self) -> None:
        paths = resolve(self._settings.vfp_exe or None, self._settings.fb2p_home or None)
        self._lbl_vfp.setText(str(paths.vfp_exe) if paths.vfp_exe else "<no encontrado>")
        self._lbl_fb2p.setText(str(paths.fb2p_home) if paths.fb2p_home else "<no encontrado>")
        self._lbl_bridge.setText(str(paths.bridge_dir))

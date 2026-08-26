"""Tab Acerca de: version + rutas detectadas."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFormLayout, QLabel, QVBoxLayout, QWidget

from fb2p_studio import __version__
from fb2p_studio.core.discovery import bundled_fb2p_dir, resolve
from fb2p_studio.core.settings import Settings


class AboutTab(QWidget):
    def __init__(self, settings: Settings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._settings = settings

        self._lbl_vfp = QLabel()
        self._lbl_fb2p = QLabel()
        self._lbl_bridge = QLabel()

        header = QLabel(
            f"<h2>FoxBin2Prg-Studio {__version__}</h2>"
            + self.tr(
                "<p>GUI de administracion para <b>FoxBin2Prg</b> — utilitario generico "
                "para proyectos VFP9.</p>"
            )
        )
        header.setTextFormat(Qt.TextFormat.RichText)
        header.setWordWrap(True)

        form = QFormLayout()
        form.addRow(self.tr("vfp9.exe:"), self._lbl_vfp)
        form.addRow(self.tr("FoxBin2Prg (home):"), self._lbl_fb2p)
        form.addRow(self.tr("Bridge PRG:"), self._lbl_bridge)

        credits = QLabel(
            self.tr(
                "<p><b>FoxBin2Prg</b> es obra de <a href='https://github.com/fdbozzo/foxbin2prg'>Fernando D. Bozzo</a> "
                "y mantenido por <a href='https://github.com/lscheffler/foxbin2prg'>Lutz Scheffler</a>. "
                "Se distribuye bajo licencia "
                "<a href='https://creativecommons.org/licenses/by/4.0/'>CC BY 4.0</a>.</p>"
                "<p>Esta GUI habla con FoxBin2Prg vía su <b>Object API</b> (<code>c_foxbin2prg</code>) "
                "para reportar errores estructurados (excepción, línea, detalle) en lugar del "
                "<code>ErrorLevel 0/1</code> del CLI.</p>"
                "<p>FoxBin2Prg-Studio: MIT.</p>"
            )
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
        self._lbl_vfp.setText(str(paths.vfp_exe) if paths.vfp_exe else self.tr("<no encontrado>"))
        self._lbl_fb2p.setText(self._fb2p_text(paths.fb2p_home))
        self._lbl_bridge.setText(str(paths.bridge_dir))

    def _fb2p_text(self, home: Path | None) -> str:
        """Marca si el FoxBin2Prg en uso es el embebido o uno externo."""
        if home is None:
            return self.tr("<no encontrado>")
        if home == bundled_fb2p_dir():
            return self.tr("{0}  (embebido en Studio)").format(home)
        return self.tr("{0}  (externo)").format(home)

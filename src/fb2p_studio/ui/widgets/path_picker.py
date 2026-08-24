"""QLineEdit + boton [...] + drag & drop de archivo o carpeta."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QLineEdit, QPushButton, QWidget


class PathPicker(QWidget):
    path_changed = Signal(str)

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        mode: str = "file",  # "file" | "dir"
        placeholder: str = "",
        file_filter: str = "Todos (*.*)",
    ) -> None:
        super().__init__(parent)
        self._mode = mode
        self._file_filter = file_filter

        self._edit = QLineEdit(self)
        self._edit.setPlaceholderText(placeholder)
        self._edit.textChanged.connect(self.path_changed.emit)

        self._btn = QPushButton("...", self)
        self._btn.setFixedWidth(28)
        self._btn.clicked.connect(self._pick)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addWidget(self._edit, 1)
        layout.addWidget(self._btn)

        self.setAcceptDrops(True)

    # ------------------------------------------------------------------ mode
    def set_mode(self, mode: str) -> None:
        self._mode = mode

    # ------------------------------------------------------------------ value
    def value(self) -> str:
        return self._edit.text().strip()

    def set_value(self, path: str) -> None:
        self._edit.setText(path)

    # ------------------------------------------------------------------ pick
    def _pick(self) -> None:
        if self._mode == "dir":
            chosen = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta", self.value() or "")
        else:
            chosen, _ = QFileDialog.getOpenFileName(self, "Seleccionar archivo", self.value() or "", self._file_filter)
        if chosen:
            self._edit.setText(chosen)

    # ------------------------------------------------------------------ drag
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        for url in event.mimeData().urls():
            if url.isLocalFile():
                p = Path(url.toLocalFile())
                if self._mode == "dir" and not p.is_dir():
                    p = p.parent
                self._edit.setText(str(p))
                event.acceptProposedAction()
                return

"""Preview readonly del `job.ini` que se enviara al driver + boton Copiar."""

from __future__ import annotations

from PySide6.QtGui import QFont, QGuiApplication
from PySide6.QtWidgets import (
    QHBoxLayout,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class CommandPreview(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._edit = QPlainTextEdit(self)
        self._edit.setReadOnly(True)
        font = QFont("Consolas", 9)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self._edit.setFont(font)
        self._edit.setPlaceholderText("Vista previa del job.ini que se enviara al bridge VFP...")
        self._edit.setMaximumHeight(180)

        btn_copy = QPushButton("Copiar", self)
        btn_copy.clicked.connect(self._copy)

        toolbar = QHBoxLayout()
        toolbar.addStretch(1)
        toolbar.addWidget(btn_copy)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._edit, 1)
        layout.addLayout(toolbar)

    def set_text(self, text: str) -> None:
        self._edit.setPlainText(text)

    def _copy(self) -> None:
        QGuiApplication.clipboard().setText(self._edit.toPlainText())

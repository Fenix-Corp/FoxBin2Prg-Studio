"""Vista de log con toolbar (limpiar / guardar) y colores por severidad."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import (
    QFileDialog,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
)


class LogView(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._edit = QPlainTextEdit(self)
        self._edit.setReadOnly(True)
        self._edit.setMaximumBlockCount(5000)
        font = QFont("Consolas", 9)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self._edit.setFont(font)

        btn_clear = QPushButton("Limpiar", self)
        btn_clear.clicked.connect(self._edit.clear)
        btn_save = QPushButton("Guardar...", self)
        btn_save.clicked.connect(self._save)

        toolbar = QHBoxLayout()
        toolbar.addStretch(1)
        toolbar.addWidget(btn_clear)
        toolbar.addWidget(btn_save)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._edit, 1)
        layout.addLayout(toolbar)

    def append(self, text: str, severity: str = "info") -> None:
        color = {
            "info": QColor("#212121"),
            "ok": QColor("#1b7f34"),
            "warn": QColor("#a86500"),
            "error": QColor("#c62828"),
            "muted": QColor("#767676"),
        }.get(severity, QColor("#212121"))
        cursor = self._edit.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        fmt = QTextCharFormat()
        fmt.setForeground(color)
        cursor.setCharFormat(fmt)
        cursor.insertText(text + "\n")
        self._edit.setTextCursor(cursor)
        self._edit.ensureCursorVisible()

    def _save(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Guardar log", "fb2p_studio.log", "Log (*.log);;Todos (*.*)")
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self._edit.toPlainText())

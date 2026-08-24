"""Vista de log con toolbar (limpiar / guardar) y colores por severidad.

Los colores por nivel vienen del modulo `theme` para que se ajusten al
tema del OS (claro/oscuro).
"""

from __future__ import annotations

from PySide6.QtGui import QFont, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from fb2p_studio.ui.theme import LogColors


class LogView(QWidget):
    def __init__(self, colors: LogColors, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._colors = colors

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
            "info": self._colors.info,
            "ok": self._colors.ok,
            "warn": self._colors.warn,
            "error": self._colors.error,
            "muted": self._colors.muted,
        }.get(severity, self._colors.info)
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

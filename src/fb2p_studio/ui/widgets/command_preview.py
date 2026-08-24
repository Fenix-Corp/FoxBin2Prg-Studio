"""Preview readonly del `job.ini` que se enviara al driver + boton Copiar.

El QPlainTextEdit crece con el contenido entre un minimo (~4 lineas) y un
maximo (~20 lineas). Con contenidos mas grandes muestra scroll interno.
"""

from __future__ import annotations

from PySide6.QtGui import QFont, QFontMetrics, QGuiApplication
from PySide6.QtWidgets import (
    QHBoxLayout,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class CommandPreview(QWidget):
    _MIN_LINES = 4
    _MAX_LINES = 20

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._edit = QPlainTextEdit(self)
        self._edit.setReadOnly(True)
        font = QFont("Consolas", 9)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self._edit.setFont(font)
        self._edit.setPlaceholderText("Vista previa del job.ini que se enviara al bridge VFP...")
        self._edit.setObjectName("commandPreview")

        # Altura minima al inicio (placeholder + margen)
        self._apply_height(self._MIN_LINES)

        btn_copy = QPushButton("Copiar", self)
        btn_copy.clicked.connect(self._copy)

        toolbar = QHBoxLayout()
        toolbar.addStretch(1)
        toolbar.addWidget(btn_copy)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._edit)
        layout.addLayout(toolbar)

    # ------------------------------------------------------------------ api
    def set_text(self, text: str) -> None:
        self._edit.setPlainText(text)
        lines = text.count("\n") + 1 if text else self._MIN_LINES
        self._apply_height(max(self._MIN_LINES, min(self._MAX_LINES, lines)))

    # ------------------------------------------------------------------ private
    def _apply_height(self, lines: int) -> None:
        fm = QFontMetrics(self._edit.font())
        line_h = fm.lineSpacing()
        # margenes internos + frame
        chrome = int(self._edit.contentsMargins().top()
                     + self._edit.contentsMargins().bottom()
                     + 2 * self._edit.frameWidth() + 8)
        target = line_h * lines + chrome
        self._edit.setFixedHeight(target)

    def _copy(self) -> None:
        QGuiApplication.clipboard().setText(self._edit.toPlainText())

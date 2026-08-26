"""Aviso flotante que aparece, se lee y se va solo.

Para lo que hay que decir sin interrumpir. El caso que lo motivó es el chequeo
de actualizaciones al arrancar: la lectura del manifiesto puede tardar (esta en
el NAS) y llega cuando la ventana ya se abrio, asi que un modal apareceria
encima de alguien que ya empezo a trabajar. El toast avisa sin robar el foco y
se retira solo.

Se dibuja sobre la ventana, anclado abajo a la derecha, y se reubica cuando la
ventana cambia de tamano.
"""

from __future__ import annotations

from PySide6.QtCore import (
    QEasingCurve,
    QEvent,
    QObject,
    QPropertyAnimation,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
)

#: Cuanto queda visible antes de desvanecerse, en milisegundos.
DURACION = 9000
_FADE = 400
_MARGEN = 18

_ESTILOS = {
    "info": ("#1F3A5E", "#ffffff"),
    "ok": ("#1a6b3c", "#ffffff"),
    "warn": ("#8a5e00", "#ffffff"),
    "error": ("#9d2235", "#ffffff"),
}


class Toast(QFrame):
    """Un aviso. Se crea con `Toast.show_message(...)`, no a mano."""

    clicked = Signal()

    def __init__(
        self,
        parent: QWidget,
        text: str,
        *,
        level: str = "info",
        action: str = "",
        duration: int = DURACION,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("toast")
        self.setFrameShape(QFrame.Shape.NoFrame)
        # Sin foco: el toast no interrumpe lo que se este haciendo.
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)

        fondo, texto_color = _ESTILOS.get(level, _ESTILOS["info"])
        self.setStyleSheet(
            f"#toast {{ background: {fondo}; border-radius: 4px; }}"
            f"#toast QLabel {{ color: {texto_color}; font-size: 10pt; }}"
            f"#toast QPushButton {{"
            f"  color: {texto_color}; background: transparent;"
            f"  border: 1px solid rgba(255,255,255,0.55); border-radius: 3px;"
            f"  padding: 3px 10px; font-weight: 600;"
            f"}}"
            f"#toast QPushButton:hover {{ background: rgba(255,255,255,0.16); }}"
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 10, 10)
        layout.setSpacing(12)

        etiqueta = QLabel(text)
        etiqueta.setWordWrap(True)
        etiqueta.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(etiqueta, 1)

        if action:
            boton = QPushButton(action)
            boton.setCursor(Qt.CursorShape.PointingHandCursor)
            boton.clicked.connect(self._on_action)
            layout.addWidget(boton, 0)

        self._efecto = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._efecto)
        self._efecto.setOpacity(0.0)

        self._entrada = QPropertyAnimation(self._efecto, b"opacity", self)
        self._entrada.setDuration(_FADE)
        self._entrada.setStartValue(0.0)
        self._entrada.setEndValue(1.0)
        self._entrada.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._salida = QPropertyAnimation(self._efecto, b"opacity", self)
        self._salida.setDuration(_FADE)
        self._salida.setStartValue(1.0)
        self._salida.setEndValue(0.0)
        self._salida.finished.connect(self.deleteLater)

        self._reloj = QTimer(self)
        self._reloj.setSingleShot(True)
        self._reloj.setInterval(max(_FADE, duration))
        self._reloj.timeout.connect(self.dismiss)

        # Reubicarse cuando la ventana cambia de tamano.
        self._vigia = _Reubicador(self)
        parent.installEventFilter(self._vigia)

    # ------------------------------------------------------------------ api
    @classmethod
    def show_message(
        cls,
        parent: QWidget,
        text: str,
        *,
        level: str = "info",
        action: str = "",
        duration: int = DURACION,
    ) -> Toast:
        toast = cls(parent, text, level=level, action=action, duration=duration)
        toast.reposition()
        toast.show()
        toast.raise_()
        toast._entrada.start()
        toast._reloj.start()
        return toast

    def dismiss(self) -> None:
        self._reloj.stop()
        self._salida.start()

    def reposition(self) -> None:
        padre = self.parentWidget()
        if padre is None:
            return
        ancho = min(460, max(260, padre.width() - 2 * _MARGEN))
        self.setFixedWidth(ancho)
        self.adjustSize()
        self.move(
            padre.width() - self.width() - _MARGEN,
            padre.height() - self.height() - _MARGEN,
        )

    # ------------------------------------------------------------------ interno
    def _on_action(self) -> None:
        self.clicked.emit()
        self.dismiss()

    def mousePressEvent(self, event) -> None:  # noqa: ANN001, N802 — API de Qt
        """Un click en cualquier parte del aviso lo cierra."""
        self.dismiss()
        super().mousePressEvent(event)


class _Reubicador(QObject):
    """Mantiene el toast pegado a la esquina cuando la ventana se mueve."""

    def __init__(self, toast: Toast) -> None:
        super().__init__(toast)
        self._toast = toast

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:  # noqa: N802 — API de Qt
        if event.type() in (QEvent.Type.Resize, QEvent.Type.Move):
            self._toast.reposition()
        return False

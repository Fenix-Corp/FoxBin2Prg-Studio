"""Genera `src/fb2p_studio/resources/fb2p_studio.ico` (icono de la app).

El icono se dibuja por codigo con QPainter (no hay binarios sueltos en el
repo que despues nadie sepa de donde salieron) y se ensambla un .ico
multi-tamano a mano:

  - 16 / 32 / 48 px -> entradas DIB (BITMAPINFOHEADER + BGRA + mascara AND),
    el formato clasico que entiende cualquier version de Windows.
  - 64 / 128 / 256 px -> entradas PNG (soportado desde Vista) para no inflar
    el .ico ni el .exe.

Uso (desde la raiz del repo, con el .venv activo):

    .venv\Scripts\python.exe build\make_icon.py
"""

from __future__ import annotations

import struct
import sys
from pathlib import Path

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QImage,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "src" / "fb2p_studio" / "resources" / "fb2p_studio.ico"

# Todo el dibujo se define en un lienzo logico de 256x256 y se escala.
CANVAS = 256.0
SIZES = [16, 32, 48, 64, 128, 256]
PNG_FROM = 64  # a partir de este tamano, entrada PNG en vez de DIB

_TOP = QColor("#F7A325")   # ambar (arriba)
_BOTTOM = QColor("#DE5B14")  # naranja quemado (abajo) — guino al zorro de VFP
_EDGE = QColor(120, 42, 0, 90)
_GLYPH = QColor("#FFFFFF")


def _arrow(y: float, pointing_right: bool) -> QPainterPath:
    """Flecha horizontal (cuerpo + punta) centrada en `y`, en el lienzo 256."""
    x0, x1 = 52.0, 204.0
    half = 17.0   # medio grosor del cuerpo
    head_h = 24.0  # cuanto sobresale la punta por arriba/abajo del cuerpo
    head_w = 50.0

    if pointing_right:
        tail, tip, head_base = x0, x1, x1 - head_w
    else:
        tail, tip, head_base = x1, x0, x0 + head_w

    path = QPainterPath(QPointF(tail, y - half))
    path.lineTo(head_base, y - half)
    path.lineTo(head_base, y - half - head_h)
    path.lineTo(tip, y)
    path.lineTo(head_base, y + half + head_h)
    path.lineTo(head_base, y + half)
    path.lineTo(tail, y + half)
    path.closeSubpath()
    return path


def render(size: int) -> QImage:
    img = QImage(size, size, QImage.Format.Format_ARGB32)
    img.fill(Qt.GlobalColor.transparent)

    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    p.scale(size / CANVAS, size / CANVAS)

    # Fondo: cuadrado redondeado con degradado vertical.
    body = QRectF(10, 10, CANVAS - 20, CANVAS - 20)
    grad = QLinearGradient(0, body.top(), 0, body.bottom())
    grad.setColorAt(0.0, _TOP)
    grad.setColorAt(1.0, _BOTTOM)
    p.setBrush(QBrush(grad))
    p.setPen(QPen(_EDGE, 4))
    p.drawRoundedRect(body, 52, 52)

    # Glifo: doble flecha (bin <-> prg).
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(_GLYPH)
    p.drawPath(_arrow(96, pointing_right=True))
    p.drawPath(_arrow(160, pointing_right=False))
    p.end()
    return img


# ---------------------------------------------------------------------------
# Serializacion .ico
# ---------------------------------------------------------------------------
def _png_bytes(img: QImage) -> bytes:
    data = QByteArray()  # tiene que vivir mas que el QBuffer que lo envuelve
    buf = QBuffer(data)
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    img.save(buf, "PNG")
    buf.close()
    return bytes(data)


def _dib_bytes(img: QImage) -> bytes:
    """Entrada BMP clasica: header + pixeles BGRA (bottom-up) + mascara AND."""
    w, h = img.width(), img.height()

    pixels = bytearray()
    for y in range(h - 1, -1, -1):  # el DIB va de abajo hacia arriba
        for x in range(w):
            c = img.pixelColor(x, y)
            pixels += bytes((c.blue(), c.green(), c.red(), c.alpha()))

    mask_stride = ((w + 31) // 32) * 4  # filas de 1bpp alineadas a 4 bytes
    mask = bytes(mask_stride * h)       # 0 = opaco; el alpha del BGRA manda

    header = struct.pack(
        "<IiiHHIIiiII",
        40,        # biSize
        w,         # biWidth
        h * 2,     # biHeight (XOR + AND)
        1,         # biPlanes
        32,        # biBitCount
        0,         # biCompression (BI_RGB)
        len(pixels) + len(mask),  # biSizeImage
        0, 0, 0, 0,               # resolucion y paleta
    )
    return header + bytes(pixels) + mask


def build_ico(sizes: list[int]) -> bytes:
    images: list[bytes] = []
    for size in sizes:
        img = render(size)
        images.append(_png_bytes(img) if size >= PNG_FROM else _dib_bytes(img))

    offset = 6 + 16 * len(sizes)
    directory = struct.pack("<HHH", 0, 1, len(sizes))
    for size, data in zip(sizes, images, strict=True):
        dim = 0 if size >= 256 else size  # 256 se codifica como 0
        directory += struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(data), offset)
        offset += len(data)
    return directory + b"".join(images)


def main() -> int:
    # QImage/QPainter no necesitan QGuiApplication: se dibuja sin ventana ni
    # plataforma grafica, asi que el script corre igual en un servidor de CI.
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_bytes(build_ico(SIZES))
    print(f"[icon] {OUT.relative_to(ROOT)} ({OUT.stat().st_size:,} bytes) — {SIZES}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

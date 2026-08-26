"""El icono versionado tiene que seguir siendo un .ico multi-tamano valido.

Se genera con `build/make_icon.py`, pero lo que viaja al .exe es el archivo
commiteado. Si alguien lo borra, lo trunca o lo reemplaza por un PNG renombrado,
el build de PyInstaller falla lejos de la causa; este test lo agarra antes.
"""

from __future__ import annotations

import struct

from fb2p_studio.core.discovery import app_icon_path

TAMANOS_ESPERADOS = {16, 32, 48, 64, 128, 256}


def _entradas_del_ico(data: bytes) -> list[dict[str, int]]:
    """Parsea el ICONDIR y devuelve una entrada por imagen."""
    reserved, tipo, cantidad = struct.unpack("<HHH", data[:6])
    assert reserved == 0, "el header del .ico no arranca en 0"
    assert tipo == 1, f"tipo {tipo}: no es un icono (2 seria un cursor)"

    entradas = []
    for i in range(cantidad):
        base = 6 + 16 * i
        ancho, alto, _colores, _res, planos, bits, tam, offset = struct.unpack(
            "<BBBBHHII", data[base : base + 16]
        )
        entradas.append(
            {
                # 0 en el ICONDIR significa 256: no entra en un byte
                "ancho": ancho or 256,
                "alto": alto or 256,
                "planos": planos,
                "bits": bits,
                "tam": tam,
                "offset": offset,
            }
        )
    return entradas


def test_el_icono_existe() -> None:
    assert app_icon_path() is not None, "falta el .ico: correr build/make_icon.py"


def test_tiene_todos_los_tamanos() -> None:
    path = app_icon_path()
    assert path is not None
    entradas = _entradas_del_ico(path.read_bytes())

    assert {e["ancho"] for e in entradas} == TAMANOS_ESPERADOS
    assert all(e["ancho"] == e["alto"] for e in entradas), "hay entradas no cuadradas"
    assert all(e["bits"] == 32 for e in entradas), "se esperan 32 bpp (con alpha)"


def test_cada_imagen_esta_completa_y_bien_formada() -> None:
    """Offsets y tamanos tienen que caer dentro del archivo, sin datos truncados."""
    path = app_icon_path()
    assert path is not None
    data = path.read_bytes()

    for e in _entradas_del_ico(data):
        fin = e["offset"] + e["tam"]
        assert fin <= len(data), f"imagen de {e['ancho']}px truncada"

        imagen = data[e["offset"] : fin]
        if imagen[:8] == b"\x89PNG\r\n\x1a\n":
            ancho, alto = struct.unpack(">II", imagen[16:24])  # cabecera IHDR
        else:
            ancho, alto = struct.unpack("<ii", imagen[4:12])  # BITMAPINFOHEADER
            alto //= 2  # el DIB apila XOR + mascara AND
        assert (ancho, alto) == (e["ancho"], e["alto"]), (
            f"la entrada dice {e['ancho']}x{e['alto']} pero la imagen es {ancho}x{alto}"
        )

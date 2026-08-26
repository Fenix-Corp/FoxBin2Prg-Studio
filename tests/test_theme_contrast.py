"""Contraste WCAG de los pares texto/fondo del tema ADS.

Portado de `UtilitiesDevelopment/tools/check_contrast.py`, donde el ambar
"natural" (#9d6b00) se cambio justamente porque daba 4,09:1 y no llegaba al
minimo. Aca vive como test y no como script para que el gate lo corra siempre:
un retoque de color que rompa la accesibilidad no pasa en silencio.

Los colores se LEEN del modulo del tema, no se copian: el test verifica el
codigo que se va a compilar.

Umbral WCAG 2.1 AA: 4,5:1 para texto normal, 3:1 para texto grande o en
negrita.
"""

from __future__ import annotations

import pytest

from fb2p_studio.ui import theme_ads as T


def luminancia(color: str) -> float:
    """Luminancia relativa segun WCAG 2.1."""
    h = color.lstrip("#")
    canales = []
    for i in (0, 2, 4):
        c = int(h[i : i + 2], 16) / 255.0
        canales.append(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * canales[0] + 0.7152 * canales[1] + 0.0722 * canales[2]


def contraste(texto: str, fondo: str) -> float:
    a, b = luminancia(texto), luminancia(fondo)
    return (max(a, b) + 0.05) / (min(a, b) + 0.05)


#: (descripcion, texto, fondo, umbral)
CASOS = [
    # La bitacora, que es donde se lee el resultado de una conversion.
    ("log · info", T.INFO, T.SURFACE_CODE, 4.5),
    ("log · ok", T.OK, T.SURFACE_CODE, 4.5),
    ("log · warn", T.WARN, T.SURFACE_CODE, 4.5),
    ("log · error", T.ERROR, T.SURFACE_CODE, 4.5),
    ("log · muted", T.MUTED, T.SURFACE_CODE, 4.5),
    # El arbol de contenido y el de resultados, con sus cuatro estados.
    ("arbol · reposo", T.TEXT, T.SURFACE, 4.5),
    ("arbol · fila alterna", T.TEXT, T.ALT_ROW, 4.5),
    ("arbol · raton encima", T.PRIMARY_DARK, T.HOVER_BG, 4.5),
    ("arbol · elegido con foco", T.TEXT_ON_PRIMARY, T.PRIMARY, 4.5),
    ("arbol · elegido raton encima", T.TEXT_ON_PRIMARY, T.PRIMARY_MID, 4.5),
    ("arbol · elegido sin foco", T.PRIMARY_DARK, T.SELECTED_INACTIVE_BG, 4.5),
    ("arbol · ok sobre fila alterna", T.OK, T.ALT_ROW, 4.5),
    ("arbol · error sobre fila alterna", T.ERROR, T.ALT_ROW, 4.5),
    ("arbol · muted sobre fila alterna", T.MUTED, T.ALT_ROW, 4.5),
    # Controles.
    ("boton principal", T.TEXT_ON_PRIMARY, T.PRIMARY, 3.0),
    ("boton principal · raton encima", T.TEXT_ON_PRIMARY, T.PRIMARY_MID, 3.0),
    ("boton principal · inhabilitado", T.TEXT_MUTED, "#cdd4de", 3.0),
    ("boton normal", T.TEXT, T.SURFACE, 4.5),
    ("boton normal · raton encima", T.PRIMARY, T.SURFACE, 4.5),
    ("campo de texto", T.TEXT, T.SURFACE, 4.5),
    ("campo inhabilitado", T.TEXT_MUTED, T.SURFACE_ALT, 4.5),
    ("pestana elegida", T.PRIMARY, T.SURFACE, 4.5),
    ("pestana sin elegir", T.TEXT_MUTED, T.SURFACE_ALT, 4.5),
    ("titulo de grupo", T.PRIMARY, T.SURFACE, 4.5),
    # La banda corporativa.
    ("banda · titulo", T.TEXT_ON_PRIMARY, T.PRIMARY, 3.0),
    ("banda · subtitulo", "#c8d4e4", T.PRIMARY, 4.5),
    # Textos de ayuda y barra de estado.
    ("texto de ayuda", T.TEXT_MUTED, T.SURFACE_ALT, 4.5),
    ("barra de estado", T.TEXT_MUTED, T.SURFACE_ALT, 4.5),
    ("encabezado de columna", T.TEXT_MUTED, T.SURFACE_ALT, 4.5),
]


@pytest.mark.parametrize(("descripcion", "texto", "fondo", "umbral"), CASOS)
def test_contraste_wcag_aa(descripcion: str, texto: str, fondo: str, umbral: float) -> None:
    medido = contraste(texto, fondo)
    assert medido >= umbral, (
        f"{descripcion}: {texto} sobre {fondo} da {medido:.2f}:1, "
        f"por debajo del minimo {umbral}:1 de WCAG AA"
    )


def test_la_formula_reconoce_un_par_ilegible() -> None:
    """Si el calculo estuviera mal, todos los casos pasarian por casualidad."""
    assert contraste("#ffffff", "#ffffff") == pytest.approx(1.0)
    assert contraste("#000000", "#ffffff") == pytest.approx(21.0, abs=0.01)
    assert contraste("#9d6b00", T.SURFACE_CODE) < 4.5  # el ambar que se descarto

"""Mapeo de extensiones binarias VFP <-> texto FoxBin2Prg."""

from __future__ import annotations

BIN_TO_TEXT: dict[str, str] = {
    "pjx": "pj2",
    "vcx": "vc2",
    "scx": "sc2",
    "frx": "fr2",
    "lbx": "lb2",
    "mnx": "mn2",
    "dbc": "dc2",
    "dbf": "db2",
    "fky": "fk2",
    "mem": "me2",
}
TEXT_TO_BIN: dict[str, str] = {v: k for k, v in BIN_TO_TEXT.items()}

#: Extensiones de proyecto. Son las unicas que admiten el modo "todo el
#: proyecto" (cType "*" / "*-") de FoxBin2Prg.
PROJECT_BIN = "pjx"
PROJECT_TEXT = "pj2"

#: cType para procesar un proyecto entero. La direccion NO se indica: la
#: decide la extension del archivo (.pjx -> a texto, .pj2 -> a binario).
PROJECT_WITH_PJX = "*"
PROJECT_WITHOUT_PJX = "*-"

#: Nivel de soporte por extension: los valores **por defecto** de las claves
#: `n_XXX_Conversion_Support` de FoxBin2Prg.
#:
#:   2 = las dos direcciones.
#:   1 = SOLO binario -> texto.
#:
#: `hasSupport_Bin2Prg()` pide `> 0` y `hasSupport_Prg2Bin()` pide `= 2` (para
#: DBF acepta tambien 8, "import de datos"). De ahi que `.dbf`, `.fky` y `.mem`
#: se vuelquen a texto pero **no** se reconstruyan: rearmar una tabla desde su
#: dump pisaria los datos, asi que hay que pedirlo explicitamente por `.cfg`.
#:
#: Un `foxbin2prg.cfg` puede cambiar cualquiera de estos valores; esto es lo
#: que pasa si nadie lo toco.
DEFAULT_SUPPORT: dict[str, int] = {
    "pjx": 2,
    "vcx": 2,
    "scx": 2,
    "frx": 2,
    "lbx": 2,
    "mnx": 2,
    "dbc": 2,
    "dbf": 1,
    "fky": 1,
    "mem": 1,
}

#: Extensiones binarias que, por defecto, no se regeneran desde el texto.
ONE_WAY_BY_DEFAULT = frozenset(ext for ext, nivel in DEFAULT_SUPPORT.items() if nivel < 2)


def ext_of(path: str) -> str:
    """Extension en minusculas, sin punto. `""` si el nombre no tiene."""
    return path.rsplit(".", 1)[-1].lower() if "." in path else ""


def direction_from_ext(path: str) -> str:
    """Determina 'BIN2PRG', 'PRG2BIN' o '' (desconocida) segun la extension."""
    ext = ext_of(path)
    if ext in BIN_TO_TEXT:
        return "BIN2PRG"
    if ext in TEXT_TO_BIN:
        return "PRG2BIN"
    return ""


def is_supported(path: str) -> bool:
    ext = ext_of(path)
    return ext in BIN_TO_TEXT or ext in TEXT_TO_BIN


def is_project(path: str) -> bool:
    """True si es un archivo de proyecto (.pjx binario o .pj2 texto)."""
    return ext_of(path) in (PROJECT_BIN, PROJECT_TEXT)


def project_ctype(*, include_project_file: bool) -> str:
    """cType del modo proyecto segun se quiera incluir o no el propio .pjx/.pj2."""
    return PROJECT_WITH_PJX if include_project_file else PROJECT_WITHOUT_PJX


def bin_ext_of(path: str) -> str:
    """Extension binaria equivalente, venga el archivo en binario o en texto.

    `login.scx` y `login.sc2` devuelven los dos `scx`. Sirve para consultar el
    soporte, que FoxBin2Prg indexa por el tipo de archivo, no por el formato.
    """
    ext = ext_of(path)
    if ext in BIN_TO_TEXT:
        return ext
    return TEXT_TO_BIN.get(ext, "")


def supports(path: str, direction: str) -> bool:
    """Si FoxBin2Prg convierte ese archivo en esa direccion, con la config por defecto.

    Replica `hasSupport_Bin2Prg()` / `hasSupport_Prg2Bin()` usando los valores
    de `DEFAULT_SUPPORT`. Un `foxbin2prg.cfg` en el arbol puede cambiarlo: esto
    es una prediccion, no la palabra final.
    """
    nivel = DEFAULT_SUPPORT.get(bin_ext_of(path), 0)
    if direction == "BIN2PRG":
        return nivel > 0
    if direction == "PRG2BIN":
        return nivel == 2
    return False

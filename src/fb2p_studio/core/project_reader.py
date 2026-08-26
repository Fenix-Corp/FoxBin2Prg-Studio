"""Lee el contenido de un proyecto VFP: que archivos lo componen.

Sirve para saber **antes** de ejecutar que va a procesar FoxBin2Prg. Sin esto,
un proyecto con archivos faltantes o no convertibles se procesa igual y esos
archivos se saltan en silencio (FoxBin2Prg los registra con `P0`/`S0` y sigue).

Se replica exactamente lo que hace FoxBin2Prg para armar su lista, para que lo
que muestra Studio sea lo que realmente va a pasar:

**`.pjx` (a texto)** — `evaluate_Full_PJX()` abre el propio `.pjx`, que es un
DBF, y recorre `For Not Deleted() And Type <> 'H'`. El nombre sale del campo
memo `NAME` (por eso hay que leer tambien el `.pjt`) y se resuelve contra la
carpeta del proyecto.

**`.pj2` (a binario)** — `evaluate_Full_PJ2()` toma el texto entre
`*<BuildProj>` y `*</BuildProj>`, se queda con las lineas que contienen
`.ADD(`, extrae la ruta entre `.ADD('` y `')`, y **le cambia la extension a la
de texto** (`Forceext(..., get_Ext2FromExt(...))`): el `.pj2` lista los
binarios, pero lo que se lee para convertir es el `.sc2`, el `.fr2`, etc.

En los dos casos FoxBin2Prg procesa el archivo sólo si `hasSupport_*()` acepta
la extension **y** el archivo existe. Esa doble condicion es la que aqui se
reporta (ver `core/validators.py`).
"""

from __future__ import annotations

import ntpath
import re
import struct
from dataclasses import dataclass
from pathlib import Path

from fb2p_studio.core.extensions import BIN_TO_TEXT, PROJECT_BIN, PROJECT_TEXT, ext_of

#: Delimitadores del bloque de archivos en el .pj2 (C_BUILDPROJ_I / _F).
_BUILDPROJ_INI = "*<BuildProj>"
_BUILDPROJ_FIN = "*</BuildProj>"

_RE_ADD = re.compile(r"\.ADD\(\s*['\"](?P<ruta>[^'\"]+)['\"]\s*\)", re.IGNORECASE)
_RE_TIPO = re.compile(r'FileMetadata:\s*Type="(?P<tipo>[^"]*)"')
_RE_EXCLUDE = re.compile(
    r"\.ITEM\(\s*['\"](?P<ruta>[^'\"]+)['\"]\s*\)\s*\.Exclude\s*=\s*\.T\.", re.IGNORECASE
)
_RE_SETMAIN = re.compile(r"\.SetMain\(\s*['\"](?P<ruta>[^'\"]+)['\"]\s*\)", re.IGNORECASE)

#: Tipos de archivo del proyecto (campo TYPE del .pjx / Type= del .pj2).
TIPOS = {
    "H": "cabecera",
    "P": "programa",
    "K": "formulario",
    "V": "class library",
    "R": "reporte",
    "B": "etiqueta",
    "M": "menu",
    "d": "base de datos",
    "D": "tabla libre",
    "Q": "consulta",
    "T": "texto",
    "x": "otro",
    "X": "otro",
    "Z": "app / exe",
}


class ProjectReadError(Exception):
    """El proyecto no se pudo leer (no existe, esta corrupto, o lo tiene tomado VFP)."""


@dataclass(frozen=True, slots=True)
class ProjectItem:
    """Un archivo miembro del proyecto."""

    listed: str
    """Ruta tal como figura en el proyecto (relativa, casi siempre)."""

    path: Path
    """Ruta absoluta del archivo tal como lo lista el proyecto (el binario)."""

    source: Path
    """Archivo que FoxBin2Prg va a **leer**.

    Para un `.pjx` es el mismo `path`; para un `.pj2`, el mismo nombre con la
    extension de texto (`.scx` -> `.sc2`), que es lo que existe en disco
    cuando se va de texto a binario.
    """

    type_code: str = ""
    excluded: bool = False
    """Marcado como "excluido" del build. No afecta a la conversion: se informa
    porque explica por que un archivo del proyecto no termina en el EXE."""

    main: bool = False

    @property
    def type_label(self) -> str:
        return TIPOS.get(self.type_code, self.type_code or "?")


@dataclass(frozen=True, slots=True)
class ProjectContents:
    project: Path
    direction: str
    """`BIN2PRG` para un `.pjx`, `PRG2BIN` para un `.pj2`."""

    items: tuple[ProjectItem, ...]
    warnings: tuple[str, ...] = ()

    def __len__(self) -> int:
        return len(self.items)


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------
def read_project(path: str | Path) -> ProjectContents:
    """Lee un `.pjx` o un `.pj2`. Lanza `ProjectReadError` si no se puede."""
    proyecto = Path(path)
    ext = ext_of(str(proyecto))
    if ext == PROJECT_BIN:
        return _read_pjx(proyecto)
    if ext == PROJECT_TEXT:
        return _read_pj2(proyecto)
    raise ProjectReadError(f"No es un proyecto (.pjx / .pj2): {proyecto.name}")


# ---------------------------------------------------------------------------
# .pjx — DBF + memo .pjt
# ---------------------------------------------------------------------------
def _read_pjx(proyecto: Path) -> ProjectContents:
    try:
        dbf = proyecto.read_bytes()
    except OSError as e:
        raise ProjectReadError(f"No se pudo leer {proyecto.name}: {e.strerror or e}") from e

    avisos: list[str] = []
    memo = _leer_memo_file(proyecto, avisos)

    try:
        campos, header_len, rec_len, n_rec = _dbf_layout(dbf)
    except (struct.error, IndexError, ValueError) as e:
        raise ProjectReadError(f"{proyecto.name} no parece un DBF valido: {e}") from e

    if "NAME" not in campos:
        raise ProjectReadError(f"{proyecto.name} no tiene el campo NAME: no es un proyecto VFP")

    base = proyecto.parent
    items: list[ProjectItem] = []
    for i in range(n_rec):
        ini = header_len + i * rec_len
        registro = dbf[ini : ini + rec_len]
        if len(registro) < rec_len:
            avisos.append(f"el DBF declara {n_rec} registros pero se corta en el {i}")
            break
        if registro[0:1] == b"*":  # borrado
            continue

        tipo = _campo(registro, campos, "TYPE").strip()
        if tipo == "H":  # cabecera: es el propio proyecto, no un miembro
            continue

        listado = _memo_valor(memo, registro, campos, "NAME")
        if not listado:
            continue

        absoluta = _absolutizar(listado, base)
        items.append(
            ProjectItem(
                listed=listado,
                path=absoluta,
                source=absoluta,  # a texto: se lee el binario tal cual
                type_code=tipo,
                excluded=_campo(registro, campos, "EXCLUDE").strip().upper() == "T",
                main=_campo(registro, campos, "MAINPROG").strip().upper() == "T",
            )
        )

    return ProjectContents(
        project=proyecto, direction="BIN2PRG", items=tuple(items), warnings=tuple(avisos)
    )


def _dbf_layout(dbf: bytes) -> tuple[dict[str, tuple[int, int, str]], int, int, int]:
    """Devuelve ({campo: (desplazamiento, largo, tipo)}, headerLen, recLen, nRec)."""
    n_rec, header_len, rec_len = struct.unpack("<IHH", dbf[4:12])
    campos: dict[str, tuple[int, int, str]] = {}
    off = 32
    desp = 1  # el byte 0 de cada registro es la marca de borrado
    while off < len(dbf) and dbf[off] != 0x0D:
        descriptor = dbf[off : off + 32]
        nombre = descriptor[:11].split(b"\x00")[0].decode("cp1252", "replace").upper()
        tipo = chr(descriptor[11])
        largo = descriptor[16]
        campos[nombre] = (desp, largo, tipo)
        desp += largo
        off += 32
    if not campos:
        raise ValueError("sin descriptores de campo")
    return campos, header_len, rec_len, n_rec


def _campo(registro: bytes, campos: dict[str, tuple[int, int, str]], nombre: str) -> str:
    if nombre not in campos:
        return ""
    desp, largo, _tipo = campos[nombre]
    return registro[desp : desp + largo].decode("cp1252", "replace")


def _leer_memo_file(proyecto: Path, avisos: list[str]) -> tuple[bytes, int] | None:
    """Carga el `.pjt` (memo del proyecto) y su tamano de bloque."""
    for sufijo in (".pjt", ".PJT"):
        memo_path = proyecto.with_suffix(sufijo)
        if memo_path.is_file():
            try:
                datos = memo_path.read_bytes()
            except OSError as e:
                avisos.append(f"no se pudo leer {memo_path.name}: {e.strerror or e}")
                return None
            if len(datos) < 8:
                avisos.append(f"{memo_path.name} esta truncado")
                return None
            (bloque,) = struct.unpack(">H", datos[6:8])
            if bloque <= 0:
                avisos.append(f"{memo_path.name} declara un tamano de bloque invalido")
                return None
            return datos, bloque
    avisos.append(f"falta {proyecto.stem}.pjt: no se pueden leer los nombres de archivo")
    return None


def _memo_valor(
    memo: tuple[bytes, int] | None,
    registro: bytes,
    campos: dict[str, tuple[int, int, str]],
    nombre: str,
) -> str:
    """Contenido del campo memo `nombre`, o `""` si no se puede resolver."""
    if memo is None or nombre not in campos:
        return ""
    datos, bloque = memo
    desp, largo, _tipo = campos[nombre]
    crudo = registro[desp : desp + largo]

    if largo == 4:
        (numero,) = struct.unpack("<I", crudo)
    else:  # dBASE clasico: el numero de bloque va en ASCII
        texto = crudo.decode("cp1252", "replace").strip()
        numero = int(texto) if texto.isdigit() else 0
    if numero <= 0:
        return ""

    ini = numero * bloque
    if ini + 8 > len(datos):
        return ""
    _tipo_memo, largo_memo = struct.unpack(">II", datos[ini : ini + 8])
    contenido = datos[ini + 8 : ini + 8 + largo_memo]
    # Los nombres del .pjt vienen terminados en NUL (de ahi el
    # Alltrim(Name, 0, ' ', Chr(0)) de FoxBin2Prg).
    return contenido.decode("cp1252", "replace").strip().strip("\x00").strip()


# ---------------------------------------------------------------------------
# .pj2 — texto
# ---------------------------------------------------------------------------
def _read_pj2(proyecto: Path) -> ProjectContents:
    try:
        texto = proyecto.read_text(encoding="cp1252", errors="replace")
    except OSError as e:
        raise ProjectReadError(f"No se pudo leer {proyecto.name}: {e.strerror or e}") from e

    avisos: list[str] = []
    bloque = _extraer(texto, _BUILDPROJ_INI, _BUILDPROJ_FIN)
    if bloque is None:
        raise ProjectReadError(
            f"{proyecto.name} no tiene el bloque {_BUILDPROJ_INI}: no parece un .pj2 de FoxBin2Prg"
        )

    excluidos = {_norm(m.group("ruta")) for m in _RE_EXCLUDE.finditer(texto)}
    principales = {_norm(m.group("ruta")) for m in _RE_SETMAIN.finditer(texto)}

    base = proyecto.parent
    items: list[ProjectItem] = []
    for linea in bloque.splitlines():
        m = _RE_ADD.search(linea)
        if m is None:
            continue
        listado = m.group("ruta")
        absoluta = _absolutizar(listado, base)
        tipo_m = _RE_TIPO.search(linea)
        items.append(
            ProjectItem(
                listed=listado,
                path=absoluta,
                source=_a_texto(absoluta),
                type_code=tipo_m.group("tipo") if tipo_m else "",
                excluded=_norm(listado) in excluidos,
                main=_norm(listado) in principales,
            )
        )

    if not items:
        avisos.append("el bloque BuildProj no lista ningun archivo")

    return ProjectContents(
        project=proyecto, direction="PRG2BIN", items=tuple(items), warnings=tuple(avisos)
    )


def _extraer(texto: str, inicio: str, fin: str) -> str | None:
    """Equivalente a `STREXTRACT(texto, inicio, fin)` de VFP."""
    i = texto.find(inicio)
    if i < 0:
        return None
    i += len(inicio)
    j = texto.find(fin, i)
    return texto[i:j] if j >= 0 else texto[i:]


def _a_texto(binario: Path) -> Path:
    """`forms\\artdetalle.scx` -> `forms\\artdetalle.sc2` (Forceext + get_Ext2FromExt)."""
    texto_ext = BIN_TO_TEXT.get(ext_of(binario.name))
    return binario.with_suffix("." + texto_ext) if texto_ext else binario


# ---------------------------------------------------------------------------
# Rutas
# ---------------------------------------------------------------------------
def _absolutizar(listado: str, base: Path) -> Path:
    """Resuelve la ruta del proyecto contra su carpeta (`get_AbsolutePath`).

    Se usa `ntpath` a proposito: los proyectos VFP guardan rutas con `\\` y hay
    que interpretarlas igual corriendo los tests en cualquier plataforma.
    """
    limpio = listado.strip().strip("\x00")
    if ntpath.isabs(limpio) or limpio.startswith("\\\\"):
        return Path(ntpath.normpath(limpio))
    return Path(ntpath.normpath(ntpath.join(str(base), limpio)))


def _norm(ruta: str) -> str:
    """Clave para comparar rutas del proyecto entre si (case/sep-insensitive)."""
    return ntpath.normcase(ntpath.normpath(ruta.strip().strip("\x00")))

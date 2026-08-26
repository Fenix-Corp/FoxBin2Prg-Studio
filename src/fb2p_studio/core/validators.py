"""Chequeos previos a ejecutar: que va a pasar realmente con cada archivo.

FoxBin2Prg procesa un archivo del proyecto sólo si se cumplen **las dos**
condiciones (`evaluate_Full_PJX` / `evaluate_Full_PJ2`):

    If .hasSupport_*( Justext(lcFile) ) And Adir( laDirInfo, lcFile ) > 0

Si alguna falla, lo registra como no procesado (`P0`/`S0`) y **sigue sin
avisar**. Eso es correcto para una herramienta de linea de comandos, pero en
una GUI deja a la persona creyendo que convirtio el proyecto entero. Este
modulo calcula por adelantado esas dos condiciones para poder mostrarlas.
"""

from __future__ import annotations

import ntpath
from dataclasses import dataclass
from pathlib import Path

from fb2p_studio.core.extensions import ONE_WAY_BY_DEFAULT, bin_ext_of, supports
from fb2p_studio.core.project_reader import ProjectContents, ProjectItem

#: Estados posibles de un archivo del proyecto.
CONVIERTE = "convierte"
FALTA = "falta"
NO_CONVERTIBLE = "no convertible"


@dataclass(frozen=True, slots=True)
class ItemCheck:
    item: ProjectItem
    exists: bool
    supported: bool
    other_drive: bool
    reason: str = ""
    """Por que no se convierte, cuando `supported` es False."""

    @property
    def will_convert(self) -> bool:
        return self.exists and self.supported

    @property
    def status(self) -> str:
        """Que va a hacer FoxBin2Prg con este archivo.

        El orden importa: un `.txt` que falta no es un problema (igual no se
        convertiria), asi que "no convertible" gana sobre "falta".
        """
        if not self.supported:
            return NO_CONVERTIBLE
        if not self.exists:
            return FALTA
        return CONVIERTE


@dataclass(frozen=True, slots=True)
class ProjectPreflight:
    contents: ProjectContents
    checks: tuple[ItemCheck, ...]
    include_project_file: bool

    @property
    def will_convert(self) -> tuple[ItemCheck, ...]:
        return tuple(c for c in self.checks if c.status == CONVIERTE)

    @property
    def missing(self) -> tuple[ItemCheck, ...]:
        return tuple(c for c in self.checks if c.status == FALTA)

    @property
    def unsupported(self) -> tuple[ItemCheck, ...]:
        return tuple(c for c in self.checks if c.status == NO_CONVERTIBLE)

    @property
    def other_drive(self) -> tuple[ItemCheck, ...]:
        return tuple(c for c in self.checks if c.other_drive)

    @property
    def total_to_convert(self) -> int:
        """Archivos que se van a convertir, contando el proyecto si corresponde."""
        return len(self.will_convert) + (1 if self.include_project_file else 0)

    @property
    def has_problems(self) -> bool:
        """Sólo los faltantes son un problema: lo no convertible es lo normal
        (un proyecto tiene `.prg`, `.txt`, iconos... que FoxBin2Prg no toca)."""
        return bool(self.missing)


def preflight(contents: ProjectContents, *, include_project_file: bool = True) -> ProjectPreflight:
    unidad_proyecto = _drive(contents.project)

    checks = tuple(
        _check(item, contents.direction, unidad_proyecto) for item in contents.items
    )
    return ProjectPreflight(
        contents=contents, checks=checks, include_project_file=include_project_file
    )


def _check(item: ProjectItem, direction: str, unidad_proyecto: str) -> ItemCheck:
    soportado = supports(item.source.name, direction)
    return ItemCheck(
        item=item,
        exists=_exists(item.source),
        supported=soportado,
        other_drive=bool(unidad_proyecto) and _drive(item.path) != unidad_proyecto,
        reason="" if soportado else _reason(item, direction),
    )


def _reason(item: ProjectItem, direction: str) -> str:
    """Por que FoxBin2Prg no va a tocar este archivo.

    Distingue los dos casos, que se arreglan de forma muy distinta: un `.txt`
    simplemente no es un binario VFP, mientras que un `.dbf` si lo es y sólo
    esta desactivado por defecto en esa direccion.
    """
    binaria = bin_ext_of(item.source.name)
    if not binaria:
        propia = item.source.suffix.lstrip(".").lower()
        return f"FoxBin2Prg no maneja archivos .{propia}"
    if direction == "PRG2BIN" and binaria in ONE_WAY_BY_DEFAULT:
        return (
            f"por defecto los .{binaria} se vuelcan a texto pero no se reconstruyen desde "
            f"el, para no pisar los datos; se habilita con "
            f"n_{binaria.upper()}_Conversion_Support=2 (o 8, import de datos) en el "
            f"foxbin2prg.cfg"
        )
    return "la configuracion no habilita esta conversion"


def _exists(path: Path) -> bool:
    """`Adir() > 0` de FoxBin2Prg. Una ruta inaccesible cuenta como ausente."""
    try:
        return path.is_file()
    except OSError:
        return False


def _drive(path: Path) -> str:
    """Unidad o recurso UNC, normalizado. `""` si la ruta no la trae."""
    return ntpath.normcase(ntpath.splitdrive(str(path))[0])

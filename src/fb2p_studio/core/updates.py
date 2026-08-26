"""Chequeo de version nueva contra un manifiesto en el NAS.

No hay auto-update: Studio sólo avisa. Bajar e instalar lo hace la persona,
copiando el .exe nuevo — coherente con que la app no tiene instalador.

**El manifiesto** es un JSON en una carpeta de red (por defecto, la misma del
NAS donde vive el resto del compilado). No hace falta servidor: leer un archivo
por SMB alcanza, y la carpeta ya existe.

    {
      "version": "0.2.0",
      "paquete": "\\\\192.168.0.16\\Compilado_16\\FoxBin2Prg-Studio\\FoxBin2Prg-Studio-0.2.0.zip",
      "notas": "Tab Proyecto + arbol de resultados."
    }

Sólo `version` es obligatorio.

Leer de un share de red puede colgarse varios segundos si el NAS no responde,
asi que el chequeo NUNCA corre en el hilo de la UI: ver `UpdateChecker`.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal

#: Ubicacion por defecto del manifiesto. Se puede cambiar en Preferencias.
DEFAULT_MANIFEST = r"\\192.168.0.16\Compilado_16\FoxBin2Prg-Studio\latest.json"


@dataclass(slots=True, frozen=True)
class UpdateInfo:
    """Lo que dice el manifiesto sobre la ultima version publicada."""

    version: str
    package: str = ""
    notes: str = ""


def parse_version(raw: str) -> tuple[int, ...]:
    """`"0.2.10-beta"` -> `(0, 2, 10)`. Corta en el primer tramo no numerico."""
    numeros: list[int] = []
    for parte in re.split(r"[.\-+_]", raw.strip()):
        if not parte.isdigit():
            break
        numeros.append(int(parte))
    return tuple(numeros)


def is_newer(remote: str, local: str) -> bool:
    """True si `remote` es posterior a `local`.

    Compara de a numeros, rellenando con ceros para que `0.2` y `0.2.0` sean
    la misma version. Una version ilegible nunca se considera mas nueva: mejor
    no avisar que avisar de mas.
    """
    r, ln = parse_version(remote), parse_version(local)
    if not r:
        return False
    largo = max(len(r), len(ln))
    return r + (0,) * (largo - len(r)) > ln + (0,) * (largo - len(ln))


def parse_manifest(raw: str) -> UpdateInfo:
    """Lee el JSON del manifiesto. Lanza `ValueError` si no sirve."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"el manifiesto no es JSON valido: {e}") from e

    if not isinstance(data, dict):
        raise ValueError("el manifiesto tiene que ser un objeto JSON")

    version = str(data.get("version", "")).strip()
    if not version:
        raise ValueError("el manifiesto no trae 'version'")

    return UpdateInfo(
        version=version,
        package=str(data.get("paquete", data.get("package", ""))).strip(),
        notes=str(data.get("notas", data.get("notes", ""))).strip(),
    )


def read_manifest(manifest_path: str | Path) -> UpdateInfo:
    """Lee y parsea el manifiesto. Lanza `OSError` o `ValueError`.

    Bloqueante: no llamarla desde el hilo de la UI (usar `UpdateChecker`).
    """
    return parse_manifest(Path(manifest_path).read_text(encoding="utf-8"))


class UpdateChecker(QObject):
    """Corre `read_manifest()` en el thread pool y avisa por signal.

    `found` se emite sólo si hay una version mas nueva que `current_version`;
    `up_to_date` si no la hay; `failed` si el manifiesto no se pudo leer (NAS
    caido, ruta mal escrita, JSON roto). Los tres son excluyentes.
    """

    found = Signal(UpdateInfo)
    up_to_date = Signal(str)  # la version que corre ahora
    failed = Signal(str)  # motivo, para el log

    def __init__(self, manifest_path: str, current_version: str, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._manifest_path = manifest_path
        self._current = current_version

    def start(self) -> None:
        QThreadPool.globalInstance().start(_CheckTask(self))

    # Lo llama la tarea desde otro hilo: emitir signals es thread-safe, Qt las
    # encola hacia el hilo del receptor.
    def _run(self) -> None:
        if not self._manifest_path.strip():
            self.failed.emit("no hay manifiesto configurado")
            return
        try:
            info = read_manifest(self._manifest_path)
        except OSError as e:
            self.failed.emit(f"no se pudo leer {self._manifest_path}: {e.strerror or e}")
            return
        except ValueError as e:
            self.failed.emit(str(e))
            return

        if is_newer(info.version, self._current):
            self.found.emit(info)
        else:
            self.up_to_date.emit(self._current)


class _CheckTask(QRunnable):
    def __init__(self, checker: UpdateChecker) -> None:
        super().__init__()
        self._checker = checker

    def run(self) -> None:
        self._checker._run()  # noqa: SLF001 — mismo modulo, es la mitad "worker"

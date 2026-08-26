"""Chequeo de version nueva contra un manifiesto en el NAS.

No hay auto-update: Studio sólo avisa. Bajar e instalar lo hace la persona,
copiando el .exe nuevo — coherente con que la app no tiene instalador.

**El manifiesto** es un JSON. Por defecto vive en la misma carpeta del NAS que
el resto del compilado: no hace falta servidor, leer un archivo por SMB alcanza
y la carpeta ya existe.

Tambien acepta una **URL https**, para las maquinas que no ven el NAS (una
laptop en un cliente). Los links de compartir de Google Drive y SharePoint se
convierten solos a su forma de descarga directa (`normalize_source`), porque el
link que se copia del navegador devuelve una pagina HTML y no el JSON.

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
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal

#: Ubicacion por defecto del manifiesto. Se puede cambiar en Preferencias, y
#: admite tanto una carpeta de red como una URL https.
DEFAULT_MANIFEST = r"\\192.168.0.16\Compilado_16\FoxBin2Prg-Studio\latest.json"

#: `https://drive.google.com/file/d/<ID>/view?usp=sharing` es lo que se copia
#: del navegador; el ID es lo unico que sirve para armar la descarga directa.
_RE_DRIVE = re.compile(
    r"drive\.google\.com/(?:file/d/|open\?id=|uc\?[^\s]*id=)(?P<id>[\w-]{10,})"
)

#: Techo de espera de la red. Corto a proposito: esto corre al arrancar y no
#: tiene que hacerse notar aunque el servidor no conteste.
TIMEOUT_HTTP = 12.0

#: Un manifiesto son unos cientos de bytes. Pasado esto, lo que llego no es un
#: manifiesto (tipicamente, la pagina del visor de Drive o un login).
_MAX_BYTES = 64 * 1024


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


def is_url(origen: str) -> bool:
    """Si el manifiesto esta en la web en vez de en una carpeta."""
    return origen.strip().lower().startswith(("http://", "https://"))


def normalize_source(origen: str) -> str:
    """Adapta links de compartir conocidos a su forma de descarga directa.

    Un link de Google Drive copiado del navegador (`.../file/d/<ID>/view`)
    devuelve una pagina HTML, no el JSON. El de descarga directa es
    `uc?export=download&id=<ID>`. Se convierte aca para que nadie tenga que
    acordarse del formato al configurarlo.
    """
    origen = origen.strip()
    m = _RE_DRIVE.search(origen)
    if m:
        return f"https://drive.google.com/uc?export=download&id={m.group('id')}"
    if "sharepoint.com" in origen.lower() and "download=1" not in origen.lower():
        # SharePoint sirve el archivo con ?download=1; sin eso devuelve el visor.
        separador = "&" if "?" in origen else "?"
        return f"{origen}{separador}download=1"
    return origen


def read_manifest(manifest_path: str | Path) -> UpdateInfo:
    """Lee y parsea el manifiesto, este en una carpeta o en la web.

    Lanza `OSError` si no se pudo traer (NAS caido, sin red, 404) y
    `ValueError` si lo que llego no es un manifiesto valido.

    Bloqueante: no llamarla desde el hilo de la UI (usar `UpdateChecker`).
    """
    origen = str(manifest_path)
    crudo = _fetch_url(origen) if is_url(origen) else Path(origen).read_text(encoding="utf-8")
    return parse_manifest(crudo)


def _fetch_url(url: str) -> str:
    """Trae el manifiesto por HTTP. Los errores salen como `OSError`.

    `urllib` ya levanta `URLError`/`HTTPError`, que son `OSError`, asi que el
    llamador no distingue entre "el NAS no responde" y "el servidor devolvio
    404": las dos cosas se reportan igual.
    """
    peticion = urllib.request.Request(  # noqa: S310 — el esquema se valido en is_url()
        normalize_source(url),
        headers={"User-Agent": "FoxBin2Prg-Studio"},
    )
    try:
        with urllib.request.urlopen(peticion, timeout=TIMEOUT_HTTP) as respuesta:  # noqa: S310
            datos = respuesta.read(_MAX_BYTES + 1)
    except urllib.error.HTTPError as e:
        raise OSError(f"el servidor respondio {e.code} {e.reason}") from e
    except urllib.error.URLError as e:
        raise OSError(f"no se pudo conectar: {e.reason}") from e

    if len(datos) > _MAX_BYTES:
        # Casi siempre significa que la URL devolvio una pagina HTML (un visor,
        # un login) en vez del JSON. Decirlo asi ahorra media hora de confusion.
        raise ValueError(
            "lo que devolvio la URL no parece un manifiesto: es demasiado grande. "
            "¿Es un link de descarga directa?"
        )
    return datos.decode("utf-8", errors="replace")


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

"""Chequeo de version nueva contra el canal de distribucion en GitHub.

No hay auto-update: Studio sólo avisa. Bajar e instalar lo hace la persona,
reemplazando el .exe — coherente con que la app no tiene instalador.

**El canal** es el repo publico `Fenix-Corp/Utilities-Dist`, el mismo donde
publican las Utilidades de Desarrollo. Cada version de Studio es un Release con
la etiqueta `foxbin2prg-studio-vX.Y.Z` y el `FoxBin2Prg-Studio.exe` adjunto: lo
sube `build_exe.bat` (ver `build\\publish.bat`). Como es publico, consultarlo no
necesita token: se lee la API de GitHub sin autenticar. El prefijo propio evita
confundirse con las etiquetas `fnxUtilidades-v*` del cajon, que viven en el
mismo repo.

El origen se puede cambiar en Preferencias por cualquier otro repo de GitHub, o
por un **manifiesto JSON** (carpeta de red o URL https), para las maquinas que no
ven GitHub:

    {
      "version": "0.2.0",
      "paquete": "\\\\192.168.0.16\\Compilado_16\\FoxBin2Prg-Studio\\FoxBin2Prg-Studio-0.2.0.zip",
      "notas": "Tab Proyecto + arbol de resultados."
    }

Sólo `version` es obligatorio. Los links de compartir de Google Drive y
SharePoint se convierten solos a su forma de descarga directa
(`normalize_source`), porque el link que se copia del navegador devuelve una
pagina HTML y no el JSON.

Consultar la red puede colgarse varios segundos, asi que el chequeo NUNCA corre
en el hilo de la UI: ver `UpdateChecker`.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal

#: Origen por defecto de las actualizaciones: el repo de distribucion. Se puede
#: cambiar en Preferencias; admite otro repo de GitHub, un manifiesto JSON en una
#: carpeta de red o una URL https.
DEFAULT_SOURCE = "https://github.com/Fenix-Corp/Utilities-Dist.git"

#: Lo que identifica a Studio entre los Releases del canal (que comparte con
#: otras utilidades): la etiqueta es `<prefijo><version>` y el asset, este nombre.
#: `build\publish.bat` publica con los mismos valores: si cambian, cambian los dos.
TAG_PREFIX = "foxbin2prg-studio-v"
ASSET_NAME = "FoxBin2Prg-Studio.exe"

#: `https://github.com/<dueno>/<repo>` con o sin `.git` (la forma de `git clone`).
_RE_GITHUB = re.compile(
    r"^https?://(?:www\.)?github\.com/(?P<owner>[\w.-]+)/(?P<repo>[\w.-]+?)(?:\.git)?/?$",
    re.IGNORECASE,
)

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

#: La lista de Releases trae los assets de cada uno (el repo comparte canal con
#: otras utilidades, ~9 binarios por Release): pesa cientos de KB, no unos bytes.
_MAX_BYTES_RELEASES = 4 * 1024 * 1024


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


def parse_releases(raw: str) -> UpdateInfo:
    """La version mas nueva de Studio entre los Releases que devuelve GitHub.

    Ignora borradores, pre-releases y toda etiqueta que no empiece por
    `TAG_PREFIX` (el canal es compartido). El paquete es la URL de descarga del
    `.exe` adjunto; si el Release no lo trae, la pagina del Release. Lanza
    `ValueError` si no hay ninguna version de Studio publicada.
    """
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"GitHub no devolvio JSON valido: {e}") from e

    if not isinstance(data, list):
        raise ValueError("GitHub no devolvio una lista de releases")

    mejor: tuple[str, dict] | None = None
    for release in data:
        if not isinstance(release, dict) or release.get("draft") or release.get("prerelease"):
            continue
        tag = str(release.get("tag_name", "")).strip()
        if not tag.lower().startswith(TAG_PREFIX):
            continue
        version = tag[len(TAG_PREFIX) :]
        if not parse_version(version):
            continue
        if mejor is None or is_newer(version, mejor[0]):
            mejor = (version, release)

    if mejor is None:
        raise ValueError("el canal no tiene ninguna version publicada de FoxBin2Prg-Studio")

    version, release = mejor
    return UpdateInfo(
        version=version,
        package=_asset_url(release),
        notes=str(release.get("body") or "").strip(),
    )


def _asset_url(release: dict) -> str:
    """URL de descarga del `.exe` del Release; la del Release si no lo trae."""
    for asset in release.get("assets") or []:
        if isinstance(asset, dict) and str(asset.get("name", "")).lower() == ASSET_NAME.lower():
            return str(asset.get("browser_download_url", "")).strip()
    return str(release.get("html_url", "")).strip()


def parse_github_repo(origen: str) -> tuple[str, str] | None:
    """`(dueno, repo)` si el origen es un repo de GitHub, o None.

    Acepta la URL de la pagina (`https://github.com/Fenix-Corp/Utilities-Dist`) y
    la de `git clone` (con `.git`).
    """
    m = _RE_GITHUB.match(origen.strip())
    return (m.group("owner"), m.group("repo")) if m else None


def is_url(origen: str) -> bool:
    """Si el origen esta en la web en vez de en una carpeta."""
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


def read_manifest(origen: str | Path) -> UpdateInfo:
    """Lee la ultima version publicada, venga de GitHub, de la web o de una carpeta.

    Un repo de GitHub se consulta por su API de Releases; cualquier otra URL o
    ruta se lee como manifiesto JSON.

    Lanza `OSError` si no se pudo traer (sin red, 404, NAS caido) y `ValueError`
    si lo que llego no sirve (JSON roto, sin version publicada).

    Bloqueante: no llamarla desde el hilo de la UI (usar `UpdateChecker`).
    """
    origen = str(origen)
    repo = parse_github_repo(origen)
    if repo is not None:
        url = f"https://api.github.com/repos/{repo[0]}/{repo[1]}/releases?per_page=100"
        return parse_releases(_fetch_url(url, max_bytes=_MAX_BYTES_RELEASES, api=True))
    crudo = _fetch_url(origen) if is_url(origen) else Path(origen).read_text(encoding="utf-8")
    return parse_manifest(crudo)


def _fetch_url(url: str, *, max_bytes: int = _MAX_BYTES, api: bool = False) -> str:
    """Trae el contenido por HTTP. Los errores salen como `OSError`.

    `urllib` ya levanta `URLError`/`HTTPError`, que son `OSError`, asi que el
    llamador no distingue entre "el NAS no responde" y "el servidor devolvio
    404": las dos cosas se reportan igual.
    """
    cabeceras = {"User-Agent": "FoxBin2Prg-Studio"}
    if api:
        cabeceras["Accept"] = "application/vnd.github+json"
        cabeceras["X-GitHub-Api-Version"] = "2022-11-28"
    peticion = urllib.request.Request(  # noqa: S310 — el esquema se valido en is_url()
        normalize_source(url),
        headers=cabeceras,
    )
    try:
        with urllib.request.urlopen(peticion, timeout=TIMEOUT_HTTP) as respuesta:  # noqa: S310
            datos = respuesta.read(max_bytes + 1)
    except urllib.error.HTTPError as e:
        if api and e.code in (403, 429):
            # Sin token GitHub deja 60 consultas por hora y por IP: en una red
            # compartida (la oficina entera sale por una IP) se agota.
            raise OSError("GitHub limito las consultas desde esta red; reintenta mas tarde") from e
        raise OSError(f"el servidor respondio {e.code} {e.reason}") from e
    except urllib.error.URLError as e:
        raise OSError(f"no se pudo conectar: {e.reason}") from e

    if len(datos) > max_bytes:
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

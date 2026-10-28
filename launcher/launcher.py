"""
Lanzador de FoxBin2Prg-Studio: baja la ultima version si hace falta y la ejecuta.

Autor: AJACH
Fecha: 2026-10-28 16:40:37

Mismo esquema que `fnxLauncher` de UtilitiesDevelopment. El equipo NO abre
FoxBin2Prg-Studio.exe directo: abre FoxBin2Prg-Studio-Launcher.exe (un acceso
directo). El lanzador consulta el ultimo Release de Studio en el canal de
distribucion y, si hay una version mas nueva que la que esta maquina ya tiene, la
baja a una carpeta UNICA por maquina (no una por usuario) y la ejecuta. Asi, en
un servidor RDP con muchos usuarios, el .exe (~45 MB) no se duplica: se mantiene
y actualiza en una sola ruta.

El canal es el repo PUBLICO `Fenix-Corp/Utilities-Dist` (el mismo de las
Utilidades de Desarrollo; solo binarios). Como es publico, bajar NO requiere
ningun secreto: se usa la API publica de GitHub sin autenticarse y se descarga el
asset por su `browser_download_url`. Por eso es seguro ponerlo en cualquier
maquina. Si existe la variable de entorno FNX_GH_TOKEN se usa SOLO para subir el
limite de peticiones de la API; nunca es obligatoria.

Los Releases de Studio se distinguen de los de las utilidades (que comparten el
canal) por su etiqueta: `foxbin2prg-studio-vX.Y.Z`. Lo publica `build_exe.bat`
(ver build\\publish.bat); estas constantes deben coincidir con las de
`fb2p_studio/core/updates.py` y `build/publish.bat` (tests/test_launcher.py lo
verifica).

La logica pura (elegir la etiqueta mas nueva, comparar versiones, decidir) vive
separada de la entrada/salida (red, disco) para poder probarse sin red.

Este archivo se mantiene en ASCII a proposito: sus mensajes salen por la consola
de Windows, donde los acentos se corrompen segun la pagina de codigos activa. Y
solo usa la biblioteca estandar, para que el .exe sea diminuto y no lleve Qt.
"""

from __future__ import annotations

import contextlib
import datetime as _dt
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path

#: Canal de distribucion PUBLICO (solo binarios).
REPO = "Fenix-Corp/Utilities-Dist"

#: Raiz de la API de GitHub para ese repositorio.
API_ROOT = "https://api.github.com/repos/" + REPO

#: Los Releases de Studio se etiquetan con este prefijo; deja fuera los de las
#: utilidades (`fnxUtilidades-v...`) que viven en el mismo canal.
TAG_PREFIX = "foxbin2prg-studio-v"

#: Nombre del asset (el .exe de la aplicacion) dentro del Release.
ASSET_NAME = "FoxBin2Prg-Studio.exe"

#: Marca local con la etiqueta que esta maquina ya bajo, junto al .exe cacheado.
MARKER_NAME = "installed.txt"

#: Bitacora del lanzador, junto a la copia cacheada. El lanzador es de consola y su
#: ventana se cierra sola: sin esto no habria forma de saber que paso.
LOG_NAME = "launcher.log"

#: Si el log pasa de este tamano, se reinicia (no crece sin fin con los anios).
LOG_MAX_BYTES = 512 * 1024

#: Techo de espera de la red. Corto: no hace falta mas para leer una lista.
NET_TIMEOUT = 30

#: Carpeta UNICA (por maquina) donde vive la copia ejecutable, el log y la marca.
#: En servidores RDP con muchos usuarios NO se usa %LOCALAPPDATA%: duplicaria el
#: .exe por usuario. Se puede redefinir con la variable de entorno FNX_STUDIO_DIR.
DEFAULT_INSTALL_DIR = r"C:\Fnx_Backup\exes\foxbin2prg_studio"
ENV_INSTALL_DIR = "FNX_STUDIO_DIR"


# --------------------------------------------------------------- logica pura


def parse_version(tag: str) -> tuple[int, ...]:
    """`"foxbin2prg-studio-v1.2.10"` -> `(1, 2, 10)`. Corta en el primer no numerico."""
    crudo = tag[len(TAG_PREFIX) :] if tag.startswith(TAG_PREFIX) else tag
    crudo = crudo.lstrip("vV").strip()
    numeros: list[int] = []
    for parte in re.split(r"[.\-+_]", crudo):
        if not parte.isdigit():
            break
        numeros.append(int(parte))
    return tuple(numeros)


def is_newer(remote: str, local: str) -> bool:
    """True si la etiqueta `remote` es posterior a `local`.

    Rellena con ceros para que 1.2 y 1.2.0 sean lo mismo. Una etiqueta ilegible
    nunca se considera mas nueva: mejor no bajar de mas.
    """
    r, ln = parse_version(remote), parse_version(local)
    if not r:
        return False
    largo = max(len(r), len(ln))
    return r + (0,) * (largo - len(r)) > ln + (0,) * (largo - len(ln))


def pick_latest_tag(tags: list[str]) -> str | None:
    """La etiqueta mas nueva de las que son de Studio, o None si no hay ninguna."""
    candidatas = [t for t in tags if t.startswith(TAG_PREFIX) and parse_version(t)]
    return max(candidatas, key=parse_version) if candidatas else None


def tags_from_releases_json(raw: str) -> list[str]:
    """Las etiquetas de una lista de Releases (borradores y pre-releases fuera). [] si no sirve."""
    try:
        filas = json.loads(raw or "[]")
    except json.JSONDecodeError:
        return []
    if not isinstance(filas, list):
        return []
    return [
        str(f.get("tag_name") or "")
        for f in filas
        if isinstance(f, dict) and not f.get("draft") and not f.get("prerelease")
    ]


def asset_url_from_release_json(raw: str, asset_name: str = ASSET_NAME) -> str | None:
    """La URL publica de descarga (`browser_download_url`) del asset, o None."""
    try:
        rel = json.loads(raw)
    except json.JSONDecodeError:
        return None
    for a in (rel.get("assets") or []) if isinstance(rel, dict) else []:
        if isinstance(a, dict) and a.get("name") == asset_name:
            url = a.get("browser_download_url")
            if isinstance(url, str) and url:
                return url
    return None


def needs_download(latest_tag: str, installed_tag: str | None, exe_exists: bool) -> bool:
    """Si hay que bajar el .exe: no esta, no hay marca, o el Release es mas nuevo."""
    if not exe_exists or not installed_tag:
        return True
    return is_newer(latest_tag, installed_tag)


# --------------------------------------------------------------- disco local


def cache_dir() -> Path:
    """La carpeta UNICA donde vive la copia ejecutable, la marca y el log.

    En un servidor RDP, quien ACTUALIZA (tecnico/admin) necesita permiso de
    escritura aqui; los usuarios normales, con solo lectura/ejecucion, corren la
    copia que ya este (ver `ensure_current`: una descarga que no se puede escribir
    no borra la copia buena). Asi no se duplica el .exe por usuario.
    """
    carpeta = Path(os.environ.get(ENV_INSTALL_DIR) or DEFAULT_INSTALL_DIR)
    # Puede existir sin permiso de creacion para este usuario; se usa igual.
    with contextlib.suppress(OSError):
        carpeta.mkdir(parents=True, exist_ok=True)
    return carpeta


def read_marker(carpeta: Path) -> str | None:
    try:
        return (carpeta / MARKER_NAME).read_text(encoding="utf-8").strip() or None
    except OSError:
        return None


def write_marker(carpeta: Path, tag: str) -> None:
    (carpeta / MARKER_NAME).write_text(tag, encoding="utf-8")


def make_say(carpeta: Path) -> Callable[[str], None]:
    """Un `say` que imprime en consola Y agrega al log, con marca de tiempo.

    Si el log no se puede escribir (permiso, disco), no estorba: solo imprime. Se
    reinicia solo cuando pasa de `LOG_MAX_BYTES`.
    """
    ruta = carpeta / LOG_NAME
    try:
        if ruta.exists() and ruta.stat().st_size > LOG_MAX_BYTES:
            ruta.unlink()
    except OSError:
        pass

    def say(mensaje: str) -> None:
        try:
            print(mensaje)
        except UnicodeEncodeError:
            # El texto de un error de Windows trae acentos; una consola con otra
            # pagina de codigos no los puede mostrar y NO debe tumbar al lanzador
            # justo cuando intenta informar un fallo. El log (UTF-8) lo conserva.
            print(mensaje.encode("ascii", "replace").decode("ascii"))
        try:
            with open(ruta, "a", encoding="utf-8") as f:
                f.write(f"{_dt.datetime.now():%Y-%m-%d %H:%M:%S}  {mensaje}\n")
        except OSError:
            pass

    return say


# ----------------------------------------------------- GitHub API (publica)


def _api_request(path: str, token: str | None = None) -> urllib.request.Request:
    peticion = urllib.request.Request(API_ROOT + path)
    peticion.add_header("Accept", "application/vnd.github+json")
    peticion.add_header("User-Agent", "FoxBin2Prg-Studio-Launcher")
    peticion.add_header("X-GitHub-Api-Version", "2022-11-28")
    # El token es opcional (sube el limite de rate). Como no-redirigible: al bajar
    # un asset GitHub redirige a una URL firmada que RECHAZA Authorization.
    if token:
        peticion.add_unredirected_header("Authorization", "Bearer " + token)
    return peticion


def _download_request(url: str) -> urllib.request.Request:
    """Peticion simple para bajar el asset publico (sin Authorization)."""
    peticion = urllib.request.Request(url)
    peticion.add_header("User-Agent", "FoxBin2Prg-Studio-Launcher")
    return peticion


def latest_tag_api(token: str | None = None, say: Callable[[str], None] = print) -> str | None:
    """La etiqueta del ultimo Release de Studio segun la API publica, o None."""
    try:
        # 100 (el maximo): el canal es compartido y Studio podria quedar lejos en la lista.
        with urllib.request.urlopen(_api_request("/releases?per_page=100", token), timeout=NET_TIMEOUT) as r:  # noqa: S310
            crudo = r.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as err:
        say(f"La API de GitHub respondio {err.code} al listar Releases.")
        return None
    except OSError as err:
        say(f"No se pudo consultar la API de GitHub: {err}")
        return None
    return pick_latest_tag(tags_from_releases_json(crudo))


def download_api(
    tag: str, carpeta: Path, token: str | None = None, say: Callable[[str], None] = print
) -> bool:
    """Baja el asset del Release `tag` a `carpeta` desde el canal publico.

    Se baja a un archivo temporal y se renombra al final: si la descarga se corta
    a la mitad, o el .exe esta en uso por otro usuario, la copia buena anterior no
    se toca.
    """
    try:
        with urllib.request.urlopen(_api_request("/releases/tags/" + tag, token), timeout=NET_TIMEOUT) as r:  # noqa: S310
            rel = r.read().decode("utf-8", errors="replace")
        url = asset_url_from_release_json(rel)
        if not url:
            say(f"El Release {tag} no trae {ASSET_NAME}.")
            return False

        destino = carpeta / ASSET_NAME
        temporal = carpeta / (ASSET_NAME + ".part")
        with urllib.request.urlopen(_download_request(url), timeout=NET_TIMEOUT) as r:  # noqa: S310
            total = int(r.headers.get("Content-Length") or 0)
            _stream_to_file(r, temporal, total, say)
        temporal.replace(destino)
        return True
    except urllib.error.HTTPError as err:
        say(f"No se pudo bajar {tag}: HTTP {err.code}")
        return False
    except OSError as err:
        say(f"No se pudo bajar {tag}: {err}")
        return False


def _stream_to_file(respuesta, destino: Path, total: int, say: Callable[[str], None]) -> None:  # noqa: ANN001
    """Escribe la respuesta al archivo, avisando el avance cada tanto."""
    mb = 1024 * 1024
    leido = 0
    hito = 0
    with open(destino, "wb") as f:
        while True:
            trozo = respuesta.read(256 * 1024)
            if not trozo:
                break
            f.write(trozo)
            leido += len(trozo)
            if total and leido - hito >= 8 * mb:  # cada ~8 MB
                hito = leido
                say(f"  {leido // mb} / {total // mb} MB")
    if total:
        say(f"  {total // mb} / {total // mb} MB")


# --------------------------------------------------------------- orquestacion


def ensure_current(
    carpeta: Path,
    latest: Callable[[], str | None],
    download: Callable[[str, Path], bool],
    say: Callable[[str], None] = print,
) -> Path | None:
    """Deja en `carpeta` la ultima version y devuelve la ruta del .exe.

    Sin red (latest devuelve None), se corre la copia local que haya; si no hay
    ninguna, se devuelve None y el llamador avisa. Una descarga que falla no borra
    la copia anterior: mejor correr algo viejo que nada.
    """
    exe = carpeta / ASSET_NAME
    instalada = read_marker(carpeta)
    etiqueta = latest()
    say(f"version local (marca): {instalada or 'ninguna'}")
    say(f"ultima version remota: {etiqueta or 'desconocida'}")

    if etiqueta is None:
        if exe.exists():
            say("No se pudo comprobar la ultima version; se abre la copia local.")
            return exe
        return None

    if needs_download(etiqueta, instalada, exe.exists()):
        say(f"Descargando {etiqueta}...")
        if download(etiqueta, carpeta) and exe.exists():
            write_marker(carpeta, etiqueta)
            say(f"Listo: {etiqueta}.")
        elif exe.exists():
            say(f"No se pudo bajar {etiqueta}; se abre la copia local.")
        else:
            return None
    else:
        say(f"Ya tienes la ultima version ({etiqueta}).")
    return exe


def launch(exe: Path) -> None:
    """Ejecuta el .exe y no espera: el lanzador ya cumplio su parte."""
    subprocess.Popen([str(exe)], cwd=str(exe.parent))  # noqa: S603


def _pause() -> None:
    """Deja la ventana abierta tras un fallo, para poder leer el motivo.

    Solo en una consola real: sin ella (un acceso directo que oculta la ventana,
    una prueba) `input` no tiene a quien esperar. Cuando todo sale bien no se
    pausa: la ventana se cierra sola y la app ya esta abierta.
    """
    try:
        if sys.stdin is not None and sys.stdin.isatty():
            input("Pulsa Enter para cerrar...")
    except (EOFError, OSError):
        pass


def main(argv: list[str] | None = None) -> int:
    carpeta = cache_dir()
    say = make_say(carpeta)
    say("---- FoxBin2Prg-Studio-Launcher: inicio ----")
    say(f"cache: {carpeta}")
    say(f"fuente: {REPO} (publico)")

    # Token OPCIONAL: solo sube el limite de rate. El canal es publico.
    token = (os.environ.get("FNX_GH_TOKEN") or "").strip() or None
    if token:
        say("token presente: se usara solo para subir el limite de la API.")

    try:
        exe = ensure_current(
            carpeta,
            latest=lambda: latest_tag_api(token, say),
            download=lambda tag, d: download_api(tag, d, token, say),
            say=say,
        )
        if exe is None:
            say("")
            say("No hay una copia de FoxBin2Prg-Studio y no se pudo bajar.")
            say("Comprueba tu conexion a Internet. Detalle en el log:")
            say(f"  {carpeta / LOG_NAME}")
            _pause()
            return 1
        say(f"Ejecutando: {exe}")
        launch(exe)
        say("---- FoxBin2Prg-Studio-Launcher: ok ----")
        return 0
    except Exception as err:  # noqa: BLE001 - cualquier fallo queda en el log
        import traceback

        say(f"ERROR inesperado: {err}")
        say(traceback.format_exc())
        _pause()
        return 1


if __name__ == "__main__":
    sys.exit(main())

"""Localiza vfp9.exe, FoxBin2Prg y el driver VFP en disco.

Orden de resolucion:
1. Ruta explicita pasada por el llamador (Preferencias), si existe.
2. Variables de entorno (`VFP_EXE`, `FB2P_HOME`).
3. FoxBin2Prg: la copia embebida en el propio Studio.
4. Ubicaciones tipicas conocidas.

Ningun paso es obligatorio: si el de arriba no da, se sigue con el
siguiente. Un override viejo o roto no deja a la app sin herramienta.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

_VFP_TYPICAL = [
    r"C:\Fenix\AdsFenix\Librerias\vfp9.exe",
    r"C:\Program Files (x86)\Microsoft Visual FoxPro 9\vfp9.exe",
    r"C:\Program Files\Microsoft Visual FoxPro 9\vfp9.exe",
]

_FB2P_TYPICAL = [
    r"D:\FenixPro\Proyectos\foxbin2prg",
    r"C:\FoxBin2Prg",
]


def _frozen_base() -> Path | None:
    """Raiz donde PyInstaller (onefile) extrae los datos, o None si corre desde fuente."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return None


def _repo_root() -> Path:
    """Raiz del repo en desarrollo (subiendo desde src/fb2p_studio/core/)."""
    return Path(__file__).resolve().parents[3]


def bundled_fb2p_dir() -> Path | None:
    """Ubicacion del FoxBin2Prg embebido.

    En dev: `<repo>/bundled/foxbin2prg/`.
    Empaquetado (PyInstaller onefile): `sys._MEIPASS/bundled/foxbin2prg/`.
    """
    base = _frozen_base() or _repo_root()
    candidate = base / "bundled" / "foxbin2prg"
    return candidate if _has_fb2p(candidate) else None


@dataclass(slots=True, frozen=True)
class Paths:
    vfp_exe: Path | None
    fb2p_home: Path | None
    bridge_dir: Path


def _first_existing(candidates: list[str | Path]) -> Path | None:
    for c in candidates:
        p = Path(c)
        if p.exists():
            return p
    return None


def find_vfp_exe(override: str | os.PathLike | None = None) -> Path | None:
    """Orden: override -> VFP_EXE -> rutas tipicas.

    Un override que ya no existe (por ejemplo, un .ini copiado de otra
    maquina) no corta la busqueda: se ignora y se sigue con el resto.
    """
    if override and Path(override).exists():
        return Path(override)
    env = os.environ.get("VFP_EXE")
    if env and Path(env).exists():
        return Path(env)
    return _first_existing(_VFP_TYPICAL)


def find_fb2p_home(override: str | os.PathLike | None = None) -> Path | None:
    """Devuelve la carpeta que contiene FoxBin2Prg.EXE o .FXP.

    Orden: override -> FB2P_HOME -> FoxBin2Prg embebido -> rutas tipicas.

    El embebido va ANTES que las rutas tipicas a proposito: es la version
    que Studio trae y con la que se probo. Un `C:\\FoxBin2Prg` viejo en la
    maquina de un usuario no debe ganarle en silencio. Para usar otra copia
    (un clon de desarrollo, por ejemplo) hay que pedirlo explicitamente por
    Preferencias o `FB2P_HOME`, y la pestana Acerca de lo muestra.

    Un override que ya no existe (por ejemplo, un .ini copiado de otra
    maquina, o una carpeta que se movio) no corta la busqueda: se ignora
    y se sigue con el resto. Asi el .exe distribuido nunca queda sin
    FoxBin2Prg por una preferencia vieja.
    """
    if override and _has_fb2p(Path(override)):
        return Path(override)
    env = os.environ.get("FB2P_HOME")
    if env:
        p = Path(env)
        if _has_fb2p(p):
            return p
    bundled = bundled_fb2p_dir()
    if bundled is not None:
        return bundled
    # Sin bundle (corriendo desde fuente sin bundled/): rutas conocidas
    for cand in _FB2P_TYPICAL:
        p = Path(cand)
        if _has_fb2p(p):
            return p
    return None


def _has_fb2p(folder: Path) -> bool:
    return folder.is_dir() and (
        (folder / "FoxBin2Prg.EXE").exists() or (folder / "FoxBin2Prg.FXP").exists()
    )


def bridge_dir() -> Path:
    """Ubicacion del driver PRG/FPW.

    En desarrollo: `<repo>/vfp_bridge/`.
    Empaquetado (PyInstaller onefile): `sys._MEIPASS/vfp_bridge/`.
    """
    return (_frozen_base() or _repo_root()) / "vfp_bridge"


def resources_dir() -> Path:
    """Ubicacion de los recursos de la app (icono, etc).

    En desarrollo: `src/fb2p_studio/resources/`.
    Empaquetado (PyInstaller onefile): `sys._MEIPASS/fb2p_studio/resources/`.
    """
    base = _frozen_base()
    if base is not None:
        return base / "fb2p_studio" / "resources"
    return Path(__file__).resolve().parents[1] / "resources"


#: Nombre del manual de usuario. Es el LEEME.md que viaja en el zip y en el MSI.
MANUAL_NAME = "LEEME.md"


def manual_path() -> Path | None:
    """Ruta al manual de usuario (LEEME.md), o None si falta.

    Una sola fuente: `release/_template/LEEME.md`, el mismo archivo que se
    reparte en el zip y el MSI. Desde fuente se lee de ahi; el `.spec` lo
    embebe en el `.exe`, donde vive junto a los demas recursos.
    """
    base = _frozen_base()
    if base is not None:
        candidate = resources_dir() / MANUAL_NAME
    else:
        candidate = _repo_root() / "release" / "_template" / MANUAL_NAME
    return candidate if candidate.is_file() else None


def app_icon_path() -> Path | None:
    """Ruta al .ico de la app, o None si falta (se genera con build/make_icon.py)."""
    candidate = resources_dir() / "fb2p_studio.ico"
    return candidate if candidate.is_file() else None


def resolve(
    vfp_override: str | None = None, fb2p_override: str | None = None
) -> Paths:
    return Paths(
        vfp_exe=find_vfp_exe(vfp_override),
        fb2p_home=find_fb2p_home(fb2p_override),
        bridge_dir=bridge_dir(),
    )

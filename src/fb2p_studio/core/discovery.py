"""Localiza vfp9.exe, FoxBin2Prg y el driver VFP en disco.

Orden de resolucion:
1. Ruta explicita pasada por el llamador (Preferencias).
2. Variables de entorno (`VFP_EXE`, `FB2P_HOME`).
3. Ubicaciones tipicas conocidas.
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


def _bundled_fb2p_dir() -> Path | None:
    """Ubicacion del FoxBin2Prg embebido.

    En dev: `<repo>/bundled/foxbin2prg/`.
    Empaquetado (PyInstaller onefile): `sys._MEIPASS/bundled/foxbin2prg/`.
    """
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
        candidate = base / "bundled" / "foxbin2prg"
    else:
        candidate = Path(__file__).resolve().parents[3] / "bundled" / "foxbin2prg"
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
    if override:
        p = Path(override)
        return p if p.exists() else None
    env = os.environ.get("VFP_EXE")
    if env and Path(env).exists():
        return Path(env)
    return _first_existing(_VFP_TYPICAL)


def find_fb2p_home(override: str | os.PathLike | None = None) -> Path | None:
    """Devuelve la carpeta que contiene FoxBin2Prg.EXE o .FXP.

    Orden: override -> FB2P_HOME -> rutas tipicas -> FoxBin2Prg embebido.
    """
    if override:
        p = Path(override)
        if _has_fb2p(p):
            return p
        return None
    env = os.environ.get("FB2P_HOME")
    if env:
        p = Path(env)
        if _has_fb2p(p):
            return p
    for cand in _FB2P_TYPICAL:
        p = Path(cand)
        if _has_fb2p(p):
            return p
    # Ultimo fallback: el FoxBin2Prg que empaqueta el propio Studio
    return _bundled_fb2p_dir()


def _has_fb2p(folder: Path) -> bool:
    return folder.is_dir() and (
        (folder / "FoxBin2Prg.EXE").exists() or (folder / "FoxBin2Prg.FXP").exists()
    )


def bridge_dir() -> Path:
    """Ubicacion del driver PRG/FPW.

    En desarrollo: `<repo>/vfp_bridge/`.
    Empaquetado (PyInstaller onefile): `sys._MEIPASS/vfp_bridge/`.
    """
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
        return base / "vfp_bridge"
    # dev: subir desde src/fb2p_studio/core/ hasta repo root
    return Path(__file__).resolve().parents[3] / "vfp_bridge"


def resolve(
    vfp_override: str | None = None, fb2p_override: str | None = None
) -> Paths:
    return Paths(
        vfp_exe=find_vfp_exe(vfp_override),
        fb2p_home=find_fb2p_home(fb2p_override),
        bridge_dir=bridge_dir(),
    )

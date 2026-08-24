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


def direction_from_ext(path: str) -> str:
    """Determina 'BIN2PRG', 'PRG2BIN' o '' (desconocida) segun la extension."""
    ext = path.rsplit(".", 1)[-1].lower() if "." in path else ""
    if ext in BIN_TO_TEXT:
        return "BIN2PRG"
    if ext in TEXT_TO_BIN:
        return "PRG2BIN"
    return ""


def is_supported(path: str) -> bool:
    ext = path.rsplit(".", 1)[-1].lower() if "." in path else ""
    return ext in BIN_TO_TEXT or ext in TEXT_TO_BIN

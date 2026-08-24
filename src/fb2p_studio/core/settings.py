"""Wrapper tipado sobre QSettings.

Persiste en `%APPDATA%\\ADS Software\\FoxBin2Prg-Studio.ini` (Windows).
"""

from __future__ import annotations

from PySide6.QtCore import QSettings


class Settings:
    def __init__(self) -> None:
        self._s = QSettings(QSettings.Format.IniFormat, QSettings.Scope.UserScope, "ADS Software", "FoxBin2Prg-Studio")

    # --- rutas ---
    @property
    def vfp_exe(self) -> str:
        return str(self._s.value("paths/vfp_exe", "", type=str))

    @vfp_exe.setter
    def vfp_exe(self, value: str) -> None:
        self._s.setValue("paths/vfp_exe", value)

    @property
    def fb2p_home(self) -> str:
        return str(self._s.value("paths/fb2p_home", "", type=str))

    @fb2p_home.setter
    def fb2p_home(self, value: str) -> None:
        self._s.setValue("paths/fb2p_home", value)

    # --- defaults de opciones avanzadas ---
    def get_int(self, key: str, default: int) -> int:
        v = self._s.value(f"defaults/{key}", default, type=int)
        return int(v)

    def set_int(self, key: str, value: int) -> None:
        self._s.setValue(f"defaults/{key}", int(value))

    # --- recientes ---
    @property
    def recent_files(self) -> list[str]:
        raw = self._s.value("recent/files", [], type=list) or []
        return [str(x) for x in raw]

    def push_recent(self, path: str, max_items: int = 10) -> None:
        items = [p for p in self.recent_files if p != path]
        items.insert(0, path)
        self._s.setValue("recent/files", items[:max_items])

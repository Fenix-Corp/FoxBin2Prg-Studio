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

    # --- apariencia ---
    @property
    def theme(self) -> str:
        """Id del tema. Vacio = el de siempre (ver `ui.theme.DEFAULT`)."""
        return str(self._s.value("ui/theme", "", type=str))

    @theme.setter
    def theme(self, value: str) -> None:
        self._s.setValue("ui/theme", value)

    # --- actualizaciones ---
    @property
    def update_manifest(self) -> str:
        """Origen de las actualizaciones. Vacio = el canal por defecto (`updates.DEFAULT_SOURCE`).

        Conserva la clave `updates/manifest` de cuando solo era un manifiesto en el NAS:
        un .ini viejo sigue funcionando.
        """
        return str(self._s.value("updates/manifest", "", type=str))

    @update_manifest.setter
    def update_manifest(self, value: str) -> None:
        self._s.setValue("updates/manifest", value)

    @property
    def check_updates_on_start(self) -> bool:
        return bool(self._s.value("updates/on_start", True, type=bool))

    @check_updates_on_start.setter
    def check_updates_on_start(self, value: bool) -> None:
        self._s.setValue("updates/on_start", bool(value))

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

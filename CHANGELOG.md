# Changelog

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/).

## [Unreleased]

### Added
- Estructura inicial del proyecto: `src/fb2p_studio`, `vfp_bridge`, `build`, `tests`, `docs`.
- `pyproject.toml` con PySide6 y toolchain (ruff, pytest, pyinstaller).
- `.gitattributes` con CRLF + `working-tree-encoding=windows-1252` para `.prg` / `.fpw`.
- Driver VFP `vfp_bridge/fb2p_bridge.prg` — usa el Object API `c_foxbin2prg`, emite JSONL.
- Runner Python `core/bridge.py` — QProcess wrapper, no bloquea UI.
- Tab **Convertir** (archivo suelto BIN2PRG / PRG2BIN) y tab **Acerca de**.
- **FoxBin2Prg embebido** (`bundled/foxbin2prg/`, ~857 KB) como fallback de `discovery.find_fb2p_home()`. Redistribuido bajo CC BY 4.0; atribución en tab Acerca de y en `bundled/foxbin2prg/ATTRIBUTION.md`.
- `bundled/update_bundle.bat` — script para actualizar el bundle desde un clon local de FoxBin2Prg.
- PyInstaller spec embebe `bundled/foxbin2prg/` como datos, extraídos a `_MEIPASS` en runtime.

### Fixed
- Detección de `fb2pVersion`: `VERNO` pass-by-ref no funcionaba. Reemplazado por parseo del header de `foxbin2prg.pj2` (`Version="X.YY"`).
- `RETURN` dentro de `TRY/CATCH` en VFP9 no propagaba correctamente — refactorizado a variable de resultado.

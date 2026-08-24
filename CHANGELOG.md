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

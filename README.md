# FoxBin2Prg-Studio

GUI de escritorio (Windows) que administra [FoxBin2Prg](https://github.com/fdbozzo/foxbin2prg) como herramienta genérica para cualquier proyecto de Visual FoxPro 9.

Empaquetada como un único `.exe` (PyInstaller onefile). Habla con `FoxBin2Prg` a través del **Object API** (no del CLI), vía un driver VFP propio que emite eventos JSONL — esto permite reportar errores estructurados (`oEx.Message` / `oEx.LineNo` / `oEx.Details`), progreso en tiempo real, y dry-run.

## Estado

MVP en construcción. Tabs previstas:

| Tab | Cubre | Estado |
|---|---|---|
| Convertir | Un archivo o carpeta (BIN2PRG / PRG2BIN) | 🚧 MVP |
| Proyecto | Proyecto completo (`*` / `*-`) | ⏳ fase 2 |
| Diff | `Fb2P_Diff.EXE` | ⏳ fase 2 |
| Config | Templates `.cfg` y `.dbf.cfg` | ⏳ fase 2 |
| Acerca de | Diagnóstico + `VERNO` | 🚧 MVP |

## Requisitos de la máquina destino

| Requisito | Ruta típica | Override |
|---|---|---|
| Visual FoxPro 9 SP2 (build ≥ 3504) | `C:\Fenix\AdsFenix\Librerias\vfp9.exe` | var. entorno `VFP_EXE` o Preferencias |
| FoxBin2Prg (`.EXE` o `.FXP`) | `D:\FenixPro\Proyectos\foxbin2prg\` | var. entorno `FB2P_HOME` o Preferencias |

## Arquitectura

```
FoxBin2Prg-Studio/
├── src/fb2p_studio/           GUI Python (PySide6)
│   ├── ui/                    Widgets y tabs
│   └── core/                  bridge, ipc, job, discovery, settings
├── vfp_bridge/                Driver VFP (fb2p_bridge.prg)
├── build/                     PyInstaller spec + scripts
├── tests/                     pytest
└── docs/
```

El driver `vfp_bridge/fb2p_bridge.prg` recibe un `job.json`, ejecuta las operaciones vía `c_foxbin2prg.execute()` con captura de excepción, y emite un stream JSONL de eventos. Python lo lee en vivo con `QFileSystemWatcher` y actualiza la UI.

Ver [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) para el protocolo IPC completo.

## Desarrollo

```bash
py -3.12 -m venv .venv
.venv\Scripts\activate
pip install -e .[dev]
python -m fb2p_studio
```

Compilar el `.exe` distribuible:

```bash
build\build.bat
```

## Licencia

MIT.

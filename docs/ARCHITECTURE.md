# Arquitectura de FoxBin2Prg-Studio

## Por qué Object API y no CLI

FoxBin2Prg se puede invocar de tres formas: como `FoxBin2Prg.EXE` desde consola, como PRG desde `DO`, o como objeto `c_foxbin2prg` (Object API). Sólo el Object API entrega:

- `oEx` — objeto excepción con `Message`, `LineNo`, `Details`, `StackLevel`, `ErrorNo`.
- `get_Processed(@aProcs, mask)` — array con estado por archivo (`cInOutType`, `cProcessed`, `cHasErrors`, `cSupported`, `cExpanded`).
- `l_ProcessFiles = .F.` — modo simulación (dry-run) sin tocar disco.
- `hasSupport_Bin2Prg()` / `hasSupport_Prg2Bin()` — pre-validación por archivo.
- `get_DirSettings(cDir)` — objeto CFG efectivo tras la herencia de `.cfg`.

El CLI sólo entrega `ErrorLevel 0/1` y un CSV a stdout con mensajes localizados. Insuficiente para una GUI seria.

## Componentes

```
┌────────────────────────────┐   spawn      ┌──────────────────────────┐
│  fb2p_studio (Python/Qt)   │─────────────▶│ vfp9.exe -T -C bridge.fpw│
│                            │              │ └ fb2p_bridge.prg        │
│  UI  ─▶  core.bridge       │              │    └ c_foxbin2prg        │
│                            │              │       (Object API)       │
│  core.ipc  ◀──────────────╌╌╌ JSONL ╌╌╌╌╌╌│ STRTOFILE(...,ADDITIVE)  │
└────────────────────────────┘              └──────────────────────────┘
```

### Python (`src/fb2p_studio/`)

- **`core.job`**: `Job`, `Operation`, `FileResult` — dataclasses tipadas.
- **`core.discovery`**: localiza `vfp9.exe` y `foxbin2prg` (var. entorno + `QSettings` + defaults).
- **`core.bridge`**: envuelve `QProcess`. Genera `job.json`, lanza VFP con el driver, escucha `finished()`.
- **`core.ipc`**: `QFileSystemWatcher` sobre `progress.jsonl`, emite señales Qt por evento.
- **`core.settings`**: wrapper sobre `QSettings` (ubicación: `%APPDATA%\FoxBin2Prg-Studio\`).
- **`ui.*`**: PySide6, `QMainWindow` con `QTabWidget`.

### Driver VFP (`vfp_bridge/`)

- **`fb2p_bridge.prg`**: entrypoint. Lee `job.json` de la variable de entorno `FB2P_JOB`, itera operaciones, escribe JSONL en la ruta indicada en el propio job.
- **`fb2p_bridge.fpw`**: `SCREEN=OFF` + `COMMAND=DO fb2p_bridge.prg`.

## Protocolo IPC (JSONL)

### Job (Python → driver)

Archivo `%TEMP%\fb2p_studio\<uuid>\job.json`:

```json
{
  "schemaVersion": 1,
  "foxbin2prgHome": "D:\\FenixPro\\Proyectos\\foxbin2prg",
  "eventStream": "C:\\Users\\...\\Temp\\fb2p_studio\\<uuid>\\events.jsonl",
  "dryRun": false,
  "operations": [
    {
      "id": "op1",
      "file": "C:\\proj\\form.scx",
      "type": "BIN2PRG",
      "options": {
        "noTimestamps": 1,
        "debug": 0,
        "recompile": 1,
        "backupLevels": 1,
        "clearUniqueID": 1
      },
      "outputFolder": null,
      "cfgFile": null
    }
  ]
}
```

Ruta del `job.json` pasa al driver por variable de entorno `FB2P_JOB`.

### Eventos (driver → Python)

Un JSON por línea, con `flush` implícito (cada línea es un `STRTOFILE(..., ADDITIVE)` que cierra el handle).

```
{"event":"job_start","total":3,"timestamp":"2026-08-24T10:30:00","vfpVersion":"09.00.0000.7423","fb2pVersion":"1.21.5"}
{"event":"op_start","opId":"op1","file":"C:\\proj\\form.scx","direction":"BIN2PRG"}
{"event":"file_processed","opId":"op1","inOut":"O","file":"C:\\proj\\form.sc2","hasErrors":0,"supported":1,"expanded":1}
{"event":"op_error","opId":"op2","errorNo":11,"message":"...","lineNo":842,"details":"..."}
{"event":"op_done","opId":"op1","returnCode":0,"elapsedMs":124}
{"event":"job_done","okCount":2,"errCount":1,"elapsedMs":410}
```

### Códigos de evento

| event | Cuándo | Campos |
|---|---|---|
| `job_start` | Al arrancar el driver | `total`, `timestamp`, `vfpVersion`, `fb2pVersion` |
| `op_start` | Antes de cada `execute()` | `opId`, `file`, `direction` |
| `file_processed` | Fila del `get_Processed()` | `opId`, `inOut`, `file`, `hasErrors`, `supported`, `expanded` |
| `op_error` | `CATCH TO loEx` disparó | `opId`, `errorNo`, `message`, `lineNo`, `details` |
| `op_done` | Después de cada `execute()` | `opId`, `returnCode`, `elapsedMs` |
| `job_done` | Antes de `QUIT` | `okCount`, `errCount`, `elapsedMs` |
| `driver_error` | Falla del propio driver (job.json ilegible, etc.) | `message`, `stage` |

## Cancelación

Python escribe un archivo sentinela `<work>\\.cancel` cuando el usuario cancela. El driver lo chequea entre operaciones (no interrumpe una operación en curso — FoxBin2Prg no es interrumpible) y sale limpio con `job_done` reportando lo hecho.

## Riesgos cubiertos

- **`INTERACTIVE` prohibido**: el driver nunca lo pasa; la GUI muestra sus propios diálogos.
- **`MESSAGEBOX` bloqueante**: el driver siempre pasa `cDontShowErrors=1`.
- **`ShowProgressbar` VFP**: `cDontShowProgress=1`.
- **Locks de binarios**: `core.validators` chequea antes de cada `op_start`.
- **Proyecto con archivos en otra unidad**: `core.validators` advierte antes de encolar.

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

- **`core.job`**: `Job`, `Operation`, `OperationOptions` y los `*Event` — dataclasses tipadas.
- **`core.project_reader`**: lee que archivos componen un proyecto — el `.pjx` es un DBF (con sus nombres en el memo `.pjt`), el `.pj2` es texto. Replica como arma la lista FoxBin2Prg.
- **`core.validators`**: pre-flight. Para cada archivo del proyecto dice si existe y si se convierte en esa direccion, que son las dos condiciones que FoxBin2Prg evalua en silencio.
- **`core.discovery`**: localiza `vfp9.exe` y `foxbin2prg` (var. entorno + `QSettings` + defaults).
- **`core.bridge`**: envuelve `QProcess`. Genera `job.ini`, lanza VFP con el driver, escucha `finished()`.
- **`core.ipc`**: `QFileSystemWatcher` sobre `progress.jsonl`, emite señales Qt por evento.
- **`core.settings`**: wrapper sobre `QSettings` (ubicación: `%APPDATA%\FoxBin2Prg-Studio\`).
- **`ui.*`**: PySide6, `QMainWindow` con un menu lateral (`ui.sidenav.SideNav`) y un `QStackedWidget`: la barra solo navega y la ventana muestra la pagina que toca. Las paginas que ejecutan jobs (Convertir, Proyecto) comparten `ui.job_runner.JobRunner` (ciclo de vida del bridge + volcado de eventos al log) y `ui.widgets.advanced_options.AdvancedOptions`.

### Driver VFP (`vfp_bridge/`)

- **`fb2p_bridge.prg`**: entrypoint. Lee el `job.ini` que indica la variable de entorno `FB2P_JOB`, itera operaciones, escribe JSONL en la ruta indicada en el propio job.
- **`fb2p_bridge.fpw`**: `SCREEN=OFF` + `COMMAND=DO fb2p_bridge.prg`.

## Protocolo IPC (JSONL)

### Job (Python → driver)

Archivo `%TEMP%\fb2p_studio_<hex>\job.ini`. **Es INI, no JSON**: el driver es VFP y parsear INI ahí son treinta líneas, mientras que parsear JSON son trescientas. El JSONL de vuelta sí es JSON porque lo consume Python.

```ini
[job]
foxbin2prghome = D:\FenixPro\Proyectos\FoxBin2Prg-Studio\bundled\foxbin2prg
eventstream = C:\Users\...\Temp\fb2p_studio_a1b2c3d4\events.jsonl
dryrun = 0

[op:op1]
file = C:\proj\form.scx
type = BIN2PRG
notimestamps = 1
debug = 0
recompile = 1
backuplevels = 1
clearuniqueid = 1
cfgfile =
outputfolder =
```

`configparser` baja las claves a minúsculas al escribir; el parser del driver también, así que el protocolo es case-insensitive de los dos lados.

La ruta del `job.ini` llega al driver por la variable de entorno `FB2P_JOB`.

#### `type` — el `cType` de FoxBin2Prg

| Valor | Significado |
|---|---|
| *(vacío)* | La dirección la decide la extensión del archivo. |
| `BIN2PRG` | Binario → texto. |
| `PRG2BIN` | Texto → binario. |
| `*` | **Modo proyecto:** el `.pjx`/`.pj2` y todos sus archivos. La dirección la decide la extensión del proyecto. |
| `*-` | Igual, pero **sin** el propio archivo de proyecto. |

FoxBin2Prg entra al modo proyecto cuando el `cType` **empieza** con `*` y la extensión es `PJX`/`PJ2` (`Left(Evl(tcType,'0'),1) == '*'` en `foxbin2prg.prg`), y dentro decide con `If tcType <> '*-'` si convierte también el proyecto.

> El driver **no** puede aplicar su recorte de guiones al modo proyecto: `sanitize_ctype()` sale temprano cuando el valor empieza con `*`, porque el recorte convertiría `*-` en `*` — es decir, incluiría el `.pjx` que el usuario pidió excluir. Hay tests que fijan esto (`tests/test_project_mode.py`).

`INTERACTIVE` y `SHOWMSG` se eliminan siempre: abren diálogos que colgarían el proceso headless.

#### Soporte de conversión: depende de la dirección

FoxBin2Prg no convierte todo en las dos direcciones. Cada tipo de archivo tiene una clave `n_XXX_Conversion_Support` y las dos funciones de soporte piden cosas distintas:

- `hasSupport_Bin2Prg()` → `n_XXX_Conversion_Support > 0`
- `hasSupport_Prg2Bin()` → `n_XXX_Conversion_Support = 2` (para DBF acepta también `8`, *import de datos*)

Con los valores por defecto:

| Extensión | Soporte | Bin → Prg | Prg → Bin |
|---|---|---|---|
| PJX, VCX, SCX, FRX, LBX, MNX, DBC | 2 | sí | sí |
| **DBF, FKY, MEM** | **1** | sí | **no** |

Es decir: una tabla se **vuelca** a texto pero no se **reconstruye** desde él — rearmar el `.dbf` desde su dump pisaría los datos, así que hay que pedirlo explícitamente en el `.cfg`. Cuando no se cumple el soporte, FoxBin2Prg registra el archivo como no procesado (`P0`/`S0`) y **sigue sin avisar**.

`core/extensions.py` replica esta tabla en `DEFAULT_SUPPORT` y `supports(path, direction)`. Es una **predicción con la configuración por defecto**: no se leen los `foxbin2prg.cfg` del árbol (con toda su herencia), así que un `.cfg` puede cambiar el resultado. La UI lo dice donde muestra el número.

#### `recompile` — acepta una carpeta

Además de `0`/`1`, `cRecompile` acepta un **directorio**: FoxBin2Prg hace `CD` ahí antes de recompilar y sigue recompilando (`l_Recompile = (Empty(x) Or x == '1' Or Directory(x))`). La pestaña Proyecto lo usa para recompilar desde la carpeta del proyecto en vez de la de cada archivo, que es lo que rompe las rutas relativas de los `#include`.

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
| `progress` | **En vivo**, una vez por archivo mientras `execute()` sigue corriendo (via `BINDEVENT` a `updateProgressbar`, tipo 0) | `opId`, `current`, `total`, `text` |
| `file_processed` | Fila del `get_Processed()` (al volver `execute()`) | `opId`, `inOut`, `file`, `hasErrors`, `supported`, `expanded` |
| `op_error` | `CATCH TO loEx` disparó | `opId`, `errorNo`, `message`, `lineNo`, `details` |
| `op_done` | Después de cada `execute()` | `opId`, `returnCode`, `elapsedMs` |
| `job_done` | Antes de `QUIT` | `okCount`, `errCount`, `elapsedMs` |
| `driver_error` | Falla del propio driver (job.ini ilegible, FoxBin2Prg ausente, etc.) | `message`, `stage` |

## Cancelación

Python escribe un archivo sentinela `<work>\\.cancel` cuando el usuario cancela. El driver lo chequea entre operaciones (no interrumpe una operación en curso — FoxBin2Prg no es interrumpible) y sale limpio con `job_done` reportando lo hecho.

## Riesgos cubiertos

- **`INTERACTIVE` prohibido**: el driver nunca lo pasa; la GUI muestra sus propios diálogos.
- **`MESSAGEBOX` bloqueante**: el driver siempre pasa `cDontShowErrors=1`.
- **`ShowProgressbar` VFP**: `cDontShowProgress=1`.
- **Archivos faltantes o no convertibles**: `core.validators` los reporta ANTES de ejecutar (la pestana Proyecto los lista y pide confirmacion si falta alguno). Es lo que FoxBin2Prg se salta sin decir nada.
- **Locks de binarios**: NO se pre-valida. Si el binario esta abierto en VFP, la operacion falla y llega como `op_error` con el mensaje de VFP.
- **Proyecto con archivos en otra unidad**: lo arregla FoxBin2Prg desde la v1.19.45 (bug reportado por Matt Slay); el bundle embebido es 1.21, asi que esta cubierto.

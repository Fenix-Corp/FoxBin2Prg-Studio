# vfp_bridge

Driver VFP que ejecuta las operaciones de FoxBin2Prg vía **Object API** (`c_foxbin2prg`) y emite eventos JSONL que la GUI Python consume en vivo.

## Archivos

| Archivo | Rol |
|---|---|
| `fb2p_bridge.prg` | Driver principal. Lee `FB2P_JOB`, itera operaciones con `TRY/CATCH TO loEx`, escribe JSONL |
| `fb2p_bridge.fpw` | Config para arranque headless (`SCREEN=OFF`, `COMMAND=DO fb2p_bridge.prg`) |

## Invocación

```
set FB2P_JOB=C:\path\to\job.ini
vfp9.exe -T -C "path\to\fb2p_bridge.fpw"
```

El CWD del proceso debe ser `vfp_bridge/` (o el `.prg` debe estar accesible por SET PATH).

## Formato del job (INI)

```ini
[job]
foxbin2prgHome = D:\FenixPro\Proyectos\foxbin2prg
eventStream    = C:\Users\...\Temp\fb2p_studio\<uuid>\events.jsonl
dryRun         = 0

[op:op1]
file           = C:\proj\form.scx
type           = BIN2PRG
noTimestamps   = 1
debug          = 0
recompile      = 1
backupLevels   = 1
clearUniqueID  = 1
```

- `type` puede ser `BIN2PRG`, `PRG2BIN`, o combinaciones con `-` y modificadores `*` / `*-` para proyecto. El driver **elimina automáticamente** `INTERACTIVE` y `SHOWMSG` (bloqueantes).
- Sección `[op:<id>]` — el `<id>` se propaga como `opId` en los eventos.

## Eventos emitidos

Ver [../docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md#eventos-driver--python).

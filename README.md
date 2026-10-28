# FoxBin2Prg-Studio

GUI de escritorio (Windows) que administra [FoxBin2Prg](https://github.com/fdbozzo/foxbin2prg) como herramienta genérica para cualquier proyecto de Visual FoxPro 9.

Empaquetada como un único `.exe` (PyInstaller onefile). Habla con `FoxBin2Prg` a través del **Object API** (no del CLI), vía un driver VFP propio que emite eventos JSONL — esto permite reportar errores estructurados (`oEx.Message` / `oEx.LineNo` / `oEx.Details`), progreso en tiempo real, y dry-run.

## Estado

MVP en construcción. Tabs previstas:

| Tab | Cubre | Estado |
|---|---|---|
| Convertir | Un archivo o carpeta (BIN2PRG / PRG2BIN) | ✅ |
| Proyecto | Proyecto completo (`*` / `*-`), con pre-flight del contenido | ✅ |
| Diff | `Fb2P_Diff.EXE` | ⏳ fase 2 |
| Config | Templates `.cfg` y `.dbf.cfg` | ⏳ fase 2 |
| Acerca de | Diagnóstico + `VERNO` | 🚧 MVP |

## Requisitos de la máquina destino

Sólo **una** dependencia externa: Visual FoxPro 9 SP2 instalado (build ≥ 3504). No se puede embeber por licencia de Microsoft — pero cualquier desarrollador VFP9 ya lo tiene.

| Requisito | Ruta típica | Override |
|---|---|---|
| **Externo:** `vfp9.exe` | `C:\Fenix\AdsFenix\Librerias\vfp9.exe` o `C:\Program Files (x86)\Microsoft Visual FoxPro 9\` | var. entorno `VFP_EXE` o Preferencias |
| **Embebido:** FoxBin2Prg (~857 KB) | `bundled/foxbin2prg/` (dev), `_MEIPASS/bundled/foxbin2prg/` (empaquetado) | var. entorno `FB2P_HOME` o Preferencias |

Orden de resolución de FoxBin2Prg: `Preferencias` → `FB2P_HOME` → **bundle embebido** → rutas típicas (sólo si no hubiera bundle).

Por defecto, entonces, **siempre corre el FoxBin2Prg que viaja dentro del `.exe`**: el usuario no instala nada, y todo el equipo usa la misma versión. Un `C:\FoxBin2Prg` viejo en la máquina de alguien no le gana en silencio al embebido; para usar otra copia (un clon de desarrollo, por ejemplo) hay que pedirlo explícitamente por `FB2P_HOME` o Preferencias. La pestaña **Acerca de** muestra cuál está en uso, marcado como `(embebido en Studio)` o `(externo)`.

Ningún paso de la cadena es obligatorio: un override que ya no existe (un `.ini` copiado de otra máquina, una carpeta que se movió) se ignora y la búsqueda sigue, en vez de dejar la app sin herramienta.

> **El SP2 no es opcional.** Verificar con `? VERSION(4)` en la ventana de comandos de VFP9: tiene que devolver `09.00.0000.3504` o superior. Si el build es menor, correr el instalador `setup_bussinesRule.exe`, que deja VFP9 en SP2, disponible en el NAS (`\\192.168.0.16\Compilado_16`) o en [SharePoint](https://adssoftware.sharepoint.com/:f:/s/SOPORTE_ADS/IgDgpcrWtLgYQZsc32SzmgLRAVF8stWKYEFlzKkmYGi6FVw?e=sqfAVY). El log de Studio también lo muestra: el evento `job_start` trae `vfpVersion`.

## Arquitectura

```
FoxBin2Prg-Studio/
├── src/fb2p_studio/           GUI Python (PySide6)
│   ├── ui/                    Widgets y tabs
│   ├── core/                  bridge, ipc, job, discovery, settings, updates,
│   │                          project_reader, validators
│   └── resources/             Icono (.ico), logo ADS + traducciones (i18n/)
├── vfp_bridge/                Driver VFP (fb2p_bridge.prg)
├── build/                     PyInstaller spec + scripts (build, check, package, msi, i18n)
├── .github/workflows/         CI
├── tests/                     pytest
└── docs/
```

El driver `vfp_bridge/fb2p_bridge.prg` recibe un `job.json`, ejecuta las operaciones vía `c_foxbin2prg.execute()` con captura de excepción, y emite un stream JSONL de eventos. Python lo lee en vivo con `QFileSystemWatcher` y actualiza la UI.

Ver [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) para el protocolo IPC completo.

## Desarrollo

Repositorio: <https://github.com/Fenix-Corp/FoxBin2Prg-Studio> (privado).
**Se trabaja en `dev`**; `master` se actualiza por PR desde `dev`.

```bash
py -3.12 -m venv .venv
.venv\Scripts\activate
pip install -e .[dev]
python -m fb2p_studio
```

Antes de commitear, el gate de calidad — es exactamente lo que corre CI:

```bash
build\check.bat
```

Con `--build` compila además el `.exe`; con `--fix` aplica antes los autofixes de ruff.

### Scripts de `build/`

| Script | Qué hace |
|---|---|
| `build.bat` | Compila `dist\FoxBin2Prg-Studio.exe` (PyInstaller onefile). Regenera el icono y las traducciones si faltan. |
| `check.bat` | Lint (ruff) + tests (pytest), opcionalmente + build. Lo mismo que CI. |
| `package.bat` | Arma `release\FoxBin2Prg-Studio-<ver>\` con el `.exe` y la documentación. Con `--zip`, comprime. |
| `msi.bat` | Genera `release\FoxBin2Prg-Studio-<ver>.msi` (ver *Instalador MSI*). |
| `i18n.bat` | Extrae (`extract`) y compila (`release`) las traducciones. |
| `make_icon.py` | Regenera el `.ico` de la app. |

### CI

[`.github/workflows/ci.yml`](.github/workflows/ci.yml) corre lint + tests + build en `windows-latest` y publica el `.exe` como artifact. Dispara en cada push a `master` y a `dev`, y en los PR hacia `master`. Para correrlo en una máquina propia en vez de en los runners de GitHub, cambiar `runs-on: windows-latest` por `runs-on: [self-hosted, windows]`.

### Instalador MSI

El `.exe` suelto es la vía normal. El MSI existe para equipos de IT que despliegan por GPO/Intune: instala en Program Files, deja acceso directo en el menú Inicio y entrada de desinstalación.

```bash
dotnet tool install --global wix --version 5.0.2
```

```bash
build\msi.bat
```

Se fija la versión **5** de WiX a propósito: de la 6 en adelante hay que aceptar la EULA del *Open Source Maintenance Fee*, que para uso comercial es paga. La 5 es libre y usa el mismo esquema de `build/msi/fb2p_studio.wxs`.

> El `UpgradeCode` del `.wxs` identifica al producto de por vida. Si se cambia, Windows deja de ver las versiones nuevas como actualizaciones y quedan dos instalaciones en paralelo.

### Traducciones

El idioma fuente es el español: las cadenas viven en el código tal como se ven, envueltas en `self.tr(...)`. No hace falta traducir nada para que la app funcione en español.

```bash
build\i18n.bat extract
```

Eso actualiza `src/fb2p_studio/resources/i18n/fb2p_studio_<lang>.ts` con las cadenas nuevas. Se traducen con Qt Linguist (`.venv\Scripts\pyside6-linguist.exe <archivo>.ts`) y se compilan con `build\i18n.bat release`. Los `.ts` se versionan; los `.qm` no (los genera el build).

Para sumar un idioma, agregarlo a `IDIOMAS` en `build/i18n.bat`. En runtime, `app.py` carga el `.qm` que corresponda al locale del sistema; si no hay, la UI queda en español.

### Aviso de versión nueva

Studio lee un manifiesto JSON al arrancar y avisa con un toast si hay una versión más nueva. **Sólo avisa**: no descarga ni instala nada.

El origen se configura en **Herramientas → Preferencias** y admite las dos formas:

| Origen | Ejemplo |
|---|---|
| Carpeta de red (por defecto) | `\192.168.0.16\Compilado_16\FoxBin2Prg-Studio\latest.json` |
| URL https | un link de Google Drive o SharePoint |

Los links de compartir de Drive y SharePoint se convierten solos a su forma de descarga directa: el link que se copia del navegador devuelve una página HTML, no el JSON. La lectura corre fuera del hilo de la UI y con timeout, así que un NAS caído o sin red no demora el arranque.

### Temas

Hay tres, elegibles en **Herramientas → Preferencias** y aplicables sin reiniciar:

| Tema | Qué es |
|---|---|
| **ADS corporativo** | La identidad de la casa: azul `#1F3A5E`, banda superior con logo y hoja de estilo propia — la misma que el resto de las utilidades del departamento y que los PDF de `md2pdf`. |
| **Claro** | Fusion con los neutros de la paleta Fénix (fondo `#F7FAFC`, texto `#2D3748`). Selecciona con un azul **claro** (`#AFC3DC`) y texto negro, para que lo elegido se lea sin esfuerzo. |
| **Oscuro** | Fusion con fondo gris oscuro. |

Claro y Oscuro se eligen por separado, **no según Windows**. Mientras no se elija ninguno, Studio arranca en Claro u Oscuro según Windows, como hacía el antiguo tema «Sistema»; su id (`sistema`) se sigue aceptando del `.ini`. La separación y los colores son los mismos de `UtilitiesDevelopment`.

En el tema ADS, los menús desplegables marcan la opción bajo el ratón con un tono claro y texto azul marino, igual que el árbol y la barra de menús.

El tema ADS está portado de `UtilitiesDevelopment/shell/theme.py`; los colores viven en [`ui/theme_ads.py`](src/fb2p_studio/ui/theme_ads.py) y **están medidos, no elegidos a ojo**: [`tests/test_theme_contrast.py`](tests/test_theme_contrast.py) verifica en cada corrida que cada par texto/fondo cumpla el 4,5:1 de WCAG 2.1 AA. Si cambia la identidad corporativa, se corrige ahí y en el CSS de `md2pdf`, no en veinte widgets sueltos.

### Icono

El icono (`src/fb2p_studio/resources/fb2p_studio.ico`) está versionado, pero se genera por código — no hay que editarlo con un editor de íconos. Se dibuja con QPainter y se ensambla un `.ico` multi-tamaño (16/32/48 como DIB, 64/128/256 como PNG):

```bash
.venv\Scripts\python.exe build\make_icon.py
```

Se usa en dos lugares: como icono del `.exe` (`icon=` del spec) y como `QApplication.setWindowIcon()` (ventana y barra de tareas). Para cambiarlo, tocar los colores o el glifo en `build/make_icon.py` y regenerar.

## Licencia

MIT.

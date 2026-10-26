# Changelog

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/).

## [Unreleased]

### Fixed
- **Una corrida larga no mostraba avance.** FoxBin2Prg procesa un proyecto entero dentro de un solo `execute()` y el driver sólo emitia eventos al volver, asi que con un proyecto grande la ventana quedaba en "procesando..." minutos, sin barra y sin nada en el log. Ahora el driver se engancha con `BINDEVENT` a `updateProgressbar` de `c_foxbin2prg` y emite un evento `progress` por archivo; la GUI muestra una barra (`n / N`, porcentaje y archivo en curso) en las pestanas Convertir y Proyecto, y una linea `[n/N]` por archivo en el log. Los `file_processed` siguen llegando al final, con el detalle de cada archivo.

### Added
- **Árbol de resultados** (`ui/widgets/results_view.py`) — reemplaza al log lineal como vista principal de una corrida: cada operación es una fila con sus archivos colgando (Archivo · Dirección · Estado · Tiempo · Error), con filtro *sólo lo que falló* y panel de detalle del error abajo. El log sigue disponible en una pestaña al lado.
- **Tema ADS corporativo, elegible en Preferencias** — el mismo azul #1F3A5E, la banda superior y la hoja de estilo de las demás utilidades del departamento. El tema **Sistema** (Fusion claro/oscuro) sigue siendo el de por defecto y quedó igual que antes. Se cambia sin reiniciar. Los colores del log están medidos contra su fondo y `tests/test_theme_contrast.py` verifica WCAG AA en cada corrida.
- **Toast de aviso** (`ui/widgets/toast.py`) — el chequeo de actualización al arrancar avisa con un aviso flotante que se va solo, en vez de un modal: la lectura del manifiesto puede tardar (está en el NAS) y llega cuando la ventana ya se abrió.
- **Pre-flight del proyecto** — la pestana Proyecto ahora **lista el contenido antes de ejecutar**: cada archivo con su tipo y que va a pasar con el (`se convierte` / `FALTA en disco` / `no convertible`, con el motivo en el tooltip). Antes esto sólo se sabia despues, leyendo el log.
  - `core/project_reader.py` lee los dos formatos: el `.pjx` es un DBF con los nombres en el memo `.pjt`; el `.pj2` es texto y hay que sacar los `.ADD(...)` de entre `*<BuildProj>` y `*</BuildProj>`, cambiandoles la extension a la de texto (que es lo que FoxBin2Prg realmente lee en esa direccion).
  - `core/validators.py` calcula las dos condiciones que FoxBin2Prg evalua en silencio: que el archivo exista y que su tipo tenga soporte en esa direccion. Cierra el `core.validators` que `ARCHITECTURE.md` prometia desde el MVP y no existia.
  - Si falta algun archivo, pedir Ejecutar avisa cuales y pide confirmacion; los faltantes tambien quedan en el log.
  - La prediccion se verifico contra corridas reales de FoxBin2Prg en los cuatro escenarios (`.pjx`/`.pj2` x `*`/`*-`, mas un proyecto con un archivo borrado): coincide archivo por archivo.
- **Tab Proyecto** — convierte un `.pjx`/`.pj2` con todos los archivos del proyecto (modo `*` / `*-` del Usage 1 de FoxBin2Prg). Es el caso de uso real: un dev VFP rara vez convierte un archivo suelto.
  - La direccion **no se elige**: en este modo FoxBin2Prg la deduce de la extension (`.pjx` -> texto, `.pj2` -> binario), asi que la pestana la muestra en vez de ofrecer un selector que seria ignorado.
  - Checkbox para incluir o excluir el propio archivo de proyecto (`*` vs `*-`).
  - Checkbox "Recompilar desde la carpeta del proyecto": aprovecha que `cRecompile` acepta un directorio, para que los `#include` con rutas relativas no fallen al recompilar.
  - Verificado end-to-end con VFP9 real sobre un proyecto de prueba, en las cuatro combinaciones (`.pjx`/`.pj2` x `*`/`*-`).
- Estructura inicial del proyecto: `src/fb2p_studio`, `vfp_bridge`, `build`, `tests`, `docs`.
- `pyproject.toml` con PySide6 y toolchain (ruff, pytest, pyinstaller).
- `.gitattributes` con CRLF + `working-tree-encoding=windows-1252` para `.prg` / `.fpw`.
- Driver VFP `vfp_bridge/fb2p_bridge.prg` — usa el Object API `c_foxbin2prg`, emite JSONL.
- Runner Python `core/bridge.py` — QProcess wrapper, no bloquea UI.
- Tab **Convertir** (archivo suelto BIN2PRG / PRG2BIN) y tab **Acerca de**.
- **FoxBin2Prg embebido** (`bundled/foxbin2prg/`, ~857 KB) como fallback de `discovery.find_fb2p_home()`. Redistribuido bajo CC BY 4.0; atribución en tab Acerca de y en `bundled/foxbin2prg/ATTRIBUTION.md`.
- `bundled/update_bundle.bat` — script para actualizar el bundle desde un clon local de FoxBin2Prg.
- PyInstaller spec embebe `bundled/foxbin2prg/` como datos, extraídos a `_MEIPASS` en runtime.
- **Icono propio** (`src/fb2p_studio/resources/fb2p_studio.ico`), generado por código con `build/make_icon.py` (multi-tamaño 16→256). Se aplica al `.exe` (spec) y a la ventana / barra de tareas (`QApplication.setWindowIcon` + `AppUserModelID`).
- LEEME (`.md` y `.txt`): pre-requisito de VFP9 **SP2** (build ≥ 3504) con cómo verificarlo (`? VERSION(4)`) y de dónde bajar `setup_bussinesRule.exe` (NAS / SharePoint).

- **Chequeo de actualización** (`core/updates.py`): al arrancar, Studio lee un manifiesto JSON en la red (por defecto `\\192.168.0.16\Compilado_16\FoxBin2Prg-Studio\latest.json`) y, si hay versión nueva, deja un aviso clicable en la barra de estado. Menú **Ayuda → Buscar actualizaciones...** para pedirlo a mano. Sólo avisa: no descarga ni instala. La lectura corre fuera del hilo de la UI, así que un NAS caído no cuelga la ventana. Ubicación y chequeo-al-arrancar configurables en Preferencias.
- **Gate de calidad** `build/check.bat` — ruff + pytest (+ build opcional con `--build`, autofix con `--fix`).
- **CI** en `.github/workflows/ci.yml` — lint + tests + build del `.exe` como artifact en `windows-latest`. Inerte hasta que el repo tenga remoto.
- **Instalador MSI** — `build/msi/fb2p_studio.wxs` + `build/msi.bat` (WiX 5). Instala en Program Files, acceso directo en menú Inicio, entrada de desinstalación, icono en "Agregar o quitar programas" y upgrade mayor sin duplicar instalaciones.
- **i18n preparado** — las cadenas de la UI (146 a hoy) pasaron a `self.tr(...)`; `build/i18n.bat` extrae/compila los `.ts`/`.qm` y `app.py` carga la traducción del locale del sistema. El idioma fuente sigue siendo el español, así que sin `.qm` no cambia nada.
- `tests/test_icon.py`, `tests/test_updates.py`, `tests/test_project_mode.py` y `tests/test_project_reader.py` (que fabrica `.pjx` byte a byte, DBF + memo, para documentar el formato que se soporta). La suite pasó de 6 a 172 tests.

### Changed
- El ciclo de vida del bridge y el volcado de eventos al log salieron de `ConvertTab` a `ui/job_runner.py`, y las opciones avanzadas a `ui/widgets/advanced_options.py`: los comparten Convertir y Proyecto en vez de existir dos veces. Verificado que la pestana Convertir muestra exactamente el mismo texto que antes.
- `ConvertTab` registra el archivo en "recientes" al lanzar el job, no al terminarlo.
- `docs/ARCHITECTURE.md`: el job se documentaba como `job.json` cuando el protocolo real es INI, y se listaba un `core.validators` que no existía (ahora sí existe). Corregido, y documentados el `cType` de proyecto, el `cRecompile` con directorio y la tabla de soporte por dirección.
- `discovery.find_fb2p_home()`: el **bundle embebido ahora va antes que las rutas típicas** (`C:\FoxBin2Prg`, clones locales). Una copia vieja instalada en la máquina ya no le gana en silencio a la que viaja en el `.exe`; para usar otra hay que pedirlo por `FB2P_HOME` o Preferencias.
- Tab **Acerca de**: el FoxBin2Prg resuelto se muestra marcado como `(embebido en Studio)` o `(externo)`.
- Diálogo de **Preferencias**: las rutas autodetectadas se muestran como *placeholder*, no como texto del campo. Antes, abrir el diálogo y aceptar persistía la ruta de esa máquina como override.

### Fixed
- **La ventana no entraba en 1366x768 maximizada: los controles se montaban unos sobre otros.** El mínimo de la ventana era de **1013 px de alto**, más que la pantalla, así que Qt aplastaba los widgets por debajo de su mínimo. Tres causas sumadas:
  - El preview del `job.ini` usaba `setFixedHeight()`: con 17 líneas imponía 270 px que no podía ceder, y por eso **tampoco aparecía nunca el scroll**. Ahora el alto del contenido es el *máximo* y el mínimo son 4 líneas: cuando no entra, encoge y muestra la barra.
  - "Opciones avanzadas" decía ser colapsable pero un `QGroupBox` checkable sólo deshabilita a sus hijos: seguían ocupando 209 px en gris. Ahora se ocultan de verdad (41 px colapsado).
  - Las rutas de la pestaña Acerca de, en `QLabel` normales, le fijaban a la ventana **1318 px de ancho** (una sola ruta pedía 1040). Nuevo `ElidedLabel`: acorta con puntos suspensivos en el medio y deja la ruta completa en el tooltip, seleccionable.
  - Mínimo resultante: 766x520 (tema Sistema) y 840x674 (tema ADS). `tests/test_layout.py` lo verifica midiendo solapamientos reales, en las tres pestañas, los dos temas y con las opciones avanzadas abiertas y cerradas.
- **El detalle del error estaba vacío justo cuando hacía falta.** La mayoría de los fallos de FoxBin2Prg no son excepciones VFP: devuelve el código en `op_done` (`rc=1098`) y escribe la explicación legible en stderr. Sólo se miraba `op_error`, así que la causa quedaba enterrada en el log. Ahora se acumula stderr por operación y se muestra en la columna Error y en el panel de detalle.
- **El soporte de conversion depende de la direccion, y no se estaba teniendo en cuenta.** `hasSupport_Bin2Prg()` pide `n_XXX_Conversion_Support > 0` pero `hasSupport_Prg2Bin()` pide `= 2`, asi que con la configuracion por defecto un `.dbf` se vuelca a `.db2` pero el `.db2` **no** se reconstruye (rearmar la tabla pisaria los datos). Studio lo daba por convertible en las dos direcciones: en la pestana Convertir, Ejecutar sobre un `.db2` no hacia nada sin explicar por que. Ahora `core/extensions.py` modela el nivel de soporte por extension y direccion, la pestana Convertir avisa antes de lanzar, y el pre-flight del proyecto lo refleja.
- `sanitize_ctype()` del driver VFP recortaba el guion final del `cType`, convirtiendo `*-` en `*`: pedir "el proyecto sin el .pjx" habria procesado el .pjx igual, sin aviso. Ahora el modo proyecto sale temprano de la normalizacion, con tests que lo fijan.
- Un override de ruta que ya no existe (`.ini` traído de otra máquina, carpeta movida) dejaba a Studio en `<no encontrado>` en vez de seguir buscando: `find_fb2p_home()` / `find_vfp_exe()` ahora lo ignoran y continúan la cadena hasta el FoxBin2Prg embebido.
- `.bat` del repo con finales de línea LF: `cmd.exe` los mal-parseaba (`package.bat` fallaba con `"M" no se reconoce como un comando`). Pasados a CRLF, como ya declaraba `.gitattributes`.
- Los 5 hallazgos de ruff que tenía el repo (import sin ordenar, `if` anidados, variable `l` ambigua, import sin usar). El lint quedó limpio para que el gate sirva de algo.
- Detección de `fb2pVersion`: `VERNO` pass-by-ref no funcionaba. Reemplazado por parseo del header de `foxbin2prg.pj2` (`Version="X.YY"`).
- `RETURN` dentro de `TRY/CATCH` en VFP9 no propagaba correctamente — refactorizado a variable de resultado.

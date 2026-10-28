# Estado del proyecto — FoxBin2Prg-Studio

**Última actualización:** 2026-08-25
**Versión actual:** `0.1.0` (empaquetada y distribuida)
**Repositorio:** <https://github.com/Fenix-Corp/FoxBin2Prg-Studio> (privado)
**Rama de trabajo:** `dev` — `master` se actualiza por PR desde `dev`

Este documento resume la propuesta original, todo lo completado, lo que quedó pendiente y el backlog a futuro. Es la fuente de verdad para saber en qué punto está el proyecto entre sesiones.

---

## 1. Propuesta original

### Objetivo

Construir un **utilitario genérico** de escritorio Windows que administre [FoxBin2Prg](https://github.com/fdbozzo/foxbin2prg) para cualquier proyecto Visual FoxPro 9 — no atado al proyecto `resources`. Debe hacer la conversión bidireccional binario ↔ texto FoxBin2Prg accesible por GUI sin que el usuario tenga que abrir consola, con reporte de errores estructurado y experiencia consistente en Windows.

### Regla fundamental (del prompt inicial)

Antes de programar, cumplir estos 8 pasos:

| # | Paso | Estado |
|---|---|---|
| 1 | Analizar la implementación actual de FoxBin2Prg en el proyecto | ✅ (hecho contra `resources/hooks/`) |
| 2 | Identificar funcionalidades actualmente usadas | ✅ (sólo `DO FoxBin2Prg.FXP WITH <file>`) |
| 3 | Determinar todos los comandos y parámetros disponibles | ✅ (Usage 1/2/3 de `docs/FoxBin2Prg_Run.md`) |
| 4 | Mapear cada funcionalidad con un elemento de la nueva interfaz | ✅ (5 tabs planeadas: Convertir, Proyecto, Diff, Config, Acerca de) |
| 5 | Identificar riesgos y operaciones destructivas | ✅ (`INTERACTIVE`/`SHOWMSG` bloqueantes, `Prg2Bin` sobre binarios abiertos, issue #93 archivos en otra unidad, etc.) |
| 6 | Proponer la arquitectura de la nueva pantalla | ✅ (separación UI / core / bridge VFP) |
| 7 | Presentar el flujo de usuario | ✅ (arrastrar → auto-detección → Ejecutar → log en vivo) |
| 8 | Implementar la solución | 🚧 (MVP 0.1.0 entregado; hay backlog) |

### Decisiones arquitectónicas clave

Todas discutidas y confirmadas con el usuario:

1. **Python + PySide6 + PyInstaller onefile** (no VFP9 puro, no .NET). Justificación: paquete distribuible en un solo `.exe`, sin dependencias externas más allá de VFP9 (que los devs ya tienen).
2. **Object API (no CLI).** Comunicación con FoxBin2Prg vía `c_foxbin2prg` a través de un driver PRG propio. El CLI sólo devuelve `ErrorLevel 0/1` y mensajes localizados — insuficiente para GUI seria. El Object API expone `oEx.Message/LineNo/Details`, `get_Processed()`, `l_ProcessFiles=.F.` para dry-run, `hasSupport_*()` para pre-validación.
3. **IPC por JSONL.** Python escribe `job.ini`, el driver VFP escribe eventos JSONL con `flush` por evento, Python los lee incrementalmente con polling.
4. **FoxBin2Prg embebido** (~857 KB, CC BY 4.0). Requisito único en máquina destino: `vfp9.exe`.
5. **VFP runtime redistribuible NO se empaqueta** — `vfp9r.dll`/`vfp9renu.dll`/`vfp9t.dll` sólo hacen falta para EXEs VFP standalone; nuestro `FoxBin2Prg.EXE` se carga con `SET PROCEDURE`, como librería, no como proceso hijo.

Ver [ARCHITECTURE.md](ARCHITECTURE.md) para detalles del protocolo IPC.

---

## 2. Estado actual (0.1.0)

### Lo que funciona

- **Ejecutable distribuible:** `dist/FoxBin2Prg-Studio.exe` (48 MB, onefile).
- **Paquete listo para compartir:** `release/FoxBin2Prg-Studio-0.1.0/` con `.exe`, `LEEME.txt`, `LEEME.md`, `LICENCIA.txt`, `CAMBIOS.txt`. `release/FoxBin2Prg-Studio-0.1.0.zip` (45 MB) armado.
- **Verificado end-to-end** con archivo real (`articulos_recalculo.sc2` de `C:\Facturas2\FenixForms\`): round-trip Prg→Bin y Bin→Prg en ~150-500 ms.
- **Tests unitarios:** 172/172 pasando. Lint (ruff) limpio. `build\check.bat` corre las dos cosas.

### Requisitos en máquina destino

Uno solo: **Visual FoxPro 9 SP2 (build ≥ 3504)**. Autodetección en rutas típicas; override en Preferencias.
Si el build es menor a 3504 hay que correr `setup_bussinesRule.exe` (NAS `\192.168.0.16\Compilado_16` o SharePoint); está documentado en el LEEME.

---

## 3. Tareas completadas

### 3.1 Sesión inicial — MVP (commit `b635c32`)

| Ítem | Detalles |
|---|---|
| Estructura del repo | `src/fb2p_studio`, `vfp_bridge`, `build`, `tests`, `docs`, `pyproject.toml`, `.gitattributes` con `working-tree-encoding=windows-1252` para `.prg` |
| Driver VFP | `vfp_bridge/fb2p_bridge.prg` + `.fpw`. Object API + `TRY/CATCH TO loEx` + parser INI + saneo de `INTERACTIVE`/`SHOWMSG` |
| Core Python | `core/{bridge,ipc,job,discovery,settings,extensions}.py` |
| UI | `ui/{main_window,tab_convert,tab_about,dialog_preferences}.py` + `widgets/{path_picker,log_view,command_preview}.py` |
| Tests | 6 tests (parse eventos, serialización INI, mapping de extensiones) |
| PyInstaller spec | `build/fb2p_studio.spec` + `build/build.bat` |

**Trampas VFP cazadas en esta sesión:**

- `Name` reservado en `Custom` → renombrado a `sec_name` en `ini_section`.
- `get_Processed()` devuelve tokens `"P1"/"E0"/"S1"/"X1"`, no dígitos puros → tomar el último carácter.

### 3.2 Fix del `fb2pVersion` y bundle (commit `664c324`)

- Detección de versión FoxBin2Prg vía parseo del header `Version="X.YY"` de `foxbin2prg.pj2` (el `VERNO` pass-by-ref devolvía el path, no la versión).
- `RETURN` dentro de `TRY/CATCH` en VFP9 no propaga — refactorizado a variable de resultado.
- **FoxBin2Prg embebido** en `bundled/foxbin2prg/` (857 KB, 4 archivos).
- `discovery.find_fb2p_home()` cae al bundle si no hay override/env/rutas típicas.
- PyInstaller spec extiende `datas` para embeber el bundle.
- `bundled/update_bundle.bat` para actualizar el bundle desde un clon local.
- Atribución CC BY 4.0 en tab Acerca de y en `bundled/foxbin2prg/ATTRIBUTION.md`.

### 3.3 Fix del `-C` glued (commit `5189c25`)

- QProcess pasaba `["-T", "-C", path]` como argumentos separados. VFP tomaba `-C` como flag vacío y abría el `.fpw` en el editor, ejecutando su contenido como código y explotando en `Variable 'OFF' is not found`.
- Fix: pasar `["-T", f"-C{fpw_path}"]` — `-C` pegado al path como un solo argumento.
- Se manifestaba sólo en el `.exe` empaquetado; en dev había funcionado por coincidencia.

### 3.4 UI: preview auto-grow + tema (commit `585b40b`)

- `CommandPreview`: la altura se ajusta al contenido entre 4 y 20 líneas. Antes tenía `setMaximumHeight(180)` fijo y la sección `[op:op1]` quedaba scrolleada.
- Nuevo `ui/theme.py`:
  - Fuerza estilo Fusion (consistencia Windows).
  - Detecta dark mode con `QStyleHints.colorScheme()` (Qt 6.5+) y heurística de fallback.
  - Aplica paleta light/dark completa (Window, Base, Text, Button, Highlight, Disabled, PlaceholderText).
  - Expone `LogColors` semánticos (info/ok/warn/error/muted) tematizados.
- `LogView`, `ConvertTab`, `MainWindow` reciben los colores desde `app.py` por inyección.

### 3.5 Packaging (commit `d5fc744`)

- `release/_template/` con `LEEME.txt`, `LICENCIA.txt`, `CAMBIOS.txt` (fuente única, se copia a cada release).
- `build/package.bat` con flag `--zip`, versión leída desde `pyproject.toml` con `tomllib`.
- `.gitignore` excluye `release/FoxBin2Prg-Studio-*/` y `release/*.zip` (los generados).

### 3.6 LEEME en Markdown (commit `e69d600`)

- `release/_template/LEEME.md` con mismo contenido que `LEEME.txt`, formato Markdown (tablas, headers, code blocks).

### 3.7 Iteraciones posteriores (commit `9c6e095` + `915dc6b`)

Mejoras de UX de rutas, icono y prerequisito SP2:

| Área | Cambio | Archivos |
|---|---|---|
| **Icono propio** | `.ico` generado por código Python, referenciado por el spec, y regenerable con `build\make_icon.py`. El `build\build.bat` lo regenera si falta. | `build/make_icon.py`, `src/fb2p_studio/resources/fb2p_studio.ico`, `build/build.bat`, `build/fb2p_studio.spec`, `src/fb2p_studio/app.py` |
| **Preferencias** | Refactor: los campos muestran sólo el override guardado; lo autodetectado va como placeholder. Se guarda sólo si el usuario escribió algo — evita clavar rutas de una máquina en el `.ini` que después viaja. | `src/fb2p_studio/ui/dialog_preferences.py`, `src/fb2p_studio/ui/widgets/path_picker.py` (`set_placeholder`) |
| **Discovery** | Prioridad: override → env → **bundled → rutas típicas** (bundled sube por delante de rutas típicas). Overrides inexistentes se ignoran (no cortan la búsqueda). Nuevas API públicas: `bundled_fb2p_dir()`, `resources_dir()`, `app_icon_path()`. | `src/fb2p_studio/core/discovery.py` |
| **Tab Acerca de** | Marca si el FoxBin2Prg en uso es `(embebido en Studio)` o `(externo)`. | `src/fb2p_studio/ui/tab_about.py` |
| **Doc de pre-requisito VFP SP2** | Sección en `LEEME` (txt + md) y `CAMBIOS.txt` que explica cómo verificar el build (`? VERSION(4)`) y dónde bajar `setup_bussinesRule.exe`. | `release/_template/LEEME.txt`, `release/_template/LEEME.md`, `release/_template/CAMBIOS.txt` |
| **Test de discovery fallback** | Verifica el orden de resolución cuando falla el override. | `tests/test_discovery_fallback.py` |

### 3.8 Sesión DX / infraestructura (commit `915dc6b`)

Cierra toda la sección 4.3. Detalle y decisiones tomadas, en §4.3.

| Área | Cambio | Archivos |
|---|---|---|
| **Entorno de dev** | `pip install -e .[dev]` corrido (faltaban `ruff`, `pytest-qt` y el paquete en editable: `pytest` no encontraba `fb2p_studio` sin `PYTHONPATH`). | — |
| **Lint limpio** | 5 hallazgos de ruff arreglados (I001, SIM102, E741 ×2, F401). | `ui/tab_convert.py`, `ui/widgets/path_picker.py` |
| **Gate de calidad** | `check.bat` = ruff + pytest (+ `--build`, `--fix`). | `build/check.bat` |
| **CI** | Workflow de lint + tests + build + artifact. | `.github/workflows/ci.yml` |
| **Update check** | Manifiesto JSON en red, leído fuera del hilo de UI; aviso no intrusivo + opción «Buscar actualizaciones...» del menú lateral; configurable en Preferencias. | `core/updates.py`, `core/settings.py`, `ui/main_window.py`, `ui/dialog_preferences.py` |
| **MSI** | Instalador WiX 5 verificado. | `build/msi/fb2p_studio.wxs`, `build/msi.bat` |
| **i18n** | 85 cadenas en `self.tr()`, extracción/compilación, carga por locale, `.qm` bundleado en el spec. | todo `ui/`, `app.py`, `build/i18n.bat`, `build/fb2p_studio.spec` |
| **Tests** | Icono (estructura del `.ico`) y updates (versiones + manifiesto). **39 tests**, todos en verde. | `tests/test_icon.py`, `tests/test_updates.py` |

Commiteado en `9c6e095` (aplicación) y `915dc6b` (build + documentación).

### 3.9 Tab Proyecto (commit `9c6e095`)

Cierra el primer item de la seccion 4.1.

| Area | Cambio | Archivos |
|---|---|---|
| **Pestana Proyecto** | Convierte un `.pjx`/`.pj2` con todos sus archivos. Direccion mostrada (no elegible), checkbox incluir/excluir el archivo de proyecto, checkbox recompilar desde la carpeta del proyecto. | `ui/tab_project.py` |
| **Fix del driver** | `sanitize_ctype()` recortaba el guion final y convertia `*-` en `*`. | `vfp_bridge/fb2p_bridge.prg` |
| **Core** | `Direction` acepta `*` / `*-`; `OperationOptions.recompile_cwd` para el `cRecompile` con directorio; helpers `ext_of`, `is_project`, `project_ctype`. | `core/job.py`, `core/extensions.py` |
| **Refactor compartido** | El ciclo de vida del bridge + los handlers de eventos salieron a `JobRunner`; las opciones avanzadas, a un widget. Los usan las dos pestanas. | `ui/job_runner.py`, `ui/widgets/advanced_options.py`, `ui/tab_convert.py` |
| **Docs** | `ARCHITECTURE.md`: protocolo real (INI, no JSON), tabla de `cType`, `cRecompile` con carpeta, y correccion del `core.validators` inexistente. | `docs/ARCHITECTURE.md` |
| **Tests** | `test_project_mode.py` (19 casos). **58 tests** en verde. | `tests/test_project_mode.py` |

**Decisiones de diseno, con su porque:**

1. **La direccion no se ofrece como selector.** En modo proyecto FoxBin2Prg la deduce de la extension (`Left(tcType,1) == '*'` mas `Justext() == 'PJX'/'PJ2'`); un radio button BIN2PRG/PRG2BIN seria ignorado. La pestana muestra que va a pasar, en vez de mentir.
2. **`*-` es una trampa real.** El `sanitize_ctype()` del driver recortaba guiones sueltos (herencia del saneo de `INTERACTIVE`/`SHOWMSG`, que se separan con `-`) y convertia `*-` en `*`. O sea: "el proyecto sin el .pjx" habria procesado el .pjx igual, sin ningun aviso. Ahora el modo proyecto sale temprano de esa normalizacion, y hay tests que lo fijan en Python.
3. **`cRecompile` acepta un directorio.** `l_Recompile = (Empty(x) Or x == '1' Or Directory(x))`: pasarle una carpeta mantiene la recompilacion Y hace `CD` ahi antes. Para un proyecto es lo correcto — recompilar desde la carpeta de cada archivo rompe los `#include` relativos. Va como checkbox, activado por defecto.

**Verificacion end-to-end** (VFP9 09.00.0000.7423 + FoxBin2Prg 1.21 embebido, sobre una copia de `D:\FenixPro\Proyectos\Capacitacion`):

| Caso | Resultado |
|---|---|
| `.pjx` + `*` | rc=0. Genero `GridDetalle.pj2`, `forms/artdetalle.sc2`, `rptDetalle.fr2`, `data/articulo.db2`. |
| `.pjx` + `*-` | rc=0. Genero los mismos **menos** `GridDetalle.pj2`. |
| `.pj2` + `*` | rc=0. Regenero `GridDetalle.pjx/.pjt`, `artdetalle.scx/.sct`, `rptDetalle.frx/.frt`. |

### 3.10 Pre-flight del proyecto (commit `9c6e095`)

Resuelve el pendiente que habia quedado a la vista en 3.9: la pestana ahora sabe que contiene el proyecto **antes** de ejecutar.

| Area | Cambio | Archivos |
|---|---|---|
| **Lector de proyectos** | Lee los dos formatos: `.pjx` (DBF + nombres en el memo `.pjt`) y `.pj2` (texto, `.ADD(...)` dentro de `*<BuildProj>`). Replica como arma la lista FoxBin2Prg, incluido el cambio de extension a texto en la direccion PRG2BIN. | `core/project_reader.py` |
| **Pre-flight** | Las dos condiciones que FoxBin2Prg evalua en silencio: existe + tiene soporte en esa direccion. Con motivo cuando no convierte. Es el `core.validators` que el doc prometia desde el MVP. | `core/validators.py` |
| **Soporte por direccion** | `DEFAULT_SUPPORT` + `supports(path, direction)`. | `core/extensions.py` |
| **UI** | Pestanas "Contenido" / "job.ini". El arbol lista archivo, tipo y estado, con color por estado y el detalle en el tooltip. Resumen arriba. Confirmacion al ejecutar si falta algo, y los faltantes al log. | `ui/widgets/project_contents.py`, `ui/tab_project.py` |
| **Convertir** | Avisa antes de lanzar si la conversion no esta soportada en esa direccion. | `ui/tab_convert.py` |
| **Tests** | 44 casos nuevos. **102 tests** en verde. | `tests/test_project_reader.py`, `tests/test_project_mode.py` |

**El hallazgo de fondo:** el soporte de conversion **depende de la direccion**. `hasSupport_Bin2Prg()` pide `n_XXX_Conversion_Support > 0`, pero `hasSupport_Prg2Bin()` pide `= 2` (para DBF acepta `2` u `8`). Con los defaults de FoxBin2Prg:

| Extension | Soporte | Bin -> Prg | Prg -> Bin |
|---|---|---|---|
| PJX, VCX, SCX, FRX, LBX, MNX, DBC | 2 | si | si |
| **DBF, FKY, MEM** | **1** | si | **no** |

O sea: una tabla se vuelca a texto pero NO se reconstruye desde el (rearmarla pisaria los datos; se habilita a mano en el `.cfg`). Studio la daba por convertible en las dos direcciones, asi que en la pestana Convertir un `.db2` no hacia nada y no se sabia por que. Salio de comparar la prediccion contra la corrida real, no de leer el codigo.

**Verificacion:** un script contrasta lo que el pre-flight predice contra los `file_processed` de una corrida real de FoxBin2Prg. Coincide archivo por archivo en los cuatro escenarios: `.pjx`+`*` (4), `.pjx`+`*-` (3), `.pj2`+`*` (3, con el `.db2` salteado) y un proyecto con el reporte borrado (3, con el faltante detectado).

**Limite conocido, dicho en la UI:** no se leen los `foxbin2prg.cfg` del arbol (con su herencia), asi que el soporte se predice con los valores por defecto. Un `.cfg` que cambie `n_XXX_Conversion_Support` haria que la prediccion no coincida. La via exacta seria preguntarle al propio FoxBin2Prg (`hasSupport_*()` via el bridge, o un dry-run), a costa de lanzar VFP en cada seleccion de proyecto.

**Pendiente natural que sigue abierto:** el arbol de *resultados* (§4.1) — hoy el resultado de la corrida sigue saliendo como log lineal. La vista de contenido ya deja la mitad del camino hecho: mismas columnas, misma idea.

### 3.11 Tema ADS, árbol de resultados y toast — sin commitear (working tree actual)

Cierra la seccion 4.1 completa.

| Área | Cambio | Archivos |
|---|---|---|
| **Tema elegible** | Dos temas: **Sistema** (Fusion claro/oscuro, el de siempre y el de por defecto) y **ADS corporativo**, portado de `UtilitiesDevelopment/shell/theme.py`. Se elige en Preferencias y se aplica sin reiniciar. | `ui/theme.py`, `ui/theme_ads.py`, `ui/widgets/corporate_header.py`, `ui/dialog_preferences.py`, `core/settings.py` |
| **Contraste medido** | Los colores del log y del árbol se verifican contra su fondo en cada corrida (WCAG 2.1 AA). Portado de `tools/check_contrast.py`, pero como test. | `tests/test_theme_contrast.py` |
| **Árbol de resultados** | Operación → archivos, con Estado, Tiempo y Error; filtro *sólo lo que falló*; panel de detalle. El log queda en una pestaña al lado. | `ui/widgets/results_view.py`, `ui/job_runner.py`, las dos pestañas |
| **Toast** | Aviso flotante que se va solo, anclado abajo a la derecha. Lo usa el chequeo de actualización al arrancar. | `ui/widgets/toast.py` |
| **Tests** | 46 casos nuevos. **148 tests** en verde. | `tests/test_results_view.py`, `tests/test_theme_contrast.py` |

**El hallazgo de esta sesión:** el plan original decía "cuando `op_error` llega, abrir un panel con `Message`, `LineNo`, ...". Pero **la mayoría de los fallos de FoxBin2Prg no son excepciones VFP**. Corrompiendo un `.sc2` real y mirando qué llegaba: `execute()` devolvió `rc=1098`, no hubo `op_error`, y la explicación util viajó por **stderr**:

```
Error 1098, No se ha encontrado el marcador de fin [ENDDEFINE] de la línea 35 para el identificador [formset]
analyzecodeblock_define_class, 11239
```

Con el diseño del plan, el panel habría quedado vacío justo en el caso más común. Ahora `JobRunner` acumula stderr por operación y se lo pasa al árbol: la columna Error muestra la línea `Error NNNN,` y el panel, el volcado completo.

**Sobre el tema ADS:** la banda corporativa sólo aparece con ese tema; con el tema Sistema la ventana queda exactamente como estaba (sin banda y sin márgenes propios). El logo (`resources/ads_logo.png`) se copió de `UtilitiesDevelopment/fnxMd2Pdf/templates/`.

### 3.12 Layout en 1366x768 — sin commitear (working tree actual)

Reportado desde la maquina de un usuario: al maximizar en 1366x768 los textos y
controles se montaban, y al preview del `job.ini` no se le podia hacer scroll.

**La causa medida:** el minimo de la ventana era **1013 px de alto**, mas que la
pantalla. Cuando el minimo no entra, Qt aplasta los widgets por debajo de su
minimo y se dibujan unos sobre otros. Tres cosas lo inflaban:

| Culpable | Costaba | Por que |
|---|---|---|
| `CommandPreview` | 301 px | `setFixedHeight()` con el alto de 17 lineas de job.ini: no podia ceder ni mostrar scroll |
| `AdvancedOptions` | 209 px | un `QGroupBox` checkable sólo deshabilita a los hijos; seguian ocupando su lugar |
| `AboutTab` | 1318 px de **ancho** | las rutas en `QLabel` normales; una sola pedia 1040 px |

Minimo resultante: **766x520** (Sistema) y **840x674** (ADS). Verificado ademas
a 1024x600 y en el dialogo de Preferencias.

`tests/test_layout.py` (11 casos) mide **solapamientos reales** — dos hermanos
visibles cuyos rectangulos se intersectan — en las tres pestanas, los dos temas,
y con las opciones avanzadas abiertas y cerradas. No depende de mirar capturas.

**Trampa de Qt que aparecio armando esos tests:** `processEvents()` NO entrega
los eventos `DeferredDelete`, asi que las ventanas cerradas con `deleteLater()`
seguian vivas. Como `theme.apply()` reestila TODAS las ventanas vivas, cada test
costaba mas que el anterior (0,2 s el primero, 2,6 s el tercero; 69 s la suite).
Con `QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)` bajo a
10 s.

---

## 4. Tareas pendientes

### 4.1 Prioridad alta — funcionalidad core que faltó del MVP ✅ (cerrada)

- [x] **Tab Proyecto** — modos `*` y `*-` sobre `.pjx`/`.pj2`. Ver §3.9 para el detalle y las trampas encontradas.
- [x] **Panel de árbol de resultados** — `ui/widgets/results_view.py`. Cada operación es una fila con sus archivos colgando (Archivo · Dirección · Estado · Tiempo · Error), filtro *sólo lo que falló*, y el log queda en una pestaña al lado para diagnóstico crudo.
  - El tiempo va en la fila de la **operación**, no del archivo: FoxBin2Prg mide por operación (`op_done.elapsedMs`) y un tiempo por archivo sería inventado.
- [x] **Panel de detalle de error** — abajo del árbol, aparece al elegir una fila con problema y se esconde si no hay nada que mostrar.
  - **Corregido de paso un supuesto equivocado del plan original:** el detalle no podía salir sólo de `op_error`, porque *la mayoría de los errores no son excepciones*. Ante un `.sc2` mal formado, `execute()` devuelve `rc=1098` y manda la explicación legible a **stderr** (`Error 1098, No se ha encontrado el marcador de fin [ENDDEFINE] de la línea 35...`). El `JobRunner` ahora acumula stderr por operación y se lo pasa al árbol, así la columna Error trae el motivo y el panel el volcado completo. Descubierto corrompiendo un archivo real y mirando qué llegaba.

### 4.2 Prioridad media — funcionalidad adicional prevista

- [ ] **Tab Diff** — wrapper de `Fb2P_Diff.EXE`. Comparar dos versiones de un binario (o dos ramas del texto FoxBin2Prg) sin salir de Studio. El ejecutable está presente en el clon oficial de FoxBin2Prg (`Fb2P_Diff/Fb2P_Diff.EXE`, 20 KB); habría que bundlelearlo también.
- [ ] **Tab Config** — cubrir el *Usage 2* de FoxBin2Prg: templates `.cfg` (`-c` inactive defaults, `-C` con settings actuales del path) y templates `.dbf.cfg` (`-t`). Útil para diagnosticar por qué una conversión da distinto entre dos máquinas.
- [ ] **Multi-selección para batch** — hoy el tab Convertir toma un archivo por vez. Permitir seleccionar varios y encolarlos como operaciones múltiples en un mismo `job.ini` (el driver ya soporta N operaciones, sólo falta la UI para armarlas).
- [ ] **Recientes en menú Archivo** — ya persistidos por `Settings.push_recent()` pero no expuestos en la UI.
- [ ] **Persistir preferencias por extensión** — recordar la última dirección forzada por tipo de archivo (`.scx` → siempre BIN2PRG, etc.), mejora sutil pero apreciada por poweruser.

### 4.3 Prioridad baja — DX / infraestructura ✅ (cerrada, sin commitear)

- [x] **CI (GitHub Actions)** — `.github/workflows/ci.yml`: lint + tests + build del `.exe` como artifact, en `windows-latest`. **Queda inerte hasta que el repo tenga remoto** (hoy no hay ninguno: `git remote -v` vacío). Para un runner propio en el NAS, cambiar una línea (`runs-on: [self-hosted, windows]`). El blocker de "dónde correrlo" no se resolvió por definición sino por diseño: el workflow sirve igual en los dos escenarios.
  - Substrato: `build/check.bat` (ruff + pytest, `--build` y `--fix`). Es lo que ejecuta CI, y corre igual en local.
  - De paso: el repo tenía 5 hallazgos de ruff y el `.venv` no tenía instaladas las dependencias de dev. Ambas cosas arregladas — sin eso el gate no servía.
- [x] **Chequeo de actualización in-app** — `core/updates.py` + opción **Buscar actualizaciones...** del pie del menú lateral. Consulta los Releases del repo público `Fenix-Corp/Utilities-Dist` (o un manifiesto JSON, como override), fuera del hilo de la UI; el aviso ofrece **Descargar**. Al arrancar sólo deja un link en la barra de estado (sin modal); pedido a mano, contesta siempre. Sin auto-update, como estaba previsto.
  - El `.exe` lo sube `build_exe.bat` (paso 7) en cada versión nueva. Ver §4.5.
- [x] **Empaquetado MSI** — `build/msi/fb2p_studio.wxs` + `build/msi.bat`, verificado (se inspeccionó la base del MSI generado: producto, versión, 5 archivos, acceso directo, filas de upgrade).
  - **WiX fijado en la versión 5 a propósito:** de la 6 en adelante hay que aceptar la EULA del *Open Source Maintenance Fee*, que para uso comercial es paga. La 5 es libre y usa el mismo esquema.
- [x] **Localización** — las 85 cadenas de la UI pasaron a `self.tr(...)`; `build/i18n.bat` extrae y compila; `app.py` carga el `.qm` del locale del sistema. El idioma fuente sigue siendo el español: sin traducir nada, la app no cambia (verificado comparando las 79 cadenas que la UI muestra, antes y después: idénticas). El `.ts` de inglés está generado y sin traducir, listo para Qt Linguist.

### 4.5 Publicacion y remoto

**Decidido (2026-10-28):** las actualizaciones salen del repo publico
`Fenix-Corp/Utilities-Dist` (el canal de las Utilidades de Desarrollo), como
Releases `foxbin2prg-studio-vX.Y.Z` con el `.exe` adjunto. Reemplaza al
`latest.json` del NAS, que no habia que publicar a mano en cada version y nunca se
creo. El NAS y las URL https siguen aceptandose como override en Preferencias
(`updates/manifest` en el .ini, misma clave de siempre), y los links de Drive y
SharePoint se siguen convirtiendo a descarga directa (`normalize_source`).

- [x] **Publicacion desde el build.** `build_exe.bat` termina (paso 7) llamando a `build\publish.bat`, que crea el Release con `gh release create ... --latest=false` y sube el `.exe` y el `.zip`. `--latest=false` para no quitarle a las utilidades la marca *Latest* del repo.
  - **Solo versiones nuevas:** si el Release ya existe sale con codigo 2 y no sube nada (`--republish` / `--force` para reemplazar). Sin pruebas no hay publicacion (`--nocheck` implica `--nopublish`).
  - **Verificado** con un `gh` de mentira que registra los comandos: version nueva (create), ya existe (omitido, codigo 2), `--force` (upload `--clobber`), sin sesion (falla) y el recorrido completo de `build_exe.bat`. La subida real a GitHub **no se ejecuto desde la sesion**: es un repo publico del equipo y publicar es decision del usuario.
  - Lectura verificada contra GitHub real: mientras no haya un Release `foxbin2prg-studio-v*`, el chequeo contesta «el canal no tiene ninguna version publicada de FoxBin2Prg-Studio».
- **Canal compartido:** el launcher del cajon lista los 50 Releases mas recientes y filtra por `fnxUtilidades-v`; Studio lista 100 y filtra por `foxbin2prg-studio-v`. Si algun dia se acumulan muchos Releases de Studio, convendria que el launcher pagine.
- **Limite de la API:** 60 consultas/hora por IP sin token. Si molesta en una red compartida habria que agregar un token opcional (el launcher del cajon ya lo hace con `FNX_GH_TOKEN`); Studio hoy no lleva ninguno.

- [x] **Repositorio publicado** en <https://github.com/Fenix-Corp/FoxBin2Prg-Studio> (privado), con `master` y `dev`. El historial se reviso antes de subirlo y no tiene secretos; lo unico interno son la IP del NAS y el link de SharePoint, aceptables en un repo privado (si algun dia se hiciera publico, habria que sacarlos a configuracion). El `bundled/foxbin2prg/` es redistribuible (CC BY 4.0, con atribucion). Total versionado: 1,2 MB.

  CI dispara en push a `master` y `dev`, y en los PR hacia `master`. En un repo privado de cuenta Free hay 2.000 minutos/mes de Actions y los runners de Windows cuentan doble; esta corrida son ~4 minutos, asi que sobra.

---

## 5. Backlog / preguntas abiertas

Ideas que aparecieron pero no están priorizadas. Discutir cuando tenga sentido:

- **Modo headless / línea de comandos** para automatización (`FoxBin2Prg-Studio.exe --convert <path> --direction bin2prg`). Útil para hooks git de otros proyectos que hoy usan `resources/hooks/fb2p_convert.prg` — podrían llamar a Studio en lugar de mantener su propio driver.
- **Integración con Git** dentro del propio Studio: detectar que el archivo abierto está en un repo, mostrar el estado, agregar al commit. Riesgo: scope creep hacia "otro cliente Git".
- **Panel de configuración efectiva** del `foxbin2prg.cfg` para el directorio activo (`get_DirSettings(cDir)` del Object API), útil para diagnosticar comportamiento inesperado por herencia de configs.
- **Modo dry-run** de la GUI ya está en `l_ProcessFiles=.F.` — pero la UI no expone qué archivos SE PROCESARÍAN. Podría abrir un preview del árbol antes de ejecutar en real.
- **Estadísticas** de la sesión: cuántas conversiones, cuántas fallaron, tiempo promedio. Trivial de calcular a partir del stream de eventos.

---

## 6. Cómo interpretar este documento

- **✅** = completado y verificado
- **🚧** = en progreso (MVP entregado, hay más)
- **❌** = descartado explícitamente (no re-abrir sin motivo nuevo)
- **[ ]** = pendiente

**Este archivo se actualiza al cerrar cada sesión de trabajo** que agregue o cierre ítems. Si vas a hacer un cambio sustancial, actualizá esta lista para que la próxima sesión (o el próximo dev) tenga contexto sin tener que reconstruirlo del `git log`.

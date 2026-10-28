# FoxBin2Prg-Studio — Manual de usuario

**GUI de administración para FoxBin2Prg — utilitario genérico para proyectos Visual FoxPro 9.**

ADS Software · 2026

Este manual se puede leer dentro del propio Studio: menú lateral → **Ayuda → Manual** (o la tecla **F1**).

---

## Qué hace Studio

Los archivos binarios de Visual FoxPro (formularios `.scx`, librerías `.vcx`, proyectos `.pjx`, reportes `.frx`…) no se pueden comparar ni versionar bien en Git. **FoxBin2Prg** los convierte a texto (`.sc2`, `.vc2`, `.pj2`…) y de vuelta a binario.

**Studio** es la ventana que maneja FoxBin2Prg por ti: eliges el archivo o el proyecto, pulsas **Ejecutar** y ves en vivo qué se convirtió, cuánto tardó y por qué falló lo que falló. No necesitas escribir configuraciones ni usar la línea de comandos.

Hay dos formas de trabajar:

| Quiero… | Voy a… |
|---|---|
| Convertir **un archivo** o una carpeta | **Herramientas → Convertir** |
| Convertir **un proyecto entero** (`.pjx` / `.pj2`) con todos sus archivos | **Herramientas → Proyecto** |

---

## Requisitos

- **Windows 10 / 11 (64 bits).**
- **Visual FoxPro 9 SP2** (build ≥ 3504) instalado en la máquina — ver el *Pre-requisito* más abajo.

  Rutas típicas que Studio detecta solo:
  - `C:\Fenix\AdsFenix\Librerias\vfp9.exe`
  - `C:\Program Files (x86)\Microsoft Visual FoxPro 9\vfp9.exe`

  Si `vfp9.exe` está en otro lugar, indícalo en **Preferencias** (ver [Preferencias](#preferencias)).

Nada más hace falta. FoxBin2Prg (`FoxBin2Prg.EXE` + `filename_caps.exe` + `filename_caps.cfg`) ya viene **embebido** dentro del ejecutable: no hay que instalarlo ni copiar ninguna carpeta. La página *Acerca de* lo muestra como `(embebido en Studio)`.

Si prefieres usar otra copia de FoxBin2Prg, indica su carpeta en **Preferencias** (o en la variable de entorno `FB2P_HOME`); *Acerca de* la mostrará como `(externo)`.

---

## Pre-requisito: que VFP9 sea SP2 (build ≥ 3504)

FoxBin2Prg corre **dentro** de Visual FoxPro 9 y necesita el **Service Pack 2**. Con un build anterior las conversiones fallan.

**Cómo verificar el build.** En la ventana de comandos de VFP9:

```foxpro
? VERSION(4)      && 09.00.0000.3504 o superior = SP2
```

También aparece en el Log de Studio: la línea del inicio de la corrida trae la versión de VFP.

**Cómo actualizar.** Si el build es menor a 3504, ejecuta el instalador **`setup_bussinesRule.exe`**, que deja VFP9 en SP2. Está disponible en:

| Origen | Ubicación |
|---|---|
| NAS | `\\192.168.0.16\Compilado_16` |
| SharePoint | [SOPORTE_ADS](https://adssoftware.sharepoint.com/:f:/s/SOPORTE_ADS/IgDgpcrWtLgYQZsc32SzmgLRAVF8stWKYEFlzKkmYGi6FVw?e=sqfAVY) |

Terminada la instalación, vuelve a correr `? VERSION(4)` para confirmar el build.

---

## Instalación

1. Copia el `.exe` donde quieras (Escritorio, `C:\Tools\`, una carpeta de red; no importa).
2. Doble clic en `FoxBin2Prg-Studio.exe`.

No requiere instalador, no modifica el registro y no pide permisos de administrador. (Para equipos gestionados por IT existe también un `.msi`.)

Las preferencias de cada usuario se guardan en:

```
%APPDATA%\ADS Software\FoxBin2Prg-Studio.ini
```

---

## La ventana

Todo se alcanza desde el **menú lateral**, a la izquierda:

| Grupo | Opción | Para qué |
|---|---|---|
| **Herramientas** | Convertir | Convertir un archivo o carpeta |
| | Proyecto | Convertir un proyecto `.pjx` / `.pj2` completo |
| **Ayuda** | Manual | Este manual |
| | Acerca de | Qué `vfp9.exe` y qué FoxBin2Prg está usando Studio |
| **Preferencias** (pie) | Tema | Cambiar entre ADS corporativo, Claro y Oscuro |
| | Preferencias... | Rutas, origen de actualizaciones |
| | Buscar actualizaciones... | Consultar si hay una versión nueva |

- El botón **☰** de arriba **colapsa** el menú a solo íconos (el nombre aparece al pasar el ratón) y lo vuelve a expandir.
- Sobre cada página se ve dónde estás: *Grupo › Página*.
- La barra de estado, abajo, muestra mensajes breves y, a la derecha, un aviso cuando hay una versión nueva.

### Atajos de teclado

| Tecla | Acción |
|---|---|
| **Ctrl+Tab** / **Ctrl+RePág** | Página siguiente del menú |
| **Ctrl+Shift+Tab** / **Ctrl+AvPág** | Página anterior |
| **F1** | Abrir este manual |
| **Ctrl+F** | Buscar dentro del manual (cuando está abierto) |
| **Ctrl+Q** | Salir |

---

## Convertir un archivo

Para un binario suelto (un formulario, una librería, un reporte…) o su texto equivalente.

1. Ve a **Herramientas → Convertir**.
2. En **Archivo**, elige el archivo con el botón de examinar o **arrástralo** sobre el campo. Studio reconoce:

   | Binario | Texto | Qué es |
   |---|---|---|
   | `.scx` | `.sc2` | Formularios |
   | `.vcx` | `.vc2` | Librerías de clases |
   | `.frx` | `.fr2` | Reportes |
   | `.lbx` | `.lb2` | Etiquetas |
   | `.mnx` | `.mn2` | Menús |
   | `.pjx` | `.pj2` | Proyectos (para un proyecto completo, usa mejor la página *Proyecto*) |
   | `.dbc` | `.dc2` | Contenedores de base de datos |
   | `.dbf` | `.db2` | Tablas (solo a texto, ver *Solución de problemas*) |
   | `.fky` | `.fk2` | Macros de teclado (solo a texto) |
   | `.mem` | `.me2` | Variables guardadas (solo a texto) |

   Los archivos de memo (`.sct`, `.vct`, `.frt`…) no se eligen: viajan junto con su archivo principal.
3. En **Operación** deja **Auto (por extensión)**: Studio decide solo si hay que ir de binario a texto (**Bin → Prg**) o de texto a binario (**Prg → Bin**). Si necesitas forzarlo, elige una de las otras dos.
4. Pulsa **Ejecutar**.

Mientras corre, una **barra de progreso** muestra `n / N`, el porcentaje y el archivo en curso. **Cancelar** detiene la corrida; se aplica *entre operaciones*, es decir, la operación que ya está en marcha termina.

Al pie de la página hay un **preview del `job.ini`**: la configuración exacta que se le entrega a FoxBin2Prg. Es solo informativo, pero útil para entender qué va a pasar o para reportar un problema.

### Opciones avanzadas

Es un grupo **colapsable** (viene cerrado). Se marca para desplegarlo:

| Opción | Por defecto | Qué hace |
|---|---|---|
| **Limpiar timestamps** | Sí | Quita las marcas de fecha del texto generado. Evita diferencias falsas en el control de versiones. |
| **Limpiar UniqueID** | Sí | Ídem para los identificadores únicos. |
| **Recompilar tras generar binario** | Sí | Recompila el binario después de Prg → Bin. |
| **Solo simular (dry-run)** | No | Muestra qué archivos se procesarían **sin tocar el disco**. |
| **Backups (n .bak)** | 1 | Cuántos niveles de `.bak` crear antes de sobrescribir. `0` = sin respaldo (0 a 10). |
| **Debug** | 0 | `0` sin debug · `1` log por archivo · `2` log extendido. |

> **Consejo.** Antes de convertir algo importante por primera vez, marca **Solo simular** y revisa en *Resultados* qué se procesaría.

---

## Convertir un proyecto

Es el caso de uso habitual: un proyecto VFP rara vez se convierte archivo por archivo.

1. Ve a **Herramientas → Proyecto**.
2. En **Proyecto**, elige el `.pjx` (para pasar a texto) o el `.pj2` (para volver a binario). También se puede arrastrar.
3. La **Operación** **no se elige**: FoxBin2Prg la deduce de la extensión, y Studio te la muestra:
   - `.pjx` → **Bin → Prg**: el proyecto y sus archivos pasan a texto.
   - `.pj2` → **Prg → Bin**: el texto del proyecto vuelve a binario.
4. Revisa la pestaña **Contenido** (ver abajo) y pulsa **Ejecutar**.

Dos casillas controlan el lote:

| Casilla | Por defecto | Qué hace |
|---|---|---|
| **Incluir el propio archivo de proyecto en el lote** | Sí | Marcada procesa también el `.pjx`/`.pj2`. Desmarcada procesa **solo los archivos** del proyecto y lo deja intacto. |
| **Recompilar desde la carpeta del proyecto** | Sí | FoxBin2Prg recompila desde la carpeta de cada archivo, y eso rompe las rutas relativas (los `#include`, típicamente). Con esto se le pasa la carpeta del proyecto como base. |

Las **Opciones avanzadas** son las mismas de *Convertir*.

### La pestaña Contenido: saber antes de ejecutar

Apenas eliges el proyecto, Studio **lista todos sus archivos y dice qué va a pasar con cada uno**, antes de tocar nada. Arriba hay un resumen (`N archivo(s) a convertir`).

| Estado | Significado |
|---|---|
| **se convierte** | El archivo existe y FoxBin2Prg lo convierte en esa dirección. |
| **FALTA en disco** | El proyecto lo menciona, pero no está en la carpeta. Se saltea. |
| **no convertible** | FoxBin2Prg no convierte ese tipo en esa dirección (el motivo está en el tooltip). |

Además, junto al estado pueden aparecer las marcas **principal** (es el programa principal), **excluido** (excluido del build; no afecta a la conversión) y **otra unidad** (el archivo vive en otra unidad que el proyecto).

Si al pulsar **Ejecutar** falta algún archivo, Studio te lo avisa, lista cuáles son y **pide confirmación**; los faltantes también quedan anotados en el Log.

La otra pestaña, **job.ini**, es el preview de la configuración, igual que en *Convertir*.

---

## Leer los resultados

Debajo de cada página hay dos pestañas: **Resultados** y **Log**.

### Resultados

Es un árbol: cada **operación** es una fila y sus **archivos** cuelgan de ella.

| Columna | Qué muestra |
|---|---|
| **Archivo** | Ruta del archivo (completa en el tooltip). |
| **Dirección** | Bin → Prg o Prg → Bin. |
| **Estado** | `OK`, `con errores`, `no procesado` o `procesando...`. En la fila de la operación, `OK` o `rc=<código>`. |
| **Tiempo** | Cuánto tardó la **operación** (FoxBin2Prg mide por operación, no por archivo). |
| **Error** | El motivo, si lo hubo. |

- La casilla **Sólo lo que falló o no se procesó** oculta lo que salió bien, para ir directo a los problemas.
- Al elegir una fila con error, el panel de abajo muestra el **detalle completo**: la excepción o lo que FoxBin2Prg reportó. La mayoría de los errores no son excepciones: son una explicación legible (por ejemplo, un `.sc2` mal formado dice en qué línea falta el `ENDDEFINE`).
- La línea de resumen indica `N operación(es), M archivo(s) · K con error · tiempo total`.

### Log

El paso a paso en bruto, con colores: normal, **verde** (éxito), **ámbar** (aviso), **rojo** (error) y gris (informativo). Anota una línea `[n/N]` por archivo. Sirve para diagnóstico fino; al pedir ayuda, adjunta su contenido.

---

## Preferencias

**Preferencias → Preferencias...** (pie del menú lateral). Los campos de ruta muestran **solo lo que tú hayas fijado**; si los dejas **vacíos**, Studio autodetecta, y lo que encontró aparece en gris como sugerencia.

| Campo | Para qué |
|---|---|
| **Tema** | ADS corporativo, Claro u Oscuro. Se aplica al instante. |
| **vfp9.exe** | Ruta a `vfp9.exe` si no está en un lugar típico. |
| **FoxBin2Prg (carpeta)** | Solo si quieres usar otra copia en vez de la embebida. |
| **Origen de actualizaciones** | De dónde se consulta si hay una versión nueva (ver [Actualizaciones](#actualizaciones)). |
| **Buscar actualizaciones al arrancar** | Activa o desactiva el chequeo automático. |

Si más adelante una ruta fijada deja de existir (por ejemplo, un `.ini` copiado de otra máquina), Studio la ignora y vuelve a la autodetección: nunca se queda sin herramienta por una preferencia vieja.

---

## Temas

Hay tres, y se cambian sin reiniciar desde el menú **Tema** (pie del menú lateral) o desde Preferencias:

- **ADS corporativo** — la identidad de la casa: azul `#1F3A5E` y banda superior, igual que las demás utilidades del departamento. Siempre claro.
- **Claro** — neutros de la paleta Fénix, con selección en azul claro.
- **Oscuro** — para quien prefiere un fondo oscuro, aunque Windows esté en claro.

Mientras no elijas uno, Studio arranca en Claro u Oscuro según el modo de Windows.

---

## Actualizaciones

Al arrancar, Studio consulta si hay una versión más nueva y, si la hay, avisa con un **mensaje flotante** que se va solo y deja un enlace en la barra de estado. También puedes pedirlo cuando quieras con **Buscar actualizaciones...**: esa vez contesta siempre, incluso si no pudo consultar.

El aviso ofrece **Descargar**, que abre el enlace del `.exe` nuevo. **Studio solo avisa**: no descarga ni instala nada por sí mismo. Para actualizar, cierra Studio y reemplaza el `.exe` por el nuevo.

Las versiones se publican en el repositorio público de distribución `Fenix-Corp/Utilities-Dist`, que es el origen por defecto. Si trabajas en una máquina que no ve GitHub, en Preferencias puedes apuntar el origen a otro repositorio, a un manifiesto JSON en una carpeta de red o a una URL https.

> **Límite de GitHub.** Sin credenciales, GitHub permite unas 60 consultas por hora desde una misma red. Si una oficina entera sale por la misma IP, el chequeo manual avisará «GitHub limitó las consultas»; reintenta más tarde.

---

## Acerca de

Muestra con qué herramientas está trabajando Studio en este momento:

- **vfp9.exe** — la ruta detectada, o `<no encontrado>`.
- **FoxBin2Prg (home)** — la carpeta, marcada `(embebido en Studio)` o `(externo)`.
- **Bridge PRG** — el pequeño programa de VFP con el que Studio habla con FoxBin2Prg.

Es lo primero que conviene mirar cuando algo no funciona.

---

## Solución de problemas

| Síntoma | Causa probable | Qué hacer |
|---|---|---|
| *Acerca de* dice `vfp9.exe: <no encontrado>` | VFP9 no está en una ruta típica | Fija la ruta en **Preferencias → vfp9.exe**. |
| Las conversiones fallan todas | VFP9 anterior al SP2 | Verifica `? VERSION(4)`: debe ser ≥ 3504. Ver *Pre-requisito*. |
| Un archivo sale **no convertible** | FoxBin2Prg no lo convierte en esa dirección. Por ejemplo, una tabla (`.dbf`, y lo mismo `.fky` y `.mem`) se vuelca a texto, pero **no se reconstruye desde él**: rearmarla pisaría los datos | Es esperado; el motivo está en el tooltip del archivo. Si de verdad lo necesitas, se habilita a mano en el `foxbin2prg.cfg`. |
| Un archivo sale **FALTA en disco** | El proyecto lo menciona pero no está donde dice | Restaura el archivo o ignóralo: se saltea. |
| Errores de `#include` al recompilar | Rutas relativas al proyecto | En *Proyecto*, deja marcada **Recompilar desde la carpeta del proyecto**. |
| Un `.sc2` da error con número y línea | Texto mal formado (falta un `ENDDEFINE`, por ejemplo) | Abre la fila en *Resultados* y lee el detalle: dice la línea. |
| «Estás en la última versión» pero sabes que hay otra | El Release aún no se publicó, o el origen apunta a otro lado | Revisa **Preferencias → Origen de actualizaciones**. |
| «No se pudo verificar» al buscar actualizaciones | Sin red, o GitHub limitó las consultas | Reintenta más tarde, o cambia el origen. |

---

## Reportar problemas

Contacto: **desarrolloads@adsecuador.com**

Para que sea rápido, incluye: la **versión de Studio** (está en el título de la ventana), lo que muestra **Acerca de**, qué hiciste y el contenido del **Log**.

# FoxBin2Prg-Studio

**GUI de administración para FoxBin2Prg — utilitario genérico para proyectos Visual FoxPro 9.**

ADS Software · 2026

---

## Contenido del paquete

| Archivo | Rol |
|---|---|
| `FoxBin2Prg-Studio.exe` | Ejecutable autocontenido (~48 MB). Incluye Python + Qt + PySide6 + FoxBin2Prg embebido (v1.21, redistribuido bajo CC BY 4.0). |
| `LEEME.txt` / `LEEME.md` | Este archivo (dos formatos). |
| `LICENCIA.txt` | Términos de licencia y atribuciones. |
| `CAMBIOS.txt` | Historial de cambios. |

---

## Requisitos

- **Windows 10 / 11 (64 bits).**
- **Visual FoxPro 9 SP2** (build ≥ 3504) instalado en la máquina — ver el *Pre-requisito* de abajo.

  Rutas típicas que la GUI autodetecta:
  - `C:\Fenix\AdsFenix\Librerias\vfp9.exe`
  - `C:\Program Files (x86)\Microsoft Visual FoxPro 9\vfp9.exe`

  Si `vfp9.exe` está en otro lugar: **Herramientas → Preferencias**.

Nada más hace falta. FoxBin2Prg (`FoxBin2Prg.EXE` + `filename_caps.exe` + `filename_caps.cfg`) ya viene embebido dentro del ejecutable: **no hay que instalarlo ni copiar ninguna carpeta**. La pestaña *Acerca de* lo muestra como `(embebido en Studio)`.

Si en tu máquina preferís usar otra copia de FoxBin2Prg, indicá su carpeta en **Herramientas → Preferencias** (o en la variable de entorno `FB2P_HOME`); ahí *Acerca de* la mostrará como `(externo)`.

---

## Pre-requisito: que VFP9 sea SP2 (build ≥ 3504)

FoxBin2Prg corre **dentro** de Visual FoxPro 9 y necesita el **Service Pack 2**. Con un build anterior las conversiones fallan.

**Cómo verificar el build.** En la ventana de comandos de VFP9:

```foxpro
? VERSION(4)      && 09.00.0000.3504 o superior = SP2
```

También aparece en el log de Studio: la línea `job_start` trae el campo `vfpVersion`.

**Cómo actualizar.** Si el build es menor a 3504, ejecutar el instalador **`setup_bussinesRule.exe`**, que deja VFP9 en SP2. Está disponible en:

| Origen | Ubicación |
|---|---|
| NAS | `\\192.168.0.16\Compilado_16` |
| SharePoint | [SOPORTE_ADS](https://adssoftware.sharepoint.com/:f:/s/SOPORTE_ADS/IgDgpcrWtLgYQZsc32SzmgLRAVF8stWKYEFlzKkmYGi6FVw?e=sqfAVY) |

Terminada la instalación, volver a correr `? VERSION(4)` para confirmar el build.

---

## Instalación

1. Copiar el `.exe` donde quieran (Escritorio, `C:\Tools\`, carpeta de red, no importa).
2. Doble click en `FoxBin2Prg-Studio.exe`.

No requiere instalador. No modifica el registro. No pide permisos de administrador.

Las preferencias del usuario (rutas override, opciones por defecto) se guardan en:

```
%APPDATA%\ADS Software\FoxBin2Prg-Studio.ini
```

---

## Primer uso

1. Abrir `FoxBin2Prg-Studio.exe`.

2. Ir a la pestaña **Acerca de** para verificar que detectó `vfp9.exe`. Si dice `<no encontrado>`, ir a **Herramientas → Preferencias** y setear la ruta manualmente.

3. Ir a la pestaña **Convertir**.

4. Arrastrar sobre el campo *Archivo* cualquier binario VFP:

   - `.scx` / `.sct` (formularios)
   - `.vcx` / `.vct` (class libraries)
   - `.pjx` / `.pjt` (proyectos)
   - `.frx` / `.lbx` / `.mnx` / `.dbc` / `.dbf`

   O el archivo de texto equivalente (`.sc2` / `.vc2` / `.pj2` / etc.).

5. La operación (**Bin → Prg** o **Prg → Bin**) se detecta por la extensión. Se puede forzar con los radio buttons.

6. Click en **Ejecutar**. El log al pie muestra el progreso en vivo:

   ```
   job_start → op_start → file_processed → op_done → job_done
   ```

---

## Opciones avanzadas

Colapsables, por defecto ocultas:

| Opción | Recomendado | Notas |
|---|---|---|
| **Limpiar timestamps** | ON | Reduce diferencias falsas en control de versión. |
| **Limpiar UniqueID** | ON | Idem. |
| **Recompilar tras generar binario** | ON | Fuerza recompilación del binario tras Prg → Bin. |
| **Solo simular (dry-run)** | — | Muestra qué archivos se procesarían sin tocar disco. Usa `l_ProcessFiles=.F.` del Object API. |
| **Backups (n `.bak`)** | 1 | Cuántos niveles de `.bak` crear. `0` = sin backup. |
| **Debug** | 0 | `0` = sin log, `1` = log por archivo, `2` = extendido. |

---

## Reportar problemas

Contacto: **desarrolloads@adsecuador.com**

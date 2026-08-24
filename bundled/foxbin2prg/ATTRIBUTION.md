# FoxBin2Prg — redistribuido en FoxBin2Prg-Studio

Los archivos de esta carpeta pertenecen al proyecto **FoxBin2Prg**, mantenido por [Lutz Scheffler](https://github.com/lscheffler) y originalmente creado por [Fernando D. Bozzo](https://github.com/fdbozzo). Repositorio oficial: <https://github.com/fdbozzo/foxbin2prg>.

## Archivos incluidos

| Archivo | Tamaño | Rol |
|---|---|---|
| `FoxBin2Prg.EXE` | 799 KB | Programa autocontenido (contiene los `props_*.txt`) |
| `filename_caps.exe` | 30 KB | Capitalización de nombres de archivo |
| `filename_caps.cfg` | 1 KB | Config del anterior |
| `foxbin2prg.pj2` | 8 KB | Fuente FoxBin2Prg del proyecto (usada solo para detectar versión) |

## Licencia

FoxBin2Prg se distribuye bajo **Creative Commons Attribution 4.0 International (CC BY 4.0)**. Ver: <http://creativecommons.org/licenses/by/4.0/>.

FoxBin2Prg-Studio incluye estos archivos con atribución y sin modificación, cumpliendo con los términos de la licencia. La atribución también figura en la pestaña **Acerca de** de la GUI.

## Versión bundled

Ver `foxbin2prg.pj2` — cabecera `*< FOXBIN2PRG: Version="X.YY" ... />`.

## Actualizar el bundle

Para reemplazar con una versión más nueva:

```bat
bundled\update_bundle.bat D:\path\to\your\foxbin2prg
```

O manualmente, copiar los 4 archivos desde tu clon de FoxBin2Prg (previamente compilado con `DO ReCreate_FoxBin2Prg.prg` — o mejor, con `BUILD EXE`).

"""Version de FoxBin2Prg-Studio: leerla y subirla. Es el UNICO lugar que la toca.

Autor: AJACH
Fecha: 2026-10-28 16:40:37

La version vive en un solo sitio: `__version__` en `src/fb2p_studio/__init__.py`.
De ahi la lee la app (titulo de la ventana, chequeo de actualizaciones) y, por
`pyproject.toml` (`dynamic = ["version"]`), el paquete. Los .bat (build_exe,
package, msi, publish) la piden a este script en vez de duplicarla.

Como en UtilitiesDevelopment (`shell/version.py`), la version se sube A MANO, a
proposito: es la que compara el lanzador contra lo que cada maquina ya tiene
para decidir si baja el .exe nuevo, y una version nueva es una decision, no un
efecto secundario de compilar. `--bump` la sube cuando se pide expresamente.

Uso (desde la raiz del repo):

    python build\\version.py                  imprime la version (0.1.0)
    python build\\version.py --bump patch     0.1.0 -> 0.1.1
    python build\\version.py --bump minor     0.1.1 -> 0.2.0
    python build\\version.py --bump major     0.2.0 -> 1.0.0

Solo stdlib y ASCII: lo ejecutan los .bat antes de que exista nada mas.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

INIT = Path(__file__).resolve().parents[1] / "src" / "fb2p_studio" / "__init__.py"

#: `__version__ = "0.1.0"` — literal simple: es lo que setuptools lee por AST.
_RE = re.compile(r'^(__version__\s*=\s*)(["\'])(?P<v>\d+(?:\.\d+){1,3})\2', re.MULTILINE)


def read(path: Path = INIT) -> str:
    """La version actual. Lanza ValueError si el archivo no trae una valida."""
    m = _RE.search(path.read_text(encoding="utf-8"))
    if m is None:
        raise ValueError(f"no encuentro __version__ = \"X.Y.Z\" en {path}")
    return m.group("v")


def bump(version: str, kind: str) -> str:
    """`bump("0.1.9", "patch")` -> `"0.1.10"`. Siempre devuelve X.Y.Z."""
    partes = [int(p) for p in version.split(".")[:3]]
    while len(partes) < 3:
        partes.append(0)
    mayor, menor, parche = partes
    if kind == "major":
        return f"{mayor + 1}.0.0"
    if kind == "minor":
        return f"{mayor}.{menor + 1}.0"
    if kind == "patch":
        return f"{mayor}.{menor}.{parche + 1}"
    raise ValueError(f"tipo de subida desconocido: {kind!r} (major, minor o patch)")


def write(version: str, path: Path = INIT) -> None:
    """Reescribe `__version__` sin tocar el resto del archivo (ni su fin de linea)."""
    crudo = path.read_bytes().decode("utf-8")
    nuevo, n = _RE.subn(lambda m: f'{m.group(1)}{m.group(2)}{version}{m.group(2)}', crudo, count=1)
    if n != 1:
        raise ValueError(f"no encuentro __version__ en {path}")
    path.write_bytes(nuevo.encode("utf-8"))


def main(argv: list[str]) -> int:
    try:
        if argv[:1] == ["--bump"]:
            if len(argv) != 2:
                print("uso: version.py --bump major|minor|patch", file=sys.stderr)
                return 2
            anterior = read()
            nueva = bump(anterior, argv[1])
            write(nueva)
            print(f"{anterior} -> {nueva}", file=sys.stderr)
            print(nueva)
            return 0
        if argv:
            print("uso: version.py [--bump major|minor|patch]", file=sys.stderr)
            return 2
        print(read())
        return 0
    except (ValueError, OSError) as e:
        print(f"[version] {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

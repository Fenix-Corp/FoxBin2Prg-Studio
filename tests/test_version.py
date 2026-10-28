"""La version de Studio vive en un solo sitio y solo se sube a proposito.

Autor: AJACH
Fecha: 2026-10-28 16:40:37

`build/version.py` es quien la lee y la sube; `__version__` en
`src/fb2p_studio/__init__.py` es su unico origen. Antes habia dos copias a mano
(esa y `pyproject.toml`) que podian desfasarse sin que nada lo notara.
"""

from __future__ import annotations

import importlib.util
import tomllib
from pathlib import Path

import pytest

import fb2p_studio

RAIZ = Path(__file__).resolve().parents[1]


def _cargar():  # noqa: ANN202
    spec = importlib.util.spec_from_file_location("fb2p_build_version", RAIZ / "build" / "version.py")
    modulo = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(modulo)  # type: ignore[union-attr]
    return modulo


V = _cargar()


def test_la_version_leida_es_la_que_usa_la_app() -> None:
    assert V.read() == fb2p_studio.__version__


def test_pyproject_no_repite_la_version() -> None:
    """Una segunda copia es justo lo que se quito: la lee de __init__."""
    proyecto = tomllib.loads((RAIZ / "pyproject.toml").read_text(encoding="utf-8"))

    assert "version" not in proyecto["project"], "pyproject.toml volvio a declarar la version"
    assert "version" in proyecto["project"]["dynamic"]
    assert proyecto["tool"]["setuptools"]["dynamic"]["version"] == {"attr": "fb2p_studio.__version__"}


@pytest.mark.parametrize(
    ("version", "tipo", "esperada"),
    [
        ("0.1.0", "patch", "0.1.1"),
        ("0.1.9", "patch", "0.1.10"),  # por numeros, no por texto
        ("0.1.9", "minor", "0.2.0"),  # sube el menor y baja el parche a 0
        ("0.9.9", "major", "1.0.0"),
        ("0.2", "patch", "0.2.1"),  # X.Y se completa
    ],
)
def test_bump(version: str, tipo: str, esperada: str) -> None:
    assert V.bump(version, tipo) == esperada


def test_bump_con_un_tipo_desconocido() -> None:
    with pytest.raises(ValueError, match="desconocido"):
        V.bump("0.1.0", "mega")


def test_write_cambia_solo_la_version(tmp_path: Path) -> None:
    archivo = tmp_path / "__init__.py"
    original = '"""Docstring."""\r\n\r\n__version__ = "0.1.0"\r\n\r\nOTRA = "0.1.0"\r\n'
    archivo.write_bytes(original.encode("utf-8"))

    V.write("0.2.0", archivo)

    assert archivo.read_bytes().decode("utf-8") == original.replace('__version__ = "0.1.0"', '__version__ = "0.2.0"')
    assert V.read(archivo) == "0.2.0"


def test_read_de_un_archivo_sin_version(tmp_path: Path) -> None:
    archivo = tmp_path / "__init__.py"
    archivo.write_text("x = 1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="__version__"):
        V.read(archivo)


def test_subir_la_version_dos_veces_acumula(tmp_path: Path) -> None:
    archivo = tmp_path / "__init__.py"
    archivo.write_text('__version__ = "0.1.0"\n', encoding="utf-8")

    for _ in range(2):
        V.write(V.bump(V.read(archivo), "patch"), archivo)

    assert V.read(archivo) == "0.1.2"


def test_el_cli_imprime_la_version(capsys: pytest.CaptureFixture[str]) -> None:
    assert V.main([]) == 0
    assert capsys.readouterr().out.strip() == fb2p_studio.__version__


@pytest.mark.parametrize("argv", [["--bump"], ["--bump", "patch", "extra"], ["--nope"]])
def test_el_cli_rechaza_argumentos_invalidos(argv: list[str]) -> None:
    assert V.main(argv) == 2


@pytest.mark.parametrize("bat", ["build_exe.bat", "build/package.bat", "build/msi.bat", "build/publish.bat"])
def test_ningun_bat_lee_la_version_de_pyproject(bat: str) -> None:
    """Todos le piden la version a build/version.py; ninguno la lee de pyproject.toml
    (ahi ya no esta)."""
    texto = (RAIZ / bat).read_text(encoding="ascii", errors="replace")
    assert "tomllib" not in texto, f"{bat} sigue leyendo la version de pyproject.toml"
    assert "version.py" in texto, f"{bat} no usa build/version.py"

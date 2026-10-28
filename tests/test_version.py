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


# ------------------------------------------------------------------- --ask
class _Consola:
    """Un stdin que dice ser (o no) una consola real."""

    def __init__(self, interactiva: bool) -> None:
        self._interactiva = interactiva

    def isatty(self) -> bool:
        return self._interactiva


@pytest.fixture
def init(tmp_path: Path) -> Path:
    archivo = tmp_path / "__init__.py"
    archivo.write_text('__version__ = "0.1.0"\n', encoding="utf-8")
    return archivo


def _responder(monkeypatch: pytest.MonkeyPatch, respuesta: str | None) -> list[str]:
    """Simula una consola; `respuesta=None` es un Ctrl+Z/EOF. Devuelve lo preguntado."""
    preguntas: list[str] = []

    def input_falso(pregunta: str = "") -> str:
        preguntas.append(pregunta)
        if respuesta is None:
            raise EOFError
        return respuesta

    monkeypatch.setattr("sys.stdin", _Consola(True))
    monkeypatch.setattr("builtins.input", input_falso)
    return preguntas


def test_ask_sin_consola_no_pregunta_ni_sube_nada(
    init: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Un build automatico (stdin redirigido o cerrado) jamas cambia la version solo."""
    llamadas: list[str] = []
    monkeypatch.setattr("builtins.input", lambda *_: llamadas.append("pregunto") or "")

    for stdin in (_Consola(False), None):
        monkeypatch.setattr("sys.stdin", stdin)
        assert V.ask(init) is None

    assert llamadas == [], "pregunto sin una consola real"
    assert V.read(init) == "0.1.0"


@pytest.mark.parametrize(
    ("respuesta", "esperada"),
    [
        ("", "0.1.1"),  # Enter = patch
        ("p", "0.1.1"),
        ("  P  ", "0.1.1"),
        ("m", "0.2.0"),
        ("M", "0.2.0"),
        ("j", "1.0.0"),
    ],
)
def test_ask_sube_segun_la_respuesta(
    init: Path, monkeypatch: pytest.MonkeyPatch, respuesta: str, esperada: str
) -> None:
    preguntas = _responder(monkeypatch, respuesta)

    assert V.ask(init) == esperada
    assert V.read(init) == esperada
    assert len(preguntas) == 1
    assert "0.1.1" in preguntas[0], "la pregunta tiene que mostrar a que version se subiria"


@pytest.mark.parametrize("respuesta", ["n", "N", "no", "x", "patch", "1", None])
def test_ask_ante_la_duda_deja_la_version(
    init: Path, monkeypatch: pytest.MonkeyPatch, respuesta: str | None
) -> None:
    """N, una respuesta que no se entiende o un Ctrl+Z: no se publica una version nueva."""
    _responder(monkeypatch, respuesta)

    assert V.ask(init) is None
    assert V.read(init) == "0.1.0"


def test_el_cli_ask_no_falla_sin_consola(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.stdin", _Consola(False))
    assert V.main(["--ask"]) == 0


def test_build_exe_pregunta_solo_cuando_corresponde() -> None:
    """La pregunta se salta con --bump, --nobump, --nopause o sin publicacion."""
    bat = (RAIZ / "build_exe.bat").read_text(encoding="ascii")

    assert 'version.py --ask' in bat
    antes = bat[: bat.index("version.py --ask")]
    for salto in (
        'if defined BUMP goto ask_done',
        'if "%NOBUMP%"=="1" goto ask_done',
        'if "%NOPAUSE%"=="1" goto ask_done',
        'if "%DOPUBLISH%"=="0" goto ask_done',
    ):
        assert salto in antes, f"build_exe.bat ya no se salta la pregunta con: {salto}"
    assert 'if /i "%~1"=="--nobump"' in bat, "build_exe.bat no reconoce --nobump"


def test_el_script_de_version_es_ascii() -> None:
    """Lo ejecutan los .bat en una consola donde los acentos se corrompen."""
    assert (RAIZ / "build" / "version.py").read_text(encoding="utf-8").isascii()

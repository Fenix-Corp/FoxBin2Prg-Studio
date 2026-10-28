"""El lanzador: decide si bajar la ultima version de Studio y la ejecuta.

Autor: AJACH
Fecha: 2026-10-28 16:40:37

`launcher/launcher.py` es un script suelto (se compila aparte, solo con stdlib),
asi que se carga por ruta. La logica pura y la orquestacion se prueban sin red:
la red y el disco se sustituyen por dobles.

Es el codigo mas importante de probar: el equipo lo tiene anclado en un acceso
directo y un lanzador roto no se puede arreglar a distancia.
"""

from __future__ import annotations

import importlib.util
import io
import json
import re
import urllib.error
from pathlib import Path

import pytest

from fb2p_studio.core import updates

RAIZ = Path(__file__).resolve().parents[1]
RUTA = RAIZ / "launcher" / "launcher.py"


def _cargar():  # noqa: ANN202
    spec = importlib.util.spec_from_file_location("fb2p_launcher", RUTA)
    modulo = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(modulo)  # type: ignore[union-attr]
    return modulo


L = _cargar()
TAG = L.TAG_PREFIX  # abreviatura: TAG + "0.2.0" es una etiqueta de Studio


# ----------------------------------------------------------- versiones y tags
@pytest.mark.parametrize(
    ("etiqueta", "esperado"),
    [
        (TAG + "0.1.0", (0, 1, 0)),
        (TAG + "1.2.10", (1, 2, 10)),
        (TAG + "0.2", (0, 2)),
        (TAG + "0.2.0-beta", (0, 2, 0)),
        ("v1.0", (1, 0)),
        (TAG + "nada", ()),
        ("", ()),
    ],
)
def test_parse_version(etiqueta: str, esperado: tuple[int, ...]) -> None:
    assert L.parse_version(etiqueta) == esperado


@pytest.mark.parametrize(
    ("remota", "local", "es_nueva"),
    [
        (TAG + "0.2.0", TAG + "0.1.0", True),
        (TAG + "0.10.0", TAG + "0.9.0", True),  # por numeros, no por texto
        (TAG + "0.1.0", TAG + "0.1.0", False),
        (TAG + "0.1.0", TAG + "0.2.0", False),
        (TAG + "0.2", TAG + "0.2.0", False),  # 0.2 == 0.2.0
        (TAG + "nada", TAG + "0.1.0", False),  # ilegible: nunca baja de mas
    ],
)
def test_is_newer(remota: str, local: str, es_nueva: bool) -> None:
    assert L.is_newer(remota, local) is es_nueva


def test_pick_latest_ignora_las_etiquetas_de_otras_utilidades() -> None:
    """El canal es compartido: fnxUtilidades-v9.9.9 no es una version de Studio."""
    etiquetas = ["fnxUtilidades-v9.9.9", TAG + "0.1.0", TAG + "0.3.0", TAG + "0.2.0", "otra-v5"]
    assert L.pick_latest_tag(etiquetas) == TAG + "0.3.0"


def test_pick_latest_sin_candidatas() -> None:
    assert L.pick_latest_tag([]) is None
    assert L.pick_latest_tag(["fnxUtilidades-v1.1.1"]) is None


def test_tags_ignoran_borradores_y_prereleases() -> None:
    crudo = json.dumps(
        [
            {"tag_name": TAG + "0.3.0", "draft": True},
            {"tag_name": TAG + "0.2.0", "prerelease": True},
            {"tag_name": TAG + "0.1.0"},
        ]
    )
    assert L.tags_from_releases_json(crudo) == [TAG + "0.1.0"]


@pytest.mark.parametrize("crudo", ["no soy json", '{"message": "Not Found"}', "", "null"])
def test_tags_de_una_respuesta_inservible(crudo: str) -> None:
    assert L.tags_from_releases_json(crudo) == []


def test_asset_url() -> None:
    crudo = json.dumps(
        {
            "assets": [
                {"name": "FoxBin2Prg-Studio-0.2.0.zip", "browser_download_url": "https://x/zip"},
                {"name": L.ASSET_NAME, "browser_download_url": "https://x/exe"},
            ]
        }
    )
    assert L.asset_url_from_release_json(crudo) == "https://x/exe"
    assert L.asset_url_from_release_json('{"assets": []}') is None
    assert L.asset_url_from_release_json("no json") is None


@pytest.mark.parametrize(
    ("remota", "instalada", "hay_exe", "baja"),
    [
        (TAG + "0.2.0", None, True, True),  # sin marca: no se sabe que hay
        (TAG + "0.2.0", TAG + "0.1.0", False, True),  # la marca existe pero falta el .exe
        (TAG + "0.2.0", TAG + "0.1.0", True, True),  # hay version nueva
        (TAG + "0.2.0", TAG + "0.2.0", True, False),  # al dia
        (TAG + "0.1.0", TAG + "0.2.0", True, False),  # la local es mas nueva: no retrocede
    ],
)
def test_needs_download(remota: str, instalada: str | None, hay_exe: bool, baja: bool) -> None:
    assert L.needs_download(remota, instalada, hay_exe) is baja


# ------------------------------------------------------------- orquestacion
class _Dobles:
    """Doble de red para `ensure_current`: registra las bajadas."""

    def __init__(self, ultima: str | None, *, descarga_ok: bool = True, crea_exe: bool = True) -> None:
        self.ultima = ultima
        self.descarga_ok = descarga_ok
        self.crea_exe = crea_exe
        self.bajadas: list[str] = []

    def latest(self) -> str | None:
        return self.ultima

    def download(self, tag: str, carpeta: Path) -> bool:
        self.bajadas.append(tag)
        if self.descarga_ok and self.crea_exe:
            (carpeta / L.ASSET_NAME).write_bytes(b"EXE " + tag.encode())
        return self.descarga_ok


def _asegurar(carpeta: Path, dobles: _Dobles) -> Path | None:
    return L.ensure_current(carpeta, dobles.latest, dobles.download, say=lambda _m: None)


def test_primera_vez_baja_y_deja_la_marca(tmp_path: Path) -> None:
    d = _Dobles(TAG + "0.1.0")
    exe = _asegurar(tmp_path, d)

    assert exe == tmp_path / L.ASSET_NAME
    assert d.bajadas == [TAG + "0.1.0"]
    assert L.read_marker(tmp_path) == TAG + "0.1.0"


def test_al_dia_no_baja_nada(tmp_path: Path) -> None:
    (tmp_path / L.ASSET_NAME).write_bytes(b"EXE")
    L.write_marker(tmp_path, TAG + "0.1.0")
    d = _Dobles(TAG + "0.1.0")

    assert _asegurar(tmp_path, d) == tmp_path / L.ASSET_NAME
    assert d.bajadas == []


def test_una_version_nueva_reemplaza_y_actualiza_la_marca(tmp_path: Path) -> None:
    (tmp_path / L.ASSET_NAME).write_bytes(b"EXE viejo")
    L.write_marker(tmp_path, TAG + "0.1.0")
    d = _Dobles(TAG + "0.2.0")

    _asegurar(tmp_path, d)

    assert d.bajadas == [TAG + "0.2.0"]
    assert (tmp_path / L.ASSET_NAME).read_bytes().endswith(b"0.2.0")
    assert L.read_marker(tmp_path) == TAG + "0.2.0"


def test_sin_red_abre_la_copia_local(tmp_path: Path) -> None:
    (tmp_path / L.ASSET_NAME).write_bytes(b"EXE")
    L.write_marker(tmp_path, TAG + "0.1.0")
    d = _Dobles(None)  # la API no contesto

    assert _asegurar(tmp_path, d) == tmp_path / L.ASSET_NAME
    assert d.bajadas == []
    assert L.read_marker(tmp_path) == TAG + "0.1.0"


def test_sin_red_y_sin_copia_devuelve_none(tmp_path: Path) -> None:
    assert _asegurar(tmp_path, _Dobles(None)) is None


def test_una_descarga_fallida_no_toca_la_copia_buena(tmp_path: Path) -> None:
    """Mejor correr algo viejo que nada: ni se borra el .exe ni se mueve la marca."""
    (tmp_path / L.ASSET_NAME).write_bytes(b"EXE bueno")
    L.write_marker(tmp_path, TAG + "0.1.0")
    d = _Dobles(TAG + "0.2.0", descarga_ok=False)

    exe = _asegurar(tmp_path, d)

    assert exe == tmp_path / L.ASSET_NAME
    assert exe.read_bytes() == b"EXE bueno"
    assert L.read_marker(tmp_path) == TAG + "0.1.0"


def test_una_descarga_fallida_sin_copia_devuelve_none(tmp_path: Path) -> None:
    assert _asegurar(tmp_path, _Dobles(TAG + "0.1.0", descarga_ok=False)) is None


def test_si_la_descarga_dice_ok_pero_no_hay_exe_no_deja_marca(tmp_path: Path) -> None:
    d = _Dobles(TAG + "0.1.0", descarga_ok=True, crea_exe=False)
    assert _asegurar(tmp_path, d) is None
    assert L.read_marker(tmp_path) is None


# --------------------------------------------------- descarga real (red falsa)
class _Respuesta(io.BytesIO):
    """Lo minimo de lo que devuelve urlopen: lectura, cabeceras y `with`."""

    def __init__(self, datos: bytes, *, corta_en: int | None = None) -> None:
        super().__init__(datos)
        self.headers = {"Content-Length": str(len(datos))}
        self._corta_en = corta_en

    def read(self, n: int = -1) -> bytes:
        if self._corta_en is not None and self.tell() >= self._corta_en:
            raise OSError("se corto la conexion")
        return super().read(n)


def _red_falsa(monkeypatch: pytest.MonkeyPatch, *, exe: bytes, corta_en: int | None = None) -> None:
    release = json.dumps({"assets": [{"name": L.ASSET_NAME, "browser_download_url": "https://x/exe"}]})

    def urlopen(peticion, timeout=None):  # noqa: ANN001, ANN202
        url = peticion.full_url
        if url.endswith("/releases/tags/" + TAG + "0.2.0"):
            return _Respuesta(release.encode())
        if url == "https://x/exe":
            return _Respuesta(exe, corta_en=corta_en)
        raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)  # type: ignore[arg-type]

    monkeypatch.setattr(L.urllib.request, "urlopen", urlopen)


def test_download_escribe_el_exe_y_no_deja_el_temporal(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _red_falsa(monkeypatch, exe=b"MZ" + b"x" * 1000)

    assert L.download_api(TAG + "0.2.0", tmp_path, say=lambda _m: None) is True

    assert (tmp_path / L.ASSET_NAME).read_bytes().startswith(b"MZ")
    assert not (tmp_path / (L.ASSET_NAME + ".part")).exists()


def test_una_descarga_cortada_a_la_mitad_no_reemplaza_la_copia_buena(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / L.ASSET_NAME).write_bytes(b"EXE bueno")
    _red_falsa(monkeypatch, exe=b"x" * 1_000_000, corta_en=300_000)

    assert L.download_api(TAG + "0.2.0", tmp_path, say=lambda _m: None) is False

    assert (tmp_path / L.ASSET_NAME).read_bytes() == b"EXE bueno"


def test_un_release_que_no_existe_da_false(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _red_falsa(monkeypatch, exe=b"x")
    assert L.download_api(TAG + "9.9.9", tmp_path, say=lambda _m: None) is False


# ----------------------------------------------------------- carpeta y log
def test_la_carpeta_se_puede_redefinir_por_entorno(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    destino = tmp_path / "otra" / "carpeta"
    monkeypatch.setenv(L.ENV_INSTALL_DIR, str(destino))

    assert L.cache_dir() == destino
    assert destino.is_dir()


def test_la_carpeta_por_defecto_es_unica_por_maquina() -> None:
    """Sin override es una ruta fija, no una por usuario (RDP): nada de %LOCALAPPDATA%."""
    assert L.DEFAULT_INSTALL_DIR.upper().startswith("C:\\")
    assert "appdata" not in L.DEFAULT_INSTALL_DIR.lower()


def test_el_log_anota_con_fecha_y_se_reinicia_si_crece(tmp_path: Path) -> None:
    say = L.make_say(tmp_path)
    say("hola")
    linea = (tmp_path / L.LOG_NAME).read_text(encoding="utf-8")
    assert re.match(r"\d{4}-\d\d-\d\d \d\d:\d\d:\d\d  hola\n", linea)

    (tmp_path / L.LOG_NAME).write_bytes(b"x" * (L.LOG_MAX_BYTES + 1))
    L.make_say(tmp_path)("nuevo")
    assert "x" * 50 not in (tmp_path / L.LOG_NAME).read_text(encoding="utf-8")


# ------------------------------------------------------------------- main
@pytest.fixture
def entorno(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv(L.ENV_INSTALL_DIR, str(tmp_path))
    monkeypatch.delenv("FNX_GH_TOKEN", raising=False)
    return tmp_path


def test_main_baja_y_ejecuta(entorno: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    lanzados: list[Path] = []
    monkeypatch.setattr(L, "latest_tag_api", lambda token=None, say=print: TAG + "0.1.0")
    monkeypatch.setattr(
        L,
        "download_api",
        lambda tag, carpeta, token=None, say=print: (carpeta / L.ASSET_NAME).write_bytes(b"EXE") and True,
    )
    monkeypatch.setattr(L, "launch", lanzados.append)

    assert L.main() == 0
    assert lanzados == [entorno / L.ASSET_NAME]
    assert L.read_marker(entorno) == TAG + "0.1.0"


def test_main_sin_red_y_sin_copia_falla_con_codigo_1(entorno: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    lanzados: list[Path] = []
    monkeypatch.setattr(L, "latest_tag_api", lambda token=None, say=print: None)
    monkeypatch.setattr(L, "launch", lanzados.append)

    assert L.main() == 1
    assert lanzados == []
    assert "no se pudo bajar" in (entorno / L.LOG_NAME).read_text(encoding="utf-8")


def test_main_un_error_inesperado_queda_en_el_log(entorno: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def roto(token=None, say=print):  # noqa: ANN001, ANN202
        raise RuntimeError("explotó")

    monkeypatch.setattr(L, "latest_tag_api", roto)

    assert L.main() == 1
    assert "explotó" in (entorno / L.LOG_NAME).read_text(encoding="utf-8")


# --------------------------------------------------- guardas contra desfases
def test_el_lanzador_y_la_app_hablan_del_mismo_canal() -> None:
    """Si cambia la etiqueta, el asset o el repo en un lado y no en el otro, el
    lanzador dejaria de ver los Releases que publica el build."""
    assert L.TAG_PREFIX == updates.TAG_PREFIX
    assert L.ASSET_NAME == updates.ASSET_NAME
    assert updates.parse_github_repo(updates.DEFAULT_SOURCE) == tuple(L.REPO.split("/"))


def test_publish_bat_publica_con_lo_que_el_lanzador_espera() -> None:
    publish = (RAIZ / "build" / "publish.bat").read_text(encoding="ascii")
    assert f'set "PREFIX={L.TAG_PREFIX}"' in publish
    assert f'set "REPO={L.REPO}"' in publish
    assert L.ASSET_NAME in publish


def test_el_nombre_del_lanzador_coincide_entre_el_bat_y_quien_lo_reparte() -> None:
    nombre = "FoxBin2Prg-Studio-Launcher"
    assert f"--name {nombre}" in (RAIZ / "build" / "launcher.bat").read_text(encoding="ascii")
    assert f"{nombre}.exe" in (RAIZ / "build" / "publish.bat").read_text(encoding="ascii")
    assert f"{nombre}.exe" in (RAIZ / "build" / "package.bat").read_text(encoding="utf-8")


def test_el_lanzador_es_ascii_y_solo_usa_la_biblioteca_estandar() -> None:
    """Su consola corrompe los acentos, y con Qt dejaria de ser un .exe diminuto."""
    fuente = RUTA.read_text(encoding="utf-8")
    assert fuente.isascii(), "launcher.py tiene caracteres no ASCII"
    importados = set(re.findall(r"^\s*(?:from|import)\s+([a-zA-Z_][\w]*)", fuente, re.MULTILINE))
    ajenos = importados - {
        "__future__", "contextlib", "datetime", "json", "os", "re", "subprocess", "sys",
        "urllib", "collections", "pathlib", "traceback",
    }  # fmt: skip
    assert not ajenos, f"launcher.py importa de fuera de la biblioteca estandar: {ajenos}"


def test_una_consola_que_no_puede_mostrar_acentos_no_tumba_al_lanzador(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Windows en espanol devuelve errores con acentos; una consola con otra pagina de
    codigos lanza UnicodeEncodeError al imprimirlos."""
    reales = print

    def print_ascii(texto: str = "", *a: object, **k: object) -> None:
        texto.encode("ascii")  # lanza UnicodeEncodeError como una consola cp437 con otros caracteres
        reales(texto)

    monkeypatch.setattr("builtins.print", print_ascii)
    say = L.make_say(tmp_path)

    say("No se pudo establecer una conexión")  # no debe lanzar

    assert "conexión" in (tmp_path / L.LOG_NAME).read_text(encoding="utf-8"), "el log UTF-8 lo conserva"
    assert "conexi?n" in capsys.readouterr().out

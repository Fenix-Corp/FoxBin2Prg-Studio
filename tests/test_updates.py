"""Comparacion de versiones y lectura del manifiesto de actualizaciones."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from fb2p_studio.core import updates
from fb2p_studio.core.updates import (
    ASSET_NAME,
    DEFAULT_SOURCE,
    TAG_PREFIX,
    UpdateInfo,
    is_newer,
    is_url,
    normalize_source,
    parse_github_repo,
    parse_manifest,
    parse_releases,
    parse_version,
    read_manifest,
)


@pytest.mark.parametrize(
    ("crudo", "esperado"),
    [
        ("0.1.0", (0, 1, 0)),
        ("1.2.30", (1, 2, 30)),
        ("0.2", (0, 2)),
        ("  0.1.0  ", (0, 1, 0)),
        ("0.2.0-beta", (0, 2, 0)),  # corta en el tramo no numerico
        ("v1.0", ()),  # 'v1' no es numero: no arranca
        ("", ()),
    ],
)
def test_parse_version(crudo: str, esperado: tuple[int, ...]) -> None:
    assert parse_version(crudo) == esperado


@pytest.mark.parametrize(
    ("remota", "local", "es_nueva"),
    [
        ("0.2.0", "0.1.0", True),
        ("0.1.1", "0.1.0", True),
        ("1.0.0", "0.9.9", True),
        ("0.1.0", "0.1.0", False),
        ("0.1.0", "0.2.0", False),
        ("0.2", "0.2.0", False),  # 0.2 == 0.2.0
        ("0.2.1", "0.2", True),
        ("nada", "0.1.0", False),  # ilegible: nunca avisa de mas
    ],
)
def test_is_newer(remota: str, local: str, es_nueva: bool) -> None:
    assert is_newer(remota, local) is es_nueva


def test_parse_manifest_completo() -> None:
    info = parse_manifest(
        json.dumps({"version": "0.2.0", "paquete": r"\\nas\x\y.zip", "notas": "Tab Proyecto."})
    )
    assert info == UpdateInfo(version="0.2.0", package=r"\\nas\x\y.zip", notes="Tab Proyecto.")


def test_parse_manifest_minimo() -> None:
    """Sólo 'version' es obligatorio."""
    info = parse_manifest('{"version": "0.3.0"}')
    assert info.version == "0.3.0"
    assert info.package == ""
    assert info.notes == ""


def test_parse_manifest_acepta_claves_en_ingles() -> None:
    info = parse_manifest('{"version": "0.3.0", "package": "p.zip", "notes": "n"}')
    assert (info.package, info.notes) == ("p.zip", "n")


@pytest.mark.parametrize(
    "crudo",
    [
        "no soy json",
        "[1, 2, 3]",  # tiene que ser un objeto
        '{"paquete": "x.zip"}',  # sin version
        '{"version": "   "}',
    ],
)
def test_manifiesto_invalido(crudo: str) -> None:
    with pytest.raises(ValueError):
        parse_manifest(crudo)


def test_read_manifest_desde_disco(tmp_path: Path) -> None:
    manifiesto = tmp_path / "latest.json"
    manifiesto.write_text('{"version": "9.9.9"}', encoding="utf-8")
    assert read_manifest(manifiesto).version == "9.9.9"


def test_read_manifest_inexistente_es_oserror(tmp_path: Path) -> None:
    """El NAS caido o la ruta mal escrita dan OSError, no ValueError."""
    with pytest.raises(OSError):
        read_manifest(tmp_path / "no-existe.json")


# --------------------------------------------------------------------- origenes
@pytest.mark.parametrize(
    ("origen", "es_url"),
    [
        ("https://drive.google.com/uc?export=download&id=abc", True),
        ("http://interno/latest.json", True),
        ("HTTPS://MAYUSCULAS/x.json", True),
        (r"\\192.168.0.16\Compilado_16\FoxBin2Prg-Studio\latest.json", False),
        (r"C:\local\latest.json", False),
        ("", False),
    ],
)
def test_is_url(origen: str, es_url: bool) -> None:
    assert is_url(origen) is es_url


@pytest.mark.parametrize(
    "compartido",
    [
        "https://drive.google.com/file/d/1A2b3C4d5E6f7G8h9I/view?usp=sharing",
        "https://drive.google.com/open?id=1A2b3C4d5E6f7G8h9I",
        "https://drive.google.com/uc?id=1A2b3C4d5E6f7G8h9I",
    ],
)
def test_los_links_de_drive_se_vuelven_descarga_directa(compartido: str) -> None:
    """El link que se copia del navegador devuelve HTML, no el JSON."""
    assert (
        normalize_source(compartido)
        == "https://drive.google.com/uc?export=download&id=1A2b3C4d5E6f7G8h9I"
    )


def test_sharepoint_recibe_el_download() -> None:
    url = "https://adssoftware.sharepoint.com/:u:/s/SOPORTE_ADS/Abc123?e=xyz"
    assert normalize_source(url).endswith("&download=1")


def test_sharepoint_no_se_duplica() -> None:
    url = "https://adssoftware.sharepoint.com/x/latest.json?download=1"
    assert normalize_source(url) == url


@pytest.mark.parametrize(
    "origen",
    [
        r"\\192.168.0.16\Compilado_16\latest.json",
        "https://interno.ads/latest.json",
    ],
)
def test_lo_que_no_reconoce_lo_deja_igual(origen: str) -> None:
    assert normalize_source(origen) == origen


# ------------------------------------------------------------- canal de GitHub
def _release(tag: str, *, assets: list[str] | None = None, **extra: object) -> dict:
    """Un Release como lo devuelve la API de GitHub, con lo que lee `parse_releases`."""
    return {
        "tag_name": tag,
        "html_url": f"https://github.com/Fenix-Corp/Utilities-Dist/releases/tag/{tag}",
        "body": "",
        "draft": False,
        "prerelease": False,
        "assets": [
            {"name": n, "browser_download_url": f"https://github.com/dl/{tag}/{n}"}
            for n in (assets if assets is not None else [ASSET_NAME])
        ],
        **extra,
    }


@pytest.mark.parametrize(
    "origen",
    [
        "https://github.com/Fenix-Corp/Utilities-Dist.git",
        "https://github.com/Fenix-Corp/Utilities-Dist",
        "https://github.com/Fenix-Corp/Utilities-Dist/",
        "HTTPS://GitHub.com/Fenix-Corp/Utilities-Dist.git",
        "  https://github.com/Fenix-Corp/Utilities-Dist.git  ",
    ],
)
def test_parse_github_repo_acepta_la_pagina_y_la_url_de_clone(origen: str) -> None:
    assert parse_github_repo(origen) == ("Fenix-Corp", "Utilities-Dist")


@pytest.mark.parametrize(
    "origen",
    [
        "https://interno.ads/latest.json",
        "https://github.com/Fenix-Corp",  # sin repo
        "https://github.com/Fenix-Corp/Utilities-Dist/releases",  # otra pagina
        "https://gitlab.com/Fenix-Corp/Utilities-Dist.git",
        r"\\192.168.0.16\Compilado_16\latest.json",
        "",
    ],
)
def test_parse_github_repo_rechaza_lo_que_no_es_un_repo(origen: str) -> None:
    assert parse_github_repo(origen) is None


def test_el_origen_por_defecto_es_el_repo_de_distribucion() -> None:
    assert parse_github_repo(DEFAULT_SOURCE) == ("Fenix-Corp", "Utilities-Dist")


def test_parse_releases_toma_la_version_mas_nueva() -> None:
    raw = json.dumps(
        [
            _release(TAG_PREFIX + "0.2.0"),
            _release(TAG_PREFIX + "0.10.0", body="  Menu lateral.  "),
            _release(TAG_PREFIX + "0.9.5"),
        ]
    )
    info = parse_releases(raw)

    assert info.version == "0.10.0"  # 0.10 > 0.9: se compara por numeros, no por texto
    assert info.notes == "Menu lateral."
    assert info.package == f"https://github.com/dl/{TAG_PREFIX}0.10.0/{ASSET_NAME}"


def test_parse_releases_ignora_las_etiquetas_de_otras_utilidades() -> None:
    """El canal es compartido: fnxUtilidades-v9.9.9 no es una version de Studio."""
    raw = json.dumps(
        [_release("fnxUtilidades-v9.9.9"), _release(TAG_PREFIX + "0.1.1"), _release("otra-v5.0.0")]
    )
    assert parse_releases(raw).version == "0.1.1"


def test_parse_releases_ignora_borradores_y_prereleases() -> None:
    raw = json.dumps(
        [
            _release(TAG_PREFIX + "0.3.0", draft=True),
            _release(TAG_PREFIX + "0.2.0", prerelease=True),
            _release(TAG_PREFIX + "0.1.1"),
        ]
    )
    assert parse_releases(raw).version == "0.1.1"


def test_parse_releases_sin_el_exe_cae_a_la_pagina_del_release() -> None:
    info = parse_releases(json.dumps([_release(TAG_PREFIX + "0.2.0", assets=["otro.zip"])]))
    assert info.package == f"https://github.com/Fenix-Corp/Utilities-Dist/releases/tag/{TAG_PREFIX}0.2.0"


def test_parse_releases_elige_el_asset_por_nombre() -> None:
    info = parse_releases(
        json.dumps([_release(TAG_PREFIX + "0.2.0", assets=["Otro.exe", ASSET_NAME.lower()])])
    )
    assert info.package.endswith("/" + ASSET_NAME.lower())  # sin distinguir mayusculas


@pytest.mark.parametrize(
    "crudo",
    [
        "no soy json",
        '{"message": "Not Found"}',  # error de la API: es un objeto, no una lista
        "[]",  # canal sin releases
        json.dumps([_release("fnxUtilidades-v1.1.1")]),  # solo hay de otras utilidades
        json.dumps([_release(TAG_PREFIX + "nada")]),  # version ilegible
    ],
)
def test_parse_releases_invalido_o_sin_version_de_studio(crudo: str) -> None:
    with pytest.raises(ValueError):
        parse_releases(crudo)


def test_read_manifest_de_un_repo_consulta_la_api_de_releases(monkeypatch: pytest.MonkeyPatch) -> None:
    pedidos: list[tuple[str, dict]] = []

    def falso(url: str, **kw: object) -> str:
        pedidos.append((url, kw))
        return json.dumps([_release(TAG_PREFIX + "0.4.0")])

    monkeypatch.setattr(updates, "_fetch_url", falso)

    assert read_manifest(DEFAULT_SOURCE).version == "0.4.0"
    url, kw = pedidos[0]
    assert url.startswith("https://api.github.com/repos/Fenix-Corp/Utilities-Dist/releases")
    assert kw["api"] is True
    assert kw["max_bytes"] > 64 * 1024  # la lista de releases pesa mas que un manifiesto


def test_read_manifest_de_una_url_cualquiera_sigue_siendo_un_manifiesto(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(updates, "_fetch_url", lambda url, **kw: '{"version": "7.0.0"}')
    assert read_manifest("https://interno.ads/latest.json").version == "7.0.0"


@pytest.mark.parametrize(
    ("paquete", "esperado"),
    [
        ("https://github.com/dl/x.exe", "https://github.com/dl/x.exe"),
        ("", None),
        ("   ", None),
    ],
)
def test_destino_del_paquete(paquete: str, esperado: str | None) -> None:
    from fb2p_studio.ui.main_window import _destino_del_paquete

    destino = _destino_del_paquete(paquete)
    assert (destino.toString() if destino is not None else None) == esperado


def test_destino_del_paquete_de_una_ruta_de_red_abre_la_carpeta() -> None:
    from fb2p_studio.ui.main_window import _destino_del_paquete

    destino = _destino_del_paquete("C:/Compilado/Studio-0.2.0.zip")
    assert destino is not None
    assert destino.isLocalFile()
    assert destino.toLocalFile().replace("\\", "/").endswith("Compilado")

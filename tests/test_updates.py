"""Comparacion de versiones y lectura del manifiesto de actualizaciones."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from fb2p_studio.core.updates import (
    UpdateInfo,
    is_newer,
    is_url,
    normalize_source,
    parse_manifest,
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

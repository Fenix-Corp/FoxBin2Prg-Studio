"""Modo proyecto: cType `*` / `*-` y la carpeta de recompilacion.

Lo delicado de este modo es que dos strings casi iguales significan cosas
distintas: `*` procesa el proyecto Y sus archivos, `*-` sólo los archivos. Si
en algun punto de la cadena (Python -> INI -> driver VFP -> FoxBin2Prg) se cae
el guion, el usuario pide una cosa y obtiene la otra sin enterarse.
"""

from __future__ import annotations

import configparser
from pathlib import Path

import pytest

from fb2p_studio.core.extensions import (
    PROJECT_WITH_PJX,
    PROJECT_WITHOUT_PJX,
    bin_ext_of,
    direction_from_ext,
    ext_of,
    is_project,
    project_ctype,
    supports,
)
from fb2p_studio.core.job import Job, Operation, OperationOptions


# --------------------------------------------------------------------- extensiones
@pytest.mark.parametrize(
    ("ruta", "esperado"),
    [
        (r"C:\proj\app.pjx", "pjx"),
        (r"C:\proj\app.PJX", "pjx"),
        (r"C:\proj\app.pj2", "pj2"),
        (r"C:\proj\sin_extension", ""),
        (r"C:\ruta.con.puntos\app.pjx", "pjx"),
    ],
)
def test_ext_of(ruta: str, esperado: str) -> None:
    assert ext_of(ruta) == esperado


@pytest.mark.parametrize(
    ("ruta", "es_proyecto"),
    [
        (r"C:\proj\app.pjx", True),
        (r"C:\proj\app.PJ2", True),
        (r"C:\proj\form.scx", False),
        (r"C:\proj\form.sc2", False),
        (r"C:\proj\app.pjt", False),  # el .pjt es la memo del .pjx, no el proyecto
        ("", False),
    ],
)
def test_is_project(ruta: str, es_proyecto: bool) -> None:
    assert is_project(ruta) is es_proyecto


def test_la_direccion_del_proyecto_sale_de_la_extension() -> None:
    """En modo proyecto no se elige direccion: la fija la extension."""
    assert direction_from_ext(r"C:\proj\app.pjx") == "BIN2PRG"
    assert direction_from_ext(r"C:\proj\app.pj2") == "PRG2BIN"


def test_project_ctype() -> None:
    assert project_ctype(include_project_file=True) == "*"
    assert project_ctype(include_project_file=False) == "*-"


# --------------------------------------------------------------- soporte por direccion
@pytest.mark.parametrize(
    ("archivo", "esperado"),
    [
        ("login.scx", "scx"),
        ("login.sc2", "scx"),  # el texto se indexa por su binario
        ("app.PJ2", "pjx"),
        ("datos.db2", "dbf"),
        ("leeme.txt", ""),
        ("main.prg", ""),  # un .prg no es un binario que FoxBin2Prg convierta
    ],
)
def test_bin_ext_of(archivo: str, esperado: str) -> None:
    assert bin_ext_of(archivo) == esperado


@pytest.mark.parametrize(
    ("archivo", "direccion", "soportado"),
    [
        # Soporte 2: las dos direcciones.
        ("login.scx", "BIN2PRG", True),
        ("login.sc2", "PRG2BIN", True),
        ("app.pjx", "BIN2PRG", True),
        ("app.pj2", "PRG2BIN", True),
        ("base.vcx", "BIN2PRG", True),
        ("base.vc2", "PRG2BIN", True),
        ("datos.dbc", "BIN2PRG", True),
        ("datos.dc2", "PRG2BIN", True),
        # Soporte 1: SOLO binario -> texto. Rearmar la tabla desde el dump
        # pisaria los datos, asi que por defecto no se hace.
        ("datos.dbf", "BIN2PRG", True),
        ("datos.db2", "PRG2BIN", False),
        ("teclas.fky", "BIN2PRG", True),
        ("teclas.fk2", "PRG2BIN", False),
        ("vars.mem", "BIN2PRG", True),
        ("vars.me2", "PRG2BIN", False),
        # Lo que FoxBin2Prg no maneja.
        ("leeme.txt", "BIN2PRG", False),
        ("main.prg", "PRG2BIN", False),
    ],
)
def test_supports_depende_de_la_direccion(archivo: str, direccion: str, soportado: bool) -> None:
    """`hasSupport_Bin2Prg()` pide `n_*_Conversion_Support > 0`; `hasSupport_Prg2Bin()`
    pide `= 2`. De ahi que DBF/FKY/MEM (soporte 1) sean de ida y no de vuelta."""
    assert supports(archivo, direccion) is soportado


def test_una_direccion_desconocida_no_soporta_nada() -> None:
    assert supports("login.scx", "") is False


# --------------------------------------------------------------------- job / INI
def _leer_ini(job: Job) -> configparser.ConfigParser:
    cp = configparser.ConfigParser(interpolation=None)
    cp.read_string(job.to_ini())
    return cp


def _job(ctype: str, options: OperationOptions | None = None) -> Job:
    return Job(
        foxbin2prg_home=r"D:\FoxBin2Prg",
        event_stream=Path("events.jsonl"),
        operations=[
            Operation(
                id="proyecto",
                file=r"C:\proj\app.pjx",
                type=ctype,
                options=options or OperationOptions(),
            )
        ],
    )


@pytest.mark.parametrize("ctype", [PROJECT_WITH_PJX, PROJECT_WITHOUT_PJX])
def test_el_ctype_del_proyecto_llega_intacto_al_ini(ctype: str) -> None:
    cp = _leer_ini(_job(ctype))
    assert cp["op:proyecto"]["type"] == ctype


def test_el_guion_de_asterisco_menos_no_se_pierde() -> None:
    """`*-` y `*` tienen que seguir siendo distinguibles en el INI."""
    con = _leer_ini(_job(PROJECT_WITH_PJX))["op:proyecto"]["type"]
    sin = _leer_ini(_job(PROJECT_WITHOUT_PJX))["op:proyecto"]["type"]
    assert con != sin
    assert (con, sin) == ("*", "*-")


# --------------------------------------------------------------------- recompile
def test_recompile_cwd_manda_la_carpeta_cuando_recompila() -> None:
    opts = OperationOptions(recompile=1, recompile_cwd=r"C:\proj")
    assert opts.ctype_recompile() == r"C:\proj"
    assert _leer_ini(_job("*", opts))["op:proyecto"]["recompile"] == r"C:\proj"


def test_recompile_cwd_se_ignora_si_no_se_recompila() -> None:
    """Sin recompilacion, mandar una carpeta la re-activaria: FoxBin2Prg hace
    `l_Recompile = (... Or Directory(x))`."""
    opts = OperationOptions(recompile=0, recompile_cwd=r"C:\proj")
    assert opts.ctype_recompile() == "0"
    assert _leer_ini(_job("*", opts))["op:proyecto"]["recompile"] == "0"


def test_sin_recompile_cwd_se_manda_el_flag() -> None:
    assert OperationOptions(recompile=1).ctype_recompile() == "1"
    assert OperationOptions(recompile=0).ctype_recompile() == "0"

"""Lectura del contenido de un proyecto y pre-flight.

Los `.pjx` de prueba se fabrican byte a byte (DBF + memo `.pjt`) en vez de
copiar un binario al repo: asi se ve exactamente que estructura se esta
soportando, y el test explica el formato.
"""

from __future__ import annotations

import struct
from pathlib import Path

import pytest

from fb2p_studio.core.project_reader import (
    ProjectReadError,
    read_project,
)
from fb2p_studio.core.validators import CONVIERTE, FALTA, NO_CONVERTIBLE, preflight

# --------------------------------------------------------------------- fixtures
#: Campos del .pjx que nos interesan. NAME y OUTFILE son memo (4 bytes de
#: numero de bloque); el resto, caracteres.
_CAMPOS = [
    (b"NAME", b"M", 4),
    (b"TYPE", b"C", 1),
    (b"EXCLUDE", b"L", 1),
    (b"MAINPROG", b"L", 1),
]
_BLOQUE_MEMO = 64


def _descriptor(nombre: bytes, tipo: bytes, largo: int) -> bytes:
    return nombre.ljust(11, b"\x00") + tipo + b"\x00" * 4 + bytes([largo, 0]) + b"\x00" * 14


def escribir_pjx(
    carpeta: Path,
    nombre: str,
    filas: list[tuple[str, str, bool, bool]],
    *,
    borrados: set[int] = frozenset(),  # type: ignore[assignment]
    con_pjt: bool = True,
) -> Path:
    """Fabrica un `<nombre>.pjx` + `.pjt` con las filas dadas.

    Cada fila es `(ruta, type_code, excluded, main)`. Se agrega sola la fila
    de cabecera `TYPE='H'`, que es la que FoxBin2Prg saltea.
    """
    registros = [(str(carpeta / f"{nombre}.pjx"), "H", False, False), *filas]

    memo = bytearray(b"\x00" * 512)
    struct.pack_into(">H", memo, 6, _BLOQUE_MEMO)  # tamano de bloque
    bloques: list[int] = []
    for ruta, *_ in registros:
        nro = len(memo) // _BLOQUE_MEMO
        datos = ruta.encode("cp1252") + b"\x00"
        cuerpo = struct.pack(">II", 1, len(datos)) + datos
        cuerpo += b"\x00" * (-len(cuerpo) % _BLOQUE_MEMO)
        memo += cuerpo
        bloques.append(nro)
    struct.pack_into(">I", memo, 0, len(memo) // _BLOQUE_MEMO)

    rec_len = 1 + sum(largo for _n, _t, largo in _CAMPOS)
    header_len = 32 + 32 * len(_CAMPOS) + 1
    cabecera = bytearray(struct.pack("<BBBB", 0x30, 26, 8, 1))
    cabecera += struct.pack("<IHH", len(registros), header_len, rec_len)
    cabecera += b"\x00" * 20
    for n, t, largo in _CAMPOS:
        cabecera += _descriptor(n, t, largo)
    cabecera += b"\x0d"

    cuerpo = bytearray()
    for i, (_ruta, tipo, excluido, principal) in enumerate(registros):
        cuerpo += b"*" if i in borrados else b" "
        cuerpo += struct.pack("<I", bloques[i])
        cuerpo += tipo.encode("cp1252")[:1].ljust(1)
        cuerpo += b"T" if excluido else b"F"
        cuerpo += b"T" if principal else b"F"

    pjx = carpeta / f"{nombre}.pjx"
    pjx.write_bytes(bytes(cabecera + cuerpo) + b"\x1a")
    if con_pjt:
        (carpeta / f"{nombre}.pjt").write_bytes(bytes(memo))
    return pjx


def escribir_pj2(carpeta: Path, nombre: str, entradas: list[tuple[str, str]]) -> Path:
    """Fabrica un `.pj2` con el bloque BuildProj y las entradas `.ADD(...)`."""
    lineas = [
        "*< FOXBIN2PRG: Version=\"1.21\" />",
        "*<BuildProj>",
        f"BUILD PROJECT {nombre}.pjx FROM '__newproject.f2b'",
        "WITH loProject.FILES",
    ]
    for ruta, tipo in entradas:
        lineas.append(f"\t.ADD('{ruta}')\t\t&& *< FileMetadata: Type=\"{tipo}\" Cpid=\"1252\" />")
    lineas += [
        "*</BuildProj>",
        "\t.ITEM('__newproject.f2b').Remove()",
    ]
    pj2 = carpeta / f"{nombre}.pj2"
    pj2.write_text("\n".join(lineas), encoding="cp1252")
    return pj2


# --------------------------------------------------------------------- .pjx
def test_lee_los_miembros_de_un_pjx(tmp_path: Path) -> None:
    pjx = escribir_pjx(
        tmp_path,
        "app",
        [
            (r"forms\login.scx", "K", False, True),
            (r"libs\base.vcx", "V", False, False),
            (r"data\clientes.dbf", "D", True, False),
        ],
    )
    c = read_project(pjx)

    assert c.direction == "BIN2PRG"
    assert [i.listed for i in c.items] == [
        r"forms\login.scx",
        r"libs\base.vcx",
        r"data\clientes.dbf",
    ]
    assert c.warnings == ()


def test_la_cabecera_no_es_un_miembro(tmp_path: Path) -> None:
    """El registro TYPE='H' es el propio proyecto: FoxBin2Prg lo saltea."""
    pjx = escribir_pjx(tmp_path, "app", [(r"forms\login.scx", "K", False, False)])
    c = read_project(pjx)
    assert len(c) == 1
    assert all(i.type_code != "H" for i in c.items)


def test_los_registros_borrados_se_ignoran(tmp_path: Path) -> None:
    pjx = escribir_pjx(
        tmp_path,
        "app",
        [(r"forms\a.scx", "K", False, False), (r"forms\b.scx", "K", False, False)],
        borrados={1},  # el indice 0 es la cabecera; el 1 es forms\a.scx
    )
    c = read_project(pjx)
    assert [i.listed for i in c.items] == [r"forms\b.scx"]


def test_las_rutas_se_resuelven_contra_la_carpeta_del_proyecto(tmp_path: Path) -> None:
    pjx = escribir_pjx(tmp_path, "app", [(r"forms\login.scx", "K", False, False)])
    (item,) = read_project(pjx).items
    assert item.path == tmp_path / "forms" / "login.scx"


def test_una_ruta_absoluta_se_respeta(tmp_path: Path) -> None:
    """Un proyecto puede referenciar archivos fuera de su carpeta, incluso en
    otra unidad (fue un bug historico de FoxBin2Prg, arreglado en 1.19.45)."""
    pjx = escribir_pjx(tmp_path, "app", [(r"Z:\compartido\comun.vcx", "V", False, False)])
    (item,) = read_project(pjx).items
    assert str(item.path).upper().startswith("Z:")


def test_banderas_excluido_y_principal(tmp_path: Path) -> None:
    pjx = escribir_pjx(
        tmp_path,
        "app",
        [(r"main.prg", "P", False, True), (r"data\tmp.dbf", "D", True, False)],
    )
    principal, excluido = read_project(pjx).items
    assert (principal.main, principal.excluded) == (True, False)
    assert (excluido.main, excluido.excluded) == (False, True)


def test_sin_pjt_avisa_en_vez_de_explotar(tmp_path: Path) -> None:
    """Sin el memo no hay nombres; se reporta y no se inventa nada."""
    pjx = escribir_pjx(
        tmp_path, "app", [(r"forms\login.scx", "K", False, False)], con_pjt=False
    )
    c = read_project(pjx)
    assert c.items == ()
    assert any("pjt" in w for w in c.warnings)


def test_un_dbf_que_no_es_proyecto(tmp_path: Path) -> None:
    falso = tmp_path / "cualquiera.pjx"
    falso.write_bytes(b"esto no es un dbf")
    with pytest.raises(ProjectReadError):
        read_project(falso)


def test_extension_que_no_es_de_proyecto(tmp_path: Path) -> None:
    with pytest.raises(ProjectReadError):
        read_project(tmp_path / "form.scx")


# --------------------------------------------------------------------- .pj2
def test_lee_los_miembros_de_un_pj2(tmp_path: Path) -> None:
    pj2 = escribir_pj2(
        tmp_path,
        "app",
        [(r"forms\login.scx", "K"), (r"libs\base.vcx", "V"), (r"leeme.txt", "T")],
    )
    c = read_project(pj2)

    assert c.direction == "PRG2BIN"
    assert [i.listed for i in c.items] == [r"forms\login.scx", r"libs\base.vcx", r"leeme.txt"]


def test_el_pj2_lista_binarios_pero_se_lee_el_texto(tmp_path: Path) -> None:
    """FoxBin2Prg hace `Forceext(file, get_Ext2FromExt(ext))`: el `.pj2` dice
    `login.scx`, pero lo que existe en disco y se convierte es `login.sc2`."""
    pj2 = escribir_pj2(tmp_path, "app", [(r"forms\login.scx", "K")])
    (item,) = read_project(pj2).items
    assert item.path.name == "login.scx"
    assert item.source.name == "login.sc2"


def test_el_scaffolding_de_build_no_es_un_miembro(tmp_path: Path) -> None:
    """`__newproject.f2b` aparece en el BUILD PROJECT y en un .ITEM(), pero no
    en un `.ADD(`: no es parte del proyecto."""
    pj2 = escribir_pj2(tmp_path, "app", [(r"forms\login.scx", "K")])
    c = read_project(pj2)
    assert all("f2b" not in i.listed for i in c.items)


def test_solo_cuenta_lo_que_esta_dentro_de_buildproj(tmp_path: Path) -> None:
    pj2 = escribir_pj2(tmp_path, "app", [(r"forms\login.scx", "K")])
    pj2.write_text(
        pj2.read_text(encoding="cp1252") + "\n\t.ADD('fuera\\del\\bloque.scx')\n",
        encoding="cp1252",
    )
    c = read_project(pj2)
    assert [i.listed for i in c.items] == [r"forms\login.scx"]


def test_pj2_sin_bloque_buildproj(tmp_path: Path) -> None:
    malo = tmp_path / "app.pj2"
    malo.write_text("* cualquier cosa\n", encoding="cp1252")
    with pytest.raises(ProjectReadError):
        read_project(malo)


# --------------------------------------------------------------------- preflight
def _tocar(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x")


def test_preflight_clasifica_los_tres_casos(tmp_path: Path) -> None:
    pjx = escribir_pjx(
        tmp_path,
        "app",
        [
            (r"forms\existe.scx", "K", False, False),
            (r"forms\borrado.scx", "K", False, False),
            (r"leeme.txt", "T", False, False),
        ],
    )
    _tocar(tmp_path / "forms" / "existe.scx")
    _tocar(tmp_path / "leeme.txt")

    pf = preflight(read_project(pjx))
    estados = {c.item.listed: c.status for c in pf.checks}

    assert estados[r"forms\existe.scx"] == CONVIERTE
    assert estados[r"forms\borrado.scx"] == FALTA
    assert estados[r"leeme.txt"] == NO_CONVERTIBLE  # existe, pero no se convierte
    assert pf.has_problems is True


def test_un_txt_que_falta_no_es_un_problema(tmp_path: Path) -> None:
    """No convertible gana sobre faltante: igual no se iba a tocar."""
    pjx = escribir_pjx(tmp_path, "app", [(r"leeme.txt", "T", False, False)])
    pf = preflight(read_project(pjx))
    assert pf.checks[0].status == NO_CONVERTIBLE
    assert pf.has_problems is False


def test_el_total_cuenta_el_proyecto_solo_si_se_incluye(tmp_path: Path) -> None:
    pjx = escribir_pjx(tmp_path, "app", [(r"forms\login.scx", "K", False, False)])
    _tocar(tmp_path / "forms" / "login.scx")
    contenido = read_project(pjx)

    assert preflight(contenido, include_project_file=True).total_to_convert == 2
    assert preflight(contenido, include_project_file=False).total_to_convert == 1


def test_detecta_archivos_en_otra_unidad(tmp_path: Path) -> None:
    pjx = escribir_pjx(
        tmp_path,
        "app",
        [(r"forms\local.scx", "K", False, False), (r"Z:\remoto\otro.scx", "K", False, False)],
    )
    pf = preflight(read_project(pjx))
    otra = {c.item.listed for c in pf.other_drive}

    assert otra == {r"Z:\remoto\otro.scx"}


def test_una_tabla_va_a_texto_pero_no_vuelve(tmp_path: Path) -> None:
    """El caso que aparecio corriendo la conversion de verdad: FoxBin2Prg
    volca un `.dbf` a `.db2`, pero por defecto NO reconstruye el `.dbf` desde
    el `.db2` (soporte 1, para no pisar los datos)."""
    pjx = escribir_pjx(tmp_path, "app", [(r"data\clientes.dbf", "D", False, False)])
    _tocar(tmp_path / "data" / "clientes.dbf")
    ida = preflight(read_project(pjx))
    assert ida.checks[0].status == CONVIERTE

    pj2 = escribir_pj2(tmp_path, "app", [(r"data\clientes.dbf", "D")])
    _tocar(tmp_path / "data" / "clientes.db2")
    vuelta = preflight(read_project(pj2))
    assert vuelta.checks[0].status == NO_CONVERTIBLE
    assert vuelta.has_problems is False  # no es un error: es como funciona


def test_el_motivo_distingue_los_dos_casos(tmp_path: Path) -> None:
    """Un `.txt` no es convertible nunca; un `.db2` lo es si se habilita."""
    pj2 = escribir_pj2(tmp_path, "app", [(r"data\clientes.dbf", "D"), (r"leeme.txt", "T")])
    tabla, texto = preflight(read_project(pj2)).checks

    assert "Conversion_Support" in tabla.reason
    assert "no maneja" in texto.reason


def test_preflight_de_un_pj2_mira_el_archivo_de_texto(tmp_path: Path) -> None:
    """Existe el `.sc2` pero no el `.scx`: igual se convierte, porque en esta
    direccion lo que se lee es el texto."""
    pj2 = escribir_pj2(tmp_path, "app", [(r"forms\login.scx", "K")])
    _tocar(tmp_path / "forms" / "login.sc2")

    pf = preflight(read_project(pj2))
    assert pf.checks[0].status == CONVIERTE
    assert not (tmp_path / "forms" / "login.scx").exists()

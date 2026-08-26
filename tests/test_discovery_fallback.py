"""La resolucion de rutas nunca se queda sin FoxBin2Prg por un override viejo.

El caso real: el .ini de preferencias guarda una carpeta que existia en la
maquina del que empaqueto (o que despues se movio). En la maquina destino esa
ruta no existe, pero el .exe trae FoxBin2Prg adentro — tiene que usarlo.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from fb2p_studio.core import discovery


@pytest.fixture(autouse=True)
def _sin_entorno_ni_rutas_tipicas(monkeypatch: pytest.MonkeyPatch) -> None:
    """Aisla el test de la maquina donde corre."""
    monkeypatch.delenv("FB2P_HOME", raising=False)
    monkeypatch.delenv("VFP_EXE", raising=False)
    monkeypatch.setattr(discovery, "_FB2P_TYPICAL", [])
    monkeypatch.setattr(discovery, "_VFP_TYPICAL", [])


def _fake_fb2p(folder: Path) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "FoxBin2Prg.EXE").write_bytes(b"")
    return folder


def test_override_inexistente_cae_al_bundle(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    bundle = _fake_fb2p(tmp_path / "bundled" / "foxbin2prg")
    monkeypatch.setattr(discovery, "bundled_fb2p_dir", lambda: bundle)

    assert discovery.find_fb2p_home(r"D:\ruta\que\no\existe") == bundle


def test_bundle_le_gana_a_las_rutas_tipicas(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Un FoxBin2Prg viejo instalado en la maquina no debe ganarle al embebido."""
    bundle = _fake_fb2p(tmp_path / "bundled" / "foxbin2prg")
    viejo = _fake_fb2p(tmp_path / "C_FoxBin2Prg")
    monkeypatch.setattr(discovery, "bundled_fb2p_dir", lambda: bundle)
    monkeypatch.setattr(discovery, "_FB2P_TYPICAL", [str(viejo)])

    assert discovery.find_fb2p_home() == bundle


def test_sin_bundle_valen_las_rutas_tipicas(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Corriendo desde fuente sin bundled/, las rutas tipicas siguen sirviendo."""
    externo = _fake_fb2p(tmp_path / "C_FoxBin2Prg")
    monkeypatch.setattr(discovery, "bundled_fb2p_dir", lambda: None)
    monkeypatch.setattr(discovery, "_FB2P_TYPICAL", [str(externo)])

    assert discovery.find_fb2p_home() == externo


def test_override_valido_gana(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    bundle = _fake_fb2p(tmp_path / "bundled" / "foxbin2prg")
    externo = _fake_fb2p(tmp_path / "clon")
    monkeypatch.setattr(discovery, "bundled_fb2p_dir", lambda: bundle)

    assert discovery.find_fb2p_home(str(externo)) == externo


def test_carpeta_sin_foxbin2prg_no_cuenta_como_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Una carpeta que existe pero no tiene el .EXE/.FXP tampoco vale."""
    bundle = _fake_fb2p(tmp_path / "bundled" / "foxbin2prg")
    vacia = tmp_path / "vacia"
    vacia.mkdir()
    monkeypatch.setattr(discovery, "bundled_fb2p_dir", lambda: bundle)

    assert discovery.find_fb2p_home(str(vacia)) == bundle


def test_vfp_override_inexistente_sigue_buscando(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(discovery, "_VFP_TYPICAL", [])
    assert discovery.find_vfp_exe(r"D:\vfp9\que\no\existe.exe") is None

    monkeypatch.setenv("VFP_EXE", __file__)  # cualquier archivo que exista
    assert discovery.find_vfp_exe(r"D:\vfp9\que\no\existe.exe") == Path(__file__)

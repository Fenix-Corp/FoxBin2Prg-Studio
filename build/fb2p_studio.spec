# PyInstaller spec — FoxBin2Prg-Studio
#
# Genera un unico .exe (onefile, windowed) que embebe:
#   - PySide6 + interprete Python
#   - El driver VFP (vfp_bridge/) como datos, extraidos en _MEIPASS al arrancar
#   - El icono de la app (src/fb2p_studio/resources/fb2p_studio.ico), que va
#     tanto como recurso (icono de ventana) como icono del propio .exe
#
# Uso: pyinstaller build\\fb2p_studio.spec  (desde la raiz del repo)

# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

ROOT = Path(SPECPATH).parent  # noqa: F821 — SPECPATH lo inyecta PyInstaller
BRIDGE = ROOT / "vfp_bridge"
BUNDLED = ROOT / "bundled" / "foxbin2prg"
RESOURCES = ROOT / "src" / "fb2p_studio" / "resources"
ICON = RESOURCES / "fb2p_studio.ico"
MANUAL = ROOT / "release" / "_template" / "LEEME.md"

if not ICON.is_file():
    raise SystemExit(
        f"Falta el icono {ICON}. Generalo con: "
        r".venv\Scripts\python.exe build\make_icon.py"
    )

if not MANUAL.is_file():
    raise SystemExit(f"Falta el manual {MANUAL}: lo embebe el .exe (Ayuda > Manual).")

datas = [
    # Icono de la app (tambien se aplica como icono del .exe, mas abajo)
    (str(ICON), "fb2p_studio/resources"),
    # Manual de usuario: el LEEME.md que tambien se reparte en el zip y el MSI.
    # Studio lo muestra en Ayuda > Manual.
    (str(MANUAL), "fb2p_studio/resources"),
    (str(BRIDGE / "fb2p_bridge.prg"), "vfp_bridge"),
    (str(BRIDGE / "fb2p_bridge.fpw"), "vfp_bridge"),
    # FoxBin2Prg redistribuible (CC BY 4.0, ver bundled/foxbin2prg/ATTRIBUTION.md)
    (str(BUNDLED / "FoxBin2Prg.EXE"),    "bundled/foxbin2prg"),
    (str(BUNDLED / "filename_caps.exe"), "bundled/foxbin2prg"),
    (str(BUNDLED / "filename_caps.cfg"), "bundled/foxbin2prg"),
    (str(BUNDLED / "foxbin2prg.pj2"),    "bundled/foxbin2prg"),
    (str(BUNDLED / "ATTRIBUTION.md"),    "bundled/foxbin2prg"),
]

# Traducciones compiladas (build\i18n.bat release). Son opcionales: sin .qm
# la app corre en su idioma fuente, el espanol.
datas += [
    (str(qm), "fb2p_studio/resources/i18n")
    for qm in sorted((RESOURCES / "i18n").glob("*.qm"))
]

a = Analysis(
    [str(ROOT / "src" / "fb2p_studio" / "__main__.py")],
    pathex=[str(ROOT / "src")],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "unittest", "pdb", "test"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="FoxBin2Prg-Studio",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ICON),
)

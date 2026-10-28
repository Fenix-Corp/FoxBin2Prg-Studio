@echo off
REM ==========================================================================
REM  launcher.bat - compila dist\FoxBin2Prg-Studio-Launcher.exe
REM  Autor: AJACH
REM  Fecha: [2026-10-28 16:40:37]
REM
REM  El lanzador es lo que el equipo ancla con un acceso directo: al abrirlo baja
REM  la ultima version de Studio del canal publico (Fenix-Corp/Utilities-Dist) y
REM  la ejecuta. Consola diminuta (solo stdlib, sin Qt), sin token ni secreto.
REM  Ver launcher\launcher.py.
REM
REM  Requiere: .venv activo (o en el PATH) con [dev] instalado.
REM ==========================================================================
setlocal
pushd "%~dp0.."

where pyinstaller >nul 2>nul
if errorlevel 1 (
  echo [launcher] pyinstaller no esta en el PATH. Instala con: pip install -e .[dev]
  popd
  exit /b 1
)

REM Se prueba la logica antes de empaquetarla: un lanzador roto no se puede
REM arreglar a distancia, porque el equipo ya lo tiene anclado.
python -m pytest -q -p no:cacheprovider tests\test_launcher.py
if errorlevel 1 (
  echo [launcher] Las pruebas del lanzador fallaron. No se compila.
  popd
  exit /b 1
)

REM --icon con ruta ABSOLUTA: PyInstaller resuelve las relativas contra --specpath, no
REM contra la carpeta actual, y fallaba con "Icon input file ... not found".
REM --workpath/--specpath aparte: build\ es la carpeta de scripts, y el .spec y los
REM temporales del lanzador no deben mezclarse con el spec de la aplicacion.
pyinstaller --noconfirm --clean --onefile --console ^
  --name FoxBin2Prg-Studio-Launcher ^
  --icon "%CD%\src\fb2p_studio\resources\fb2p_studio.ico" ^
  --exclude-module PySide6 ^
  --exclude-module tkinter ^
  --distpath dist ^
  --workpath build\launcher_work ^
  --specpath build\launcher_work ^
  launcher\launcher.py
if errorlevel 1 (
  echo [launcher] Fallo pyinstaller.
  REM No dejar un .exe a medias en dist: parece valido y no lo es.
  del /q "dist\FoxBin2Prg-Studio-Launcher.exe" 2>nul
  popd
  exit /b 1
)

echo.
echo [launcher] Listo: dist\FoxBin2Prg-Studio-Launcher.exe
popd
endlocal
exit /b 0

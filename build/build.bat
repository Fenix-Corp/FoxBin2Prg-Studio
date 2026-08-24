@echo off
REM ==========================================================================
REM  build.bat — construye FoxBin2Prg-Studio.exe (onefile, windowed)
REM  Requiere: .venv activo con [dev] instalado (pip install -e .[dev])
REM ==========================================================================
setlocal
pushd "%~dp0.."

where pyinstaller >nul 2>nul
if errorlevel 1 (
  echo [build] pyinstaller no esta en el PATH. Instala con: pip install -e .[dev]
  popd
  exit /b 1
)

pyinstaller --noconfirm --clean build\fb2p_studio.spec
if errorlevel 1 (
  echo [build] Fallo pyinstaller.
  popd
  exit /b 1
)

echo.
echo [build] Ejecutable listo: dist\FoxBin2Prg-Studio.exe
popd
endlocal

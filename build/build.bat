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

REM El icono esta versionado, pero si falta (clon parcial, limpieza) se
REM regenera solo: se dibuja por codigo, no hay que buscar el binario.
if not exist "src\fb2p_studio\resources\fb2p_studio.ico" (
  echo [build] Falta el icono. Generandolo...
  python build\make_icon.py
  if errorlevel 1 (
    echo [build] Fallo generando el icono.
    popd
    exit /b 1
  )
)

REM Las traducciones compiladas (.qm) no se versionan: se generan aca. Si no
REM hay ninguna traducida, esto igual corre y la app queda en espanol.
if exist "src\fb2p_studio\resources\i18n" (
  call build\i18n.bat release
  if errorlevel 1 (
    echo [build] Fallo compilando traducciones.
    popd
    exit /b 1
  )
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

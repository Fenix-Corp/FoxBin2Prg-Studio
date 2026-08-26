@echo off
REM ==========================================================================
REM  msi.bat - genera release\FoxBin2Prg-Studio-<version>.msi
REM
REM  El .exe suelto (build\package.bat) sigue siendo la via normal. Este MSI
REM  existe para equipos de IT que despliegan por GPO / Intune: instala en
REM  Program Files, deja acceso directo en el menu Inicio y entrada de
REM  desinstalacion.
REM
REM  Requiere WiX (una vez por maquina):
REM      dotnet tool install --global wix
REM
REM  Uso:
REM      build\msi.bat              (version del pyproject.toml)
REM      build\msi.bat 0.1.1        (fuerza esa version)
REM ==========================================================================
setlocal enabledelayedexpansion
pushd "%~dp0.."

set "VERSION=%~1"

where wix >nul 2>nul
if errorlevel 1 (
    echo [msi] No encuentro "wix" en el PATH. Instalalo con:
    echo    dotnet tool install --global wix
    goto :fail
)

REM --- Version ---------------------------------------------------------------
if "%VERSION%"=="" (
    if not exist ".venv\Scripts\python.exe" (
        echo [msi] No hay .venv para leer la version. Pasala como argumento:
        echo    build\msi.bat 0.1.0
        goto :fail
    )
    for /f "delims=" %%v in ('.venv\Scripts\python.exe -c "import tomllib,pathlib;print(tomllib.loads(pathlib.Path(r'pyproject.toml').read_text())['project']['version'])"') do set "VERSION=%%v"
)
if "%VERSION%"=="" (
    echo [msi] No pude determinar la version.
    goto :fail
)

REM --- El .exe tiene que existir ---------------------------------------------
if not exist "dist\FoxBin2Prg-Studio.exe" (
    echo [msi] dist\FoxBin2Prg-Studio.exe no existe. Compilando...
    call build\build.bat
    if errorlevel 1 goto :fail
)

if not exist "release" mkdir "release"
set "OUT=release\FoxBin2Prg-Studio-%VERSION%.msi"

echo [msi] Empaquetando FoxBin2Prg-Studio %VERSION%

wix build build\msi\fb2p_studio.wxs -arch x64 -out "%OUT%" ^
    -d Version=%VERSION% ^
    -d ExeFile=dist\FoxBin2Prg-Studio.exe ^
    -d IconFile=src\fb2p_studio\resources\fb2p_studio.ico ^
    -d DocDir=release\_template
if errorlevel 1 (
    echo [msi] Fallo wix build.
    goto :fail
)

echo.
echo [msi] MSI listo:
echo   %CD%\%OUT%
popd
endlocal
exit /b 0

:fail
echo.
echo [msi] FALLO.
popd
endlocal
exit /b 1

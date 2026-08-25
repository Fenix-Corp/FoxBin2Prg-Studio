@echo off
REM ==========================================================================
REM  package.bat — genera release\FoxBin2Prg-Studio-<version>\ listo para
REM  compartir con el equipo.
REM
REM  Contenido:
REM    - FoxBin2Prg-Studio.exe   (compilado con PyInstaller si falta)
REM    - LEEME.txt / LICENCIA.txt / CAMBIOS.txt   (traidos del template)
REM
REM  Uso:
REM    build\package.bat                  (usa version del pyproject.toml)
REM    build\package.bat 0.1.1            (fuerza esa version)
REM    build\package.bat --zip            (empaqueta + zippea)
REM    build\package.bat 0.1.1 --zip      (version + zip)
REM ==========================================================================
setlocal enabledelayedexpansion
pushd "%~dp0.."

REM --- 0. Parseo de argumentos ---------------------------------------------
set "VERSION="
set "DOZIP=0"
:parse_args
if "%~1"=="" goto after_args
if /i "%~1"=="--zip" (
    set "DOZIP=1"
    shift
    goto parse_args
)
if "%VERSION%"=="" (
    set "VERSION=%~1"
    shift
    goto parse_args
)
shift
goto parse_args
:after_args

REM --- 1. Version -----------------------------------------------------------
REM Leemos la version con Python (tomllib, stdlib). El venv de dev
REM esta disponible porque el build lo necesita si o si. Se puede
REM overridear pasando la version como primer argumento.
if "%VERSION%"=="" (
    if not exist ".venv\Scripts\python.exe" (
        echo [package] No hay .venv con Python. Crealo con:
        echo    py -3 -m venv .venv
        echo    .venv\Scripts\pip install -e .[dev]
        popd
        exit /b 1
    )
    for /f "delims=" %%v in ('.venv\Scripts\python.exe -c "import tomllib,pathlib;print(tomllib.loads(pathlib.Path(r'pyproject.toml').read_text())['project']['version'])"') do set "VERSION=%%v"
)
if "%VERSION%"=="" (
    echo [package] No pude leer la version del pyproject.toml.
    popd
    exit /b 1
)
echo [package] Empaquetando FoxBin2Prg-Studio %VERSION%

REM --- 2. Build del EXE si falta o esta desactualizado ---------------------
if not exist "dist\FoxBin2Prg-Studio.exe" (
    echo [package] dist\FoxBin2Prg-Studio.exe no existe. Compilando...
    call build\build.bat
    if errorlevel 1 (
        echo [package] Fallo la compilacion.
        popd
        exit /b 1
    )
)

REM --- 3. Preparar carpeta de release --------------------------------------
set "RELDIR=release\FoxBin2Prg-Studio-%VERSION%"
set "TEMPLATE=release\_template"

REM Si la carpeta ya existe, borrar solo su contenido (no la carpeta) para
REM evitar sorpresas si alguien la tiene abierta.
if exist "%RELDIR%" (
    echo [package] Limpiando "%RELDIR%"...
    del /f /q "%RELDIR%\*" 2>nul
) else (
    mkdir "%RELDIR%"
)

REM --- 4. Copiar payload ---------------------------------------------------
copy /y "dist\FoxBin2Prg-Studio.exe" "%RELDIR%\" >nul || goto :err

REM Los .txt / .md vienen del template si existen
if exist "%TEMPLATE%\LEEME.txt"    copy /y "%TEMPLATE%\LEEME.txt"    "%RELDIR%\" >nul
if exist "%TEMPLATE%\LEEME.md"     copy /y "%TEMPLATE%\LEEME.md"     "%RELDIR%\" >nul
if exist "%TEMPLATE%\LICENCIA.txt" copy /y "%TEMPLATE%\LICENCIA.txt" "%RELDIR%\" >nul
if exist "%TEMPLATE%\CAMBIOS.txt"  copy /y "%TEMPLATE%\CAMBIOS.txt"  "%RELDIR%\" >nul

echo.
echo [package] Paquete listo en:
echo   %CD%\%RELDIR%\
echo.
dir /b "%RELDIR%"

REM --- 5. Zip opcional ------------------------------------------------------
if "%DOZIP%"=="1" (
    echo.
    echo [package] Generando ZIP...
    set "ZIPFILE=release\FoxBin2Prg-Studio-%VERSION%.zip"
    if exist "!ZIPFILE!" del /q "!ZIPFILE!"
    powershell -NoProfile -Command "Compress-Archive -Path '%RELDIR%' -DestinationPath '!ZIPFILE!' -Force"
    if errorlevel 1 (
        echo [package] Fallo generando el ZIP.
        popd
        exit /b 1
    )
    echo [package] ZIP listo: %CD%\!ZIPFILE!
) else (
    echo.
    echo Para compartir: comprimi la carpeta como
    echo   FoxBin2Prg-Studio-%VERSION%.zip
    echo o volve a correr build\package.bat --zip
)

popd
endlocal
exit /b 0

:err
echo [package] Fallo copiando archivos.
popd
endlocal
exit /b 1

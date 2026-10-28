@echo off
REM ==========================================================================
REM  publish.bat - sube FoxBin2Prg-Studio al canal de distribucion
REM  Autor: AJACH
REM  Fecha: [2026-10-28 16:20:00]
REM
REM  Crea el Release  foxbin2prg-studio-v<version>  en el repo PUBLICO
REM  Fenix-Corp/Utilities-Dist (el mismo canal de las Utilidades de Desarrollo)
REM  con el .exe adjunto. Es lo que lee Studio al buscar actualizaciones
REM  (core\updates.py: TAG_PREFIX y ASSET_NAME deben coincidir con los de aqui).
REM
REM  Sube el .exe de Studio, el lanzador (FoxBin2Prg-Studio-Launcher.exe, lo que el
REM  equipo ancla) y el .zip del paquete.
REM
REM  Solo publica una version NUEVA: si el Release ya existe no toca nada (sale
REM  con codigo 2), para no pisar un .exe que alguien ya pudo haber bajado. Sube
REM  la version (build_exe.bat --bump patch, o __version__ en __init__.py), o usa
REM  --force para reemplazar los archivos.
REM
REM  Requiere gh (GitHub CLI) autenticado con escritura en Utilities-Dist.
REM
REM  Uso:
REM    build\publish.bat                 (version del pyproject.toml)
REM    build\publish.bat 0.1.1           (fuerza esa version)
REM    build\publish.bat --dry-run       (muestra que subiria, sin subir nada)
REM    build\publish.bat --force         (reemplaza los archivos de un Release existente)
REM
REM  Codigos de salida:  0 publicado  |  1 error  |  2 omitido (ya existia)
REM ==========================================================================
setlocal enabledelayedexpansion
pushd "%~dp0.."

set "REPO=Fenix-Corp/Utilities-Dist"
set "PREFIX=foxbin2prg-studio-v"
set "EXE=dist\FoxBin2Prg-Studio.exe"

set "VERSION="
set "DRYRUN=0"
set "FORCE=0"

:parse_args
if "%~1"=="" goto after_args
if /i "%~1"=="--dry-run" (
    set "DRYRUN=1"
    shift
    goto parse_args
)
if /i "%~1"=="--force" (
    set "FORCE=1"
    shift
    goto parse_args
)
if "%VERSION%"=="" set "VERSION=%~1"
shift
goto parse_args
:after_args

REM --- 1. Version -----------------------------------------------------------
if "%VERSION%"=="" (
    if not exist ".venv\Scripts\python.exe" (
        echo [publish] No hay .venv para leer la version. Pasala como argumento:
        echo    build\publish.bat 0.1.0
        goto :fail
    )
    for /f "delims=" %%v in ('.venv\Scripts\python.exe build\version.py') do set "VERSION=%%v"
)
if "%VERSION%"=="" (
    echo [publish] No pude determinar la version.
    goto :fail
)
set "TAG=%PREFIX%%VERSION%"

REM --- 2. Archivos a subir --------------------------------------------------
if not exist "%EXE%" (
    echo [publish] No existe %EXE%. Compila primero: build_exe.bat
    goto :fail
)
set "ARCHIVOS="%EXE%""
REM El lanzador (lo que el equipo ancla) tambien va al canal, para poder bajarlo de ahi.
set "LANZADOR=dist\FoxBin2Prg-Studio-Launcher.exe"
if exist "%LANZADOR%" set "ARCHIVOS=!ARCHIVOS! "!LANZADOR!""
set "ZIP=release\FoxBin2Prg-Studio-%VERSION%.zip"
if exist "%ZIP%" set "ARCHIVOS=!ARCHIVOS! "!ZIP!""

echo [publish] Canal  : %REPO%
echo [publish] Release: %TAG%
echo [publish] Archivos: !ARCHIVOS!

REM --- 3. gh disponible y con sesion ----------------------------------------
if "%DRYRUN%"=="1" goto dryrun
where gh >nul 2>nul
if errorlevel 1 (
    echo [publish] No encuentro "gh" ^(GitHub CLI^) en el PATH. Instalalo desde https://cli.github.com
    goto :fail
)
gh auth status >nul 2>nul
if errorlevel 1 (
    echo [publish] gh no tiene sesion iniciada. Ejecuta:  gh auth login
    goto :fail
)

REM --- 4. Nueva o ya publicada? ---------------------------------------------
gh release view %TAG% --repo %REPO% >nul 2>nul
if not errorlevel 1 (
    if "%FORCE%"=="0" (
        echo.
        echo [publish] OMITIDO: el Release %TAG% ya existe en %REPO%.
        echo           No se subio nada. El lanzador compara la version, asi que
        echo           un .exe nuevo con la misma version NO llegaria al equipo.
        echo           Para publicar una version nueva:  build_exe.bat --bump patch
        echo           ^(o sube __version__ en src\fb2p_studio\__init__.py^).
        echo           Para reemplazar los archivos de esta:  build\publish.bat --force
        popd
        endlocal
        exit /b 2
    )
    echo [publish] --force: reemplazando los archivos de %TAG% ...
    gh release upload %TAG% !ARCHIVOS! --repo %REPO% --clobber
    if errorlevel 1 goto :fail
    goto :ok
)

REM --- 5. Crear el Release --------------------------------------------------
REM --latest=false: el Release "Latest" del repo sigue siendo el de las
REM utilidades; Studio se distingue por su prefijo, no por esa marca.
echo [publish] Creando el Release %TAG% ...
gh release create %TAG% !ARCHIVOS! --repo %REPO% --title "FoxBin2Prg-Studio %VERSION%" --notes "FoxBin2Prg-Studio %VERSION%. Descarga FoxBin2Prg-Studio.exe y reemplaza el actual." --latest=false
if errorlevel 1 goto :fail
goto :ok

:dryrun
echo.
echo [publish] --dry-run: no se sube nada. Se ejecutaria:
echo    gh release view %TAG% --repo %REPO%
echo    si no existe:  gh release create %TAG% !ARCHIVOS! --repo %REPO% --latest=false
echo    si existe:     se omite ^(con --force: gh release upload %TAG% ... --clobber^)
popd
endlocal
exit /b 0

:ok
echo.
echo [publish] OK - publicado: https://github.com/%REPO%/releases/tag/%TAG%
popd
endlocal
exit /b 0

:fail
echo.
echo [publish] FALLO. No se publico.
popd
endlocal
exit /b 1

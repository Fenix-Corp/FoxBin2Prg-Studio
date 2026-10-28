@echo off
setlocal EnableExtensions
cd /d "%~dp0"

REM ============================================================================
REM  FoxBin2Prg-Studio - Compilar y distribuir (PyInstaller, onefile)
REM  Autor: AJACH
REM  Fecha: [2026-10-28 15:00:30]
REM
REM  Un solo paso, doble clic o consola:
REM    1) Prepara .venv (Python 3.11) e instala dependencias ([dev] incluye
REM       PyInstaller)
REM    2) Puerta de calidad: lint (ruff) + pruebas (pytest). Si fallan, no se
REM       compila
REM    3) Limpia dist\ y el cache de PyInstaller (build\ guarda los scripts, NO
REM       se borra entero)
REM    4) Compila dist\FoxBin2Prg-Studio.exe (icono, traducciones y spec los
REM       resuelve build\build.bat)
REM    5) Distribucion: release\FoxBin2Prg-Studio-<version>\ + .zip (la version
REM       sale del pyproject.toml)
REM    6) Opcional: .msi para IT (GPO / Intune)
REM    7) Publica el .exe en el canal de actualizacion (GitHub, repo publico
REM       Fenix-Corp/Utilities-Dist) para que Studio avise de la version nueva.
REM       Solo sube una version NUEVA: si el Release ya existe, no toca nada.
REM
REM  Opciones:
REM    --msi        ademas genera release\FoxBin2Prg-Studio-<version>.msi
REM                 (requiere WiX: dotnet tool install --global wix)
REM    --nozip      deja solo la carpeta de release, sin .zip
REM    --nocheck    se salta lint + pruebas (no recomendado). Implica --nopublish:
REM                 no se publica un build que no paso las pruebas
REM    --nopublish  compila y empaqueta, pero NO sube nada a GitHub
REM    --dry-run    en el paso 7 muestra que subiria, sin subir nada
REM    --republish  si el Release de esta version ya existe, reemplaza sus archivos
REM    --nopause    no espera tecla al final (para CI o scripts)
REM
REM  Para publicar hace falta gh (GitHub CLI) con sesion y escritura en
REM  Utilities-Dist:  gh auth login
REM
REM  Archivo en ASCII y CRLF a proposito (sin chcp): evita que cmd se coma el
REM  primer caracter de cada linea.
REM ============================================================================

set "DOMSI=0"
set "DOZIP=1"
set "DOCHECK=1"
set "DOPUBLISH=1"
set "PUBARGS="
set "NOPAUSE=0"
set "DRY=0"
set "PUBSTATE=omitido"

:parse_args
if "%~1"=="" goto after_args
if /i "%~1"=="--msi"       set "DOMSI=1"
if /i "%~1"=="--nozip"     set "DOZIP=0"
if /i "%~1"=="--nocheck"   set "DOCHECK=0"
if /i "%~1"=="--nopublish" set "DOPUBLISH=0"
if /i "%~1"=="--dry-run"   set "DRY=1"
if /i "%~1"=="--dry-run"   set "PUBARGS=%PUBARGS% --dry-run"
if /i "%~1"=="--republish" set "PUBARGS=%PUBARGS% --force"
if /i "%~1"=="--nopause"   set "NOPAUSE=1"
shift
goto parse_args
:after_args

REM Sin pruebas no hay publicacion: lo que se sube lo usa todo el equipo.
if "%DOCHECK%"=="0" set "DOPUBLISH=0"

echo ============================================================
echo   FoxBin2Prg-Studio  -  Compilar y distribuir
echo ============================================================

REM --- 1) Entorno virtual -----------------------------------------------------
set "PY=.venv\Scripts\python.exe"
if exist "%PY%" goto have_venv

echo.
echo [1/7] Creando .venv ...
set "BASEPY=python"
where py >nul 2>nul && set "BASEPY=py -3.11"
%BASEPY% --version >nul 2>nul
if errorlevel 1 (
  echo [ERROR] No se encontro Python. Instala Python 3.11 de 64 bits.
  goto fail
)
%BASEPY% -m venv .venv
if errorlevel 1 (
  echo [ERROR] No se pudo crear .venv.
  goto fail
)

:have_venv
echo.
echo [1/7] Instalando dependencias (pip install -e .[dev]) ...
"%PY%" --version
"%PY%" -m pip install --upgrade pip >nul 2>nul
"%PY%" -m pip install -e ".[dev]"
if errorlevel 1 (
  echo [ERROR] Fallo "pip install". Revisa la conexion o el pyproject.toml.
  goto fail
)

REM Con el .venv al frente del PATH, build.bat encuentra pyinstaller y python.
set "PATH=%CD%\.venv\Scripts;%PATH%"

REM --- 2) Lint + pruebas (puerta de seguridad) --------------------------------
echo.
if "%DOCHECK%"=="0" (
  echo [2/7] Lint + pruebas OMITIDOS ^(--nocheck^); tampoco se publicara.
  goto after_check
)
echo [2/7] Ejecutando lint y pruebas (build\check.bat) ...
REM Los tests construyen widgets: sin plataforma explicita Qt puede morir con
REM "could not connect to display".
set "QT_QPA_PLATFORM=offscreen"
call build\check.bat
if errorlevel 1 (
  echo [ERROR] Lint o pruebas fallaron. Se aborta el build.
  goto fail
)
:after_check

REM --- 3) Limpieza de builds previos ------------------------------------------
echo.
echo [3/7] Limpiando build previo ...
if exist dist rmdir /s /q dist
if exist build\fb2p_studio rmdir /s /q build\fb2p_studio

REM --- 4) Compilacion ---------------------------------------------------------
echo.
echo [4/7] Compilando con PyInstaller (puede tardar varios minutos) ...
call build\build.bat
if errorlevel 1 (
  echo [ERROR] Fallo la compilacion de PyInstaller.
  goto fail
)
if not exist "dist\FoxBin2Prg-Studio.exe" (
  echo [ERROR] No se genero dist\FoxBin2Prg-Studio.exe.
  goto fail
)

REM --- 5) Distribucion --------------------------------------------------------
echo.
echo [5/7] Armando el paquete de distribucion ...
set "VERSION="
for /f "delims=" %%v in ('.venv\Scripts\python.exe -c "import tomllib,pathlib;print(tomllib.loads(pathlib.Path(r'pyproject.toml').read_text())['project']['version'])"') do set "VERSION=%%v"
if "%VERSION%"=="" (
  echo [ERROR] No pude leer la version del pyproject.toml.
  goto fail
)
if "%DOZIP%"=="1" (
  call build\package.bat %VERSION% --zip
) else (
  call build\package.bat %VERSION%
)
if errorlevel 1 (
  echo [ERROR] Fallo el empaquetado.
  goto fail
)

REM --- 6) MSI opcional --------------------------------------------------------
echo.
if "%DOMSI%"=="0" (
  echo [6/7] MSI omitido ^(usa --msi para generarlo^).
  goto step7
)
echo [6/7] Generando el MSI ...
call build\msi.bat %VERSION%
if errorlevel 1 (
  echo [ERROR] Fallo el MSI.
  goto fail
)

REM --- 7) Publicar en el canal de actualizacion -------------------------------
:step7
echo.
if "%DOPUBLISH%"=="0" (
  echo [7/7] Publicacion omitida ^(--nopublish o --nocheck^): no se sube nada a GitHub.
  goto done
)
echo [7/7] Publicando en el canal de actualizacion (Fenix-Corp/Utilities-Dist) ...
call build\publish.bat %VERSION%%PUBARGS%
set "PUBRC=%ERRORLEVEL%"
if "%PUBRC%"=="0" set "PUBSTATE=publicado"
if "%PUBRC%"=="0" if "%DRY%"=="1" set "PUBSTATE=simulado ^(--dry-run^)"
if "%PUBRC%"=="2" set "PUBSTATE=OMITIDO: la version %VERSION% ya estaba publicada"
if "%PUBRC%"=="0" goto done
if "%PUBRC%"=="2" goto done
echo [ERROR] No se pudo publicar. El build quedo hecho en dist\ y release\.
echo         Reintenta solo la subida con:  build\publish.bat
goto fail

:done
echo.
echo ============================================================
echo   OK  -  FoxBin2Prg-Studio %VERSION%
echo.
echo   EXE      : %~dp0dist\FoxBin2Prg-Studio.exe
echo   Carpeta  : %~dp0release\FoxBin2Prg-Studio-%VERSION%\
if "%DOZIP%"=="1" echo   ZIP      : %~dp0release\FoxBin2Prg-Studio-%VERSION%.zip
if "%DOMSI%"=="1" echo   MSI      : %~dp0release\FoxBin2Prg-Studio-%VERSION%.msi
echo   GitHub   : %PUBSTATE%
echo.
echo   - El EXE lleva PySide6, el puente VFP y FoxBin2Prg adentro (onefile).
echo   - Para compartir: entrega el .zip o la carpeta de release.
if "%PUBSTATE%"=="publicado" echo   - Studio avisara de esta version a quien la busque en Preferencias.
echo ============================================================
echo.
if "%NOPAUSE%"=="0" pause
endlocal
exit /b 0

:fail
echo.
echo ============================================================
echo   FALLO  -  revisa el mensaje de arriba.
echo ============================================================
if "%NOPAUSE%"=="0" pause
endlocal
exit /b 1

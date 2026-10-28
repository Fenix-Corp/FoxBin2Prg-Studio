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
REM       resuelve build\build.bat) y dist\FoxBin2Prg-Studio-Launcher.exe (el
REM       lanzador, build\launcher.bat)
REM    5) Distribucion: release\FoxBin2Prg-Studio-<version>\ + .zip
REM    6) Opcional: .msi para IT (GPO / Intune)
REM    7) Publica el .exe, el lanzador y el .zip en el canal de actualizacion
REM       (GitHub, repo publico Fenix-Corp/Utilities-Dist). El equipo abre el
REM       LANZADOR, que baja y ejecuta la ultima version publicada.
REM       Solo sube una version NUEVA: si el Release ya existe, no toca nada.
REM
REM  LA VERSION no la asigna la compilacion sola: vive en un solo sitio, __version__
REM  de src\fb2p_studio\__init__.py (la lee build\version.py), y la sube una
REM  persona, igual que en UtilitiesDevelopment. El lanzador compara esa version
REM  contra lo que cada maquina ya tiene: un .exe nuevo con la MISMA version no
REM  llega al equipo.
REM    - Sin parametros y con consola, build_exe.bat PREGUNTA al compilar si subirla
REM      (Enter = patch). Con --nopause, sin consola o sin publicacion, NO pregunta
REM      y NO sube nada: un build automatico no publica por accidente.
REM    - El .bat no hace commit ni push del codigo; solo deja __init__.py modificado.
REM
REM  Opciones:
REM    --bump TIPO  sube la version sin preguntar: patch (0.1.0 -> 0.1.1),
REM                 minor (0.2.0) o major (1.0.0)
REM    --nobump     no pregunta ni sube la version (compila con la actual)
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
set "BUMP="
set "NOBUMP=0"
set "PUBSTATE=omitido"

:parse_args
if "%~1"=="" goto after_args
if /i "%~1"=="--nobump"    set "NOBUMP=1"
if /i "%~1"=="--bump" (
  set "BUMP=%~2"
  shift
)
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

REM --bump solo admite estos tres; mejor fallar aqui que a mitad del build.
if not defined BUMP goto bump_ok
if /i "%BUMP%"=="patch" goto bump_ok
if /i "%BUMP%"=="minor" goto bump_ok
if /i "%BUMP%"=="major" goto bump_ok
echo [ERROR] --bump necesita patch, minor o major ^(se recibio "%BUMP%"^).
goto fail
:bump_ok

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

REM --- Version: la que hay, o la que se sube con --bump ------------------------
REM Va ANTES de las pruebas y de compilar: lo que se prueba, se empaqueta y se
REM publica es siempre la misma version. La compilacion en si no la cambia.
if defined BUMP (
  echo.
  echo Subiendo la version ^(%BUMP%^) ...
  "%PY%" build\version.py --bump %BUMP% >nul
  if errorlevel 1 (
    echo [ERROR] No se pudo subir la version ^(build\version.py^).
    goto fail
  )
)
REM Sin --bump ni --nobump, con consola y con publicacion prevista: pregunta si
REM subirla. version.py solo pregunta ante una consola real; --nopause tambien lo
REM evita (build automatico). Sin respuesta clara deja la version como esta.
if defined BUMP goto ask_done
if "%NOBUMP%"=="1" goto ask_done
if "%NOPAUSE%"=="1" goto ask_done
if "%DOPUBLISH%"=="0" goto ask_done
"%PY%" build\version.py --ask
if errorlevel 1 (
  echo [ERROR] No se pudo consultar la version ^(build\version.py^).
  goto fail
)
:ask_done
set "VERSION="
for /f "delims=" %%v in ('"%PY%" build\version.py') do set "VERSION=%%v"
if "%VERSION%"=="" (
  echo [ERROR] No pude leer la version ^(build\version.py^).
  goto fail
)
echo.
echo Version: %VERSION%

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
echo.
echo       Lanzador ...
call build\launcher.bat
if errorlevel 1 (
  echo [ERROR] Fallo la compilacion del lanzador.
  goto fail
)
if not exist "dist\FoxBin2Prg-Studio-Launcher.exe" (
  echo [ERROR] No se genero dist\FoxBin2Prg-Studio-Launcher.exe.
  goto fail
)

REM --- 5) Distribucion --------------------------------------------------------
echo.
echo [5/7] Armando el paquete de distribucion ...
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
echo   Lanzador : %~dp0dist\FoxBin2Prg-Studio-Launcher.exe
echo   Carpeta  : %~dp0release\FoxBin2Prg-Studio-%VERSION%\
if "%DOZIP%"=="1" echo   ZIP      : %~dp0release\FoxBin2Prg-Studio-%VERSION%.zip
if "%DOMSI%"=="1" echo   MSI      : %~dp0release\FoxBin2Prg-Studio-%VERSION%.msi
echo   GitHub   : %PUBSTATE%
echo.
echo   - El EXE lleva PySide6, el puente VFP y FoxBin2Prg adentro (onefile).
echo   - Para compartir: entrega el LANZADOR (acceso directo) o el .zip.
if "%PUBSTATE%"=="publicado" echo   - Quien abra el lanzador recibira esta version.
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

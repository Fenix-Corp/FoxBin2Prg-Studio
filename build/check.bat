@echo off
REM ==========================================================================
REM  check.bat - gate de calidad: lint + tests (+ build opcional)
REM
REM  Es lo mismo que corre CI. Si esto pasa en tu maquina, CI no te va a
REM  sorprender.
REM
REM  Uso:
REM    build\check.bat            lint + tests
REM    build\check.bat --build    lint + tests + compila el .exe
REM    build\check.bat --fix      aplica los autofixes de ruff y despues corre
REM ==========================================================================
setlocal enabledelayedexpansion
pushd "%~dp0.."

set "PY=.venv\Scripts\python.exe"
set "DOBUILD=0"
set "DOFIX=0"

:parse_args
if "%~1"=="" goto after_args
if /i "%~1"=="--build" set "DOBUILD=1"
if /i "%~1"=="--fix"   set "DOFIX=1"
shift
goto parse_args
:after_args

if not exist "%PY%" (
    echo [check] No hay .venv. Crealo con:
    echo    py -3 -m venv .venv
    echo    .venv\Scripts\pip install -e .[dev]
    goto :fail
)

REM Las dependencias de dev tienen que estar: sin ruff no hay lint, y sin el
REM paquete instalado en editable pytest no encuentra fb2p_studio.
"%PY%" -c "import ruff, pytest, fb2p_studio" >nul 2>nul
if errorlevel 1 (
    echo [check] Faltan dependencias de desarrollo. Instalalas con:
    echo    .venv\Scripts\python.exe -m pip install -e .[dev]
    goto :fail
)

if "%DOFIX%"=="1" (
    echo [check] ruff --fix
    "%PY%" -m ruff check . --fix
    echo.
)

echo [check] 1/2 - lint (ruff)
"%PY%" -m ruff check .
if errorlevel 1 (
    echo.
    echo [check] Lint con errores. Proba: build\check.bat --fix
    goto :fail
)

echo.
echo [check] 2/2 - tests (pytest)
"%PY%" -m pytest -q
if errorlevel 1 (
    echo.
    echo [check] Tests en rojo.
    goto :fail
)

if "%DOBUILD%"=="1" (
    echo.
    echo [check] extra - build del .exe
    call build\build.bat
    if errorlevel 1 goto :fail
)

echo.
echo [check] OK - todo verde.
popd
endlocal
exit /b 0

:fail
echo.
echo [check] FALLO.
popd
endlocal
exit /b 1

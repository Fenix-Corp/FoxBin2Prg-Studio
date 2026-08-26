@echo off
REM ==========================================================================
REM  i18n.bat - extrae y compila las traducciones de la UI
REM
REM  El idioma fuente es el espanol: las cadenas viven en el codigo tal cual
REM  se ven. Este script arma un .ts por idioma destino con todo lo que este
REM  envuelto en self.tr(...), y lo compila a .qm (que es lo que carga la app).
REM
REM  Flujo:
REM    1) build\i18n.bat extract      actualiza los .ts con las cadenas nuevas
REM    2) abrir el .ts con Qt Linguist y traducir
REM       (.venv\Scripts\pyside6-linguist.exe src\fb2p_studio\resources\i18n\fb2p_studio_en.ts)
REM    3) build\i18n.bat release      compila los .ts a .qm
REM
REM  Sin argumento hace las dos cosas.
REM
REM  Para agregar un idioma: sumarlo a IDIOMAS y correr extract.
REM ==========================================================================
setlocal enabledelayedexpansion
pushd "%~dp0.."

REM Idiomas destino (el espanol NO va: es el idioma fuente).
set "IDIOMAS=en"

set "I18N=src\fb2p_studio\resources\i18n"
set "FUENTES=src\fb2p_studio\ui src\fb2p_studio\app.py"
set "LUPDATE=.venv\Scripts\pyside6-lupdate.exe"
set "LRELEASE=.venv\Scripts\pyside6-lrelease.exe"

set "MODO=%~1"
if "%MODO%"=="" set "MODO=all"

if not exist "%LUPDATE%" (
    echo [i18n] Falta pyside6-lupdate. Instala las dependencias:
    echo    .venv\Scripts\python.exe -m pip install -e .[dev]
    goto :fail
)
if not exist "%I18N%" mkdir "%I18N%"

if /i "%MODO%"=="release" goto :release

REM --- extract ---------------------------------------------------------------
REM  -extensions py: la lista por defecto de lupdate es de C++/QML y NO trae
REM  .py, asi que al pasarle un directorio no encuentra una sola cadena.
REM  OJO: las opciones van ANTES de las fuentes; puestas despues, lupdate las
REM  ignora en silencio y reporta "Found 0 source text(s)".
for %%L in (%IDIOMAS%) do (
    echo [i18n] extract -^> %I18N%\fb2p_studio_%%L.ts
    "%LUPDATE%" -extensions py -no-obsolete -source-language es -target-language %%L %FUENTES% -ts "%I18N%\fb2p_studio_%%L.ts"
    if errorlevel 1 goto :fail
)
if /i "%MODO%"=="extract" goto :done

:release
REM --- release ---------------------------------------------------------------
for %%L in (%IDIOMAS%) do (
    if exist "%I18N%\fb2p_studio_%%L.ts" (
        echo [i18n] release -^> %I18N%\fb2p_studio_%%L.qm
        "%LRELEASE%" "%I18N%\fb2p_studio_%%L.ts" -qm "%I18N%\fb2p_studio_%%L.qm"
        if errorlevel 1 goto :fail
    ) else (
        echo [i18n] no hay %I18N%\fb2p_studio_%%L.ts, corre primero: build\i18n.bat extract
    )
)

:done
echo.
echo [i18n] OK.
popd
endlocal
exit /b 0

:fail
echo.
echo [i18n] FALLO.
popd
endlocal
exit /b 1

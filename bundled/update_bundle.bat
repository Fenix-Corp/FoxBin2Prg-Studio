@echo off
REM ==========================================================================
REM  update_bundle.bat — copia los archivos redistribuibles de FoxBin2Prg
REM  Uso: update_bundle.bat [ruta_a_foxbin2prg]
REM  Si no se pasa ruta, usa la variable FB2P_HOME.
REM ==========================================================================
setlocal
set "SRC=%~1"
if "%SRC%"=="" set "SRC=%FB2P_HOME%"
if "%SRC%"=="" (
  echo [update_bundle] Necesito ruta al clon de FoxBin2Prg. Uso:
  echo   update_bundle.bat "D:\path\to\foxbin2prg"
  exit /b 1
)
if not exist "%SRC%\FoxBin2Prg.EXE" (
  echo [update_bundle] No se encontro FoxBin2Prg.EXE en "%SRC%".
  echo Compilalo primero desde ese repo con: DO ReCreate_FoxBin2Prg.prg (o BUILD EXE).
  exit /b 1
)

set "DST=%~dp0foxbin2prg"
copy /y "%SRC%\FoxBin2Prg.EXE"      "%DST%\"  || exit /b 1
copy /y "%SRC%\filename_caps.exe"   "%DST%\"  || exit /b 1
copy /y "%SRC%\filename_caps.cfg"   "%DST%\"  || exit /b 1
copy /y "%SRC%\foxbin2prg.pj2"      "%DST%\"  || exit /b 1

echo.
echo [update_bundle] Bundle actualizado desde "%SRC%".
endlocal

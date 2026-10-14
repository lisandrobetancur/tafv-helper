@echo off
:: Biblioteca de Estudio - instalar (Windows). Doble clic para ejecutar.
:: Si Windows muestra "Windows protegio su PC": "Mas informacion" y luego "Ejecutar de todas formas".
setlocal
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"

set "PYTHON="
for %%V in (3.13 3.12 3.11 3.14) do (
  if not defined PYTHON (
    py -%%V -c "import sys" >nul 2>&1 && set "PYTHON=py -%%V"
  )
)
if not defined PYTHON (
  python -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>&1 && set "PYTHON=python"
)
if not defined PYTHON (
  echo.
  echo   No se encontro Python 3.11 o superior.
  echo   Instala Python 3.13 desde https://www.python.org/downloads/
  echo   y marca la casilla "Add python.exe to PATH". Instrucciones en INSTALACION.md
  echo.
  pause
  exit /b 1
)

%PYTHON% instalador.py instalar
set ESTADO=%ERRORLEVEL%
echo.
pause
exit /b %ESTADO%

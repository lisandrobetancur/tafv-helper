@echo off
:: Construye la version de escritorio y su instalador (Windows). Requiere Python 3.11+ e Inno Setup 6 (gratis).
setlocal
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"
py -3.13 -m venv .venv-escritorio 2>nul || python -m venv .venv-escritorio
call .venv-escritorio\Scripts\activate.bat
python -m pip install --disable-pip-version-check -q --upgrade pip
python -m pip install --disable-pip-version-check -q -r requirements-escritorio.txt || goto :error
python escritorio\construir.py || goto :error
echo.
echo   Listo. El instalador esta en la carpeta dist.
pause
exit /b 0
:error
echo.
echo   No se pudo construir. Revisa los mensajes de arriba.
pause
exit /b 1

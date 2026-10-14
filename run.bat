@echo off
rem Windows: doble clic o ejecutar run.bat
cd /d "%~dp0"
where py >nul 2>nul && (py -3 run.py %* & goto :eof)
where python >nul 2>nul && (python run.py %* & goto :eof)
echo No se encontro Python 3.10+. Instalalo desde https://www.python.org/downloads/
pause

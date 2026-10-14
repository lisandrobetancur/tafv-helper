@echo off
rem Compila app\static\src\app.css -> app\static\css\app.css (solo desarrollo).
rem Necesita tools\tailwindcss.exe (tailwindcss-windows-x64.exe de https://github.com/tailwindlabs/tailwindcss/releases/tag/v4.3.3)
cd /d "%~dp0\.."
tools\tailwindcss.exe -i app\static\src\app.css -o app\static\css\app.css --minify %*

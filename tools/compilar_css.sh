#!/usr/bin/env bash
# Compila app/static/src/app.css -> app/static/css/app.css (solo desarrollo).
# Necesita el binario standalone de Tailwind en tools/tailwindcss:
#   https://github.com/tailwindlabs/tailwindcss/releases/tag/v4.3.3  (tailwindcss-macos-arm64 / -macos-x64)
# Uso: tools/compilar_css.sh [--watch]
cd "$(dirname "$0")/.."
exec tools/tailwindcss -i app/static/src/app.css -o app/static/css/app.css --minify "$@"

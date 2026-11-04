#!/bin/bash
# Construye la versión de escritorio y su .dmg (Mac). Requiere Python 3.11+ (de python.org).
set -e
cd "$(dirname "$0")"
PY=$(command -v python3.13 || command -v python3)
"$PY" -m venv .venv-escritorio
source .venv-escritorio/bin/activate
python -m pip install --disable-pip-version-check -q --upgrade pip
python -m pip install --disable-pip-version-check -q -r requirements-escritorio.txt
python escritorio/construir.py
echo
echo "  Listo. El .dmg está en la carpeta dist."

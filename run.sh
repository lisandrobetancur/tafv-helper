#!/usr/bin/env bash
# macOS / Linux: ./run.sh
cd "$(dirname "$0")"
for py in python3 python3.14 python3.13 python3.12 python3.11 python3.10 python; do
  if command -v "$py" >/dev/null 2>&1 && "$py" -c "import sys; sys.exit(sys.version_info < (3,10))" 2>/dev/null; then
    exec "$py" run.py "$@"
  fi
done
echo "No se encontró Python 3.10+. Instálalo desde https://www.python.org/downloads/" >&2
exit 1

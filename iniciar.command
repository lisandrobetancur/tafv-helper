#!/bin/bash
# Biblioteca de Estudio — iniciar (Mac). Doble clic para abrir la biblioteca en el navegador.
# Para cerrarla, cierra esta ventana. Si macOS no deja abrirlo la primera vez, mira INSTALACION.md.
cd "$(dirname "$0")" || exit 1

buscar_python() {
  # Primero versiones concretas (instalador de python.org y Homebrew), luego "python3".
  # Se evita el /usr/bin/python3 de Apple (3.9), que además puede pedir instalar herramientas de Xcode.
  for candidato in python3.13 python3.12 python3.11 \
      /Library/Frameworks/Python.framework/Versions/3.13/bin/python3 \
      /Library/Frameworks/Python.framework/Versions/3.12/bin/python3 \
      /Library/Frameworks/Python.framework/Versions/3.11/bin/python3 \
      /opt/homebrew/bin/python3.13 /opt/homebrew/bin/python3.12 /opt/homebrew/bin/python3.11 \
      /usr/local/bin/python3.13 /usr/local/bin/python3.12 /usr/local/bin/python3.11 \
      python3.14 python3; do
    ruta=$(command -v "$candidato" 2>/dev/null) || continue
    [ "$ruta" = "/usr/bin/python3" ] && continue
    if "$ruta" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; then
      echo "$ruta"
      return 0
    fi
  done
  return 1
}

PYTHON=$(buscar_python)
if [ -z "$PYTHON" ]; then
  echo ""
  echo "  No se encontró Python 3.11 o superior."
  echo "  Instala Python 3.13 desde https://www.python.org/downloads/ y vuelve a intentarlo."
  echo "  (Las instrucciones están en INSTALACION.md)"
  echo ""
  read -r -p "  Pulsa Enter para cerrar…" _
  exit 1
fi

"$PYTHON" instalador.py iniciar "$@"
estado=$?
if [ $estado -ne 0 ]; then
  echo ""
  read -r -p "  Pulsa Enter para cerrar esta ventana…" _
fi
exit $estado

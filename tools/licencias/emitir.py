"""Emite la licencia de un equipo.

    python tools/licencias/emitir.py CODIGO-DEL-EQUIPO --nombre "Nombre de la persona" [--carpeta RUTA]
    python tools/licencias/emitir.py cualquiera --dias 8 --nombre "Prueba"      (licencia temporal)

El código lo ve la persona en la pantalla de activación del programa y te lo envía. La licencia que se imprime
se la devuelves para que la pegue allí. No vence, salvo que se emita con --dias; con el código «cualquiera»
vale en cualquier equipo (útil con --dias para repartir una versión de prueba). Cada emisión queda anotada en
registro.csv (en la misma carpeta de la clave privada).
"""
from __future__ import annotations

import argparse
import csv
import sys
from datetime import datetime
from pathlib import Path

from cryptography.hazmat.primitives import serialization

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from app.services.licencia import CUALQUIER_EQUIPO, emitir, normalizar_codigo  # noqa: E402

CARPETA = Path.home() / "LicenciasBiblioteca"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("codigo", help="código de equipo (p. ej. 7K3M-QWXD-2RPA-F4TB) o «cualquiera»")
    parser.add_argument("--nombre", default="", help="a quién se entrega (aparece en el programa)")
    parser.add_argument("--dias", type=int, default=None, help="licencia temporal: vence este número de días desde hoy")
    parser.add_argument("--carpeta", type=Path, default=CARPETA, help="carpeta de la clave privada")
    args = parser.parse_args()
    cualquiera = args.codigo.strip().lower() in ("cualquiera", "cualquier equipo", CUALQUIER_EQUIPO)
    codigo = CUALQUIER_EQUIPO if cualquiera else normalizar_codigo(args.codigo)
    if not cualquiera and len(codigo) != 19:
        sys.exit("El código de equipo tiene 16 caracteres en 4 grupos (p. ej. 7K3M-QWXD-2RPA-F4TB). Revísalo.")
    if cualquiera and not args.dias:
        sys.exit("Una licencia para cualquier equipo debe ser temporal: agrega --dias (p. ej. --dias 8).")
    if args.dias is not None and args.dias < 1:
        sys.exit("--dias debe ser 1 o más.")
    privada_pem = args.carpeta / "clave_privada.pem"
    if not privada_pem.exists():
        sys.exit(f"No se encontró {privada_pem}. Créala una vez con: python tools/licencias/crear_claves.py")
    clave = serialization.load_pem_private_key(privada_pem.read_bytes(), password=None)
    licencia = emitir(clave, codigo, args.nombre, dias=args.dias)
    registro = args.carpeta / "registro.csv"
    nuevo = not registro.exists()
    with registro.open("a", newline="", encoding="utf-8") as f:
        escritor = csv.writer(f)
        if nuevo:
            escritor.writerow(["fecha", "codigo_equipo", "nombre", "licencia"])
        escritor.writerow([datetime.now().isoformat(timespec="seconds"), codigo, args.nombre, licencia])
    detalle = "cualquier equipo" if cualquiera else codigo
    if args.dias:
        from datetime import date, timedelta
        detalle += f", vence el {(date.today() + timedelta(days=args.dias)).strftime('%d/%m/%Y')}"
    print(f"Licencia para {detalle}{' (' + args.nombre + ')' if args.nombre else ''}:\n")
    print(licencia)


if __name__ == "__main__":
    main()

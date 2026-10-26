"""Comprueba que todo lo cargado en la biblioteca sea tenido en cuenta por Acceso rápido.

    .venv/bin/python tools/carga/verificar_acceso_rapido.py

Busca cada fila de tabla, nota e imagen vigente (fuera de la papelera) por su título y por una palabra de
su contenido, y comprueba que aparezca como candidata. Sale con código 1 si alguna no aparece.
Para revisar otra carpeta de datos (p. ej. la copia de `cargar.py --prueba`), define BIBLIOTECA_DATOS.
"""
from __future__ import annotations

import sys
from collections import Counter

import comun  # noqa: F401

from app import db
from app.services import diagnostico as dg


def main() -> int:
    con = db.conectar()
    revisados, faltantes = dg.revisar_cobertura(con)
    por_tipo = Counter(r[0] for r in con.execute(
        "SELECT 'filas' FROM filas f JOIN tablas t ON t.id = f.tabla_id WHERE t.papelera_id IS NULL AND f.huerfana = 0 "
        "UNION ALL SELECT 'notas' FROM notas WHERE papelera_id IS NULL "
        "UNION ALL SELECT 'imágenes' FROM imagenes WHERE papelera_id IS NULL"))
    print(f"Elementos revisados: {revisados} ({', '.join(f'{n} {t}' for t, n in por_tipo.items())})")
    for f in faltantes:
        print(f"FALTA  {f.materia} › {f.contenedor} · {f.tipo} {f.id} «{f.titulo}»: {f.motivo}"
              + (f" («{f.busqueda}»)" if f.busqueda else ""))
    print("\nCORRECTO: todo aparece en Acceso rápido" if not faltantes else f"\n{len(faltantes)} FALTANTES")
    return 1 if faltantes else 0


if __name__ == "__main__":
    sys.exit(main())

"""Modo repaso (flashcards) a partir de una tabla: una columna es el frente y otra el reverso.

Cada fila se puede marcar "lo sé" o "repasar"; la marca se guarda para poder repasar
después solo las que faltan.
"""
from __future__ import annotations

import json
import random
import sqlite3

from ..db import ahora
from ..errores import ErrorUsuario
from ..models import Tabla

ESTADOS = {"lo_se", "repasar"}
CUALES = {"todas": "Todas", "repasar": "Solo las marcadas «repasar»", "sin_marcar": "Solo las que aún no marqué"}
MAX_TARJETAS = 3000


def tarjetas(con: sqlite3.Connection, t: Tabla, frente: str, reverso: str, cuales: str = "todas",
             barajar: bool = True, imagenes: bool = True) -> list[dict]:
    if frente not in t.claves or reverso not in t.claves:
        raise ErrorUsuario("Elige una columna para el frente y otra para el reverso.")
    if frente == reverso:
        raise ErrorUsuario("El frente y el reverso deben ser columnas distintas.")
    sql = """SELECT f.id, f.valores, r.estado FROM filas f LEFT JOIN repaso r ON r.fila_id = f.id
             WHERE f.tabla_id = ?"""
    if cuales == "repasar":
        sql += " AND r.estado = 'repasar'"
    elif cuales == "sin_marcar":
        sql += " AND r.estado IS NULL"
    salida = []
    for f in con.execute(sql + " ORDER BY f.posicion LIMIT ?", (t.id, MAX_TARJETAS)):
        valores = json.loads(f["valores"])
        if not (valores.get(frente, "").strip() or valores.get(reverso, "").strip()):
            continue
        salida.append({"fila_id": f["id"], "frente": valores.get(frente, ""), "reverso": valores.get(reverso, ""),
                       "estado": f["estado"], "imagenes": []})
    if imagenes and salida:
        por_fila: dict[int, list] = {}
        ids = [c["fila_id"] for c in salida]
        for i in range(0, len(ids), 900):
            lote = ids[i:i + 900]
            for img in con.execute(
                    f"""SELECT id, fila_id, titulo, pie FROM imagenes_fila WHERE papelera_id IS NULL
                        AND fila_id IN ({','.join('?' * len(lote))}) ORDER BY orden, id""", lote):
                por_fila.setdefault(img["fila_id"], []).append(
                    {"src": f"/imagenes-fila/{img['id']}/archivo", "mini": f"/imagenes-fila/{img['id']}/miniatura",
                     "titulo": img["titulo"], "pie": img["pie"]})
        for c in salida:
            c["imagenes"] = por_fila.get(c["fila_id"], [])
    if barajar:
        random.shuffle(salida)
    return salida


def marcar(con: sqlite3.Connection, fila_id: int, estado: str) -> None:
    if estado not in ESTADOS:
        raise ErrorUsuario("Estado no válido.")
    if con.execute("SELECT 1 FROM filas WHERE id=?", (fila_id,)).fetchone() is None:
        raise ErrorUsuario("Esa tarjeta ya no existe.")
    con.execute("INSERT INTO repaso (fila_id, estado, actualizado) VALUES (?,?,?) "
                "ON CONFLICT (fila_id) DO UPDATE SET estado = excluded.estado, actualizado = excluded.actualizado",
                (fila_id, estado, ahora()))


def resumen(con: sqlite3.Connection, tabla_id: int) -> dict[str, int]:
    fila = con.execute(
        """SELECT COUNT(*) AS total, SUM(r.estado = 'lo_se') AS lo_se, SUM(r.estado = 'repasar') AS repasar
           FROM filas f LEFT JOIN repaso r ON r.fila_id = f.id WHERE f.tabla_id = ?""", (tabla_id,)).fetchone()
    total, lo_se, repasar = fila["total"], fila["lo_se"] or 0, fila["repasar"] or 0
    return {"total": total, "lo_se": lo_se, "repasar": repasar, "sin_marcar": total - lo_se - repasar}


def reiniciar(con: sqlite3.Connection, tabla_id: int) -> None:
    con.execute("DELETE FROM repaso WHERE fila_id IN (SELECT id FROM filas WHERE tabla_id=?)", (tabla_id,))


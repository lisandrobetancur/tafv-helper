"""Etiquetas propias para cualquier elemento (imagen, nota, fila, PDF…).

Se escriben separadas por comas: "radiografía, miembro inferior". Se comparan sin tildes
ni mayúsculas, así que "Radiografia" y "radiografía" son la misma etiqueta.
"""
from __future__ import annotations

import sqlite3

from .texto import normalizar

TIPOS = {"imagen": "imagenes", "nota": "notas", "fila": "filas", "pdf": "pdfs", "tabla": "tablas"}
LARGO = 40


def separar(texto: str | list[str]) -> list[str]:
    """"radiografía, Fémur ,fémur" -> ["radiografía", "Fémur"] (sin repetidas, en orden)."""
    partes = texto if isinstance(texto, list) else (texto or "").replace(";", ",").split(",")
    vistas, salida = set(), []
    for p in partes:
        nombre = " ".join(p.split()).strip("#")[:LARGO]
        if nombre and normalizar(nombre) not in vistas:
            vistas.add(normalizar(nombre))
            salida.append(nombre)
    return salida


def _id_etiqueta(con: sqlite3.Connection, nombre: str) -> int:
    clave = normalizar(nombre)
    fila = con.execute("SELECT id FROM etiquetas WHERE clave=?", (clave,)).fetchone()
    if fila:
        return fila[0]
    return int(con.execute("INSERT INTO etiquetas (nombre, clave) VALUES (?,?)", (nombre, clave)).lastrowid)


def asignar(con: sqlite3.Connection, tipo: str, ref_id: int, etiquetas: str | list[str]) -> list[str]:
    """Reemplaza las etiquetas del elemento."""
    nombres = separar(etiquetas)
    con.execute("DELETE FROM etiquetas_elemento WHERE tipo=? AND ref_id=?", (tipo, ref_id))
    con.executemany("INSERT OR IGNORE INTO etiquetas_elemento (etiqueta_id, tipo, ref_id) VALUES (?,?,?)",
                    [(_id_etiqueta(con, n), tipo, ref_id) for n in nombres])
    return nombres


def de(con: sqlite3.Connection, tipo: str, ref_id: int) -> list[str]:
    return [r[0] for r in con.execute(
        """SELECT e.nombre FROM etiquetas e JOIN etiquetas_elemento x ON x.etiqueta_id = e.id
           WHERE x.tipo=? AND x.ref_id=? ORDER BY e.clave""", (tipo, ref_id))]


def de_varios(con: sqlite3.Connection, tipo: str, ids: list[int]) -> dict[int, list[str]]:
    if not ids:
        return {}
    marcas = ",".join("?" * len(ids))
    salida: dict[int, list[str]] = {i: [] for i in ids}
    for ref_id, nombre in con.execute(
            f"""SELECT x.ref_id, e.nombre FROM etiquetas e JOIN etiquetas_elemento x ON x.etiqueta_id = e.id
                WHERE x.tipo=? AND x.ref_id IN ({marcas}) ORDER BY e.clave""", (tipo, *ids)):
        salida[ref_id].append(nombre)
    return salida


def limpiar_huerfanas(con: sqlite3.Connection) -> None:
    """Quita asociaciones de elementos que ya no existen y etiquetas que nadie usa."""
    for tipo, tabla in TIPOS.items():
        con.execute(f"DELETE FROM etiquetas_elemento WHERE tipo=? AND ref_id NOT IN (SELECT id FROM {tabla})", (tipo,))
    con.execute("DELETE FROM etiquetas WHERE id NOT IN (SELECT etiqueta_id FROM etiquetas_elemento)")

"""Papelera interna: lo eliminado se mueve a data/papelera/ y se puede restaurar o vaciar."""
from __future__ import annotations

import logging
import sqlite3

from ..config import rutas
from ..db import ahora, transaccion
from ..errores import ErrorUsuario, NoEncontrado
from ..models import ElementoPapelera
from . import almacenamiento as alm
from . import biblioteca as bib

log = logging.getLogger(__name__)


def listar(con: sqlite3.Connection) -> list[ElementoPapelera]:
    return [ElementoPapelera.desde_fila(f) for f in con.execute("SELECT * FROM papelera ORDER BY eliminado DESC, id DESC")]


def contar(con: sqlite3.Connection) -> int:
    return con.execute("SELECT COUNT(*) FROM papelera").fetchone()[0]


def _registrar(con: sqlite3.Connection, tipo: str, ref_id: int, nombre: str, ubicacion: str) -> int:
    cur = con.execute(
        "INSERT INTO papelera (tipo, ref_id, nombre, ubicacion, eliminado) VALUES (?,?,?,?,?)",
        (tipo, ref_id, nombre, ubicacion, ahora()),
    )
    return int(cur.lastrowid)


# ------------------------------------------------------------------- enviar
def enviar_materia(con: sqlite3.Connection, materia_id: int) -> str:
    m = bib.obtener_materia(con, materia_id)
    carpeta = bib.carpeta_materia(m)
    with transaccion(con):
        pid = _registrar(con, "materia", m.id, m.nombre, "")
        destino = alm.a_papelera(carpeta, f"{pid}-{m.slug}")
        con.execute("UPDATE papelera SET ruta_original=?, ruta_papelera=? WHERE id=?",
                    (rutas.relativa(carpeta) if carpeta.exists() else None, destino, pid))
        con.execute("UPDATE materias SET papelera_id=? WHERE id=?", (pid, m.id))
        con.execute("UPDATE componentes SET papelera_id=? WHERE materia_id=? AND papelera_id IS NULL", (pid, m.id))
    log.info("Materia enviada a la papelera: %s", m.nombre)
    return m.nombre


def enviar_componente(con: sqlite3.Connection, componente_id: int) -> tuple[str, int, int | None]:
    """Envía el componente y todos sus subcomponentes. Devuelve (nombre, materia_id, padre_id)."""
    c = bib.obtener_componente(con, componente_id)
    m = bib.obtener_materia(con, c.materia_id)
    ubicacion = " › ".join([m.nombre, *(a.nombre for a in bib.ancestros(con, c))])
    carpeta = bib.carpeta_componente(con, c)
    ids = [c.id, *bib.descendientes(con, c.id)]
    with transaccion(con):
        pid = _registrar(con, "componente", c.id, c.nombre, ubicacion)
        destino = alm.a_papelera(carpeta, f"{pid}-{c.slug}")
        con.execute("UPDATE papelera SET ruta_original=?, ruta_papelera=? WHERE id=?",
                    (rutas.relativa(carpeta) if carpeta.exists() else None, destino, pid))
        con.executemany("UPDATE componentes SET papelera_id=? WHERE id=?", [(pid, i) for i in ids])
    log.info("Componente enviado a la papelera: %s (%s elementos)", c.nombre, len(ids))
    return c.nombre, c.materia_id, c.padre_id


# ---------------------------------------------------------------- restaurar
def _fila(con: sqlite3.Connection, pid: int) -> sqlite3.Row:
    f = con.execute("SELECT * FROM papelera WHERE id=?", (pid,)).fetchone()
    if f is None:
        raise NoEncontrado("Ese elemento de la papelera")
    return f


def restaurar(con: sqlite3.Connection, pid: int) -> str:
    f = _fila(con, pid)
    if f["tipo"] == "materia":
        return _restaurar_materia(con, f)
    if f["tipo"] == "componente":
        return _restaurar_componente(con, f)
    raise ErrorUsuario("Este elemento no se puede restaurar.")


def _volver(f: sqlite3.Row, destino) -> None:
    if f["ruta_papelera"]:
        origen = rutas.absoluta(f["ruta_papelera"])
        if origen.exists():
            alm.mover_carpeta(origen, destino)
    destino.mkdir(parents=True, exist_ok=True)


def _restaurar_materia(con: sqlite3.Connection, f: sqlite3.Row) -> str:
    m = con.execute("SELECT * FROM materias WHERE id=?", (f["ref_id"],)).fetchone()
    nombre = m["nombre"]
    if con.execute("SELECT 1 FROM materias WHERE nombre=? COLLATE NOCASE AND papelera_id IS NULL", (nombre,)).fetchone():
        nombre = f"{nombre} (restaurada)"
    slug = alm.slug_unico(alm.slugify(nombre), bib._slugs_materias(con))
    with transaccion(con):
        con.execute("UPDATE materias SET papelera_id=NULL, nombre=?, slug=?, actualizado=? WHERE id=?",
                    (nombre, slug, ahora(), m["id"]))
        con.execute("UPDATE componentes SET papelera_id=NULL WHERE papelera_id=?", (f["id"],))
        con.execute("DELETE FROM papelera WHERE id=?", (f["id"],))
        _volver(f, rutas.archivos / slug)
    return nombre


def _restaurar_componente(con: sqlite3.Connection, f: sqlite3.Row) -> str:
    c = con.execute("SELECT * FROM componentes WHERE id=?", (f["ref_id"],)).fetchone()
    if c is None:
        raise NoEncontrado("El componente")
    materia_ok = con.execute("SELECT 1 FROM materias WHERE id=? AND papelera_id IS NULL", (c["materia_id"],)).fetchone()
    padre_ok = c["padre_id"] is None or con.execute(
        "SELECT 1 FROM componentes WHERE id=? AND papelera_id IS NULL", (c["padre_id"],)).fetchone()
    if not materia_ok or not padre_ok:
        raise ErrorUsuario("Primero restaura la materia o el componente que lo contenía.")
    nombre = c["nombre"]
    if bib._nombre_repetido(con, c["materia_id"], c["padre_id"], nombre):
        nombre = f"{nombre} (restaurado)"
    slug = alm.slug_unico(alm.slugify(nombre), bib._slugs_hermanos(con, c["materia_id"], c["padre_id"]))
    with transaccion(con):
        con.execute("UPDATE componentes SET papelera_id=NULL WHERE papelera_id=?", (f["id"],))
        con.execute("UPDATE componentes SET nombre=?, slug=?, actualizado=? WHERE id=?", (nombre, slug, ahora(), c["id"]))
        con.execute("DELETE FROM papelera WHERE id=?", (f["id"],))
        _volver(f, bib.carpeta_componente(con, bib.obtener_componente(con, c["id"])))
    return nombre


# ---------------------------------------------------------- borrar del todo
def eliminar_definitivo(con: sqlite3.Connection, pid: int) -> str:
    f = _fila(con, pid)
    # Elementos de la papelera que quedarían huérfanos (p. ej. componentes de esta materia
    # que se habían eliminado antes por separado): se borran junto con ella.
    if f["tipo"] == "materia":
        sub = "SELECT id FROM componentes WHERE materia_id = ?"
    else:
        sub = """WITH RECURSIVE s(id) AS (SELECT id FROM componentes WHERE id = ?
                 UNION ALL SELECT c.id FROM componentes c JOIN s ON c.padre_id = s.id) SELECT id FROM s"""
    huerfanos = con.execute(
        f"SELECT id, ruta_papelera FROM papelera WHERE tipo='componente' AND id != ? AND ref_id IN ({sub})",
        (pid, f["ref_id"]),
    ).fetchall()
    with transaccion(con):
        if f["tipo"] == "materia":
            con.execute("DELETE FROM materias WHERE id=?", (f["ref_id"],))
        elif f["tipo"] == "componente":
            con.execute("DELETE FROM componentes WHERE id=?", (f["ref_id"],))
        con.execute("DELETE FROM papelera WHERE id=?", (pid,))
        con.executemany("DELETE FROM papelera WHERE id=?", [(h["id"],) for h in huerfanos])
    alm.borrar_definitivo(f["ruta_papelera"])
    for h in huerfanos:
        alm.borrar_definitivo(h["ruta_papelera"])
    log.info("Eliminado definitivamente: %s", f["nombre"])
    return f["nombre"]


def vaciar(con: sqlite3.Connection) -> int:
    ids = [r[0] for r in con.execute("SELECT id FROM papelera ORDER BY id DESC")]
    for pid in ids:
        eliminar_definitivo(con, pid)
    return len(ids)

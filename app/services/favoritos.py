"""Favoritos (estrella) y recientes (últimos elementos abiertos)."""
from __future__ import annotations

import sqlite3
from datetime import datetime

from ..errores import ErrorUsuario
from . import elementos

TIPOS_FAVORITO = {"fila", "pdf", "imagen", "nota"}
TIPOS_RECIENTE = {"tabla", "fila", "pdf", "imagen", "nota"}
MAX_RECIENTES = 60


def ahora() -> str:
    """Con microsegundos: el orden de favoritos y recientes no depende del segundo."""
    return datetime.now().isoformat(timespec="microseconds")


def es_favorito(con: sqlite3.Connection, tipo: str, ref_id: int) -> bool:
    return con.execute("SELECT 1 FROM favoritos WHERE tipo=? AND ref_id=?", (tipo, ref_id)).fetchone() is not None


def alternar(con: sqlite3.Connection, tipo: str, ref_id: int) -> bool:
    """Marca o desmarca. Devuelve si quedó como favorito."""
    if tipo not in TIPOS_FAVORITO:
        raise ErrorUsuario("Este elemento no se puede marcar como favorito.")
    if not elementos.resolver(con, [(tipo, ref_id)]):
        raise ErrorUsuario("Ese elemento ya no existe.")
    if es_favorito(con, tipo, ref_id):
        con.execute("DELETE FROM favoritos WHERE tipo=? AND ref_id=?", (tipo, ref_id))
        return False
    con.execute("INSERT INTO favoritos (tipo, ref_id, creado) VALUES (?,?,?)", (tipo, ref_id, ahora()))
    return True


def favoritos(con: sqlite3.Connection, limite: int = 100) -> list[elementos.Elemento]:
    pares = [(f[0], f[1]) for f in con.execute("SELECT tipo, ref_id FROM favoritos ORDER BY creado DESC, rowid DESC LIMIT ?", (limite,))]
    return elementos.resolver(con, pares, ocultas=False)   # lo de materias ocultas no se muestra


def registrar_visita(con: sqlite3.Connection, tipo: str, ref_id: int) -> None:
    if tipo not in TIPOS_RECIENTE:
        return
    if any(e.oculta for e in elementos.resolver(con, [(tipo, ref_id)])):
        return   # lo de una materia oculta no deja rastro en «Abiertos recientemente»
    con.execute("INSERT INTO recientes (tipo, ref_id, visto) VALUES (?,?,?) "
                "ON CONFLICT (tipo, ref_id) DO UPDATE SET visto = excluded.visto", (tipo, ref_id, ahora()))
    con.execute("DELETE FROM recientes WHERE rowid NOT IN (SELECT rowid FROM recientes ORDER BY visto DESC, rowid DESC LIMIT ?)",
                (MAX_RECIENTES,))


def limpiar_favoritos(con: sqlite3.Connection) -> int:
    """Quita todas las estrellas (los elementos no se tocan)."""
    return con.execute("DELETE FROM favoritos").rowcount


def limpiar_recientes(con: sqlite3.Connection) -> int:
    """Vacía la lista de abiertos recientemente (los elementos no se tocan)."""
    return con.execute("DELETE FROM recientes").rowcount


def recientes(con: sqlite3.Connection, limite: int = 10) -> list[elementos.Elemento]:
    pares = [(f[0], f[1]) for f in con.execute(
        "SELECT tipo, ref_id FROM recientes ORDER BY visto DESC, rowid DESC LIMIT ?", (limite * 2,))]
    return elementos.resolver(con, pares, ocultas=False)[:limite]

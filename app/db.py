"""Conexión a SQLite y migraciones del esquema.

Se usa `journal_mode=DELETE` (no WAL) para que la carpeta del proyecto se
pueda copiar o sincronizar entre equipos sin dejar archivos -wal/-shm.
"""
from __future__ import annotations

import logging
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime

from .config import rutas

log = logging.getLogger(__name__)

# Cada migración se aplica una sola vez, en orden (PRAGMA user_version guarda la última aplicada).
MIGRACIONES: list[str] = [
    # 1 — materias, componentes (árbol) y papelera
    """
    CREATE TABLE materias (
        id           INTEGER PRIMARY KEY,
        nombre       TEXT    NOT NULL,
        slug         TEXT    NOT NULL,
        descripcion  TEXT    NOT NULL DEFAULT '',
        color        TEXT    NOT NULL,
        icono        TEXT    NOT NULL,
        orden        INTEGER NOT NULL DEFAULT 0,
        archivada    INTEGER NOT NULL DEFAULT 0,
        papelera_id  INTEGER,
        creado       TEXT    NOT NULL,
        actualizado  TEXT    NOT NULL
    );
    CREATE UNIQUE INDEX ux_materias_slug ON materias(slug) WHERE papelera_id IS NULL;

    CREATE TABLE componentes (
        id           INTEGER PRIMARY KEY,
        materia_id   INTEGER NOT NULL REFERENCES materias(id) ON DELETE CASCADE,
        padre_id     INTEGER REFERENCES componentes(id) ON DELETE CASCADE,
        nombre       TEXT    NOT NULL,
        slug         TEXT    NOT NULL,
        descripcion  TEXT    NOT NULL DEFAULT '',
        tipos        TEXT    NOT NULL DEFAULT '[]',
        orden        INTEGER NOT NULL DEFAULT 0,
        papelera_id  INTEGER,
        creado       TEXT    NOT NULL,
        actualizado  TEXT    NOT NULL
    );
    CREATE UNIQUE INDEX ux_componentes_slug
        ON componentes(materia_id, COALESCE(padre_id, 0), slug) WHERE papelera_id IS NULL;
    CREATE INDEX ix_componentes_padre ON componentes(materia_id, padre_id);

    CREATE TABLE papelera (
        id             INTEGER PRIMARY KEY,
        tipo           TEXT NOT NULL,          -- materia | componente | (más adelante: archivos)
        ref_id         INTEGER NOT NULL,
        nombre         TEXT NOT NULL,
        ubicacion      TEXT NOT NULL DEFAULT '', -- texto legible: "Anatomía › Parcial 1"
        ruta_original  TEXT,                     -- relativa a data/
        ruta_papelera  TEXT,                     -- relativa a data/
        eliminado      TEXT NOT NULL
    );
    """,
]


def ahora() -> str:
    return datetime.now().isoformat(timespec="seconds")


def conectar() -> sqlite3.Connection:
    # isolation_level=None: cada sentencia se confirma sola; las escrituras de varios
    # pasos usan `transaccion()` para que no queden a medias.
    con = sqlite3.connect(rutas.db, timeout=10, check_same_thread=False, isolation_level=None)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.execute("PRAGMA journal_mode = DELETE")
    con.execute("PRAGMA synchronous = FULL")
    con.execute("PRAGMA busy_timeout = 10000")
    return con


def inicializar() -> None:
    """Crea la base de datos si no existe y aplica las migraciones pendientes."""
    rutas.crear_carpetas()
    con = conectar()
    try:
        version = con.execute("PRAGMA user_version").fetchone()[0]
        for numero, sql in enumerate(MIGRACIONES[version:], start=version + 1):
            log.info("Aplicando migración %s", numero)
            con.executescript(f"BEGIN;\n{sql}\nPRAGMA user_version = {numero};\nCOMMIT;")
        # Comprobación temprana de FTS5 (necesario para la búsqueda)
        con.execute("CREATE VIRTUAL TABLE IF NOT EXISTS temp.prueba_fts USING fts5(x)")
    finally:
        con.close()


def obtener_db() -> Iterator[sqlite3.Connection]:
    """Dependencia de FastAPI: una conexión por petición."""
    con = conectar()
    try:
        yield con
    finally:
        con.close()


@contextmanager
def transaccion(con: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """Agrupa escrituras: si algo falla, no queda nada a medias."""
    try:
        con.execute("BEGIN")
        yield con
        con.execute("COMMIT")
    except BaseException:
        con.execute("ROLLBACK")
        raise

"""Materias y componentes (árbol: componente › subcomponente › …).

Cada materia y cada componente tiene una carpeta legible en data/archivos:
    data/archivos/<materia-slug>/<componente-slug>/<subcomponente-slug>/
Al renombrar se mueve la carpeta; al eliminar se envía a la papelera.
"""
from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path

from ..config import COLOR_POR_ID, ICONOS_VALIDOS, PROFUNDIDAD_MAXIMA, TIPOS_CONTENIDO, rutas
from ..db import ahora, transaccion
from ..errores import ErrorUsuario, NoEncontrado
from ..models import Componente, Materia
from . import almacenamiento as alm

log = logging.getLogger(__name__)

LARGO_NOMBRE = 80
LARGO_DESCRIPCION = 600


# ---------------------------------------------------------------- validación
def _limpiar_nombre(nombre: str, que: str) -> str:
    nombre = " ".join((nombre or "").split())
    if not nombre:
        raise ErrorUsuario(f"Escribe un nombre para {que}.")
    if len(nombre) > LARGO_NOMBRE:
        raise ErrorUsuario(f"El nombre es muy largo (máximo {LARGO_NOMBRE} caracteres).")
    return nombre


def _limpiar_descripcion(texto: str) -> str:
    texto = (texto or "").strip()
    if len(texto) > LARGO_DESCRIPCION:
        raise ErrorUsuario(f"La descripción es muy larga (máximo {LARGO_DESCRIPCION} caracteres).")
    return texto


# ================================================================== materias
def carpeta_materia(m: Materia) -> Path:
    return rutas.archivos / m.slug


def listar_materias(con: sqlite3.Connection, archivadas: bool | None = False) -> list[Materia]:
    """archivadas=False: activas; True: solo archivadas; None: todas."""
    filtro = "" if archivadas is None else f"AND archivada = {int(archivadas)}"
    filas = con.execute(
        f"""SELECT m.*,
                   (SELECT COUNT(*) FROM componentes c WHERE c.materia_id = m.id AND c.papelera_id IS NULL) AS n_comp
            FROM materias m WHERE papelera_id IS NULL {filtro} ORDER BY orden, nombre COLLATE NOCASE"""
    ).fetchall()
    materias = []
    for f in filas:
        m = Materia.desde_fila(f)
        m.num_componentes = f["n_comp"]
        m.num_elementos = contar_elementos_materia(con, m.id)
        materias.append(m)
    return materias


def obtener_materia(con: sqlite3.Connection, materia_id: int) -> Materia:
    f = con.execute("SELECT * FROM materias WHERE id = ? AND papelera_id IS NULL", (materia_id,)).fetchone()
    if f is None:
        raise NoEncontrado("La materia")
    return Materia.desde_fila(f)


def _validar_materia(con: sqlite3.Connection, nombre: str, color: str, icono: str, excluir: int | None = None) -> None:
    if color not in COLOR_POR_ID:
        raise ErrorUsuario("Elige un color de la lista.")
    if icono not in ICONOS_VALIDOS:
        raise ErrorUsuario("Elige un ícono de la lista.")
    otra = con.execute(
        "SELECT id, archivada FROM materias WHERE nombre = ? COLLATE NOCASE AND papelera_id IS NULL AND id IS NOT ?",
        (nombre, excluir),
    ).fetchone()
    if otra and otra["archivada"]:
        raise ErrorUsuario(f"Ya existe una materia llamada «{nombre}», pero está archivada. "
                           "Búscala en «Archivadas», al final del inicio, y vuelve a activarla.")
    if otra:
        raise ErrorUsuario(f"Ya existe una materia llamada «{nombre}».")


def _slugs_materias(con: sqlite3.Connection, excluir: int | None = None) -> set[str]:
    return {r[0] for r in con.execute(
        "SELECT slug FROM materias WHERE papelera_id IS NULL AND id IS NOT ?", (excluir,))}


def crear_materia(con: sqlite3.Connection, nombre: str, descripcion: str, color: str, icono: str) -> int:
    nombre = _limpiar_nombre(nombre, "la materia")
    descripcion = _limpiar_descripcion(descripcion)
    _validar_materia(con, nombre, color, icono)
    slug = alm.slug_unico(alm.slugify(nombre), _slugs_materias(con))
    orden = con.execute("SELECT COALESCE(MAX(orden), 0) + 1 FROM materias").fetchone()[0]
    t = ahora()
    cur = con.execute(
        "INSERT INTO materias (nombre, slug, descripcion, color, icono, orden, creado, actualizado) VALUES (?,?,?,?,?,?,?,?)",
        (nombre, slug, descripcion, color, icono, orden, t, t),
    )
    (rutas.archivos / slug).mkdir(parents=True, exist_ok=True)
    log.info("Materia creada: %s (%s)", nombre, slug)
    return int(cur.lastrowid)


def editar_materia(con: sqlite3.Connection, materia_id: int, nombre: str, descripcion: str, color: str, icono: str) -> None:
    m = obtener_materia(con, materia_id)
    nombre = _limpiar_nombre(nombre, "la materia")
    descripcion = _limpiar_descripcion(descripcion)
    _validar_materia(con, nombre, color, icono, excluir=materia_id)
    slug = m.slug
    if alm.slugify(nombre) != alm.slugify(m.nombre):
        slug = alm.slug_unico(alm.slugify(nombre), _slugs_materias(con, excluir=materia_id))
    with transaccion(con):
        con.execute(
            "UPDATE materias SET nombre=?, slug=?, descripcion=?, color=?, icono=?, actualizado=? WHERE id=?",
            (nombre, slug, descripcion, color, icono, ahora(), materia_id),
        )
        if slug != m.slug:  # la carpeta acompaña al nuevo nombre
            alm.mover_carpeta(rutas.archivos / m.slug, rutas.archivos / slug)
    log.info("Materia editada: %s", nombre)


def archivar_materia(con: sqlite3.Connection, materia_id: int, archivar: bool) -> Materia:
    m = obtener_materia(con, materia_id)
    con.execute("UPDATE materias SET archivada=?, actualizado=? WHERE id=?", (int(archivar), ahora(), materia_id))
    return m


def reordenar_materias(con: sqlite3.Connection, ids: list[int]) -> None:
    with transaccion(con):
        for orden, mid in enumerate(ids, start=1):
            con.execute("UPDATE materias SET orden=? WHERE id=? AND papelera_id IS NULL", (orden, mid))


# =============================================================== componentes
def _fila_componente(con: sqlite3.Connection, componente_id: int) -> sqlite3.Row:
    f = con.execute(
        """SELECT c.* FROM componentes c JOIN materias m ON m.id = c.materia_id
           WHERE c.id = ? AND c.papelera_id IS NULL AND m.papelera_id IS NULL""", (componente_id,)
    ).fetchone()
    if f is None:
        raise NoEncontrado("El componente")
    return f


def obtener_componente(con: sqlite3.Connection, componente_id: int) -> Componente:
    return Componente.desde_fila(_fila_componente(con, componente_id))


def ancestros(con: sqlite3.Connection, comp: Componente) -> list[Componente]:
    """Del más externo al padre directo (sin incluir `comp`)."""
    cadena: list[Componente] = []
    padre_id = comp.padre_id
    while padre_id is not None:
        padre = obtener_componente(con, padre_id)
        cadena.insert(0, padre)
        padre_id = padre.padre_id
    return cadena


def nivel(con: sqlite3.Connection, comp: Componente) -> int:
    return len(ancestros(con, comp)) + 1


def carpeta_componente(con: sqlite3.Connection, comp: Componente) -> Path:
    m = obtener_materia(con, comp.materia_id)
    partes = [a.slug for a in ancestros(con, comp)] + [comp.slug]
    return rutas.archivos.joinpath(m.slug, *partes)


def hijos(con: sqlite3.Connection, materia_id: int, padre_id: int | None) -> list[Componente]:
    filas = con.execute(
        """SELECT * FROM componentes WHERE materia_id = ? AND padre_id IS ? AND papelera_id IS NULL
           ORDER BY orden, nombre COLLATE NOCASE""", (materia_id, padre_id)
    ).fetchall()
    return [Componente.desde_fila(f) for f in filas]


def arbol(con: sqlite3.Connection, materia_id: int, padre_id: int | None = None, nivel_actual: int = 1) -> list[Componente]:
    nodos = hijos(con, materia_id, padre_id)
    for n in nodos:
        n.nivel = nivel_actual
        n.num_elementos = contar_elementos_componente(con, n.id)
        n.hijos = arbol(con, materia_id, n.id, nivel_actual + 1)
    return nodos


def _validar_tipos(tipos: list[str]) -> list[str]:
    desconocidos = set(tipos) - set(TIPOS_CONTENIDO)
    if desconocidos:
        raise ErrorUsuario("Hay un tipo de contenido no válido.")
    return [t for t in TIPOS_CONTENIDO if t in tipos]  # orden canónico


def _slugs_hermanos(con: sqlite3.Connection, materia_id: int, padre_id: int | None, excluir: int | None = None) -> set[str]:
    return {r[0] for r in con.execute(
        "SELECT slug FROM componentes WHERE materia_id=? AND padre_id IS ? AND papelera_id IS NULL AND id IS NOT ?",
        (materia_id, padre_id, excluir))}


def _nombre_repetido(con: sqlite3.Connection, materia_id: int, padre_id: int | None, nombre: str, excluir: int | None = None) -> bool:
    return con.execute(
        """SELECT 1 FROM componentes WHERE materia_id=? AND padre_id IS ? AND papelera_id IS NULL
           AND nombre = ? COLLATE NOCASE AND id IS NOT ?""", (materia_id, padre_id, nombre, excluir)
    ).fetchone() is not None


def crear_componente(con: sqlite3.Connection, materia_id: int, padre_id: int | None, nombre: str,
                     descripcion: str, tipos: list[str]) -> int:
    obtener_materia(con, materia_id)
    que = "el subcomponente" if padre_id else "el componente"
    nombre = _limpiar_nombre(nombre, que)
    descripcion = _limpiar_descripcion(descripcion)
    tipos = _validar_tipos(tipos)
    if padre_id is not None:
        padre = obtener_componente(con, padre_id)
        if padre.materia_id != materia_id:
            raise ErrorUsuario("El componente padre no pertenece a esta materia.")
        if nivel(con, padre) >= PROFUNDIDAD_MAXIMA:
            raise ErrorUsuario(f"Se permiten como máximo {PROFUNDIDAD_MAXIMA} niveles de componentes.")
    if _nombre_repetido(con, materia_id, padre_id, nombre):
        raise ErrorUsuario(f"Ya existe «{nombre}» en este mismo nivel.")
    slug = alm.slug_unico(alm.slugify(nombre), _slugs_hermanos(con, materia_id, padre_id))
    orden = con.execute(
        "SELECT COALESCE(MAX(orden), 0) + 1 FROM componentes WHERE materia_id=? AND padre_id IS ?", (materia_id, padre_id)
    ).fetchone()[0]
    t = ahora()
    cur = con.execute(
        """INSERT INTO componentes (materia_id, padre_id, nombre, slug, descripcion, tipos, orden, creado, actualizado)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (materia_id, padre_id, nombre, slug, descripcion, json.dumps(tipos), orden, t, t),
    )
    nuevo = obtener_componente(con, int(cur.lastrowid))
    carpeta_componente(con, nuevo).mkdir(parents=True, exist_ok=True)
    log.info("Componente creado: %s", nombre)
    return nuevo.id


def editar_componente(con: sqlite3.Connection, componente_id: int, nombre: str, descripcion: str, tipos: list[str]) -> None:
    c = obtener_componente(con, componente_id)
    nombre = _limpiar_nombre(nombre, "el componente")
    descripcion = _limpiar_descripcion(descripcion)
    tipos = _validar_tipos(tipos)
    if _nombre_repetido(con, c.materia_id, c.padre_id, nombre, excluir=c.id):
        raise ErrorUsuario(f"Ya existe «{nombre}» en este mismo nivel.")
    antes = carpeta_componente(con, c)
    slug = c.slug
    if alm.slugify(nombre) != alm.slugify(c.nombre):
        slug = alm.slug_unico(alm.slugify(nombre), _slugs_hermanos(con, c.materia_id, c.padre_id, excluir=c.id))
    with transaccion(con):
        con.execute(
            "UPDATE componentes SET nombre=?, slug=?, descripcion=?, tipos=?, actualizado=? WHERE id=?",
            (nombre, slug, descripcion, json.dumps(tipos), ahora(), c.id),
        )
        if slug != c.slug:
            alm.mover_carpeta(antes, antes.with_name(slug))


def reordenar_componentes(con: sqlite3.Connection, materia_id: int, padre_id: int | None, ids: list[int]) -> None:
    with transaccion(con):
        for orden, cid in enumerate(ids, start=1):
            con.execute(
                "UPDATE componentes SET orden=? WHERE id=? AND materia_id=? AND padre_id IS ?",
                (orden, cid, materia_id, padre_id),
            )


def descendientes(con: sqlite3.Connection, componente_id: int) -> list[int]:
    filas = con.execute(
        """WITH RECURSIVE sub(id) AS (
               SELECT id FROM componentes WHERE padre_id = ? AND papelera_id IS NULL
               UNION ALL
               SELECT c.id FROM componentes c JOIN sub ON c.padre_id = sub.id WHERE c.papelera_id IS NULL)
           SELECT id FROM sub""", (componente_id,)
    ).fetchall()
    return [r[0] for r in filas]


# ================================================================== conteos
def contar_elementos_componente(con: sqlite3.Connection, componente_id: int) -> int:
    """Elementos cargados directamente en el componente (tablas, PDF, imágenes, notas)."""
    total = 0
    for tabla in _tablas_de_elementos(con):
        total += con.execute(
            f"SELECT COUNT(*) FROM {tabla} WHERE componente_id = ? AND papelera_id IS NULL", (componente_id,)
        ).fetchone()[0]
    return total


def contar_elementos_materia(con: sqlite3.Connection, materia_id: int) -> int:
    total = 0
    for tabla in _tablas_de_elementos(con):
        total += con.execute(
            f"""SELECT COUNT(*) FROM {tabla} e JOIN componentes c ON c.id = e.componente_id
                WHERE c.materia_id = ? AND c.papelera_id IS NULL AND e.papelera_id IS NULL""", (materia_id,)
        ).fetchone()[0]
    return total


def _tablas_de_elementos(con: sqlite3.Connection) -> list[str]:
    """Tablas de contenido que existen en esta versión del esquema (se agregan en fases posteriores)."""
    existentes = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    return [t for t in ("tablas", "pdfs", "imagenes", "notas") if t in existentes]

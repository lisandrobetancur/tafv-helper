"""Vista «Explorar» de una materia: índice de todos sus componentes y lectura de uno completo.

Solo lee: reúne notas (ya convertidas a HTML), imágenes, tablas (con las primeras filas), PDF y
subcomponentes del componente elegido, y el anterior/siguiente en el orden del índice.
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field

from ..models import Componente
from . import biblioteca as bib
from . import imagenes as servicio_imagenes
from . import notas as servicio_notas
from . import pdfs as servicio_pdfs
from . import tablas as servicio_tablas

FILAS_VISTA_PREVIA = 30


@dataclass
class Entrada:
    """Un componente en el índice, con lo que contiene (para listarlo debajo de su nombre)."""
    componente: Componente
    nivel: int
    ruta: list[str]
    notas: list[tuple[int, str]] = field(default_factory=list)
    tablas: list[tuple[int, str]] = field(default_factory=list)
    pdfs: list[tuple[int, str]] = field(default_factory=list)
    num_imagenes: int = 0

    @property
    def vacio(self) -> bool:
        return not (self.notas or self.tablas or self.pdfs or self.num_imagenes)


def indice(con: sqlite3.Connection, materia_id: int) -> list[Entrada]:
    """Todos los componentes de la materia en orden de lectura (padre antes que sus hijos)."""
    salida: list[Entrada] = []

    def recorrer(nodos: list[Componente], ruta: list[str]) -> None:
        for c in nodos:
            e = Entrada(c, c.nivel, ruta)
            e.notas = [(r[0], r[1]) for r in con.execute(
                "SELECT id, titulo FROM notas WHERE componente_id=? AND papelera_id IS NULL ORDER BY orden, id", (c.id,))]
            e.tablas = [(r[0], r[1]) for r in con.execute(
                "SELECT id, nombre FROM tablas WHERE componente_id=? AND papelera_id IS NULL ORDER BY orden, id", (c.id,))]
            e.pdfs = [(r[0], r[1]) for r in con.execute(
                "SELECT id, titulo FROM pdfs WHERE componente_id=? AND papelera_id IS NULL ORDER BY orden, id", (c.id,))]
            e.num_imagenes = con.execute(
                "SELECT COUNT(*) FROM imagenes WHERE componente_id=? AND papelera_id IS NULL", (c.id,)).fetchone()[0]
            salida.append(e)
            recorrer(c.hijos, [*ruta, c.nombre])

    recorrer(bib.arbol(con, materia_id), [])
    return salida


@dataclass
class TablaVista:
    id: int
    nombre: str
    columnas: list[dict]
    filas: list[tuple[int, str, dict]]   # (id de la fila, título, valores)
    total: int


@dataclass
class Lectura:
    entrada: Entrada
    notas: list[tuple[object, str]]       # (nota, html)
    imagenes: list[dict]                  # para el carrusel
    tablas: list[TablaVista]
    pdfs: list
    subcomponentes: list[Entrada]
    anterior: Entrada | None
    siguiente: Entrada | None


def leer(con: sqlite3.Connection, entradas: list[Entrada], componente_id: int) -> Lectura | None:
    pos = next((i for i, e in enumerate(entradas) if e.componente.id == componente_id), None)
    if pos is None:
        return None
    e = entradas[pos]
    cid = e.componente.id
    notas = [(n, servicio_notas.renderizar(n.contenido, n.formato)) for n in servicio_notas.listar(con, cid)]
    imagenes = [{"src": f"/imagenes/{i.id}/archivo", "miniatura": f"/imagenes/{i.id}/miniatura", "titulo": i.titulo,
                 "pie": i.descripcion, "url": f"/imagenes/{i.id}"} for i in servicio_imagenes.listar(con, cid)]
    tablas = []
    for t in servicio_tablas.listar(con, cid):
        filas = [(r[0], r[1], json.loads(r[2])) for r in con.execute(
            "SELECT id, titulo, valores FROM filas WHERE tabla_id=? AND huerfana=0 ORDER BY posicion LIMIT ?",
            (t.id, FILAS_VISTA_PREVIA))]
        tablas.append(TablaVista(t.id, t.nombre, t.columnas, filas, t.num_filas - t.num_huerfanas))
    hijos = [x for x in entradas[pos + 1:] if x.componente.padre_id == cid]
    # Anterior / siguiente: saltando los componentes que solo agrupan (sin contenido propio)
    anterior = next((x for x in reversed(entradas[:pos]) if not x.vacio), None)
    siguiente = next((x for x in entradas[pos + 1:] if not x.vacio), None)
    return Lectura(e, notas, imagenes, tablas, servicio_pdfs.listar(con, cid), hijos, anterior, siguiente)

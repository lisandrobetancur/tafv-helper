"""Vista «Explorar» de una materia: índice de todos sus componentes y lectura de UN elemento a la vez.

Cada componente se divide en «piezas» (sus imágenes en un carrusel, cada nota, cada tabla, cada PDF).
Se muestra solo la pieza elegida, con anterior/siguiente que recorren toda la materia en el orden del índice.
Solo lee.
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

    @property
    def piezas(self) -> list[Pieza]:
        """Lo que se puede abrir de este componente, en el orden del índice."""
        salida = [Pieza("imagenes", f"{self.num_imagenes} imagen" if self.num_imagenes == 1 else f"{self.num_imagenes} imágenes", "images")] \
            if self.num_imagenes else []
        salida += [Pieza(f"nota-{i}", t, "sticky-note") for i, t in self.notas]
        salida += [Pieza(f"tabla-{i}", t, "table") for i, t in self.tablas]
        salida += [Pieza(f"pdf-{i}", t, "file-text") for i, t in self.pdfs]
        return salida


@dataclass
class Pieza:
    clave: str      # "imagenes" | "nota-<id>" | "tabla-<id>" | "pdf-<id>"
    titulo: str
    icono: str


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
class Paso:
    """Destino de «anterior» o «siguiente»."""
    entrada: Entrada
    pieza: Pieza


@dataclass
class Lectura:
    entrada: Entrada
    pieza: Pieza | None             # None: el componente no tiene material propio (solo subcomponentes)
    posicion: int                   # 1-based dentro del componente
    nota: tuple[object, str] | None = None        # (nota, html)
    imagenes: list[dict] = field(default_factory=list)
    tabla: TablaVista | None = None
    pdf: object | None = None
    subcomponentes: list[Entrada] = field(default_factory=list)
    anterior: Paso | None = None
    siguiente: Paso | None = None


def leer(con: sqlite3.Connection, entradas: list[Entrada], componente_id: int, ver: str | None = None) -> Lectura | None:
    pos = next((i for i, e in enumerate(entradas) if e.componente.id == componente_id), None)
    if pos is None:
        return None
    e = entradas[pos]
    piezas = e.piezas
    pieza = next((p for p in piezas if p.clave == ver), piezas[0] if piezas else None)
    lectura = Lectura(e, pieza, piezas.index(pieza) + 1 if pieza else 0,
                      subcomponentes=[x for x in entradas[pos + 1:] if x.componente.padre_id == e.componente.id])
    tipo, _, ref = (pieza.clave.partition("-") if pieza else ("", "", ""))
    if tipo == "imagenes":
        lectura.imagenes = [{"src": f"/imagenes/{i.id}/archivo", "miniatura": f"/imagenes/{i.id}/miniatura",
                             "titulo": i.titulo, "pie": i.descripcion, "url": f"/imagenes/{i.id}"}
                            for i in servicio_imagenes.listar(con, e.componente.id)]
    elif tipo == "nota":
        n = servicio_notas.obtener(con, int(ref))
        lectura.nota = (n, servicio_notas.renderizar(n.contenido, n.formato))
    elif tipo == "tabla":
        t = servicio_tablas.obtener(con, int(ref))
        filas = [(r[0], r[1], json.loads(r[2])) for r in con.execute(
            "SELECT id, titulo, valores FROM filas WHERE tabla_id=? AND huerfana=0 ORDER BY posicion LIMIT ?",
            (t.id, FILAS_VISTA_PREVIA))]
        total = con.execute("SELECT COUNT(*) FROM filas WHERE tabla_id=? AND huerfana=0", (t.id,)).fetchone()[0]
        lectura.tabla = TablaVista(t.id, t.nombre, t.columnas, filas, total)
    elif tipo == "pdf":
        lectura.pdf = servicio_pdfs.obtener(con, int(ref))

    # Anterior / siguiente: recorren todas las piezas de la materia en el orden del índice
    recorrido = [Paso(x, p) for x in entradas for p in x.piezas]
    actual = next((k for k, paso in enumerate(recorrido)
                   if pieza and paso.entrada is e and paso.pieza.clave == pieza.clave), None)
    if actual is not None:
        lectura.anterior = recorrido[actual - 1] if actual > 0 else None
        lectura.siguiente = recorrido[actual + 1] if actual + 1 < len(recorrido) else None
    else:  # componente sin material: se sigue con el siguiente que tenga
        lectura.anterior = next((Paso(x, x.piezas[-1]) for x in reversed(entradas[:pos]) if x.piezas), None)
        lectura.siguiente = next((Paso(x, x.piezas[0]) for x in entradas[pos + 1:] if x.piezas), None)
    return lectura

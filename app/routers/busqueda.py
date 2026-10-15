"""Búsqueda global: página de resultados con filtros y resultados rápidos para la paleta (Ctrl/⌘+K)."""
from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Request

from ..db import obtener_db
from ..services import biblioteca as bib
from ..services import busqueda as bus
from ..web import pagina, parcial

router = APIRouter()
POR_PAGINA = 30


def _filtros(request: Request) -> bus.Filtros:
    p = request.query_params
    def entero(nombre: str) -> int | None:
        v = p.get(nombre, "")
        return int(v) if v.isdigit() else None
    return bus.Filtros(categorias=[c for c in p.getlist("tipo") if c in bus.CATEGORIAS], materia=entero("materia"),
                       componente=entero("componente"), etiqueta=p.get("etiqueta", "").strip(),
                       favoritos=p.get("favoritos") == "1")


def _componentes_planos(con: sqlite3.Connection, materia_id: int) -> list[tuple[int, str]]:
    """Componentes de una materia en forma de lista con sangría, para el filtro."""
    salida = []
    def recorrer(nodos, nivel):
        for n in nodos:
            salida.append((n.id, "    " * (nivel - 1) + n.nombre))
            recorrer(n.hijos, nivel + 1)
    recorrer(bib.arbol(con, materia_id), 1)
    return salida


@router.get("/buscar")
def buscar(request: Request, q: str = "", desde: int = 0, con: sqlite3.Connection = Depends(obtener_db)):
    filtros = _filtros(request)
    respuesta = bus.buscar(con, q, filtros, limite=POR_PAGINA, desplazamiento=max(0, desde))
    siguiente = desde + POR_PAGINA if desde + POR_PAGINA < respuesta.total else None
    contexto = dict(q=q, respuesta=respuesta, filtros=filtros, siguiente=siguiente, desde=desde,
                    categorias=bus.CATEGORIAS)
    if desde and request.headers.get("HX-Request"):   # "Cargar más"
        return parcial(request, "parciales/resultados_mas.html", **contexto)
    if request.headers.get("HX-Target") == "zona-resultados":
        return parcial(request, "parciales/resultados_zona.html", **contexto, oob=True)
    etiquetas = [r[0] for r in con.execute("SELECT nombre FROM etiquetas ORDER BY clave")]
    return pagina(request, con, "paginas/buscar.html", **contexto, materias=bib.listar_materias(con, archivadas=None),
                  componentes=_componentes_planos(con, filtros.materia) if filtros.materia else [],
                  etiquetas=etiquetas, migas=[{"texto": "Búsqueda", "icono": "search"}])


@router.get("/buscar/rapida")
def buscar_rapida(request: Request, q: str = "", con: sqlite3.Connection = Depends(obtener_db)):
    respuesta = bus.buscar(con, q, limite=12)
    return parcial(request, "parciales/resultados_paleta.html", q=q, respuesta=respuesta)


@router.get("/buscar/componentes")
def componentes_de_materia(request: Request, materia: str = "", con: sqlite3.Connection = Depends(obtener_db)):
    """Opciones del filtro de componente cuando se elige una materia."""
    opciones = _componentes_planos(con, int(materia)) if materia.isdigit() else []
    return parcial(request, "parciales/opciones_componentes.html", componentes=opciones, elegido=None)

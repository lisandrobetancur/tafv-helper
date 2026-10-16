"""Busca la materia y el componente de un plan por nombre (sin tildes ni mayúsculas) o por slug."""
from __future__ import annotations

import comun  # noqa: F401

from app.services import biblioteca as bib
from app.services.texto import normalizar


def _igual(nombre: str, slug: str, buscado: str) -> bool:
    return normalizar(nombre) == normalizar(buscado) or slug == buscado.strip()


def materia_id(con, nombre: str) -> int | None:
    return next((m.id for m in bib.listar_materias(con, archivadas=None) if _igual(m.nombre, m.slug, nombre)), None)


def partes_componente(ruta: str) -> list[str]:
    """«Parcial 1 › Atlas» -> ["Parcial 1", "Atlas"]."""
    return [p.strip() for p in ruta.split("›") if p.strip()]


def buscar_hijo(con, materia: int, padre: int | None, nombre: str) -> int | None:
    return next((c.id for c in bib.hijos(con, materia, padre) if _igual(c.nombre, c.slug, nombre)), None)


def componente_del_plan(con, plan: dict) -> int | None:
    mid = materia_id(con, plan["materia"])
    if mid is None:
        return None
    padre = None
    for nombre in partes_componente(plan["componente"]):
        padre = buscar_hijo(con, mid, padre, nombre)
        if padre is None:
            return None
    return padre

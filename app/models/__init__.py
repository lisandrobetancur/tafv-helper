"""Modelos de datos (filas de SQLite convertidas a objetos con tipos)."""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field

from ..config import COLOR_POR_ID, TIPOS_CONTENIDO


@dataclass
class Materia:
    id: int
    nombre: str
    slug: str
    descripcion: str
    color: str
    icono: str
    orden: int
    archivada: bool
    creado: str
    actualizado: str
    # Calculados al listar
    num_componentes: int = 0
    num_elementos: int = 0

    @property
    def color_hex(self) -> str:
        return COLOR_POR_ID.get(self.color, COLOR_POR_ID["pizarra"])["hex"]

    @classmethod
    def desde_fila(cls, f: sqlite3.Row) -> Materia:
        return cls(id=f["id"], nombre=f["nombre"], slug=f["slug"], descripcion=f["descripcion"],
                   color=f["color"], icono=f["icono"], orden=f["orden"], archivada=bool(f["archivada"]),
                   creado=f["creado"], actualizado=f["actualizado"])


@dataclass
class Componente:
    id: int
    materia_id: int
    padre_id: int | None
    nombre: str
    slug: str
    descripcion: str
    tipos: list[str]
    orden: int
    creado: str
    actualizado: str
    hijos: list[Componente] = field(default_factory=list)
    nivel: int = 1
    num_elementos: int = 0

    @property
    def tipos_info(self) -> list[dict[str, str]]:
        return [{"id": t, **TIPOS_CONTENIDO[t]} for t in TIPOS_CONTENIDO if t in self.tipos]

    @classmethod
    def desde_fila(cls, f: sqlite3.Row) -> Componente:
        tipos = [t for t in json.loads(f["tipos"] or "[]") if t in TIPOS_CONTENIDO]
        return cls(id=f["id"], materia_id=f["materia_id"], padre_id=f["padre_id"], nombre=f["nombre"],
                   slug=f["slug"], descripcion=f["descripcion"], tipos=tipos, orden=f["orden"],
                   creado=f["creado"], actualizado=f["actualizado"])


@dataclass
class ElementoPapelera:
    id: int
    tipo: str
    ref_id: int
    nombre: str
    ubicacion: str
    eliminado: str

    @classmethod
    def desde_fila(cls, f: sqlite3.Row) -> ElementoPapelera:
        return cls(id=f["id"], tipo=f["tipo"], ref_id=f["ref_id"], nombre=f["nombre"],
                   ubicacion=f["ubicacion"], eliminado=f["eliminado"])

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
    oculta: bool = False          # no sale en el menú, Inicio, recientes ni favoritos; se abre por su URL
    en_busqueda: bool = True      # si es oculta: ¿sale en la búsqueda y en Acceso rápido?
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
                   creado=f["creado"], actualizado=f["actualizado"],
                   oculta=bool(f["oculta"]) if "oculta" in f.keys() else False,
                   en_busqueda=bool(f["en_busqueda"]) if "en_busqueda" in f.keys() else True)


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


@dataclass
class Tabla:
    id: int
    componente_id: int
    nombre: str
    archivo: str
    archivo_original: str
    hoja: str | None
    fila_encabezado: int
    dos_filas: bool
    columnas: list[dict]
    columna_titulo: str
    columna_clave: str | None
    hash: str
    creado: str
    actualizado: str
    num_filas: int = 0
    num_imagenes: int = 0
    num_huerfanas: int = 0

    @property
    def claves(self) -> list[str]:
        return [c["clave"] for c in self.columnas]

    def nombre_columna(self, clave: str | None) -> str:
        return next((c["nombre"] for c in self.columnas if c["clave"] == clave), "")

    @classmethod
    def desde_fila(cls, f: sqlite3.Row) -> Tabla:
        return cls(id=f["id"], componente_id=f["componente_id"], nombre=f["nombre"], archivo=f["archivo"],
                   archivo_original=f["archivo_original"], hoja=f["hoja"], fila_encabezado=f["fila_encabezado"],
                   dos_filas=bool(f["dos_filas"]), columnas=json.loads(f["columnas"]),
                   columna_titulo=f["columna_titulo"], columna_clave=f["columna_clave"], hash=f["hash"],
                   creado=f["creado"], actualizado=f["actualizado"])


@dataclass
class Fila:
    id: int
    tabla_id: int
    posicion: int
    fila_origen: int | None
    titulo: str
    valores: dict[str, str]
    huerfana: bool
    num_imagenes: int = 0

    @classmethod
    def desde_fila(cls, f: sqlite3.Row) -> Fila:
        claves = f.keys()
        return cls(id=f["id"], tabla_id=f["tabla_id"], posicion=f["posicion"], fila_origen=f["fila_origen"],
                   titulo=f["titulo"], valores=json.loads(f["valores"]), huerfana=bool(f["huerfana"]),
                   num_imagenes=f["num_imagenes"] if "num_imagenes" in claves else 0)


@dataclass
class ImagenFila:
    id: int
    fila_id: int
    archivo: str
    titulo: str
    nombre_original: str
    pie: str
    orden: int
    hash: str
    ancho: int | None
    alto: int | None
    bytes: int | None
    creado: str

    @classmethod
    def desde_fila(cls, f: sqlite3.Row) -> ImagenFila:
        return cls(id=f["id"], fila_id=f["fila_id"], archivo=f["archivo"], titulo=f["titulo"],
                   nombre_original=f["nombre_original"],
                   pie=f["pie"], orden=f["orden"], hash=f["hash"], ancho=f["ancho"], alto=f["alto"],
                   bytes=f["bytes"], creado=f["creado"])

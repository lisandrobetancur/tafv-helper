"""Datos para mostrar cualquier elemento (fila, tabla, PDF, imagen, nota) en listas: título,
enlace, ícono y ubicación. Descarta lo que está en la papelera o ya no existe."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from ..config import COLOR_POR_ID
from . import biblioteca as bib

ICONOS = {"tabla": "file-spreadsheet", "fila": "list", "pdf": "file-text", "imagen": "image", "nota": "sticky-note"}
NOMBRES = {"tabla": "Tabla", "fila": "Fila", "pdf": "PDF", "imagen": "Imagen", "nota": "Nota"}

# tipo -> (consulta que devuelve id, titulo, componente_id, url) solo de elementos activos
_CONSULTAS = {
    "tabla": """SELECT t.id, t.nombre, t.componente_id, '/tablas/' || t.id FROM tablas t
                WHERE t.papelera_id IS NULL AND t.id IN ({})""",
    "fila": """SELECT f.id, f.titulo, t.componente_id, '/filas/' || f.id FROM filas f JOIN tablas t ON t.id = f.tabla_id
               WHERE t.papelera_id IS NULL AND f.id IN ({})""",
    "pdf": """SELECT d.id, d.titulo, d.componente_id, '/pdfs/' || d.id FROM pdfs d WHERE d.papelera_id IS NULL AND d.id IN ({})""",
    "imagen": """SELECT i.id, i.titulo, i.componente_id, '/imagenes/' || i.id FROM imagenes i
                 WHERE i.papelera_id IS NULL AND i.id IN ({})""",
    "nota": """SELECT n.id, n.titulo, n.componente_id, '/notas/' || n.id FROM notas n WHERE n.papelera_id IS NULL AND n.id IN ({})""",
}


@dataclass
class Elemento:
    tipo: str
    ref_id: int
    titulo: str
    url: str
    ubicacion: str
    color: str

    @property
    def icono(self) -> str:
        return ICONOS[self.tipo]

    @property
    def nombre_tipo(self) -> str:
        return NOMBRES[self.tipo]


def resolver(con: sqlite3.Connection, pares: list[tuple[str, int]]) -> list[Elemento]:
    """Mantiene el orden de `pares`."""
    datos: dict[tuple[str, int], tuple] = {}
    for tipo in {t for t, _ in pares if t in _CONSULTAS}:
        ids = [i for t, i in pares if t == tipo]
        for f in con.execute(_CONSULTAS[tipo].format(",".join("?" * len(ids))), ids):
            datos[(tipo, f[0])] = (f[1], f[2], f[3])
    ubicaciones: dict[int, tuple[str, str] | None] = {}
    salida = []
    for tipo, ref in pares:
        if (tipo, ref) not in datos:
            continue
        titulo, comp_id, url = datos[(tipo, ref)]
        if comp_id not in ubicaciones:
            try:
                c = bib.obtener_componente(con, comp_id)   # falla si el componente está en la papelera
                m = bib.obtener_materia(con, c.materia_id)
                ruta = " › ".join([m.nombre, *(a.nombre for a in bib.ancestros(con, c)), c.nombre])
                ubicaciones[comp_id] = (ruta, COLOR_POR_ID.get(m.color, COLOR_POR_ID["pizarra"])["hex"])
            except Exception:
                ubicaciones[comp_id] = None
        if ubicaciones[comp_id] is None:
            continue
        ruta, color = ubicaciones[comp_id]
        salida.append(Elemento(tipo, ref, titulo, url, ruta, color))
    return salida

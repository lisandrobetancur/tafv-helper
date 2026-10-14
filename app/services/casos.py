"""Casos del módulo Diagnóstico.

Viven en el propio módulo (no dentro de una materia): guardan los síntomas, la conclusión del
estudiante y una foto del análisis en Markdown. Al abrir un caso se vuelve a analizar con toda
la biblioteca tal como está hoy.
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from urllib.parse import urlencode

from ..db import ahora
from ..errores import ErrorUsuario, NoEncontrado
from . import diagnostico as dx

MAX_TITULO = 120


@dataclass
class Caso:
    id: int
    titulo: str
    sintomas: list[str] = field(default_factory=list)
    importantes: list[str] = field(default_factory=list)
    solo: bool = False
    conclusion: str = ""
    resumen: str = ""
    creado: str = ""
    actualizado: str = ""

    @classmethod
    def desde_fila(cls, f: sqlite3.Row) -> Caso:
        return cls(f["id"], f["titulo"], json.loads(f["sintomas"]), json.loads(f["importantes"]), bool(f["solo"]),
                   f["conclusion"], f["resumen"], f["creado"], f["actualizado"])

    @property
    def lista_sintomas(self) -> list[dx.Sintoma]:
        return dx.preparar(self.sintomas, self.importantes)

    @property
    def consulta(self) -> str:
        """Parámetros para abrir el caso en el formulario de diagnóstico."""
        params = [("caso", self.id), *(("s", s) for s in self.sintomas), *(("imp", s) for s in self.importantes)]
        if self.solo:
            params.append(("solo", "1"))
        return urlencode(params)


def _titulo(titulo: str, sintomas: list[dx.Sintoma]) -> str:
    titulo = " ".join((titulo or "").split())[:MAX_TITULO]
    return titulo or ("Caso: " + ", ".join(s.texto for s in sintomas))[:MAX_TITULO]


def _datos(sintomas: list[dx.Sintoma]) -> tuple[str, str]:
    return (json.dumps([s.texto for s in sintomas], ensure_ascii=False),
            json.dumps([s.texto for s in sintomas if s.importante], ensure_ascii=False))


def crear(con: sqlite3.Connection, titulo: str, sintomas: list[dx.Sintoma], solo: bool = False,
          conclusion: str = "") -> Caso:
    if not sintomas:
        raise ErrorUsuario("Agrega al menos un síntoma antes de guardar el caso.")
    resumen = dx.nota_markdown(dx.analizar(con, sintomas, solo_sintomas=solo))
    momento = ahora()
    cur = con.execute(
        """INSERT INTO casos (titulo, sintomas, importantes, solo, conclusion, resumen, creado, actualizado)
           VALUES (?,?,?,?,?,?,?,?)""",
        (_titulo(titulo, sintomas), *_datos(sintomas), int(solo), conclusion.strip(), resumen, momento, momento))
    return obtener(con, int(cur.lastrowid))


def obtener(con: sqlite3.Connection, caso_id: int) -> Caso:
    f = con.execute("SELECT * FROM casos WHERE id=? AND papelera_id IS NULL", (caso_id,)).fetchone()
    if f is None:
        raise NoEncontrado("El caso")
    return Caso.desde_fila(f)


def listar(con: sqlite3.Connection, limite: int | None = None) -> list[Caso]:
    sql = "SELECT * FROM casos WHERE papelera_id IS NULL ORDER BY actualizado DESC, id DESC"
    if limite:
        sql += f" LIMIT {int(limite)}"
    return [Caso.desde_fila(f) for f in con.execute(sql)]


def editar(con: sqlite3.Connection, caso_id: int, titulo: str, conclusion: str) -> Caso:
    caso = obtener(con, caso_id)
    con.execute("UPDATE casos SET titulo=?, conclusion=?, actualizado=? WHERE id=?",
                (_titulo(titulo, caso.lista_sintomas), conclusion.strip(), ahora(), caso.id))
    return obtener(con, caso.id)


def actualizar_sintomas(con: sqlite3.Connection, caso_id: int, sintomas: list[dx.Sintoma], solo: bool) -> Caso:
    """Cambia los síntomas del caso y vuelve a guardar el análisis con la biblioteca actual."""
    caso = obtener(con, caso_id)
    if not sintomas:
        raise ErrorUsuario("El caso necesita al menos un síntoma.")
    resumen = dx.nota_markdown(dx.analizar(con, sintomas, solo_sintomas=solo))
    con.execute("UPDATE casos SET sintomas=?, importantes=?, solo=?, resumen=?, actualizado=? WHERE id=?",
                (*_datos(sintomas), int(solo), resumen, ahora(), caso.id))
    return obtener(con, caso.id)

"""Notas de texto o Markdown dentro de un componente (buscables)."""
from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass, field

from markdown_it import MarkdownIt

from ..db import ahora
from ..errores import ErrorUsuario, NoEncontrado
from . import biblioteca as bib
from . import etiquetas as etq

FORMATOS = {"markdown": "Markdown", "texto": "Texto simple"}
LARGO_TITULO = 120
LARGO_CONTENIDO = 500_000

# Markdown seguro: sin HTML incrustado; con tablas y tachado
_md = MarkdownIt("commonmark", {"html": False, "breaks": True, "typographer": True}).enable(["table", "strikethrough"])


@dataclass
class Nota:
    id: int
    componente_id: int
    titulo: str
    contenido: str
    formato: str
    creado: str
    actualizado: str
    etiquetas: list[str] = field(default_factory=list)

    @property
    def extracto(self) -> str:
        texto = self.contenido
        if self.formato == "markdown":  # quita los signos de formato más comunes
            texto = re.sub(r"[#>*_`~\[\]()|-]+", " ", texto)
        texto = " ".join(texto.split())
        return texto[:220] + ("…" if len(texto) > 220 else "")

    @classmethod
    def desde_fila(cls, f: sqlite3.Row) -> Nota:
        return cls(f["id"], f["componente_id"], f["titulo"], f["contenido"], f["formato"], f["creado"], f["actualizado"])


def renderizar(contenido: str, formato: str) -> str:
    """HTML de la nota (seguro: el Markdown no admite HTML incrustado; el texto simple se escapa)."""
    if formato == "markdown":
        return _md.render(contenido)
    from markupsafe import escape
    return f'<p class="whitespace-pre-wrap">{escape(contenido)}</p>'


def _validar(titulo: str, contenido: str, formato: str) -> tuple[str, str, str]:
    titulo = " ".join((titulo or "").split())[:LARGO_TITULO]
    if not titulo:
        raise ErrorUsuario("Escribe un título para la nota.")
    if formato not in FORMATOS:
        raise ErrorUsuario("Elige un formato válido.")
    contenido = (contenido or "").replace("\r\n", "\n")
    if len(contenido) > LARGO_CONTENIDO:
        raise ErrorUsuario("La nota es demasiado larga.")
    return titulo, contenido, formato


def listar(con: sqlite3.Connection, componente_id: int) -> list[Nota]:
    notas = [Nota.desde_fila(f) for f in con.execute(
        "SELECT * FROM notas WHERE componente_id=? AND papelera_id IS NULL ORDER BY orden, actualizado DESC", (componente_id,))]
    por_id = etq.de_varios(con, "nota", [n.id for n in notas])
    for n in notas:
        n.etiquetas = por_id.get(n.id, [])
    return notas


def obtener(con: sqlite3.Connection, nota_id: int) -> Nota:
    f = con.execute(
        """SELECT n.* FROM notas n JOIN componentes c ON c.id = n.componente_id
           WHERE n.id=? AND n.papelera_id IS NULL AND c.papelera_id IS NULL""", (nota_id,)).fetchone()
    if f is None:
        raise NoEncontrado("La nota")
    nota = Nota.desde_fila(f)
    nota.etiquetas = etq.de(con, "nota", nota.id)
    return nota


def crear(con: sqlite3.Connection, componente_id: int, titulo: str, contenido: str, formato: str = "markdown",
          etiquetas: str = "") -> Nota:
    bib.obtener_componente(con, componente_id)
    titulo, contenido, formato = _validar(titulo, contenido, formato)
    t = ahora()
    orden = con.execute("SELECT COALESCE(MAX(orden),0)+1 FROM notas WHERE componente_id=?", (componente_id,)).fetchone()[0]
    nid = int(con.execute(
        "INSERT INTO notas (componente_id, titulo, contenido, formato, orden, creado, actualizado) VALUES (?,?,?,?,?,?,?)",
        (componente_id, titulo, contenido, formato, orden, t, t)).lastrowid)
    etq.asignar(con, "nota", nid, etiquetas)
    return obtener(con, nid)


def editar(con: sqlite3.Connection, nota_id: int, titulo: str, contenido: str, formato: str, etiquetas: str = "") -> Nota:
    obtener(con, nota_id)
    titulo, contenido, formato = _validar(titulo, contenido, formato)
    con.execute("UPDATE notas SET titulo=?, contenido=?, formato=?, actualizado=? WHERE id=?",
                (titulo, contenido, formato, ahora(), nota_id))
    etq.asignar(con, "nota", nota_id, etiquetas)
    return obtener(con, nota_id)

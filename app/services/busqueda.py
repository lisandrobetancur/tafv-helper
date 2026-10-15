"""Búsqueda global en toda la biblioteca (índice FTS5 `busqueda`).

- Sin tildes ni mayúsculas: "fémur" = "femur" = "FEMUR".
- Cada palabra busca por prefijo ("cardio" encuentra "cardiología"); "entre comillas" busca la frase.
- Resultados ordenados por relevancia (el título pesa más), con el término resaltado y enlace
  directo al contenido (la fila, el PDF en su página, la imagen, la nota…).
"""
from __future__ import annotations

import re
import sqlite3
import time
from dataclasses import dataclass, field
from urllib.parse import urlencode

from markupsafe import Markup, escape

from .. import indice_sql
from ..config import COLOR_POR_ID
from . import biblioteca as bib
from .texto import normalizar

INICIO, FIN = "\x02", "\x03"

# Categorías que ve la usuaria -> tipos del índice
CATEGORIAS: dict[str, dict] = {
    "excel": {"nombre": "Excel", "icono": "file-spreadsheet", "tipos": ["fila", "tabla"]},
    "pdf": {"nombre": "PDF", "icono": "file-text", "tipos": ["pagina", "pdf"]},
    "imagenes": {"nombre": "Imágenes", "icono": "images", "tipos": ["imagen", "imagen_fila"]},
    "notas": {"nombre": "Notas", "icono": "sticky-note", "tipos": ["nota"]},
    "organizacion": {"nombre": "Materias y componentes", "icono": "layers", "tipos": ["materia", "componente"]},
}
CATEGORIA_DE = {t: c for c, d in CATEGORIAS.items() for t in d["tipos"]}
ICONOS = {"materia": "graduation-cap", "componente": "folder", "tabla": "file-spreadsheet", "fila": "list",
          "pdf": "file-text", "pagina": "file-text", "imagen": "image", "imagen_fila": "image", "nota": "sticky-note"}

_EXCLUIR_PAPELERA = """
    AND (materia IS NULL OR materia NOT IN (SELECT id FROM materias WHERE papelera_id IS NOT NULL))
    AND (componente IS NULL OR componente NOT IN (SELECT id FROM componentes WHERE papelera_id IS NOT NULL))
    AND NOT (tipo IN ('tabla', 'fila', 'imagen_fila') AND padre IN (SELECT id FROM tablas WHERE papelera_id IS NOT NULL))
    AND NOT (tipo IN ('pdf', 'pagina') AND padre IN (SELECT id FROM pdfs WHERE papelera_id IS NOT NULL))
    AND NOT (tipo = 'imagen' AND ref IN (SELECT id FROM imagenes WHERE papelera_id IS NOT NULL))
    AND NOT (tipo = 'nota' AND ref IN (SELECT id FROM notas WHERE papelera_id IS NOT NULL))
    AND NOT (tipo = 'imagen_fila' AND ref IN (SELECT id FROM imagenes_fila WHERE papelera_id IS NOT NULL))
"""


# ------------------------------------------------------------------ consulta
def expresion(texto: str) -> str | None:
    """Convierte lo que escribe la usuaria en una consulta FTS5 segura.
    'cardio "nervio radial"' -> '"cardio"* "nervio radial"' (todas deben aparecer)."""
    partes = []
    for frase, palabra in re.findall(r'"([^"]*)"|(\S+)', texto or ""):
        if frase:
            tokens = re.findall(r"\w+", normalizar(frase))
            if tokens:
                partes.append('"' + " ".join(tokens) + '"')
        else:
            partes += [f'"{t}"*' for t in re.findall(r"\w+", normalizar(palabra))]
    return " ".join(partes) or None


@dataclass
class Filtros:
    categorias: list[str] = field(default_factory=list)
    materia: int | None = None
    componente: int | None = None
    etiqueta: str = ""
    favoritos: bool = False

    @property
    def activos(self) -> bool:
        return bool(self.categorias or self.materia or self.componente or self.etiqueta or self.favoritos)


def _condiciones(con: sqlite3.Connection, f: Filtros) -> tuple[str, list]:
    sql, params = _EXCLUIR_PAPELERA, []
    tipos = [t for c in f.categorias if c in CATEGORIAS for t in CATEGORIAS[c]["tipos"]]
    if tipos:
        sql += f" AND tipo IN ({','.join('?' * len(tipos))})"
        params += tipos
    if f.materia:
        sql += " AND materia = ?"
        params.append(f.materia)
    if f.componente:
        ids = [f.componente, *bib.descendientes(con, f.componente)]
        sql += f" AND componente IN ({','.join('?' * len(ids))})"
        params += ids
    if f.etiqueta:
        # La etiqueta de una tabla vale para todas sus fichas (y las imágenes de las fichas)
        sql += """ AND (((CASE WHEN tipo = 'pagina' THEN 'pdf' ELSE tipo END) || ':' || ref) IN
                   (SELECT x.tipo || ':' || x.ref_id FROM etiquetas_elemento x JOIN etiquetas e ON e.id = x.etiqueta_id
                    WHERE e.clave = ?)
                   OR (tipo IN ('tabla', 'fila', 'imagen_fila') AND padre IN
                   (SELECT x.ref_id FROM etiquetas_elemento x JOIN etiquetas e ON e.id = x.etiqueta_id
                    WHERE x.tipo = 'tabla' AND e.clave = ?)))"""
        params += [normalizar(f.etiqueta)] * 2
    if f.favoritos:
        existe = con.execute("SELECT 1 FROM sqlite_master WHERE name='favoritos'").fetchone()
        if existe:
            sql += """ AND ((CASE WHEN tipo = 'pagina' THEN 'pdf' ELSE tipo END) || ':' || ref) IN
                       (SELECT tipo || ':' || ref_id FROM favoritos)"""
        else:
            sql += " AND 0"
    return sql, params


@dataclass
class Resultado:
    tipo: str
    ref: int
    sub: int | None
    padre: int | None
    componente_id: int | None
    materia_id: int | None
    titulo: Markup
    fragmento: Markup
    url: str = ""
    detalle: str = ""

    @property
    def icono(self) -> str:
        return ICONOS[self.tipo]

    @property
    def categoria(self) -> str:
        return CATEGORIA_DE[self.tipo]


@dataclass
class Grupo:
    materia_id: int | None
    materia: str
    color: str
    ruta: str              # "Parcial 1 › Miembro superior"
    componente_id: int | None
    resultados: list[Resultado] = field(default_factory=list)


@dataclass
class Respuesta:
    q: str
    total: int = 0
    resultados: list[Resultado] = field(default_factory=list)
    por_categoria: dict[str, int] = field(default_factory=dict)
    milisegundos: float = 0

    @property
    def grupos(self) -> list[Grupo]:
        return self._grupos

    _grupos: list[Grupo] = field(default_factory=list)


def _marcar(texto: str | None) -> Markup:
    """Escapa el texto y convierte los marcadores del índice en <mark>."""
    seguro = str(escape(" ".join((texto or "").split())))
    return Markup(seguro.replace(INICIO, "<mark>").replace(FIN, "</mark>"))


def buscar(con: sqlite3.Connection, q: str, filtros: Filtros | None = None, limite: int = 40,
           desplazamiento: int = 0) -> Respuesta:
    inicio = time.perf_counter()
    respuesta = Respuesta(q=q)
    consulta = expresion(q)
    filtros = filtros or Filtros()
    if not consulta:
        # Sin texto, pero con una etiqueta: se lista todo lo que la tiene (para ver lo relacionado)
        return _por_etiqueta(con, respuesta, filtros, limite, desplazamiento, inicio) if filtros.etiqueta else respuesta
    extra, params = _condiciones(con, filtros)
    base = f"FROM busqueda WHERE busqueda MATCH ? {extra}"
    try:
        respuesta.total = con.execute(f"SELECT COUNT(*) {base}", [consulta, *params]).fetchone()[0]
        sin_categoria = Filtros(materia=filtros.materia, componente=filtros.componente, etiqueta=filtros.etiqueta,
                                favoritos=filtros.favoritos)
        extra2, params2 = _condiciones(con, sin_categoria)
        for tipo, n in con.execute(f"SELECT tipo, COUNT(*) FROM busqueda WHERE busqueda MATCH ? {extra2} GROUP BY tipo",
                                   [consulta, *params2]):
            cat = CATEGORIA_DE[tipo]
            respuesta.por_categoria[cat] = respuesta.por_categoria.get(cat, 0) + n
        filas = con.execute(
            f"""SELECT tipo, ref, sub, padre, componente, materia,
                       highlight(busqueda, 0, '{INICIO}', '{FIN}') AS titulo,
                       snippet(busqueda, 1, '{INICIO}', '{FIN}', '…', 18) AS fragmento
                {base}
                -- Primero los títulos que son exactamente lo buscado (p. ej. la fila «Fémur»), luego por relevancia
                ORDER BY (highlight(busqueda, 0, '{INICIO}', '{FIN}') = '{INICIO}' || titulo || '{FIN}') DESC,
                         bm25(busqueda, 10.0, 1.0)
                LIMIT ? OFFSET ?""",
            [consulta, *params, limite, desplazamiento]).fetchall()
    except sqlite3.OperationalError:  # consulta imposible de interpretar
        return respuesta
    respuesta.resultados = [Resultado(r["tipo"], r["ref"], r["sub"], r["padre"], r["componente"], r["materia"],
                                      _marcar(r["titulo"]), _marcar(r["fragmento"])) for r in filas]
    _completar(con, respuesta.resultados, q)
    respuesta._grupos = _agrupar(con, respuesta.resultados)
    respuesta.milisegundos = round((time.perf_counter() - inicio) * 1000, 1)
    return respuesta


def _por_etiqueta(con: sqlite3.Connection, respuesta: Respuesta, filtros: Filtros, limite: int,
                  desplazamiento: int, inicio: float) -> Respuesta:
    """Todo lo que tiene la etiqueta (y las fichas de las tablas que la tienen), sin texto de búsqueda."""
    extra, params = _condiciones(con, filtros)
    base = f"FROM busqueda WHERE 1 {extra}"
    respuesta.total = con.execute(f"SELECT COUNT(*) {base}", params).fetchone()[0]
    sin_categoria = Filtros(materia=filtros.materia, componente=filtros.componente, etiqueta=filtros.etiqueta,
                            favoritos=filtros.favoritos)
    extra2, params2 = _condiciones(con, sin_categoria)
    for tipo, n in con.execute(f"SELECT tipo, COUNT(*) FROM busqueda WHERE 1 {extra2} GROUP BY tipo", params2):
        cat = CATEGORIA_DE[tipo]
        respuesta.por_categoria[cat] = respuesta.por_categoria.get(cat, 0) + n
    orden = " ".join(f"WHEN '{t}' THEN {i}" for i, t in enumerate(ICONOS))
    filas = con.execute(
        f"""SELECT tipo, ref, sub, padre, componente, materia, titulo, substr(contenido, 1, 180) AS fragmento
            {base} ORDER BY CASE tipo {orden} END, titulo COLLATE NOCASE LIMIT ? OFFSET ?""",
        [*params, limite, desplazamiento]).fetchall()
    respuesta.resultados = [Resultado(r["tipo"], r["ref"], r["sub"], r["padre"], r["componente"], r["materia"],
                                      _marcar(r["titulo"]), _marcar(r["fragmento"])) for r in filas]
    _completar(con, respuesta.resultados, "")
    respuesta._grupos = _agrupar(con, respuesta.resultados)
    respuesta.milisegundos = round((time.perf_counter() - inicio) * 1000, 1)
    return respuesta


# ------------------------------------------------------------ presentación
def _completar(con: sqlite3.Connection, resultados: list[Resultado], q: str) -> None:
    """Enlace directo y detalle de cada resultado."""
    def nombres(sql: str, ids: set[int]) -> dict[int, str]:
        if not ids:
            return {}
        return dict(con.execute(sql.format(",".join("?" * len(ids))), list(ids)).fetchall())

    tablas = nombres("SELECT id, nombre FROM tablas WHERE id IN ({})",
                     {r.padre for r in resultados if r.tipo in ("fila", "imagen_fila")})
    filas = nombres("SELECT id, titulo FROM filas WHERE id IN ({})", {r.sub for r in resultados if r.tipo == "imagen_fila"})
    buscar_ = urlencode({"buscar": q})
    for r in resultados:
        if r.tipo == "materia":
            r.url, r.detalle = f"/materias/{r.ref}", "Materia"
        elif r.tipo == "componente":
            r.url, r.detalle = f"/componentes/{r.ref}", "Componente"
        elif r.tipo == "tabla":
            r.url, r.detalle = f"/tablas/{r.ref}?{urlencode({'q': q})}", "Tabla de Excel"
        elif r.tipo == "fila":
            r.url, r.detalle = f"/filas/{r.ref}?{buscar_}", f"Fila de «{tablas.get(r.padre, 'tabla')}»"
        elif r.tipo == "pdf":
            r.url, r.detalle = f"/pdfs/{r.ref}?{buscar_}", "PDF"
        elif r.tipo == "pagina":
            r.url, r.detalle = f"/pdfs/{r.ref}?pagina={r.sub}&{buscar_}", f"PDF · página {r.sub}"
        elif r.tipo == "imagen":
            r.url, r.detalle = f"/imagenes/{r.ref}?{buscar_}", "Imagen"
        elif r.tipo == "imagen_fila":
            r.url, r.detalle = f"/filas/{r.sub}?{buscar_}&imagen={r.ref}", f"Imagen de la ficha «{filas.get(r.sub, '')}»"
        elif r.tipo == "nota":
            r.url, r.detalle = f"/notas/{r.ref}?{buscar_}", "Nota"


def _agrupar(con: sqlite3.Connection, resultados: list[Resultado]) -> list[Grupo]:
    """Agrupa por materia › componente, en el orden del mejor resultado de cada grupo."""
    materias = {}
    ids = {r.materia_id for r in resultados if r.materia_id}
    if ids:
        for f in con.execute(f"SELECT id, nombre, color FROM materias WHERE id IN ({','.join('?' * len(ids))})", list(ids)):
            materias[f["id"]] = (f["nombre"], COLOR_POR_ID.get(f["color"], COLOR_POR_ID["pizarra"])["hex"])
    rutas: dict[int, str] = {}
    grupos: dict[tuple, Grupo] = {}
    for r in resultados:
        clave = (r.materia_id, r.componente_id)
        if clave not in grupos:
            ruta = ""
            if r.componente_id:
                if r.componente_id not in rutas:
                    try:
                        c = bib.obtener_componente(con, r.componente_id)
                        rutas[r.componente_id] = " › ".join([*(a.nombre for a in bib.ancestros(con, c)), c.nombre])
                    except Exception:
                        rutas[r.componente_id] = ""
                ruta = rutas[r.componente_id]
            nombre, color = materias.get(r.materia_id, ("", COLOR_POR_ID["pizarra"]["hex"]))
            grupos[clave] = Grupo(r.materia_id, nombre, color, ruta, r.componente_id)
        grupos[clave].resultados.append(r)
    return list(grupos.values())


def reconstruir(con: sqlite3.Connection) -> int:
    """Vuelve a crear todo el índice (mantenimiento). Devuelve cuántos documentos quedaron."""
    con.executescript("BEGIN;\n" + indice_sql.reconstruir() + "\nCOMMIT;")
    return con.execute("SELECT COUNT(*) FROM busqueda").fetchone()[0]

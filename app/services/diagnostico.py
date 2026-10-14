"""Diagnóstico por síntomas a partir del material guardado (herramienta de estudio).

Funciona como una repertorización: cada síntoma se busca en las filas de las tablas (p. ej.
medicamentos o enfermedades); los candidatos se ordenan por cuántos síntomas cubren (los
«importantes» pesan el doble) y para cada uno se muestra la evidencia (columna y texto), los
síntomas que no menciona y otros rasgos de su ficha que conviene comprobar. Además se reúne lo
que dicen los PDF, notas e imágenes sobre cada síntoma.

No inventa nada: todo sale del material de la biblioteca y siempre se muestra de dónde.
"""
from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass, field

from ..config import COLOR_POR_ID
from . import biblioteca as bib
from . import busqueda as bus
from .texto import fragmentos_resaltados, normalizar

MAX_SINTOMAS = 15
MAX_FILAS_POR_SINTOMA = 3000
PALABRAS_SINTOMA = ("sintoma", "signo", "manifestacion", "clinica", "cuadro", "caracteristic", "modalidad")


# ------------------------------------------------------------------ entrada
@dataclass
class Sintoma:
    texto: str
    importante: bool = False

    @property
    def peso(self) -> int:
        return 2 if self.importante else 1

    @property
    def palabras(self) -> list[str]:
        return [p for p in re.findall(r"\w+", normalizar(self.texto)) if len(p) > 1 or p.isdigit()]


def preparar(textos: list[str], importantes: list[str]) -> list[Sintoma]:
    """Limpia la lista (sin vacíos ni repetidos) y marca los importantes."""
    vistos, salida = set(), []
    marcas = {normalizar(i) for i in importantes}
    for t in textos:
        t = " ".join((t or "").split())[:120]
        clave = normalizar(t)
        if clave and clave not in vistos:
            vistos.add(clave)
            salida.append(Sintoma(t, clave in marcas))
    return salida[:MAX_SINTOMAS]


def _coincide(texto_norm: str, palabras: list[str]) -> bool:
    """Todas las palabras aparecen como inicio de palabra ("cardio" encuentra "cardiología")."""
    return bool(palabras) and all(re.search(r"(?<!\w)" + re.escape(p), texto_norm) for p in palabras)


def es_columna_de_sintomas(nombre: str) -> bool:
    return any(p in normalizar(nombre) for p in PALABRAS_SINTOMA)


# ------------------------------------------------------------------ salida
@dataclass
class Evidencia:
    sintoma: str
    columna: str
    fragmentos: list[list[tuple[str, bool]]]      # una o dos líneas con el síntoma resaltado


@dataclass
class Candidato:
    fila_id: int
    titulo: str
    tabla_id: int
    tabla: str
    ubicacion: str
    color: str
    materia_id: int | None = None
    materia: str = ""
    puntaje: int = 0
    puntaje_maximo: int = 0
    cubiertos: list[str] = field(default_factory=list)
    faltantes: list[str] = field(default_factory=list)
    evidencias: list[Evidencia] = field(default_factory=list)
    otros: list[tuple[str, list[str]]] = field(default_factory=list)   # (columna, líneas) para confirmar

    @property
    def porcentaje(self) -> int:
        return round(100 * self.puntaje / self.puntaje_maximo) if self.puntaje_maximo else 0


@dataclass
class GrupoMateria:
    """Candidatos de una materia (cada materia con coincidencias tiene su propio ranking)."""
    materia_id: int | None
    nombre: str
    color: str
    total: int
    candidatos: list[Candidato]


@dataclass
class Analisis:
    sintomas: list[Sintoma]
    candidatos: list[Candidato] = field(default_factory=list)       # los mejores de todas las materias
    por_materia: list[GrupoMateria] = field(default_factory=list)
    materias_revisadas: list[str] = field(default_factory=list)
    materias_sin_coincidencias: list[str] = field(default_factory=list)
    total_candidatos: int = 0
    filas_evaluadas: int = 0
    apoyo: dict[str, list] = field(default_factory=dict)
    solo_sintomas: bool = False
    sin_columnas_de_sintomas: bool = False

    @property
    def destacados(self) -> list[Candidato]:
        """Hasta 6 candidatos para comparar, tomando por turnos los mejores de cada materia."""
        elegidos: list[Candidato] = []
        ronda = 0
        while len(elegidos) < 6 and any(ronda < len(g.candidatos) for g in self.por_materia):
            elegidos += [g.candidatos[ronda] for g in self.por_materia if ronda < len(g.candidatos)]
            ronda += 1
        return elegidos[:6]

    @property
    def matriz(self) -> list[tuple[Sintoma, list[bool]]]:
        """Para la tabla comparativa: por cada síntoma, si lo cubre cada uno de los destacados."""
        return [(s, [s.texto in c.cubiertos for c in self.destacados]) for s in self.sintomas]


# ------------------------------------------------------------------ análisis
def _filas_que_mencionan(con: sqlite3.Connection, s: Sintoma, filtros: bus.Filtros, tabla_id: int | None) -> set[int]:
    consulta = bus.expresion(s.texto)
    if not consulta:
        return set()
    extra, params = bus._condiciones(con, filtros)
    sql = f"SELECT ref FROM busqueda WHERE busqueda MATCH ? AND tipo = 'fila' {extra}"
    if tabla_id:
        sql += " AND padre = ?"
        params = [*params, tabla_id]
    try:
        return {r[0] for r in con.execute(sql + f" LIMIT {MAX_FILAS_POR_SINTOMA}", [consulta, *params])}
    except sqlite3.OperationalError:
        return set()


def _lineas(valor: str) -> list[str]:
    """Separa un texto en líneas útiles ("- miedo al fracaso" -> "miedo al fracaso")."""
    salida = []
    for linea in re.split(r"[\n;]+", valor or ""):
        linea = linea.strip().lstrip("-•*·– ").strip()
        if linea:
            salida.append(linea)
    return salida


def _materias_en_alcance(con: sqlite3.Connection, filtros: bus.Filtros) -> list[tuple[int, str]]:
    """Todas las materias que se revisan (también las archivadas), en el orden de la biblioteca."""
    sql = "SELECT id, nombre FROM materias WHERE papelera_id IS NULL"
    params: list = []
    if filtros.materia:
        sql += " AND id = ?"
        params.append(filtros.materia)
    return [(r[0], r[1]) for r in con.execute(sql + " ORDER BY archivada, orden, nombre", params)]


def analizar(con: sqlite3.Connection, sintomas: list[Sintoma], filtros: bus.Filtros | None = None,
             tabla_id: int | None = None, solo_sintomas: bool = False, limite: int = 12,
             por_materia: int = 6) -> Analisis:
    """Busca en TODAS las materias (salvo que se filtre una) y arma un ranking por cada materia."""
    analisis = Analisis(sintomas=sintomas, solo_sintomas=solo_sintomas)
    if not sintomas:
        return analisis
    filtros = filtros or bus.Filtros()
    alcance = _materias_en_alcance(con, filtros)
    analisis.materias_revisadas = [n for _, n in alcance]
    por_sintoma = {s.texto: _filas_que_mencionan(con, s, filtros, tabla_id) for s in sintomas}
    ids = set().union(*por_sintoma.values())
    if not ids:
        analisis.materias_sin_coincidencias = list(analisis.materias_revisadas)
        _apoyo(con, analisis, filtros)
        return analisis

    # Datos de las filas candidatas y sus tablas
    filas, tablas = {}, {}
    lista = list(ids)
    for i in range(0, len(lista), 900):
        lote = lista[i:i + 900]
        for f in con.execute(f"""SELECT f.id, f.titulo, f.valores, f.valores_norm, f.tabla_id, t.nombre, t.columnas,
                                        t.componente_id, t.columna_titulo
                                 FROM filas f JOIN tablas t ON t.id = f.tabla_id WHERE f.id IN ({','.join('?' * len(lote))})""", lote):
            filas[f["id"]] = f
            tablas.setdefault(f["tabla_id"], (f["nombre"], json.loads(f["columnas"]), f["componente_id"], f["columna_titulo"]))
    analisis.filas_evaluadas = len(filas)

    # Columnas donde se considera "mencionado" (todas o solo las de síntomas)
    permitidas: dict[int, list[dict]] = {}
    for tid, (_, columnas, _, _) in tablas.items():
        de_sintomas = [c for c in columnas if es_columna_de_sintomas(c["nombre"])]
        if solo_sintomas and not de_sintomas:
            analisis.sin_columnas_de_sintomas = True
        permitidas[tid] = de_sintomas if (solo_sintomas and de_sintomas) else columnas

    ubicaciones: dict[int, tuple[str, str, int | None, str]] = {}
    maximo = sum(s.peso for s in sintomas)
    candidatos = []
    for fid, f in filas.items():
        valores, norm = json.loads(f["valores"]), json.loads(f["valores_norm"])
        nombre_tabla, columnas, comp_id, columna_titulo = tablas[f["tabla_id"]]
        c = Candidato(fid, f["titulo"], f["tabla_id"], nombre_tabla, "", "", puntaje_maximo=maximo)
        usadas: set[str] = set()
        for s in sintomas:
            donde = [col for col in permitidas[f["tabla_id"]] if _coincide(norm.get(col["clave"], ""), s.palabras)]
            if not donde:
                c.faltantes.append(s.texto)
                continue
            c.cubiertos.append(s.texto)
            c.puntaje += s.peso
            col = donde[0]
            usadas.add(col["clave"])
            lineas = [ln for ln in _lineas(valores.get(col["clave"], "")) if _coincide(normalizar(ln), s.palabras)]
            lineas = lineas or [valores.get(col["clave"], "")[:200]]
            c.evidencias.append(Evidencia(s.texto, col["nombre"],
                                          [fragmentos_resaltados(ln[:220], s.texto) for ln in lineas[:2]]))
        if not c.puntaje:
            continue
        # Otros rasgos de la ficha (para preguntar u observar y confirmar o descartar)
        palabras = [p for s in sintomas for p in s.palabras]
        for col in permitidas[f["tabla_id"]]:
            if col["clave"] == columna_titulo:
                continue
            extras = [ln for ln in _lineas(valores.get(col["clave"], ""))
                      if not any(re.search(r"(?<!\w)" + re.escape(p), normalizar(ln)) for p in palabras) and len(ln) <= 160]
            if extras:
                c.otros.append((col["nombre"], extras[:4]))
        c.otros = c.otros[:4]
        if comp_id not in ubicaciones:
            try:
                comp = bib.obtener_componente(con, comp_id)
                m = bib.obtener_materia(con, comp.materia_id)
                ruta = " › ".join([m.nombre, *(a.nombre for a in bib.ancestros(con, comp)), comp.nombre])
                ubicaciones[comp_id] = (ruta, COLOR_POR_ID.get(m.color, COLOR_POR_ID["pizarra"])["hex"], m.id, m.nombre)
            except Exception:
                ubicaciones[comp_id] = ("", COLOR_POR_ID["pizarra"]["hex"], None, "")
        c.ubicacion, c.color, c.materia_id, c.materia = ubicaciones[comp_id]
        candidatos.append(c)

    candidatos.sort(key=lambda c: (-c.puntaje, -len(c.cubiertos), normalizar(c.titulo)))
    analisis.total_candidatos = len(candidatos)
    analisis.candidatos = candidatos[:limite]
    # Un ranking por materia, para que ninguna quede tapada por otra con más coincidencias.
    # Las materias se ordenan por su mejor candidato.
    grupos: dict[int | None, GrupoMateria] = {}
    for c in candidatos:
        if c.materia_id not in grupos:
            grupos[c.materia_id] = GrupoMateria(c.materia_id, c.materia, c.color, 0, [])
        g = grupos[c.materia_id]
        g.total += 1
        if len(g.candidatos) < por_materia:
            g.candidatos.append(c)
    analisis.por_materia = list(grupos.values())
    con_resultados = {g.nombre for g in analisis.por_materia}
    analisis.materias_sin_coincidencias = [n for n in analisis.materias_revisadas if n not in con_resultados]
    _apoyo(con, analisis, filtros)
    return analisis


def _apoyo(con: sqlite3.Connection, analisis: Analisis, filtros: bus.Filtros) -> None:
    """Qué dicen los PDF, notas e imágenes sobre cada síntoma (3 resultados por síntoma)."""
    otros = bus.Filtros(categorias=["pdf", "notas", "imagenes"], materia=filtros.materia, componente=filtros.componente)
    for s in analisis.sintomas:
        r = bus.buscar(con, s.texto, otros, limite=5)
        if r.resultados:
            analisis.apoyo[s.texto] = r.resultados


# --------------------------------------------------------------- sugerencias
def sugerencias(con: sqlite3.Connection, q: str, limite: int = 10) -> list[str]:
    """Síntomas que existen en el material y empiezan como lo que se escribe (para autocompletar)."""
    palabras = [p for p in re.findall(r"\w+", normalizar(q))]
    consulta = bus.expresion(q)
    if not consulta or not palabras:
        return []
    ids = [r[0] for r in con.execute(
        f"SELECT ref FROM busqueda WHERE busqueda MATCH ? AND tipo = 'fila' {bus._EXCLUIR_PAPELERA} LIMIT 300", [consulta])]
    encontrados: dict[str, tuple] = {}
    for i in range(0, len(ids), 900):
        lote = ids[i:i + 900]
        for f in con.execute(f"""SELECT f.valores, t.columnas FROM filas f JOIN tablas t ON t.id = f.tabla_id
                                 WHERE f.id IN ({','.join('?' * len(lote))})""", lote):
            valores, columnas = json.loads(f["valores"]), json.loads(f["columnas"])
            for col in columnas:
                prioridad = 0 if es_columna_de_sintomas(col["nombre"]) else 1
                for ln in _lineas(valores.get(col["clave"], "")):
                    n = normalizar(ln)
                    if len(ln) <= 90 and _coincide(n, palabras):
                        clave = n.rstrip(".")
                        orden = (prioridad, not n.startswith(palabras[0]), len(ln))
                        if clave not in encontrados or orden < encontrados[clave][0]:
                            encontrados[clave] = (orden, ln.rstrip("."))
    return [t for _, t in sorted(encontrados.values())][:limite]


# ----------------------------------------------------------------- informe
def nota_markdown(a: Analisis) -> str:
    """Resumen del análisis en Markdown (se guarda con el caso)."""
    lineas = ["## Síntomas", ""]
    lineas += [f"- {s.texto}{' **(importante)**' if s.importante else ''}" for s in a.sintomas]
    lineas += ["", "## Candidatos según la biblioteca", ""]
    if a.materias_revisadas:
        lineas.append(f"Materias revisadas: {', '.join(a.materias_revisadas)}.")
        lineas.append("")
    if not a.por_materia:
        lineas.append("_Ningún registro de la biblioteca menciona estos síntomas._")
    for g in a.por_materia:
        lineas += [f"### {g.nombre or 'Sin materia'}", ""]
        for i, c in enumerate(g.candidatos[:5], 1):
            lineas.append(f"{i}. **{c.titulo}** — {len(c.cubiertos)} de {len(a.sintomas)} síntomas ({c.porcentaje} %) · "
                          f"[ver ficha](/filas/{c.fila_id}) · {c.tabla}")
            for e in c.evidencias:
                texto = " / ".join("".join(t for t, _ in frag) for frag in e.fragmentos)
                lineas.append(f"    - _{e.sintoma}_ → {e.columna}: {texto}")
            if c.faltantes:
                lineas.append(f"    - No menciona: {', '.join(c.faltantes)}")
        lineas.append("")
    if a.materias_sin_coincidencias:
        lineas.append(f"Sin coincidencias en: {', '.join(a.materias_sin_coincidencias)}.")
    lineas += ["", "> Generado por la herramienta de diagnóstico a partir del material de estudio. "
                   "No reemplaza el juicio clínico."]
    return "\n".join(lineas)

"""Acceso rápido por síntomas a partir del material guardado (herramienta de estudio).

Funciona como una repertorización: cada síntoma se busca en las filas de las tablas (p. ej.
medicamentos o enfermedades), en las notas y en el texto de las imágenes (su descripción y su OCR):
cada fila, nota o imagen es un candidato. Los candidatos se ordenan por cuántos síntomas cubren (los
«importantes» pesan el doble) y para cada uno se muestra la evidencia (columna o renglón), los
síntomas que no menciona y otros rasgos que conviene comprobar. Además se reúne lo que dicen los
PDF sobre cada síntoma.

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
    """Columnas cuyo nombre habla de síntomas: sus renglones salen primero en las sugerencias."""
    return any(p in normalizar(nombre) for p in PALABRAS_SINTOMA)


# ------------------------------------------------------------------ salida
@dataclass
class Evidencia:
    sintoma: str
    columna: str
    fragmentos: list[list[tuple[str, bool]]]      # una o dos líneas con el síntoma resaltado


# Material que puede ser candidato: tipo del índice -> (rótulo, enlace)
TIPOS_CANDIDATO = {"fila": ("Ficha", "/filas/{}"), "nota": ("Nota", "/notas/{}"), "imagen": ("Imagen", "/imagenes/{}")}


@dataclass
class Candidato:
    fila_id: int                    # id del elemento (fila, nota o imagen, según `tipo`)
    titulo: str
    tabla_id: int
    tabla: str
    ubicacion: str
    color: str
    materia_id: int | None = None
    materia: str = ""
    icono: str = "book-open"        # ícono de la materia
    puntaje: int = 0
    puntaje_maximo: int = 0
    cubiertos: list[str] = field(default_factory=list)
    faltantes: list[str] = field(default_factory=list)
    evidencias: list[Evidencia] = field(default_factory=list)
    otros: list[tuple[str, list[str]]] = field(default_factory=list)   # (columna, líneas) para confirmar
    tipo: str = "fila"              # fila | nota | imagen
    en_titulo: int = 0              # síntomas que están en su propio título (desempata: «Osteoporosis» antes que
                                    # una lámina que solo la menciona)

    @property
    def url(self) -> str:
        return TIPOS_CANDIDATO[self.tipo][1].format(self.fila_id)

    @property
    def rotulo_tipo(self) -> str:
        return TIPOS_CANDIDATO[self.tipo][0]

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
    candidatos: list[Candidato]                                       # los mejores (los que se muestran)
    todos: list[Candidato] = field(default_factory=list)              # todos, para la comparación
    icono: str = "book-open"


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

    @property
    def destacados(self) -> list[GrupoMateria]:
        """Columnas de la comparación: una por materia con resultados (identificada por su ícono)."""
        return [g for g in self.por_materia if g.todos]

    @property
    def matriz(self) -> list[tuple[Sintoma, list[list[str]]]]:
        """Para la tabla comparativa: por cada síntoma y cada materia, qué registros de esa materia lo mencionan
        (todos, no solo los que se muestran en su ranking: así ningún síntoma encontrado queda sin marca)."""
        return [(s, [[c.titulo for c in g.todos if s.texto in c.cubiertos] for g in self.destacados])
                for s in self.sintomas]


# ------------------------------------------------------------------ análisis
def _filas_que_mencionan(con: sqlite3.Connection, s: Sintoma, filtros: bus.Filtros, tabla_id: int | None,
                         tipo: str = "fila") -> set[int]:
    consulta = bus.expresion(s.texto)
    if not consulta:
        return set()
    extra, params = bus._condiciones(con, filtros)
    sql = f"SELECT ref FROM busqueda WHERE busqueda MATCH ? AND tipo = '{tipo}' {extra}"
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


def _lineas_texto(texto: str) -> list[str]:
    """Renglones legibles de una nota en Markdown o de la descripción de una imagen: sin marcas de título,
    cita o lista; las filas de una tabla quedan como «celda | celda» y sus separadores se descartan."""
    salida = []
    for linea in (texto or "").split("\n"):
        linea = linea.strip()
        if not linea or re.fullmatch(r"\|?[\s:|-]+\|?", linea):
            continue
        if linea.startswith("|"):
            linea = " | ".join(c.strip() for c in linea.strip("|").split("|") if c.strip())
        linea = re.sub(r"^(#{1,6}|>|[-*•·–✓✔️]+)\s*", "", linea)
        linea = re.sub(r"\*\*(.+?)\*\*", r"\1", linea).strip()
        if linea:
            salida.append(linea)
    return salida


def _materias_en_alcance(con: sqlite3.Connection, filtros: bus.Filtros) -> list[tuple[int, str]]:
    """Todas las materias que se revisan (también las archivadas), en el orden de la biblioteca."""
    sql = f"SELECT id, nombre FROM materias WHERE papelera_id IS NULL AND id NOT IN ({bib.SQL_OCULTAS_SIN_BUSQUEDA})"
    params: list = []
    if filtros.materia:
        sql += " AND id = ?"
        params.append(filtros.materia)
    return [(r[0], r[1]) for r in con.execute(sql + " ORDER BY archivada, orden, nombre", params)]


def analizar(con: sqlite3.Connection, sintomas: list[Sintoma], filtros: bus.Filtros | None = None,
             tabla_id: int | None = None, limite: int = 12,
             por_materia: int = 6) -> Analisis:
    """Busca en TODAS las materias (salvo que se filtre una) y arma un ranking por cada materia."""
    analisis = Analisis(sintomas=sintomas)
    if not sintomas:
        return analisis
    filtros = filtros or bus.Filtros()
    alcance = _materias_en_alcance(con, filtros)
    analisis.materias_revisadas = [n for _, n in alcance]
    por_sintoma = {s.texto: _filas_que_mencionan(con, s, filtros, tabla_id) for s in sintomas}
    ids = set().union(*por_sintoma.values())

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

    # Un síntoma cuenta en cualquier columna de la fila
    permitidas: dict[int, list[dict]] = {tid: columnas for tid, (_, columnas, _, _) in tablas.items()}
    # La numeración de filas (1, 2, 3…) no es un rasgo de la ficha: no se muestra entre «otros rasgos»
    numeracion = {tid: _columnas_de_numeracion(con, tid, columnas) for tid, columnas in permitidas.items()}

    ubicaciones: dict[int, tuple[str, str, int | None, str, str]] = {}
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
            if col["clave"] == columna_titulo or col["clave"] in numeracion[f["tabla_id"]]:
                continue
            extras = [ln for ln in _lineas(valores.get(col["clave"], ""))
                      if not any(re.search(r"(?<!\w)" + re.escape(p), normalizar(ln)) for p in palabras) and len(ln) <= 160]
            if extras:
                c.otros.append((col["nombre"], extras[:4]))
        c.otros = c.otros[:4]
        c.ubicacion, c.color, c.materia_id, c.materia, c.icono = _ubicacion(con, comp_id, ubicaciones)
        candidatos.append(c)

    # Notas e imágenes también son candidatas (salvo que se consulte una sola tabla)
    if tabla_id is None:
        candidatos += _candidatos_de_texto(con, sintomas, filtros, maximo, ubicaciones)
    for c in candidatos:
        if c.tipo == "fila":
            c.en_titulo = sum(_coincide(normalizar(c.titulo), s.palabras) for s in sintomas if s.texto in c.cubiertos)

    candidatos.sort(key=lambda c: (-c.puntaje, -len(c.cubiertos), -c.en_titulo, normalizar(c.titulo)))
    analisis.total_candidatos = len(candidatos)
    analisis.candidatos = candidatos[:limite]
    # Un ranking por materia, para que ninguna quede tapada por otra con más coincidencias.
    # Las materias se ordenan por su mejor candidato.
    grupos: dict[int | None, GrupoMateria] = {}
    for c in candidatos:
        if c.materia_id not in grupos:
            grupos[c.materia_id] = GrupoMateria(c.materia_id, c.materia, c.color, 0, [], icono=c.icono)
        g = grupos[c.materia_id]
        g.total += 1
        g.todos.append(c)
        if len(g.candidatos) < por_materia:
            g.candidatos.append(c)
    analisis.por_materia = list(grupos.values())
    con_resultados = {g.nombre for g in analisis.por_materia}
    analisis.materias_sin_coincidencias = [n for n in analisis.materias_revisadas if n not in con_resultados]
    _apoyo(con, analisis, filtros)
    return analisis


def _columnas_de_numeracion(con: sqlite3.Connection, tabla_id: int, columnas: list[dict]) -> set[str]:
    """Columnas que solo numeran las filas: en el orden de la tabla valen 1, 2, 3… (o n, n+1, n+2…),
    como la «Columna 1» que agrega Google Sheets a una tabla. Hacen falta al menos 3 filas."""
    valores = [json.loads(r[0]) for r in con.execute(
        "SELECT valores FROM filas WHERE tabla_id = ? AND huerfana = 0 ORDER BY posicion", (tabla_id,))]
    if len(valores) < 3:
        return set()
    salida = set()
    for col in columnas:
        serie = [v.get(col["clave"], "").strip() for v in valores]
        if all(s.isdigit() for s in serie):
            numeros = [int(s) for s in serie]
            if numeros == list(range(numeros[0], numeros[0] + len(numeros))):
                salida.add(col["clave"])
    return salida


def _ubicacion(con: sqlite3.Connection, comp_id: int, cache: dict) -> tuple[str, str, int | None, str, str]:
    """(ruta legible, color, id y nombre de la materia, ícono de la materia) de un componente."""
    if comp_id not in cache:
        try:
            comp = bib.obtener_componente(con, comp_id)
            m = bib.obtener_materia(con, comp.materia_id)
            ruta = " › ".join([m.nombre, *(a.nombre for a in bib.ancestros(con, comp)), comp.nombre])
            cache[comp_id] = (ruta, COLOR_POR_ID.get(m.color, COLOR_POR_ID["pizarra"])["hex"], m.id, m.nombre, m.icono)
        except Exception:
            cache[comp_id] = ("", COLOR_POR_ID["pizarra"]["hex"], None, "", "book-open")
    return cache[comp_id]


def _candidatos_de_texto(con: sqlite3.Connection, sintomas: list[Sintoma], filtros: bus.Filtros, maximo: int,
                         ubicaciones: dict) -> list[Candidato]:
    """Notas e imágenes como candidatos: cada una se evalúa como una ficha cuyo «campo» es su texto.
    Un síntoma cuenta si aparece en el título o en un renglón; la evidencia es ese renglón."""
    consultas = {
        "nota": ("SELECT id, titulo, contenido AS texto, componente_id FROM notas "
                 "WHERE papelera_id IS NULL AND id IN ({})"),
        "imagen": ("SELECT id, titulo, descripcion || char(10) || texto_ocr AS texto, componente_id FROM imagenes "
                   "WHERE papelera_id IS NULL AND id IN ({})"),
    }
    salida = []
    for tipo, sql in consultas.items():
        ids = set().union(*(_filas_que_mencionan(con, s, filtros, None, tipo) for s in sintomas))
        if not ids:
            continue
        lista = list(ids)
        for i in range(0, len(lista), 900):
            lote = lista[i:i + 900]
            for f in con.execute(sql.format(",".join("?" * len(lote))), lote):
                c = _candidato_de_texto(con, tipo, f, sintomas, maximo, ubicaciones)
                if c:
                    salida.append(c)
    return salida


def _candidato_de_texto(con, tipo: str, f, sintomas: list[Sintoma], maximo: int, ubicaciones: dict) -> Candidato | None:
    ruta, color, materia_id, materia, icono = _ubicacion(con, f["componente_id"], ubicaciones)
    componente = ruta.rsplit(" › ", 1)[-1]
    titulo = f["titulo"]
    if componente and titulo.endswith(f" - {componente}"):     # «Osteoporosis (…) - Campo Magnético»
        titulo = titulo[: -len(f" - {componente}")]
    lineas = _lineas_texto(f["texto"])
    columna = TIPOS_CANDIDATO[tipo][0]
    c = Candidato(f["id"], titulo, 0, columna, ruta, color, materia_id, materia, icono, puntaje_maximo=maximo, tipo=tipo)
    titulo_norm = normalizar(titulo)
    for s in sintomas:
        if _coincide(titulo_norm, s.palabras):
            c.cubiertos.append(s.texto)
            c.puntaje += s.peso
            c.evidencias.append(Evidencia(s.texto, "Título", [fragmentos_resaltados(titulo[:220], s.texto)]))
            c.en_titulo += 1
            continue
        coinciden = [ln for ln in lineas if _coincide(normalizar(ln), s.palabras)]
        if not coinciden:
            c.faltantes.append(s.texto)
            continue
        c.cubiertos.append(s.texto)
        c.puntaje += s.peso
        c.evidencias.append(Evidencia(s.texto, columna, [fragmentos_resaltados(ln[:220], s.texto) for ln in coinciden[:2]]))
    if not c.puntaje:
        return None
    palabras = [p for s in sintomas for p in s.palabras]
    extras = [ln for ln in lineas if len(ln) <= 160 and normalizar(ln) != titulo_norm
              and not any(re.search(r"(?<!\w)" + re.escape(p), normalizar(ln)) for p in palabras)]
    if extras:
        c.otros.append((columna, extras[:4]))
    return c


def _apoyo(con: sqlite3.Connection, analisis: Analisis, filtros: bus.Filtros) -> None:
    """Qué dicen los PDF sobre cada síntoma (las notas e imágenes ya entran como candidatos)."""
    otros = bus.Filtros(categorias=["pdf"], materia=filtros.materia, componente=filtros.componente)
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


# --------------------------------------------------------------- cobertura
@dataclass
class Faltante:
    tipo: str            # fila | nota | imagen
    id: int
    materia: str
    contenedor: str      # tabla (filas) o componente (notas e imágenes)
    titulo: str
    busqueda: str        # lo que se buscó y no lo trajo
    motivo: str


def _palabra_de_contenido(texto: str, titulo: str) -> str | None:
    """La palabra más larga del contenido que no está en el título (sin números), para buscar por el cuerpo."""
    del_titulo = set(re.findall(r"\w+", normalizar(titulo)))
    palabras = [p for p in re.findall(r"\w+", normalizar(texto))
                if p not in del_titulo and len(p) >= 5 and not any(ch.isdigit() for ch in p)]
    return max(palabras, key=len) if palabras else None


def revisar_cobertura(con: sqlite3.Connection) -> tuple[int, list[Faltante]]:
    """Comprueba que cada fila, nota e imagen vigente sea candidata en Acceso rápido: buscándola por su
    título y por una palabra de su contenido. Devuelve (elementos revisados, los que no aparecieron)."""
    vigentes = """JOIN componentes c ON c.id = {t}.componente_id JOIN materias m ON m.id = c.materia_id
                  WHERE {t}.papelera_id IS NULL AND c.papelera_id IS NULL AND m.papelera_id IS NULL
                  AND NOT (m.oculta = 1 AND m.en_busqueda = 0)"""
    elementos = []    # (tipo, id, materia, contenedor, título visible, contenido)
    for f in con.execute(f"""SELECT f.id, f.titulo, f.valores, t.nombre, t.columna_titulo, m.nombre AS materia
                             FROM filas f JOIN tablas t ON t.id = f.tabla_id {vigentes.format(t='t')}
                             AND f.huerfana = 0"""):
        valores = json.loads(f["valores"])
        titulo = f["titulo"].strip() or next((v for v in valores.values() if v.strip()), "")
        cuerpo = " ".join(v for k, v in valores.items() if k != f["columna_titulo"])
        elementos.append(("fila", f["id"], f["materia"], f["nombre"], titulo, cuerpo))
    for tipo, sql in (("nota", "SELECT x.id, x.titulo, x.contenido AS texto, m.nombre AS materia, c.nombre AS comp "
                               "FROM notas x {}"),
                      ("imagen", "SELECT x.id, x.titulo, x.descripcion || ' ' || COALESCE(x.texto_ocr, '') AS texto, "
                                 "m.nombre AS materia, c.nombre AS comp FROM imagenes x {}")):
        for f in con.execute(sql.format(vigentes.format(t="x"))):
            titulo = f["titulo"]
            if titulo.endswith(f" - {f['comp']}"):     # Acceso rápido muestra el título sin « - <componente>»
                titulo = titulo[: -len(f" - {f['comp']}")]
            elementos.append((tipo, f["id"], f["materia"], f["comp"], titulo, f["texto"] or ""))

    faltantes = []
    for tipo, ref, materia, contenedor, titulo, cuerpo in elementos:
        busquedas = []
        palabras_titulo = re.findall(r"\w+", titulo)[:6]
        if palabras_titulo:
            busquedas.append((" ".join(palabras_titulo), "no aparece al buscar su título"))
        palabra = _palabra_de_contenido(cuerpo, titulo)
        if palabra:
            busquedas.append((palabra, "no aparece al buscar una palabra de su contenido"))
        if not busquedas:
            faltantes.append(Faltante(tipo, ref, materia, contenedor, titulo, "", "no tiene texto para buscar"))
        for texto, motivo in busquedas:
            a = analizar(con, preparar([texto], []))
            if not any(c.tipo == tipo and c.fila_id == ref for g in a.por_materia for c in g.todos):
                faltantes.append(Faltante(tipo, ref, materia, contenedor, titulo, texto, motivo))
    return len(elementos), faltantes


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
                          f"[ver {c.rotulo_tipo.lower()}]({c.url}) · {c.tabla}")
            for e in c.evidencias:
                texto = " / ".join("".join(t for t, _ in frag) for frag in e.fragmentos)
                lineas.append(f"    - _{e.sintoma}_ → {e.columna}: {texto}")
            if c.faltantes:
                lineas.append(f"    - No menciona: {', '.join(c.faltantes)}")
        lineas.append("")
    if a.materias_sin_coincidencias:
        lineas.append(f"Sin coincidencias en: {', '.join(a.materias_sin_coincidencias)}.")
    lineas += ["", "> Generado por Acceso rápido a partir del material de estudio. "
                   "No reemplaza el juicio clínico."]
    return "\n".join(lineas)

"""Tablas importadas de Excel/CSV: creación, actualización sin perder imágenes y consulta.

Esquema dinámico: cada tabla guarda sus columnas en JSON y cada fila sus valores en JSON
(claves c1, c2, …), así que no hay columnas fijas en la base de datos.
"""
from __future__ import annotations

import json
import logging
import shutil
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from ..db import ahora, transaccion
from ..errores import ErrorUsuario, NoEncontrado
from ..models import Fila, Tabla
from . import almacenamiento as alm
from . import biblioteca as bib
from . import hojas as lector
from . import importacion as imp
from .texto import clave_orden, normalizar

log = logging.getLogger(__name__)

POR_PAGINA = (25, 50, 100)


# ------------------------------------------------------------------ consultas
def obtener(con: sqlite3.Connection, tabla_id: int) -> Tabla:
    f = con.execute(
        """SELECT t.* FROM tablas t JOIN componentes c ON c.id = t.componente_id
           WHERE t.id = ? AND t.papelera_id IS NULL AND c.papelera_id IS NULL""", (tabla_id,)
    ).fetchone()
    if f is None:
        raise NoEncontrado("La tabla")
    t = Tabla.desde_fila(f)
    _contar(con, t)
    return t


def _contar(con: sqlite3.Connection, t: Tabla) -> None:
    fila = con.execute(
        """SELECT COUNT(*) AS n, SUM(huerfana) AS h,
                  (SELECT COUNT(*) FROM imagenes_fila i JOIN filas f2 ON f2.id = i.fila_id
                   WHERE f2.tabla_id = ? AND i.papelera_id IS NULL) AS imgs
           FROM filas WHERE tabla_id = ?""", (t.id, t.id)).fetchone()
    t.num_filas, t.num_huerfanas, t.num_imagenes = fila["n"], fila["h"] or 0, fila["imgs"]


def listar(con: sqlite3.Connection, componente_id: int) -> list[Tabla]:
    tablas = [Tabla.desde_fila(f) for f in con.execute(
        "SELECT * FROM tablas WHERE componente_id = ? AND papelera_id IS NULL ORDER BY orden, id", (componente_id,))]
    for t in tablas:
        _contar(con, t)
    return tablas


@dataclass
class Consulta:
    q: str = ""
    filtros: dict[str, str] | None = None
    orden: str = ""
    desc: bool = False
    solo_imagenes: bool = False
    pagina: int = 1
    por_pagina: int = 50


def consultar(con: sqlite3.Connection, t: Tabla, c: Consulta) -> tuple[list[Fila], int]:
    """Filas de una página con búsqueda, filtros por columna y orden (todo en SQL)."""
    donde, params = ["f.tabla_id = ?"], [t.id]
    for palabra in normalizar(c.q).split():
        donde.append("f.texto_norm LIKE ? ESCAPE '\\'")
        params.append(f"%{_escapar(palabra)}%")
    for clave, valor in (c.filtros or {}).items():
        if clave in t.claves and normalizar(valor):
            donde.append("json_extract(f.valores_norm, ?) LIKE ? ESCAPE '\\'")
            params += [f"$.{clave}", f"%{_escapar(normalizar(valor))}%"]
    if c.solo_imagenes:
        donde.append("EXISTS (SELECT 1 FROM imagenes_fila i WHERE i.fila_id = f.id AND i.papelera_id IS NULL)")
    where = " AND ".join(donde)
    total = con.execute(f"SELECT COUNT(*) FROM filas f WHERE {where}", params).fetchone()[0]
    sentido = "DESC" if c.desc else "ASC"
    if c.orden == "_imagenes":
        orden_sql, extra = f"num_imagenes {sentido}, f.posicion", []
    elif c.orden in t.claves:
        orden_sql, extra = f"json_extract(f.valores_orden, ?) {sentido}, f.posicion", [f"$.{c.orden}"]
    else:
        orden_sql, extra = "f.huerfana, f.posicion", []
    por_pagina = c.por_pagina if c.por_pagina in POR_PAGINA else 50
    pagina = max(1, min(c.pagina, max(1, -(-total // por_pagina))))
    filas = con.execute(
        f"""SELECT f.*, (SELECT COUNT(*) FROM imagenes_fila i WHERE i.fila_id = f.id AND i.papelera_id IS NULL) AS num_imagenes
            FROM filas f WHERE {where} ORDER BY {orden_sql} LIMIT ? OFFSET ?""",
        [*params, *extra, por_pagina, (pagina - 1) * por_pagina],
    ).fetchall()
    c.pagina, c.por_pagina = pagina, por_pagina
    return [Fila.desde_fila(f) for f in filas], total


def _escapar(texto: str) -> str:
    return texto.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def obtener_fila(con: sqlite3.Connection, fila_id: int) -> Fila:
    f = con.execute(
        """SELECT f.*, (SELECT COUNT(*) FROM imagenes_fila i WHERE i.fila_id = f.id AND i.papelera_id IS NULL) AS num_imagenes
           FROM filas f JOIN tablas t ON t.id = f.tabla_id JOIN componentes c ON c.id = t.componente_id
           WHERE f.id = ? AND t.papelera_id IS NULL AND c.papelera_id IS NULL""", (fila_id,)
    ).fetchone()
    if f is None:
        raise NoEncontrado("La fila")
    return Fila.desde_fila(f)


def vecinas(con: sqlite3.Connection, fila: Fila) -> tuple[int | None, int | None]:
    anterior = con.execute("SELECT id FROM filas WHERE tabla_id=? AND posicion < ? ORDER BY posicion DESC LIMIT 1",
                           (fila.tabla_id, fila.posicion)).fetchone()
    siguiente = con.execute("SELECT id FROM filas WHERE tabla_id=? AND posicion > ? ORDER BY posicion LIMIT 1",
                            (fila.tabla_id, fila.posicion)).fetchone()
    return (anterior[0] if anterior else None, siguiente[0] if siguiente else None)


# --------------------------------------------------------------- importación
@dataclass
class Preparada:
    """Una hoja lista para guardar: columnas definitivas y registros."""
    indice: int
    hoja: str | None
    cfg: imp.ConfigHoja
    columnas: list[dict]            # [{"clave","nombre","origen","ancho"}]
    titulo: str
    clave: str | None
    registros: list[tuple[int, dict[str, str]]]


def preparar(estado: imp.Estado, hojas: list[lector.Hoja], indice: int, previas: list[dict] | None = None) -> Preparada:
    cfg = estado.config_hoja(indice)
    hoja = hojas[indice]
    if not cfg.columnas:
        raise ErrorUsuario("Elige al menos una columna para importar.")
    if cfg.titulo is None or cfg.titulo not in cfg.columnas:
        raise ErrorUsuario("Elige cuál columna es el título de cada ficha (debe estar entre las importadas).")
    disponibles = {c.indice: c for c in lector.columnas(hoja, cfg.fila_encabezado, cfg.dos_filas)}
    indices = [i for i in cfg.columnas if i in disponibles]
    filas = lector.registros(hoja, cfg.fila_encabezado, cfg.dos_filas, indices)
    # Claves estables: al actualizar se reutiliza la clave de la columna con el mismo nombre
    previas_por_nombre = {normalizar(c["nombre"]): c["clave"] for c in (previas or [])}
    siguiente = max((int(c["clave"][1:]) for c in previas or []), default=0) + 1
    columnas, clave_de = [], {}
    for pos, i in enumerate(indices):
        col = disponibles[i]
        clave = previas_por_nombre.get(normalizar(col.nombre))
        if clave is None or clave in clave_de.values():
            clave, siguiente = f"c{siguiente}", siguiente + 1
        clave_de[i] = clave
        columnas.append({"clave": clave, "nombre": col.nombre, "origen": col.letra,
                         "ancho": lector.ancho_columna(col.nombre, [f[1][pos] for f in filas[:2000]])})
    registros = [(n, {clave_de[i]: v for i, v in zip(indices, valores)}) for n, valores in filas]
    hoja_nombre = None if Path(estado.archivo_original).suffix.lower() in lector.EXTENSIONES_CSV else hoja.nombre
    return Preparada(indice, hoja_nombre, cfg, columnas, clave_de[cfg.titulo],
                     clave_de.get(cfg.clave) if cfg.clave is not None else None, registros)


def _valores_fila(valores: dict[str, str], titulo: str, clave: str | None) -> tuple:
    norm = {k: normalizar(v) for k, v in valores.items()}
    orden = {k: clave_orden(v) for k, v in valores.items()}
    texto = " ".join(v for v in norm.values() if v)
    return (valores.get(titulo, "").strip() or "(sin título)", norm.get(clave or titulo, ""),
            json.dumps(valores, ensure_ascii=False), json.dumps(norm, ensure_ascii=False),
            json.dumps(orden, ensure_ascii=False), texto)


def _guardar_archivo(con: sqlite3.Connection, estado: imp.Estado) -> tuple[str, Path]:
    """Copia el archivo subido a <componente>/excel/ con su nombre descriptivo (p. ej. "Atlas de huesos.xlsx")."""
    comp = bib.obtener_componente(con, estado.componente_id)
    carpeta = bib.carpeta_componente(con, comp) / "excel"
    carpeta.mkdir(parents=True, exist_ok=True)
    extension = Path(estado.archivo_original).suffix.lower()
    destino = alm.ruta_libre(carpeta, f"{alm.nombre_legible(estado.nombre, 80)}{extension}")
    shutil.copy2(imp.archivo_subido(estado), destino)
    return f"excel/{destino.name}", destino


def importar(con: sqlite3.Connection, estado: imp.Estado) -> list[int]:
    """Crea una tabla por cada hoja elegida."""
    todas = imp.hojas(estado)
    preparadas = [preparar(estado, todas, i) for i in estado.seleccion]
    relativo, destino = _guardar_archivo(con, estado)
    ids = []
    try:
        with transaccion(con):
            orden = con.execute("SELECT COALESCE(MAX(orden),0) FROM tablas WHERE componente_id=?",
                                (estado.componente_id,)).fetchone()[0]
            for p in preparadas:
                orden += 1
                t = ahora()
                cur = con.execute(
                    """INSERT INTO tablas (componente_id, nombre, archivo, archivo_original, hoja, fila_encabezado,
                       dos_filas, columnas, columna_titulo, columna_clave, hash, orden, creado, actualizado)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (estado.componente_id, p.cfg.nombre_tabla or "Tabla", relativo, estado.archivo_original, p.hoja,
                     p.cfg.fila_encabezado, int(p.cfg.dos_filas), json.dumps(p.columnas, ensure_ascii=False),
                     p.titulo, p.clave, estado.hash, orden, t, t))
                tabla_id = int(cur.lastrowid)
                con.executemany(
                    """INSERT INTO filas (tabla_id, posicion, fila_origen, titulo, clave_norm, valores, valores_norm, valores_orden, texto_norm)
                       VALUES (?,?,?,?,?,?,?,?,?)""",
                    [(tabla_id, pos, n, *_valores_fila(v, p.titulo, p.clave)) for pos, (n, v) in enumerate(p.registros, 1)])
                ids.append(tabla_id)
                log.info("Tabla importada: %s (%s filas)", p.cfg.nombre_tabla, len(p.registros))
    except BaseException:
        destino.unlink(missing_ok=True)
        raise
    imp.descartar(estado.token)
    return ids


@dataclass
class ResumenReemplazo:
    actualizadas: int = 0
    nuevas: int = 0
    eliminadas: int = 0
    conservadas: int = 0  # ya no están en el Excel pero tienen imágenes


def _emparejar(con: sqlite3.Connection, t: Tabla, p: Preparada) -> tuple[list, list, list, ResumenReemplazo]:
    existentes: dict[str, list[sqlite3.Row]] = {}
    con_imagenes = {r[0] for r in con.execute(
        """SELECT DISTINCT f.id FROM filas f JOIN imagenes_fila i ON i.fila_id = f.id
           WHERE f.tabla_id = ?""", (t.id,))}
    for f in con.execute("SELECT id, clave_norm FROM filas WHERE tabla_id = ? ORDER BY posicion", (t.id,)):
        existentes.setdefault(f["clave_norm"], []).append(f)
    actualizar, insertar = [], []
    for pos, (n, valores) in enumerate(p.registros, 1):
        datos = _valores_fila(valores, p.titulo, p.clave)
        candidatas = existentes.get(datos[1]) if datos[1] else None
        if candidatas:
            actualizar.append((candidatas.pop(0)["id"], pos, n, datos))
        else:
            insertar.append((pos, n, datos))
    sobrantes = [f["id"] for lista in existentes.values() for f in lista]
    resumen = ResumenReemplazo(actualizadas=len(actualizar), nuevas=len(insertar),
                               conservadas=sum(1 for i in sobrantes if i in con_imagenes),
                               eliminadas=sum(1 for i in sobrantes if i not in con_imagenes))
    return actualizar, insertar, [(i, i in con_imagenes) for i in sobrantes], resumen


def previsualizar_reemplazo(con: sqlite3.Connection, estado: imp.Estado) -> ResumenReemplazo:
    t = obtener(con, estado.tabla_id)
    p = preparar(estado, imp.hojas(estado), estado.seleccion[0], t.columnas)
    return _emparejar(con, t, p)[3]


def reemplazar(con: sqlite3.Connection, estado: imp.Estado) -> ResumenReemplazo:
    """Actualiza una tabla con un Excel nuevo. Las filas se emparejan por la columna clave
    (o la del título) y conservan sus imágenes; las que desaparecen y tienen imágenes se conservan."""
    t = obtener(con, estado.tabla_id)
    p = preparar(estado, imp.hojas(estado), estado.seleccion[0], t.columnas)
    actualizar, insertar, sobrantes, resumen = _emparejar(con, t, p)
    archivo_anterior = t.archivo
    relativo, destino = _guardar_archivo(con, estado)
    try:
        with transaccion(con):
            con.execute(
                """UPDATE tablas SET nombre=?, archivo=?, archivo_original=?, hoja=?, fila_encabezado=?, dos_filas=?,
                   columnas=?, columna_titulo=?, columna_clave=?, hash=?, actualizado=? WHERE id=?""",
                (p.cfg.nombre_tabla or t.nombre, relativo, estado.archivo_original, p.hoja, p.cfg.fila_encabezado,
                 int(p.cfg.dos_filas), json.dumps(p.columnas, ensure_ascii=False), p.titulo, p.clave, estado.hash,
                 ahora(), t.id))
            con.executemany(
                """UPDATE filas SET posicion=?, fila_origen=?, titulo=?, clave_norm=?, valores=?, valores_norm=?,
                   valores_orden=?, texto_norm=?, huerfana=0 WHERE id=?""",
                [(pos, n, *datos, fid) for fid, pos, n, datos in actualizar])
            con.executemany(
                """INSERT INTO filas (tabla_id, posicion, fila_origen, titulo, clave_norm, valores, valores_norm, valores_orden, texto_norm)
                   VALUES (?,?,?,?,?,?,?,?,?)""", [(t.id, pos, n, *datos) for pos, n, datos in insertar])
            base = len(p.registros)
            for extra, (fid, conservar) in enumerate(sobrantes, 1):
                if conservar:
                    con.execute("UPDATE filas SET huerfana=1, posicion=? WHERE id=?", (base + extra, fid))
                else:
                    con.execute("DELETE FROM filas WHERE id=?", (fid,))
    except BaseException:
        destino.unlink(missing_ok=True)
        raise
    _retirar_archivo_si_nadie_lo_usa(con, t.componente_id, archivo_anterior, t.nombre)
    imp.descartar(estado.token)
    log.info("Tabla actualizada: %s %s", t.nombre, resumen)
    return resumen


def _retirar_archivo_si_nadie_lo_usa(con: sqlite3.Connection, componente_id: int, relativo: str, nombre: str) -> None:
    """El Excel anterior va a la papelera (se puede recuperar) si ninguna tabla lo usa."""
    if con.execute("SELECT 1 FROM tablas WHERE componente_id=? AND archivo=?", (componente_id, relativo)).fetchone():
        return
    from . import papelera as pap  # evita importación circular
    comp = bib.obtener_componente(con, componente_id)
    pap.enviar_archivo(con, bib.carpeta_componente(con, comp) / relativo,
                       f"{Path(relativo).name} (versión anterior de «{nombre}»)", componente_id)


# --------------------------------------------------------------------- edición
def cambiar_titulo(con: sqlite3.Connection, tabla_id: int, clave: str) -> Tabla:
    """Elige otra columna como título de las fichas (sin volver a importar el Excel)."""
    t = obtener(con, tabla_id)
    if clave not in t.claves:
        raise ErrorUsuario("Elige una de las columnas de la tabla.")
    filas = con.execute("SELECT id, valores FROM filas WHERE tabla_id=?", (t.id,)).fetchall()
    with transaccion(con):
        con.execute("UPDATE tablas SET columna_titulo=?, actualizado=? WHERE id=?", (clave, ahora(), t.id))
        for f in filas:
            valores = json.loads(f["valores"])
            titulo = (valores.get(clave) or "").strip() or "(sin título)"
            if t.columna_clave:   # la clave para emparejar filas al actualizar el Excel no cambia
                con.execute("UPDATE filas SET titulo=? WHERE id=?", (titulo, f["id"]))
            else:                 # sin clave, las filas se emparejan por el título
                con.execute("UPDATE filas SET titulo=?, clave_norm=? WHERE id=?",
                            (titulo, normalizar(valores.get(clave, "")), f["id"]))
    return obtener(con, t.id)


def renombrar(con: sqlite3.Connection, tabla_id: int, nombre: str) -> None:
    obtener(con, tabla_id)
    nombre = " ".join((nombre or "").split())
    if not nombre:
        raise ErrorUsuario("Escribe un nombre para la tabla.")
    con.execute("UPDATE tablas SET nombre=?, actualizado=? WHERE id=?", (nombre[:80], ahora(), tabla_id))


def eliminar_huerfanas(con: sqlite3.Connection, tabla_id: int) -> int:
    """Quita las filas que ya no están en el Excel. Sus imágenes van a la papelera como archivos."""
    from . import papelera as pap
    t = obtener(con, tabla_id)
    carpeta = bib.carpeta_componente(con, bib.obtener_componente(con, t.componente_id))
    filas = con.execute("SELECT id, titulo FROM filas WHERE tabla_id=? AND huerfana=1", (tabla_id,)).fetchall()
    for f in filas:
        for img in con.execute("SELECT archivo, titulo FROM imagenes_fila WHERE fila_id=?", (f["id"],)):
            pap.enviar_archivo(con, carpeta / img["archivo"], f"{img['titulo']} (de «{f['titulo']}»)",
                               t.componente_id)
    con.executemany("DELETE FROM filas WHERE id=?", [(f["id"],) for f in filas])
    return len(filas)

"""Papelera interna: lo eliminado se mueve a data/papelera/ y se puede restaurar o vaciar.

Tipos:
- materia / componente: su carpeta completa se mueve a la papelera.
- tabla: se oculta (su Excel y las imágenes de sus filas quedan en su sitio hasta vaciar).
- imagen_fila: el archivo se mueve a la papelera y se puede devolver a su ficha.
- archivo: un archivo suelto (p. ej. la versión anterior de un Excel); al restaurar vuelve a su carpeta.
"""
from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

from ..config import rutas
from ..db import ahora, transaccion
from ..errores import ErrorUsuario, NoEncontrado
from ..models import ElementoPapelera, ImagenFila
from . import almacenamiento as alm
from . import biblioteca as bib

log = logging.getLogger(__name__)

NOMBRES_TIPO = {"materia": "Materia", "componente": "Componente", "tabla": "Tabla",
                "imagen_fila": "Imagen de una ficha", "archivo": "Archivo", "pdf": "PDF",
                "imagen": "Imagen", "nota": "Nota", "caso": "Caso de acceso rápido"}


def listar(con: sqlite3.Connection) -> list[ElementoPapelera]:
    return [ElementoPapelera.desde_fila(f) for f in con.execute("SELECT * FROM papelera ORDER BY eliminado DESC, id DESC")]


def contar(con: sqlite3.Connection) -> int:
    return con.execute("SELECT COUNT(*) FROM papelera").fetchone()[0]


def _registrar(con: sqlite3.Connection, tipo: str, ref_id: int, nombre: str, ubicacion: str) -> int:
    cur = con.execute(
        "INSERT INTO papelera (tipo, ref_id, nombre, ubicacion, eliminado) VALUES (?,?,?,?,?)",
        (tipo, ref_id, nombre, ubicacion, ahora()),
    )
    return int(cur.lastrowid)


def _ubicacion_componente(con: sqlite3.Connection, componente_id: int, incluir: bool = True) -> str:
    c = bib.obtener_componente(con, componente_id)
    m = bib.obtener_materia(con, c.materia_id)
    partes = [m.nombre, *(a.nombre for a in bib.ancestros(con, c))]
    if incluir:
        partes.append(c.nombre)
    return " › ".join(partes)


# ------------------------------------------------------------------- enviar
def enviar_materia(con: sqlite3.Connection, materia_id: int) -> str:
    m = bib.obtener_materia(con, materia_id)
    carpeta = bib.carpeta_materia(m)
    with transaccion(con):
        pid = _registrar(con, "materia", m.id, m.nombre, "")
        destino = alm.a_papelera(carpeta, f"{pid}-{m.slug}")
        con.execute("UPDATE papelera SET ruta_original=?, ruta_papelera=? WHERE id=?",
                    (rutas.relativa(carpeta) if destino else None, destino, pid))
        con.execute("UPDATE materias SET papelera_id=? WHERE id=?", (pid, m.id))
        con.execute("UPDATE componentes SET papelera_id=? WHERE materia_id=? AND papelera_id IS NULL", (pid, m.id))
    log.info("Materia enviada a la papelera: %s", m.nombre)
    return m.nombre


def enviar_componente(con: sqlite3.Connection, componente_id: int) -> tuple[str, int, int | None]:
    """Envía el componente y todos sus subcomponentes. Devuelve (nombre, materia_id, padre_id)."""
    c = bib.obtener_componente(con, componente_id)
    ubicacion = _ubicacion_componente(con, c.id, incluir=False)
    carpeta = bib.carpeta_componente(con, c)
    ids = [c.id, *bib.descendientes(con, c.id)]
    with transaccion(con):
        pid = _registrar(con, "componente", c.id, c.nombre, ubicacion)
        destino = alm.a_papelera(carpeta, f"{pid}-{c.slug}")
        con.execute("UPDATE papelera SET ruta_original=?, ruta_papelera=? WHERE id=?",
                    (rutas.relativa(carpeta) if destino else None, destino, pid))
        con.executemany("UPDATE componentes SET papelera_id=? WHERE id=?", [(pid, i) for i in ids])
    log.info("Componente enviado a la papelera: %s (%s con subcomponentes)", c.nombre, len(ids))
    return c.nombre, c.materia_id, c.padre_id


def enviar_tabla(con: sqlite3.Connection, tabla_id: int) -> tuple[str, int]:
    f = con.execute("SELECT id, nombre, componente_id FROM tablas WHERE id=? AND papelera_id IS NULL", (tabla_id,)).fetchone()
    if f is None:
        raise NoEncontrado("La tabla")
    with transaccion(con):
        pid = _registrar(con, "tabla", f["id"], f["nombre"], _ubicacion_componente(con, f["componente_id"]))
        con.execute("UPDATE tablas SET papelera_id=? WHERE id=?", (pid, f["id"]))
    return f["nombre"], f["componente_id"]


def enviar_imagen_fila(con: sqlite3.Connection, img: ImagenFila, ruta: Path) -> None:
    fila = con.execute("SELECT f.titulo, t.componente_id, t.nombre FROM filas f JOIN tablas t ON t.id=f.tabla_id WHERE f.id=?",
                       (img.fila_id,)).fetchone()
    ubicacion = f"{_ubicacion_componente(con, fila['componente_id'])} › {fila['nombre']} › {fila['titulo']}"
    with transaccion(con):
        pid = _registrar(con, "imagen_fila", img.id, img.titulo, ubicacion)
        destino = alm.a_papelera(ruta, f"{pid}-{ruta.name}")
        con.execute("UPDATE papelera SET ruta_original=?, ruta_papelera=? WHERE id=?", (img.archivo, destino, pid))
        con.execute("UPDATE imagenes_fila SET papelera_id=? WHERE id=?", (pid, img.id))


def enviar_pdf(con: sqlite3.Connection, pdf_id: int) -> tuple[str, int]:
    from . import pdfs
    pdf = pdfs.obtener(con, pdf_id)
    ruta = pdfs.ruta(con, pdf)
    with transaccion(con):
        pid = _registrar(con, "pdf", pdf.id, pdf.titulo, _ubicacion_componente(con, pdf.componente_id))
        destino = alm.a_papelera(ruta, f"{pid}-{ruta.name}")
        con.execute("UPDATE papelera SET ruta_original=?, ruta_papelera=? WHERE id=?", (pdf.archivo, destino, pid))
        con.execute("UPDATE pdfs SET papelera_id=? WHERE id=?", (pid, pdf.id))
    return pdf.titulo, pdf.componente_id


def enviar_imagen(con: sqlite3.Connection, imagen_id: int) -> tuple[str, int]:
    from . import imagenes
    img = imagenes.obtener(con, imagen_id)
    ruta = imagenes.ruta(con, img)
    with transaccion(con):
        pid = _registrar(con, "imagen", img.id, img.titulo, _ubicacion_componente(con, img.componente_id))
        destino = alm.a_papelera(ruta, f"{pid}-{ruta.name}")
        con.execute("UPDATE papelera SET ruta_original=?, ruta_papelera=? WHERE id=?", (img.archivo, destino, pid))
        con.execute("UPDATE imagenes SET papelera_id=? WHERE id=?", (pid, img.id))
    return img.titulo, img.componente_id


def enviar_nota(con: sqlite3.Connection, nota_id: int) -> tuple[str, int]:
    from . import notas
    nota = notas.obtener(con, nota_id)
    with transaccion(con):
        pid = _registrar(con, "nota", nota.id, nota.titulo, _ubicacion_componente(con, nota.componente_id))
        con.execute("UPDATE notas SET papelera_id=? WHERE id=?", (pid, nota.id))
    return nota.titulo, nota.componente_id


def enviar_caso(con: sqlite3.Connection, caso_id: int) -> str:
    from . import casos
    caso = casos.obtener(con, caso_id)
    with transaccion(con):
        pid = _registrar(con, "caso", caso.id, caso.titulo, "Acceso rápido")
        con.execute("UPDATE casos SET papelera_id=? WHERE id=?", (pid, caso.id))
    return caso.titulo


def enviar_archivo(con: sqlite3.Connection, ruta: Path, nombre: str, componente_id: int) -> None:
    """Archivo suelto (ref_id = componente al que pertenecía)."""
    if not ruta.exists():
        return
    with transaccion(con):
        pid = _registrar(con, "archivo", componente_id, nombre, _ubicacion_componente(con, componente_id))
        destino = alm.a_papelera(ruta, f"{pid}-{ruta.name}")
        con.execute("UPDATE papelera SET ruta_original=?, ruta_papelera=? WHERE id=?", (rutas.relativa(ruta), destino, pid))


# ---------------------------------------------------------------- restaurar
def _fila(con: sqlite3.Connection, pid: int) -> sqlite3.Row:
    f = con.execute("SELECT * FROM papelera WHERE id=?", (pid,)).fetchone()
    if f is None:
        raise NoEncontrado("Ese elemento de la papelera")
    return f


def restaurar(con: sqlite3.Connection, pid: int) -> str:
    f = _fila(con, pid)
    acciones = {"materia": _restaurar_materia, "componente": _restaurar_componente, "tabla": _restaurar_tabla,
                "imagen_fila": _restaurar_imagen_fila, "archivo": _restaurar_archivo, "pdf": _restaurar_pdf,
                "imagen": _restaurar_imagen, "nota": _restaurar_nota, "caso": _restaurar_caso}
    if f["tipo"] not in acciones:
        raise ErrorUsuario("Este elemento no se puede restaurar.")
    return acciones[f["tipo"]](con, f)


def _volver(f: sqlite3.Row, destino: Path) -> None:
    if f["ruta_papelera"]:
        origen = rutas.absoluta(f["ruta_papelera"])
        if origen.exists():
            alm.mover_carpeta(origen, destino)
    destino.mkdir(parents=True, exist_ok=True)


def _componente_activo(con: sqlite3.Connection, componente_id: int) -> bool:
    try:
        bib.obtener_componente(con, componente_id)
        return True
    except NoEncontrado:
        return False


def _restaurar_materia(con: sqlite3.Connection, f: sqlite3.Row) -> str:
    m = con.execute("SELECT * FROM materias WHERE id=?", (f["ref_id"],)).fetchone()
    nombre = m["nombre"]
    if con.execute("SELECT 1 FROM materias WHERE nombre=? COLLATE NOCASE AND papelera_id IS NULL", (nombre,)).fetchone():
        nombre = f"{nombre} (restaurada)"
    slug = alm.slug_unico(alm.slugify(nombre), bib._slugs_materias(con))
    with transaccion(con):
        con.execute("UPDATE materias SET papelera_id=NULL, nombre=?, slug=?, actualizado=? WHERE id=?",
                    (nombre, slug, ahora(), m["id"]))
        con.execute("UPDATE componentes SET papelera_id=NULL WHERE papelera_id=?", (f["id"],))
        con.execute("DELETE FROM papelera WHERE id=?", (f["id"],))
        _volver(f, rutas.archivos / slug)
    return nombre


def _restaurar_componente(con: sqlite3.Connection, f: sqlite3.Row) -> str:
    c = con.execute("SELECT * FROM componentes WHERE id=?", (f["ref_id"],)).fetchone()
    if c is None:
        raise NoEncontrado("El componente")
    materia_ok = con.execute("SELECT 1 FROM materias WHERE id=? AND papelera_id IS NULL", (c["materia_id"],)).fetchone()
    padre_ok = c["padre_id"] is None or con.execute(
        "SELECT 1 FROM componentes WHERE id=? AND papelera_id IS NULL", (c["padre_id"],)).fetchone()
    if not materia_ok or not padre_ok:
        raise ErrorUsuario("Primero restaura la materia o el componente que lo contenía.")
    nombre = c["nombre"]
    if bib._nombre_repetido(con, c["materia_id"], c["padre_id"], nombre):
        nombre = f"{nombre} (restaurado)"
    slug = alm.slug_unico(alm.slugify(nombre), bib._slugs_hermanos(con, c["materia_id"], c["padre_id"]))
    with transaccion(con):
        con.execute("UPDATE componentes SET papelera_id=NULL WHERE papelera_id=?", (f["id"],))
        con.execute("UPDATE componentes SET nombre=?, slug=?, actualizado=? WHERE id=?", (nombre, slug, ahora(), c["id"]))
        con.execute("DELETE FROM papelera WHERE id=?", (f["id"],))
        _volver(f, bib.carpeta_componente(con, bib.obtener_componente(con, c["id"])))
    return nombre


def _restaurar_tabla(con: sqlite3.Connection, f: sqlite3.Row) -> str:
    t = con.execute("SELECT componente_id FROM tablas WHERE id=?", (f["ref_id"],)).fetchone()
    if t is None:
        raise NoEncontrado("La tabla")
    if not _componente_activo(con, t["componente_id"]):
        raise ErrorUsuario("Primero restaura el componente que contenía esta tabla.")
    with transaccion(con):
        con.execute("UPDATE tablas SET papelera_id=NULL WHERE id=?", (f["ref_id"],))
        con.execute("DELETE FROM papelera WHERE id=?", (f["id"],))
    return f["nombre"]


def _restaurar_imagen_fila(con: sqlite3.Connection, f: sqlite3.Row) -> str:
    from . import imagenes_fila as imf
    img = con.execute("SELECT * FROM imagenes_fila WHERE id=?", (f["ref_id"],)).fetchone()
    if img is None:
        raise ErrorUsuario("La ficha a la que pertenecía esta imagen ya no existe.")
    try:
        carpeta, _ = imf.carpeta_de_fila(con, img["fila_id"])
        from . import tablas as tab
        tab.obtener_fila(con, img["fila_id"])
    except NoEncontrado as e:
        raise ErrorUsuario("Primero restaura la tabla o el componente de esta imagen.") from e
    destino = alm.ruta_libre(carpeta / "imagenes-filas", Path(img["archivo"]).name)
    destino.parent.mkdir(parents=True, exist_ok=True)
    with transaccion(con):
        if f["ruta_papelera"] and rutas.absoluta(f["ruta_papelera"]).exists():
            rutas.absoluta(f["ruta_papelera"]).rename(destino)
        con.execute("UPDATE imagenes_fila SET papelera_id=NULL, archivo=? WHERE id=?",
                    (f"imagenes-filas/{destino.name}", img["id"]))
        con.execute("DELETE FROM papelera WHERE id=?", (f["id"],))
    return f["nombre"]


def _restaurar_pdf(con: sqlite3.Connection, f: sqlite3.Row) -> str:
    d = con.execute("SELECT componente_id, archivo FROM pdfs WHERE id=?", (f["ref_id"],)).fetchone()
    if d is None:
        raise NoEncontrado("El PDF")
    if not _componente_activo(con, d["componente_id"]):
        raise ErrorUsuario("Primero restaura el componente que contenía este PDF.")
    carpeta = bib.carpeta_componente(con, bib.obtener_componente(con, d["componente_id"])) / "pdf"
    carpeta.mkdir(parents=True, exist_ok=True)
    destino = alm.ruta_libre(carpeta, Path(d["archivo"]).name)
    with transaccion(con):
        if f["ruta_papelera"] and rutas.absoluta(f["ruta_papelera"]).exists():
            rutas.absoluta(f["ruta_papelera"]).rename(destino)
        con.execute("UPDATE pdfs SET papelera_id=NULL, archivo=? WHERE id=?", (f"pdf/{destino.name}", f["ref_id"]))
        con.execute("DELETE FROM papelera WHERE id=?", (f["id"],))
    return f["nombre"]


def _restaurar_imagen(con: sqlite3.Connection, f: sqlite3.Row) -> str:
    i = con.execute("SELECT componente_id, archivo FROM imagenes WHERE id=?", (f["ref_id"],)).fetchone()
    if i is None:
        raise NoEncontrado("La imagen")
    if not _componente_activo(con, i["componente_id"]):
        raise ErrorUsuario("Primero restaura el componente que contenía esta imagen.")
    carpeta = bib.carpeta_componente(con, bib.obtener_componente(con, i["componente_id"])) / "imagenes"
    carpeta.mkdir(parents=True, exist_ok=True)
    destino = alm.ruta_libre(carpeta, Path(i["archivo"]).name)
    with transaccion(con):
        if f["ruta_papelera"] and rutas.absoluta(f["ruta_papelera"]).exists():
            rutas.absoluta(f["ruta_papelera"]).rename(destino)
        con.execute("UPDATE imagenes SET papelera_id=NULL, archivo=? WHERE id=?", (f"imagenes/{destino.name}", f["ref_id"]))
        con.execute("DELETE FROM papelera WHERE id=?", (f["id"],))
    return f["nombre"]


def _restaurar_nota(con: sqlite3.Connection, f: sqlite3.Row) -> str:
    n = con.execute("SELECT componente_id FROM notas WHERE id=?", (f["ref_id"],)).fetchone()
    if n is None:
        raise NoEncontrado("La nota")
    if not _componente_activo(con, n["componente_id"]):
        raise ErrorUsuario("Primero restaura el componente que contenía esta nota.")
    with transaccion(con):
        con.execute("UPDATE notas SET papelera_id=NULL WHERE id=?", (f["ref_id"],))
        con.execute("DELETE FROM papelera WHERE id=?", (f["id"],))
    return f["nombre"]


def _restaurar_caso(con: sqlite3.Connection, f: sqlite3.Row) -> str:
    with transaccion(con):
        con.execute("UPDATE casos SET papelera_id=NULL WHERE id=?", (f["ref_id"],))
        con.execute("DELETE FROM papelera WHERE id=?", (f["id"],))
    return f["nombre"]


def _restaurar_archivo(con: sqlite3.Connection, f: sqlite3.Row) -> str:
    if not f["ruta_papelera"] or not rutas.absoluta(f["ruta_papelera"]).exists():
        raise ErrorUsuario("El archivo ya no está en la papelera.")
    original = rutas.absoluta(f["ruta_original"])
    original.parent.mkdir(parents=True, exist_ok=True)
    destino = alm.ruta_libre(original.parent, original.name)
    rutas.absoluta(f["ruta_papelera"]).rename(destino)
    con.execute("DELETE FROM papelera WHERE id=?", (f["id"],))
    return f["nombre"]


# ---------------------------------------------------------- borrar del todo
def _componentes_afectados(con: sqlite3.Connection, f: sqlite3.Row) -> list[int]:
    if f["tipo"] == "materia":
        return [r[0] for r in con.execute("SELECT id FROM componentes WHERE materia_id=?", (f["ref_id"],))]
    if f["tipo"] == "componente":
        return [r[0] for r in con.execute(
            """WITH RECURSIVE s(id) AS (SELECT id FROM componentes WHERE id = ?
               UNION ALL SELECT c.id FROM componentes c JOIN s ON c.padre_id = s.id) SELECT id FROM s""", (f["ref_id"],))]
    return []


def _dependientes(con: sqlite3.Connection, f: sqlite3.Row) -> list[sqlite3.Row]:
    """Elementos de la papelera que quedarían huérfanos al borrar `f` (se borran con él)."""
    comps = _componentes_afectados(con, f)
    tablas: list[int] = []
    if comps:
        marcas = ",".join("?" * len(comps))
        tablas = [r[0] for r in con.execute(f"SELECT id FROM tablas WHERE componente_id IN ({marcas})", comps)]
    elif f["tipo"] == "tabla":
        tablas = [f["ref_id"]]
    if not comps and not tablas:
        return []
    condiciones, params = [], []
    if comps:
        marcas = ",".join("?" * len(comps))
        condiciones.append(f"(tipo IN ('componente','archivo') AND ref_id IN ({marcas}))")
        condiciones.append(f"(tipo='pdf' AND ref_id IN (SELECT id FROM pdfs WHERE componente_id IN ({marcas})))")
        condiciones.append(f"(tipo='imagen' AND ref_id IN (SELECT id FROM imagenes WHERE componente_id IN ({marcas})))")
        condiciones.append(f"(tipo='nota' AND ref_id IN (SELECT id FROM notas WHERE componente_id IN ({marcas})))")
        params += comps * 4
    if tablas:
        marcas = ",".join("?" * len(tablas))
        condiciones.append(f"(tipo='tabla' AND ref_id IN ({marcas}))")
        condiciones.append(f"""(tipo='imagen_fila' AND ref_id IN (SELECT i.id FROM imagenes_fila i JOIN filas fi
                               ON fi.id = i.fila_id WHERE fi.tabla_id IN ({marcas})))""")
        params += tablas * 2
    return con.execute(f"SELECT * FROM papelera WHERE id != ? AND ({' OR '.join(condiciones)})",
                       [f["id"], *params]).fetchall()


def _archivos_de_tablas(con: sqlite3.Connection, tablas: list[int]) -> list[Path]:
    """Excel e imágenes de filas (que están en la carpeta del componente) de tablas a borrar."""
    rutas_: list[Path] = []
    for tid in tablas:
        t = con.execute("SELECT componente_id, archivo FROM tablas WHERE id=?", (tid,)).fetchone()
        try:
            carpeta = bib.carpeta_componente(con, bib.obtener_componente(con, t["componente_id"]))
        except NoEncontrado:
            continue  # el componente está en la papelera: sus archivos se borran con su carpeta
        otros = con.execute("SELECT 1 FROM tablas WHERE archivo=? AND componente_id=? AND id != ?",
                            (t["archivo"], t["componente_id"], tid)).fetchone()
        if not otros:
            rutas_.append(carpeta / t["archivo"])
        rutas_ += [carpeta / r[0] for r in con.execute(
            """SELECT i.archivo FROM imagenes_fila i JOIN filas f ON f.id = i.fila_id
               WHERE f.tabla_id = ? AND i.papelera_id IS NULL""", (tid,))]
    return rutas_


def eliminar_definitivo(con: sqlite3.Connection, pid: int) -> str:
    f = _fila(con, pid)
    dependientes = _dependientes(con, f)
    archivos = _archivos_de_tablas(con, [f["ref_id"]]) if f["tipo"] == "tabla" else []
    with transaccion(con):
        if f["tipo"] == "materia":
            con.execute("DELETE FROM materias WHERE id=?", (f["ref_id"],))
        elif f["tipo"] == "componente":
            con.execute("DELETE FROM componentes WHERE id=?", (f["ref_id"],))
        elif f["tipo"] == "tabla":
            con.execute("DELETE FROM tablas WHERE id=?", (f["ref_id"],))
        elif f["tipo"] == "imagen_fila":
            con.execute("DELETE FROM imagenes_fila WHERE id=?", (f["ref_id"],))
        elif f["tipo"] == "pdf":
            con.execute("DELETE FROM pdfs WHERE id=?", (f["ref_id"],))
        elif f["tipo"] == "imagen":
            con.execute("DELETE FROM imagenes WHERE id=?", (f["ref_id"],))
        elif f["tipo"] == "nota":
            con.execute("DELETE FROM notas WHERE id=?", (f["ref_id"],))
        elif f["tipo"] == "caso":
            con.execute("DELETE FROM casos WHERE id=?", (f["ref_id"],))
        con.execute("DELETE FROM papelera WHERE id=?", (pid,))
        con.executemany("DELETE FROM papelera WHERE id=?", [(d["id"],) for d in dependientes])
    alm.borrar_definitivo(f["ruta_papelera"])
    for d in dependientes:
        alm.borrar_definitivo(d["ruta_papelera"])
    for ruta in archivos:
        ruta.unlink(missing_ok=True)
    from . import etiquetas
    etiquetas.limpiar_huerfanas(con)
    log.info("Eliminado definitivamente: %s (%s)", f["nombre"], f["tipo"])
    return f["nombre"]


def vaciar(con: sqlite3.Connection) -> int:
    n = 0
    while True:  # borrar uno puede llevarse otros (dependientes)
        fila = con.execute("SELECT id FROM papelera ORDER BY id DESC LIMIT 1").fetchone()
        if fila is None:
            return n
        eliminar_definitivo(con, fila[0])
        n += 1

"""Imágenes sueltas de un componente: nombre descriptivo, descripción, etiquetas y OCR opcional.

Se guardan en <componente>/imagenes/<nombre descriptivo>.<ext>.
"""
from __future__ import annotations

import logging
import shutil
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from ..db import ahora, transaccion
from ..errores import ErrorUsuario, NoEncontrado
from . import almacenamiento as alm
from . import biblioteca as bib
from . import etiquetas as etq
from . import ocr
from .imagenes_fila import validar_imagen

log = logging.getLogger(__name__)

LARGO_TITULO = 120
LARGO_DESCRIPCION = 2000


@dataclass
class Imagen:
    id: int
    componente_id: int
    titulo: str
    descripcion: str
    archivo: str
    nombre_original: str
    hash: str
    ancho: int | None
    alto: int | None
    bytes: int | None
    texto_ocr: str
    ocr_estado: str
    ocr_error: str | None
    creado: str
    actualizado: str
    etiquetas: list[str] = field(default_factory=list)

    @classmethod
    def desde_fila(cls, f: sqlite3.Row) -> Imagen:
        return cls(**{k: f[k] for k in ("id", "componente_id", "titulo", "descripcion", "archivo", "nombre_original",
                                         "hash", "ancho", "alto", "bytes", "texto_ocr", "ocr_estado", "ocr_error",
                                         "creado", "actualizado")})


def listar(con: sqlite3.Connection, componente_id: int, etiqueta: str = "") -> list[Imagen]:
    sql = "SELECT i.* FROM imagenes i WHERE i.componente_id=? AND i.papelera_id IS NULL"
    params: list = [componente_id]
    if etiqueta:
        from .texto import normalizar
        sql += """ AND i.id IN (SELECT x.ref_id FROM etiquetas_elemento x JOIN etiquetas e ON e.id = x.etiqueta_id
                                WHERE x.tipo='imagen' AND e.clave=?)"""
        params.append(normalizar(etiqueta))
    imagenes = [Imagen.desde_fila(f) for f in con.execute(sql + " ORDER BY i.orden, i.id", params)]
    por_id = etq.de_varios(con, "imagen", [i.id for i in imagenes])
    for img in imagenes:
        img.etiquetas = por_id.get(img.id, [])
    return imagenes


def etiquetas_del_componente(con: sqlite3.Connection, componente_id: int) -> list[tuple[str, int]]:
    """Etiquetas usadas por las imágenes del componente, con cuántas imágenes tiene cada una."""
    return [(r[0], r[1]) for r in con.execute(
        """SELECT e.nombre, COUNT(*) FROM etiquetas e JOIN etiquetas_elemento x ON x.etiqueta_id = e.id
           JOIN imagenes i ON i.id = x.ref_id AND x.tipo = 'imagen'
           WHERE i.componente_id = ? AND i.papelera_id IS NULL GROUP BY e.id ORDER BY e.clave""", (componente_id,))]


def obtener(con: sqlite3.Connection, imagen_id: int) -> Imagen:
    f = con.execute(
        """SELECT i.* FROM imagenes i JOIN componentes c ON c.id = i.componente_id
           WHERE i.id=? AND i.papelera_id IS NULL AND c.papelera_id IS NULL""", (imagen_id,)).fetchone()
    if f is None:
        raise NoEncontrado("La imagen")
    img = Imagen.desde_fila(f)
    img.etiquetas = etq.de(con, "imagen", img.id)
    return img


def ruta(con: sqlite3.Connection, img: Imagen) -> Path:
    comp = bib.obtener_componente(con, img.componente_id)
    return bib.carpeta_componente(con, comp) / Path(*img.archivo.split("/"))


def _limpiar(titulo: str, descripcion: str) -> tuple[str, str]:
    titulo = " ".join((titulo or "").split())[:LARGO_TITULO]
    if not titulo:
        raise ErrorUsuario("Escribe un nombre descriptivo para cada imagen.")
    return titulo, (descripcion or "").strip()[:LARGO_DESCRIPCION]


def agregar(con: sqlite3.Connection, componente_id: int, nombre_original: str, temporal: Path, titulo: str,
            descripcion: str = "", etiquetas: str = "", extraer_texto: bool = False) -> tuple[Imagen, str | None]:
    comp = bib.obtener_componente(con, componente_id)
    titulo, descripcion = _limpiar(titulo, descripcion)
    nombre = alm.sanear_nombre_archivo(nombre_original or "imagen")
    ext, ancho, alto = validar_imagen(temporal, nombre)
    hash_ = alm.hash_archivo(temporal)
    repetida = con.execute("SELECT titulo FROM imagenes WHERE hash=? AND papelera_id IS NULL", (hash_,)).fetchone()
    aviso = f"«{titulo}» es la misma imagen que «{repetida['titulo']}», que ya estaba en la biblioteca." if repetida else None

    carpeta = bib.carpeta_componente(con, comp) / "imagenes"
    carpeta.mkdir(parents=True, exist_ok=True)
    destino = alm.ruta_libre(carpeta, f"{alm.nombre_legible(titulo, 100)}{ext}")
    shutil.copy2(temporal, destino)
    try:
        with transaccion(con):
            t = ahora()
            orden = con.execute("SELECT COALESCE(MAX(orden),0)+1 FROM imagenes WHERE componente_id=?",
                                (componente_id,)).fetchone()[0]
            iid = int(con.execute(
                """INSERT INTO imagenes (componente_id, titulo, descripcion, archivo, nombre_original, hash, ancho, alto,
                   bytes, ocr_estado, orden, creado, actualizado) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (componente_id, titulo, descripcion, f"imagenes/{destino.name}", nombre, hash_, ancho, alto,
                 destino.stat().st_size, "pendiente" if extraer_texto else "no", orden, t, t)).lastrowid)
            etq.asignar(con, "imagen", iid, etiquetas)
    except BaseException:
        destino.unlink(missing_ok=True)
        raise
    if extraer_texto:
        ocr.avisar_trabajo()
    log.info("Imagen agregada: %s", destino.name)
    return obtener(con, iid), aviso


def editar(con: sqlite3.Connection, imagen_id: int, titulo: str, descripcion: str, etiquetas: str) -> Imagen:
    """Cambia nombre, descripción y etiquetas; el archivo se renombra para seguir legible."""
    img = obtener(con, imagen_id)
    titulo, descripcion = _limpiar(titulo, descripcion)
    archivo = img.archivo
    actual = ruta(con, img)
    if titulo != img.titulo and actual.exists():
        nuevo = alm.ruta_libre(actual.parent, f"{alm.nombre_legible(titulo, 100)}{actual.suffix}")
        actual.rename(nuevo)
        archivo = f"imagenes/{nuevo.name}"
    with transaccion(con):
        con.execute("UPDATE imagenes SET titulo=?, descripcion=?, archivo=?, actualizado=? WHERE id=?",
                    (titulo, descripcion, archivo, ahora(), imagen_id))
        etq.asignar(con, "imagen", imagen_id, etiquetas)
    return obtener(con, imagen_id)


def pedir_ocr(con: sqlite3.Connection, imagen_id: int) -> None:
    obtener(con, imagen_id)
    con.execute("UPDATE imagenes SET ocr_estado='pendiente', ocr_error=NULL WHERE id=?", (imagen_id,))
    ocr.avisar_trabajo()


def ocr_pendientes(con: sqlite3.Connection) -> int:
    return con.execute(
        """SELECT COUNT(*) FROM imagenes i JOIN componentes c ON c.id = i.componente_id
           WHERE i.ocr_estado='pendiente' AND i.papelera_id IS NULL AND c.papelera_id IS NULL""").fetchone()[0]


def reordenar(con: sqlite3.Connection, componente_id: int, ids: list[int]) -> None:
    with transaccion(con):
        for orden, iid in enumerate(ids, 1):
            con.execute("UPDATE imagenes SET orden=? WHERE id=? AND componente_id=?", (orden, iid, componente_id))


def procesar_una_imagen(con: sqlite3.Connection) -> bool:
    """Fuente de trabajos para el OCR en segundo plano: lee UNA imagen pendiente."""
    f = con.execute(
        """SELECT i.id FROM imagenes i JOIN componentes c ON c.id = i.componente_id
           WHERE i.ocr_estado='pendiente' AND i.papelera_id IS NULL AND c.papelera_id IS NULL
           ORDER BY i.id LIMIT 1""").fetchone()
    if f is None:
        return False
    try:
        img = obtener(con, f["id"])
        texto = ocr.reconocer(ruta(con, img)).strip()
        con.execute("UPDATE imagenes SET texto_ocr=?, ocr_estado='listo', ocr_error=NULL WHERE id=?", (texto, img.id))
    except Exception as e:
        log.exception("OCR falló en la imagen %s", f["id"])
        con.execute("UPDATE imagenes SET ocr_estado='error', ocr_error=? WHERE id=?", (str(e)[:300], f["id"]))
    return True


ocr.registrar_fuente(procesar_una_imagen)

"""Imágenes asociadas a una fila concreta de una tabla.

Se guardan en <componente>/imagenes-filas/ con un nombre legible: "<título de la fila> - <nombre original>".
"""
from __future__ import annotations

import logging
import shutil
import sqlite3
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from ..db import ahora, transaccion
from ..errores import ErrorUsuario, NoEncontrado
from ..models import ImagenFila
from . import almacenamiento as alm
from . import biblioteca as bib
from . import tablas as tab

log = logging.getLogger(__name__)

FORMATOS = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp", "GIF": ".gif"}
MAX_BYTES = 40 * 1024 * 1024
LARGO_PIE = 300
LARGO_TITULO = 120


def validar_imagen(ruta: Path, nombre: str) -> tuple[str, int, int]:
    """Comprueba que sea una imagen compatible. Devuelve (extensión, ancho, alto)."""
    if ruta.stat().st_size > MAX_BYTES:
        raise ErrorUsuario(f"«{nombre}» pesa más de {MAX_BYTES // (1024 * 1024)} MB.")
    try:
        with Image.open(ruta) as img:
            formato, (ancho, alto) = img.format, img.size
            img.verify()
    except (UnidentifiedImageError, OSError) as e:
        if nombre.lower().endswith((".heic", ".heif")):
            raise ErrorUsuario(f"«{nombre}» es HEIC (iPhone). Expórtala como JPG antes de subirla.") from e
        raise ErrorUsuario(f"«{nombre}» no es una imagen válida.") from e
    if formato not in FORMATOS:
        raise ErrorUsuario(f"«{nombre}» tiene un formato no compatible. Usa JPG, PNG, WEBP o GIF.")
    return FORMATOS[formato], ancho, alto


def carpeta_de_fila(con: sqlite3.Connection, fila_id: int) -> tuple[Path, int]:
    """(carpeta del componente, componente_id) de la fila."""
    comp_id = con.execute("SELECT t.componente_id FROM filas f JOIN tablas t ON t.id = f.tabla_id WHERE f.id=?",
                          (fila_id,)).fetchone()
    if comp_id is None:
        raise NoEncontrado("La fila")
    comp = bib.obtener_componente(con, comp_id[0])
    return bib.carpeta_componente(con, comp), comp.id


def listar(con: sqlite3.Connection, fila_id: int) -> list[ImagenFila]:
    return [ImagenFila.desde_fila(f) for f in con.execute(
        "SELECT * FROM imagenes_fila WHERE fila_id=? AND papelera_id IS NULL ORDER BY orden, id", (fila_id,))]


def obtener(con: sqlite3.Connection, imagen_id: int) -> ImagenFila:
    f = con.execute("SELECT * FROM imagenes_fila WHERE id=? AND papelera_id IS NULL", (imagen_id,)).fetchone()
    if f is None:
        raise NoEncontrado("La imagen")
    return ImagenFila.desde_fila(f)


def ruta(con: sqlite3.Connection, img: ImagenFila) -> Path:
    carpeta, _ = carpeta_de_fila(con, img.fila_id)
    return carpeta / Path(*img.archivo.split("/"))


def titulo_sugerido(nombre_archivo: str) -> str:
    """"rx_femur-derecho.jpg" -> "rx femur derecho" (punto de partida editable)."""
    return " ".join(Path(nombre_archivo).stem.replace("_", " ").replace("-", " ").split())[:LARGO_TITULO]


def limpiar_titulo(titulo: str) -> str:
    titulo = " ".join((titulo or "").split())
    if not titulo:
        raise ErrorUsuario("Escribe un nombre descriptivo para cada imagen.")
    return titulo[:LARGO_TITULO]


def agregar(con: sqlite3.Connection, fila_id: int, nombre_original: str, temporal: Path, titulo: str,
            pie: str = "") -> tuple[ImagenFila | None, str | None]:
    """Adjunta una imagen a la fila con su nombre descriptivo. Devuelve (imagen, aviso).
    Si ya estaba en esta fila no la repite."""
    fila = tab.obtener_fila(con, fila_id)
    titulo = limpiar_titulo(titulo)
    nombre = alm.sanear_nombre_archivo(nombre_original or "imagen")
    ext, ancho, alto = validar_imagen(temporal, nombre)
    hash_ = alm.hash_archivo(temporal)
    repetida = con.execute(
        """SELECT i.fila_id, f.titulo FROM imagenes_fila i JOIN filas f ON f.id = i.fila_id
           WHERE i.hash = ? AND i.papelera_id IS NULL""", (hash_,)).fetchall()
    if any(r["fila_id"] == fila_id for r in repetida):
        return None, f"«{titulo}» ya estaba adjunta a esta ficha."
    aviso = f"«{titulo}» también está adjunta a «{repetida[0]['titulo']}»." if repetida else None

    carpeta, _ = carpeta_de_fila(con, fila_id)
    destino_dir = carpeta / "imagenes-filas"
    destino_dir.mkdir(parents=True, exist_ok=True)
    # Nombre en disco legible: "<título de la ficha> - <nombre descriptivo>.jpg"
    destino = alm.ruta_libre(destino_dir, f"{alm.nombre_legible(fila.titulo)} - {alm.nombre_legible(titulo, 80)}{ext}")
    shutil.copy2(temporal, destino)
    orden = con.execute("SELECT COALESCE(MAX(orden),0)+1 FROM imagenes_fila WHERE fila_id=?", (fila_id,)).fetchone()[0]
    try:
        cur = con.execute(
            """INSERT INTO imagenes_fila (fila_id, archivo, titulo, nombre_original, pie, orden, hash, ancho, alto, bytes, creado)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (fila_id, f"imagenes-filas/{destino.name}", titulo, nombre, " ".join((pie or "").split())[:LARGO_PIE],
             orden, hash_, ancho, alto, destino.stat().st_size, ahora()))
    except BaseException:
        destino.unlink(missing_ok=True)
        raise
    log.info("Imagen adjunta a la fila %s: %s", fila_id, destino.name)
    return obtener(con, int(cur.lastrowid)), aviso


def editar(con: sqlite3.Connection, imagen_id: int, titulo: str, pie: str) -> ImagenFila:
    """Cambia el nombre descriptivo y el pie de foto (el archivo en disco se renombra para seguir legible)."""
    img = obtener(con, imagen_id)
    titulo = limpiar_titulo(titulo)
    archivo = img.archivo
    if titulo != img.titulo:
        actual = ruta(con, img)
        fila = tab.obtener_fila(con, img.fila_id)
        nuevo = alm.ruta_libre(actual.parent, f"{alm.nombre_legible(fila.titulo)} - {alm.nombre_legible(titulo, 80)}{actual.suffix}")
        if actual.exists():
            actual.rename(nuevo)
        archivo = f"imagenes-filas/{nuevo.name}"
    con.execute("UPDATE imagenes_fila SET titulo=?, pie=?, archivo=? WHERE id=?",
                (titulo, " ".join((pie or "").split())[:LARGO_PIE], archivo, imagen_id))
    return obtener(con, imagen_id)


def reordenar(con: sqlite3.Connection, fila_id: int, ids: list[int]) -> None:
    with transaccion(con):
        for orden, iid in enumerate(ids, 1):
            con.execute("UPDATE imagenes_fila SET orden=? WHERE id=? AND fila_id=?", (orden, iid, fila_id))


def enviar_a_papelera(con: sqlite3.Connection, imagen_id: int) -> ImagenFila:
    from . import papelera as pap
    img = obtener(con, imagen_id)
    pap.enviar_imagen_fila(con, img, ruta(con, img))
    return img

"""PDF: carga con nombre descriptivo, texto por página, OCR de páginas escaneadas y miniatura.

Se guardan en <componente>/pdf/<nombre descriptivo>.pdf. El texto de cada página se
guarda aparte para que la búsqueda pueda abrir el PDF exactamente en esa página.
"""
from __future__ import annotations

import logging
import shutil
import sqlite3
from dataclasses import dataclass
from pathlib import Path

import pymupdf

from ..config import rutas
from ..db import ahora, transaccion
from ..errores import ErrorUsuario, NoEncontrado
from . import almacenamiento as alm
from . import biblioteca as bib
from . import ocr
from .texto import normalizar

log = logging.getLogger(__name__)

MAX_BYTES = 300 * 1024 * 1024
MIN_CARACTERES = 25   # menos que esto en una página = probablemente escaneada
LARGO_TITULO = 120


@dataclass
class Pdf:
    id: int
    componente_id: int
    titulo: str
    archivo: str
    nombre_original: str
    hash: str
    paginas: int
    bytes: int
    creado: str
    actualizado: str
    ocr_pendientes: int = 0
    ocr_hechas: int = 0
    ocr_errores: int = 0

    @property
    def ocr_total(self) -> int:
        return self.ocr_pendientes + self.ocr_hechas + self.ocr_errores

    @property
    def ocr_progreso(self) -> int:
        return round(100 * (self.ocr_total - self.ocr_pendientes) / self.ocr_total) if self.ocr_total else 100

    @classmethod
    def desde_fila(cls, f: sqlite3.Row) -> Pdf:
        claves = f.keys()
        return cls(**{k: f[k] for k in ("id", "componente_id", "titulo", "archivo", "nombre_original", "hash",
                                         "paginas", "bytes", "creado", "actualizado")},
                   **{k: f[k] or 0 for k in ("ocr_pendientes", "ocr_hechas", "ocr_errores") if k in claves})


_CONTEOS = """
    (SELECT COUNT(*) FROM pdf_paginas p WHERE p.pdf_id = d.id AND p.ocr_pendiente = 1) AS ocr_pendientes,
    (SELECT COUNT(*) FROM pdf_paginas p WHERE p.pdf_id = d.id AND p.origen = 'ocr') AS ocr_hechas,
    (SELECT COUNT(*) FROM pdf_paginas p WHERE p.pdf_id = d.id AND p.ocr_error IS NOT NULL AND p.ocr_pendiente = 0) AS ocr_errores
"""


def listar(con: sqlite3.Connection, componente_id: int) -> list[Pdf]:
    return [Pdf.desde_fila(f) for f in con.execute(
        f"SELECT d.*, {_CONTEOS} FROM pdfs d WHERE componente_id=? AND papelera_id IS NULL ORDER BY orden, id",
        (componente_id,))]


def obtener(con: sqlite3.Connection, pdf_id: int) -> Pdf:
    f = con.execute(
        f"""SELECT d.*, {_CONTEOS} FROM pdfs d JOIN componentes c ON c.id = d.componente_id
            WHERE d.id = ? AND d.papelera_id IS NULL AND c.papelera_id IS NULL""", (pdf_id,)).fetchone()
    if f is None:
        raise NoEncontrado("El PDF")
    return Pdf.desde_fila(f)


def ruta(con: sqlite3.Connection, pdf: Pdf) -> Path:
    comp = bib.obtener_componente(con, pdf.componente_id)
    return bib.carpeta_componente(con, comp) / Path(*pdf.archivo.split("/"))


def pagina(con: sqlite3.Connection, pdf_id: int, numero: int) -> sqlite3.Row | None:
    return con.execute("SELECT * FROM pdf_paginas WHERE pdf_id=? AND numero=?", (pdf_id, numero)).fetchone()


def ocr_pendiente_total(con: sqlite3.Connection) -> int:
    return con.execute(
        """SELECT COUNT(*) FROM pdf_paginas p JOIN pdfs d ON d.id = p.pdf_id JOIN componentes c ON c.id = d.componente_id
           WHERE p.ocr_pendiente = 1 AND d.papelera_id IS NULL AND c.papelera_id IS NULL""").fetchone()[0]


# --------------------------------------------------------------------- carga
def titulo_sugerido(nombre_archivo: str) -> str:
    return " ".join(Path(nombre_archivo).stem.replace("_", " ").replace("-", " ").split())[:LARGO_TITULO]


def _limpiar_titulo(titulo: str) -> str:
    titulo = " ".join((titulo or "").split())
    if not titulo:
        raise ErrorUsuario("Escribe un nombre descriptivo para cada PDF.")
    return titulo[:LARGO_TITULO]


def _abrir(ruta_pdf: Path, nombre: str) -> pymupdf.Document:
    try:
        doc = pymupdf.open(ruta_pdf, filetype="pdf")
    except Exception as e:
        raise ErrorUsuario(f"«{nombre}» no es un PDF válido o está dañado.") from e
    if doc.needs_pass:
        doc.close()
        raise ErrorUsuario(f"«{nombre}» está protegido con contraseña. Quítale la contraseña y vuelve a subirlo.")
    if doc.page_count == 0:
        doc.close()
        raise ErrorUsuario(f"«{nombre}» no tiene páginas.")
    return doc


def agregar(con: sqlite3.Connection, componente_id: int, nombre_original: str, temporal: Path,
            titulo: str) -> tuple[Pdf, str | None]:
    """Guarda el PDF, extrae su texto por página y deja en cola el OCR de las escaneadas."""
    comp = bib.obtener_componente(con, componente_id)
    titulo = _limpiar_titulo(titulo)
    nombre = alm.sanear_nombre_archivo(nombre_original or "documento.pdf")
    if temporal.stat().st_size > MAX_BYTES:
        raise ErrorUsuario(f"«{nombre}» supera el tamaño máximo ({MAX_BYTES // (1024 * 1024)} MB).")
    doc = _abrir(temporal, nombre)
    try:
        paginas = []
        for i, pag in enumerate(doc, start=1):
            texto = pag.get_text("text", sort=True).strip()
            escaneada = len(texto.replace(" ", "").replace("\n", "")) < MIN_CARACTERES
            paginas.append((i, texto, escaneada))
        total = doc.page_count
    finally:
        doc.close()
    hash_ = alm.hash_archivo(temporal)
    repetido = con.execute(
        """SELECT d.titulo FROM pdfs d WHERE d.hash = ? AND d.papelera_id IS NULL""", (hash_,)).fetchone()
    aviso = f"«{titulo}» es el mismo archivo que «{repetido['titulo']}», que ya estaba en la biblioteca." if repetido else None

    carpeta = bib.carpeta_componente(con, comp) / "pdf"
    carpeta.mkdir(parents=True, exist_ok=True)
    destino = alm.ruta_libre(carpeta, f"{alm.nombre_legible(titulo, 100)}.pdf")
    shutil.copy2(temporal, destino)
    try:
        with transaccion(con):
            orden = con.execute("SELECT COALESCE(MAX(orden),0)+1 FROM pdfs WHERE componente_id=?", (componente_id,)).fetchone()[0]
            t = ahora()
            cur = con.execute(
                """INSERT INTO pdfs (componente_id, titulo, archivo, nombre_original, hash, paginas, bytes, orden, creado, actualizado)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (componente_id, titulo, f"pdf/{destino.name}", nombre, hash_, total, destino.stat().st_size, orden, t, t))
            pdf_id = int(cur.lastrowid)
            con.executemany(
                "INSERT INTO pdf_paginas (pdf_id, numero, texto, texto_norm, origen, ocr_pendiente) VALUES (?,?,?,?,?,?)",
                [(pdf_id, n, texto, normalizar(texto), "texto", int(escaneada)) for n, texto, escaneada in paginas])
    except BaseException:
        destino.unlink(missing_ok=True)
        raise
    if any(e for _, _, e in paginas):
        ocr.avisar_trabajo()
    log.info("PDF agregado: %s (%s páginas, %s para OCR)", titulo, total, sum(e for _, _, e in paginas))
    return obtener(con, pdf_id), aviso


def renombrar(con: sqlite3.Connection, pdf_id: int, titulo: str) -> Pdf:
    """Cambia el nombre descriptivo; el archivo en disco se renombra para seguir legible."""
    pdf = obtener(con, pdf_id)
    titulo = _limpiar_titulo(titulo)
    actual = ruta(con, pdf)
    archivo = pdf.archivo
    if titulo != pdf.titulo and actual.exists():
        nuevo = alm.ruta_libre(actual.parent, f"{alm.nombre_legible(titulo, 100)}.pdf")
        actual.rename(nuevo)
        archivo = f"pdf/{nuevo.name}"
    con.execute("UPDATE pdfs SET titulo=?, archivo=?, actualizado=? WHERE id=?", (titulo, archivo, ahora(), pdf_id))
    return obtener(con, pdf_id)


def pedir_ocr_completo(con: sqlite3.Connection, pdf_id: int) -> int:
    """Vuelve a reconocer TODAS las páginas con OCR (útil si el texto del PDF sale mal)."""
    obtener(con, pdf_id)
    n = con.execute("UPDATE pdf_paginas SET ocr_pendiente=1, ocr_error=NULL WHERE pdf_id=?", (pdf_id,)).rowcount
    ocr.avisar_trabajo()
    return n


def reintentar_errores(con: sqlite3.Connection, pdf_id: int) -> int:
    n = con.execute("UPDATE pdf_paginas SET ocr_pendiente=1, ocr_error=NULL WHERE pdf_id=? AND ocr_error IS NOT NULL",
                    (pdf_id,)).rowcount
    ocr.avisar_trabajo()
    return n


# ---------------------------------------------------------------- miniatura
def miniatura(con: sqlite3.Connection, pdf: Pdf, ancho: int = 480) -> Path | None:
    """Primera página como imagen (en data/cache/miniaturas, regenerable)."""
    destino = rutas.miniaturas / pdf.hash[:2] / f"{pdf.hash}-pdf-{ancho}.webp"
    if destino.exists():
        return destino
    try:
        destino.parent.mkdir(parents=True, exist_ok=True)
        with pymupdf.open(ruta(con, pdf)) as doc:
            pag = doc[0]
            escala = ancho / max(pag.rect.width, 1)
            pix = pag.get_pixmap(matrix=pymupdf.Matrix(escala, escala), alpha=False)
        from PIL import Image
        Image.frombytes("RGB", (pix.width, pix.height), pix.samples).save(destino, "WEBP", quality=80)
        return destino
    except Exception:
        log.exception("No se pudo crear la miniatura del PDF %s", pdf.id)
        return None


# -------------------------------------------------------------- OCR (fuente)
def procesar_una_pagina(con: sqlite3.Connection) -> bool:
    """Fuente de trabajos para el OCR en segundo plano: reconoce UNA página pendiente."""
    f = con.execute(
        """SELECT p.id, p.numero, p.texto, d.id AS pdf_id, d.archivo, d.componente_id
           FROM pdf_paginas p JOIN pdfs d ON d.id = p.pdf_id JOIN componentes c ON c.id = d.componente_id
           WHERE p.ocr_pendiente = 1 AND d.papelera_id IS NULL AND c.papelera_id IS NULL
           ORDER BY d.id, p.numero LIMIT 1""").fetchone()
    if f is None:
        return False
    try:
        comp = bib.obtener_componente(con, f["componente_id"])
        archivo = bib.carpeta_componente(con, comp) / Path(*f["archivo"].split("/"))
        with pymupdf.open(archivo) as doc:
            pix = doc[f["numero"] - 1].get_pixmap(dpi=ocr.RESOLUCION_PDF, alpha=False)
        from PIL import Image
        imagen = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        texto = ocr.reconocer(imagen).strip()
        # Si el OCR no encontró nada se conserva el poco texto que tuviera la página
        final = texto if len(texto) >= len(f["texto"]) else f["texto"]
        con.execute("UPDATE pdf_paginas SET texto=?, texto_norm=?, origen=?, ocr_pendiente=0, ocr_error=NULL WHERE id=?",
                    (final, normalizar(final), "ocr" if final == texto else "texto", f["id"]))
    except Exception as e:
        log.exception("OCR falló en la página %s del PDF %s", f["numero"], f["pdf_id"])
        con.execute("UPDATE pdf_paginas SET ocr_pendiente=0, ocr_error=? WHERE id=?", (str(e)[:300], f["id"]))
    return True


ocr.registrar_fuente(procesar_una_pagina)

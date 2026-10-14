"""Respaldos de toda la biblioteca en un ZIP (data/respaldos/) y restauración desde un ZIP.

El ZIP contiene la base de datos (copiada en caliente de forma consistente), los archivos
(data/archivos) y la papelera. No incluye la caché (se regenera) ni los registros.
Antes de restaurar se hace siempre un respaldo automático del estado actual.
"""
from __future__ import annotations

import json
import logging
import shutil
import sqlite3
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath

from .. import db
from ..config import rutas
from ..errores import ErrorUsuario
from . import bloqueo

log = logging.getLogger(__name__)

CARPETAS = ("archivos", "papelera")
MANIFIESTO = "respaldo.json"


@dataclass
class Respaldo:
    nombre: str
    ruta: Path
    bytes: int
    fecha: datetime

    @property
    def tamano(self) -> str:
        mb = self.bytes / 1048576
        return f"{mb:.1f} MB" if mb >= 0.1 else f"{self.bytes / 1024:.0f} KB"


def listar() -> list[Respaldo]:
    rutas.respaldos.mkdir(parents=True, exist_ok=True)
    salida = [Respaldo(p.name, p, p.stat().st_size, datetime.fromtimestamp(p.stat().st_mtime))
              for p in rutas.respaldos.glob("*.zip")]
    return sorted(salida, key=lambda r: r.fecha, reverse=True)


def obtener(nombre: str) -> Path:
    ruta = rutas.respaldos / Path(nombre).name
    if ruta.suffix.lower() != ".zip" or not ruta.exists():
        raise ErrorUsuario("Ese respaldo no existe.")
    return ruta


def crear(prefijo: str = "respaldo") -> Respaldo:
    rutas.respaldos.mkdir(parents=True, exist_ok=True)
    marca = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    destino = rutas.respaldos / f"{prefijo}-{marca}.zip"
    parcial = destino.with_suffix(".zip.parcial")
    copia_db = rutas.cache / f"respaldo-{marca}.db"
    copia_db.parent.mkdir(parents=True, exist_ok=True)
    try:
        # Copia consistente de la BD aunque esté en uso (API de respaldo de SQLite)
        origen = db.conectar()
        try:
            copia = sqlite3.connect(copia_db)
            with copia:
                origen.backup(copia)
            copia.close()
            version = origen.execute("PRAGMA user_version").fetchone()[0]
            conteos = {t: origen.execute(f"SELECT COUNT(*) FROM {t} WHERE papelera_id IS NULL").fetchone()[0]
                       for t in ("materias", "tablas", "pdfs", "imagenes", "notas")}
        finally:
            origen.close()
        with zipfile.ZipFile(parcial, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
            z.writestr(MANIFIESTO, json.dumps({"app": "Biblioteca de Estudio", "version_esquema": version,
                                               "fecha": datetime.now().isoformat(timespec="seconds"),
                                               "equipo": bloqueo.nombre_equipo(), "contenido": conteos},
                                              ensure_ascii=False, indent=2))
            z.write(copia_db, "biblioteca.db")
            for carpeta in CARPETAS:
                base = rutas.datos / carpeta
                for archivo in sorted(base.rglob("*")) if base.exists() else []:
                    if archivo.is_file():
                        # Los PDF e imágenes ya vienen comprimidos: guardarlos sin recomprimir es más rápido
                        modo = zipfile.ZIP_STORED if archivo.suffix.lower() in {".pdf", ".jpg", ".jpeg", ".png", ".webp",
                                                                                 ".gif", ".xlsx", ".zip"} else zipfile.ZIP_DEFLATED
                        z.write(archivo, f"{carpeta}/{archivo.relative_to(base).as_posix()}", compress_type=modo)
        parcial.replace(destino)
    finally:
        copia_db.unlink(missing_ok=True)
        parcial.unlink(missing_ok=True)
    log.info("Respaldo creado: %s", destino.name)
    return Respaldo(destino.name, destino, destino.stat().st_size, datetime.now())


def _validar(zip_ruta: Path) -> dict:
    if not zipfile.is_zipfile(zip_ruta):
        raise ErrorUsuario("El archivo no es un ZIP válido.")
    with zipfile.ZipFile(zip_ruta) as z:
        nombres = z.namelist()
        if "biblioteca.db" not in nombres or MANIFIESTO not in nombres:
            raise ErrorUsuario("Este ZIP no es un respaldo de la Biblioteca de Estudio.")
        for n in nombres:  # nada de rutas absolutas ni "../" (no puede escribir fuera de data/)
            partes = PurePosixPath(n).parts
            if n.startswith(("/", "\\")) or ".." in partes or ":" in n or \
                    (n not in ("biblioteca.db", MANIFIESTO) and partes[0] not in CARPETAS):
                raise ErrorUsuario("El respaldo contiene rutas no válidas y no se restaurará.")
        try:
            manifiesto = json.loads(z.read(MANIFIESTO))
        except ValueError as e:
            raise ErrorUsuario("El respaldo está dañado.") from e
    if manifiesto.get("version_esquema", 0) > len(db.MIGRACIONES):
        raise ErrorUsuario("Este respaldo es de una versión más nueva de la aplicación. Actualiza la aplicación primero.")
    return manifiesto


def restaurar(zip_ruta: Path, antes_de_cambiar=None) -> Respaldo:
    """Reemplaza la biblioteca actual por la del ZIP. Devuelve el respaldo automático previo.
    `antes_de_cambiar`: función que se llama justo antes de tocar los archivos (p. ej. detener el OCR)."""
    _validar(zip_ruta)
    previo = crear("antes-de-restaurar")
    temporal = rutas.cache / "restauracion"
    shutil.rmtree(temporal, ignore_errors=True)
    temporal.mkdir(parents=True)
    with zipfile.ZipFile(zip_ruta) as z:
        z.extractall(temporal)
    # Comprobación de la BD extraída antes de reemplazar nada
    try:
        prueba = sqlite3.connect(temporal / "biblioteca.db")
        estado = prueba.execute("PRAGMA integrity_check").fetchone()[0]
        prueba.close()
    except sqlite3.DatabaseError as e:
        raise ErrorUsuario("La base de datos del respaldo está dañada.") from e
    if estado != "ok":
        raise ErrorUsuario("La base de datos del respaldo está dañada.")
    if antes_de_cambiar:
        antes_de_cambiar()
    viejo = rutas.cache / "reemplazado"
    shutil.rmtree(viejo, ignore_errors=True)
    viejo.mkdir(parents=True)
    for carpeta in CARPETAS:
        if (rutas.datos / carpeta).exists():
            shutil.move(str(rutas.datos / carpeta), str(viejo / carpeta))
        if (temporal / carpeta).exists():
            shutil.move(str(temporal / carpeta), str(rutas.datos / carpeta))
        else:
            (rutas.datos / carpeta).mkdir(parents=True, exist_ok=True)
    if rutas.db.exists():  # la BD actual se aparta (y se borra al final si todo salió bien)
        shutil.move(str(rutas.db), str(viejo / "biblioteca.db"))
    shutil.move(str(temporal / "biblioteca.db"), str(rutas.db))
    db.inicializar()  # aplica migraciones si el respaldo era de una versión anterior
    shutil.rmtree(viejo, ignore_errors=True)
    shutil.rmtree(temporal, ignore_errors=True)
    shutil.rmtree(rutas.miniaturas, ignore_errors=True)   # se regeneran solas
    log.info("Biblioteca restaurada desde %s", zip_ruta.name)
    return previo


def eliminar(nombre: str) -> None:
    obtener(nombre).unlink()


def tamano_biblioteca() -> int:
    total = rutas.db.stat().st_size if rutas.db.exists() else 0
    for carpeta in CARPETAS:
        total += sum(p.stat().st_size for p in (rutas.datos / carpeta).rglob("*") if p.is_file())
    return total

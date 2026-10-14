"""Archivos en disco: nombres seguros, carpetas legibles, duplicados y papelera.

Todo vive dentro de `data/` y en la base de datos solo se guardan rutas
relativas, para que la carpeta funcione igual en Mac y en Windows.
"""
from __future__ import annotations

import hashlib
import re
import shutil
import unicodedata
from pathlib import Path

from ..config import rutas

# Nombres que Windows no permite como archivo o carpeta
_RESERVADOS_WINDOWS = {"con", "prn", "aux", "nul", *(f"com{i}" for i in range(1, 10)), *(f"lpt{i}" for i in range(1, 10))}
_PROHIBIDOS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def sin_tildes(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in texto if not unicodedata.combining(c))


def slugify(texto: str, largo: int = 60) -> str:
    """"Fisiología Cardíaca" -> "fisiologia-cardiaca" (seguro como nombre de carpeta)."""
    slug = re.sub(r"[^a-z0-9]+", "-", sin_tildes(texto).lower()).strip("-")[:largo].strip("-")
    if not slug:
        slug = "sin-nombre"
    if slug in _RESERVADOS_WINDOWS:
        slug += "-1"
    return slug


def slug_unico(base: str, ocupados: set[str]) -> str:
    slug, n = base, 2
    while slug in ocupados:
        slug, n = f"{base}-{n}", n + 1
    return slug


def sanear_nombre_archivo(nombre: str, largo: int = 120) -> str:
    """Conserva el nombre original pero sin caracteres problemáticos para Windows o Mac."""
    nombre = Path(nombre.replace("\\", "/")).name  # nunca rutas
    nombre = unicodedata.normalize("NFC", nombre)
    nombre = _PROHIBIDOS.sub("_", nombre).strip().strip(".")
    tronco, punto, ext = nombre.rpartition(".")
    if not punto:
        tronco, ext = nombre, ""
    tronco = re.sub(r"\s+", " ", tronco).strip() or "archivo"
    if tronco.lower() in _RESERVADOS_WINDOWS:
        tronco += "_"
    ext = re.sub(r"[^A-Za-z0-9]", "", ext)[:10].lower()
    tronco = tronco[: largo - len(ext) - 1]
    return f"{tronco}.{ext}" if ext else tronco


def ruta_libre(carpeta: Path, nombre: str) -> Path:
    """Si ya existe un archivo con ese nombre, agrega un sufijo: "atlas (2).pdf"."""
    destino = carpeta / nombre
    if not destino.exists():
        return destino
    tronco, ext = destino.stem, destino.suffix
    n = 2
    while (carpeta / f"{tronco} ({n}){ext}").exists():
        n += 1
    return carpeta / f"{tronco} ({n}){ext}"


def hash_archivo(ruta: Path) -> str:
    h = hashlib.sha256()
    with ruta.open("rb") as f:
        for bloque in iter(lambda: f.read(1024 * 1024), b""):
            h.update(bloque)
    return h.hexdigest()


def hash_bytes(datos: bytes) -> str:
    return hashlib.sha256(datos).hexdigest()


def mover_carpeta(origen: Path, destino: Path) -> None:
    """Mueve una carpeta (al renombrar materias o componentes). No falla si el origen no existe."""
    if not origen.exists() or origen.resolve() == destino.resolve():
        return
    destino.parent.mkdir(parents=True, exist_ok=True)
    if destino.is_dir() and not any(destino.iterdir()):
        destino.rmdir()  # carpeta vacía sobrante: se reemplaza
    if destino.exists():
        raise FileExistsError(f"Ya existe la carpeta {rutas.relativa(destino)}")
    shutil.move(str(origen), str(destino))
    _limpiar_vacias(origen.parent)


def a_papelera(origen: Path, nombre: str) -> str | None:
    """Mueve un archivo o carpeta a data/papelera/ y devuelve su ruta relativa allí."""
    if not origen.exists():
        return None
    rutas.papelera.mkdir(parents=True, exist_ok=True)
    destino = ruta_libre(rutas.papelera, nombre)
    shutil.move(str(origen), str(destino))
    _limpiar_vacias(origen.parent)
    return rutas.relativa(destino)


def borrar_definitivo(relativa: str | None) -> None:
    if not relativa:
        return
    ruta = rutas.absoluta(relativa)
    if ruta.is_dir():
        shutil.rmtree(ruta, ignore_errors=True)
    elif ruta.exists():
        ruta.unlink()


def _limpiar_vacias(carpeta: Path) -> None:
    """Quita carpetas vacías que quedan al mover cosas, sin salir de data/archivos."""
    base = rutas.archivos.resolve()
    carpeta = carpeta.resolve()
    while carpeta != base and carpeta.is_relative_to(base) and carpeta.exists() and not any(carpeta.iterdir()):
        carpeta.rmdir()
        carpeta = carpeta.parent

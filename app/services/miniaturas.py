"""Miniaturas en data/cache/miniaturas/ (se pueden borrar: se regeneran solas)."""
from __future__ import annotations

import logging
from pathlib import Path

from PIL import Image, ImageOps

from ..config import rutas

log = logging.getLogger(__name__)
ANCHO = 480


def ruta_miniatura(hash_: str, ancho: int = ANCHO) -> Path:
    return rutas.miniaturas / hash_[:2] / f"{hash_}-{ancho}.webp"


def obtener(original: Path, hash_: str, ancho: int = ANCHO) -> Path | None:
    """Devuelve la miniatura (creándola si hace falta) o None si no se puede generar."""
    destino = ruta_miniatura(hash_, ancho)
    if destino.exists():
        return destino
    try:
        destino.parent.mkdir(parents=True, exist_ok=True)
        with Image.open(original) as img:
            img = ImageOps.exif_transpose(img)
            if img.mode not in ("RGB", "RGBA"):
                img = img.convert("RGBA" if "A" in img.getbands() else "RGB")
            img.thumbnail((ancho, ancho * 2))
            img.save(destino, "WEBP", quality=82, method=4)
        return destino
    except Exception:
        log.exception("No se pudo crear la miniatura de %s", original.name)
        return None


def regenerar_todas() -> int:
    """Borra la caché de miniaturas (se vuelven a crear al verlas)."""
    import shutil
    n = sum(1 for _ in rutas.miniaturas.rglob("*.webp")) if rutas.miniaturas.exists() else 0
    shutil.rmtree(rutas.miniaturas, ignore_errors=True)
    rutas.miniaturas.mkdir(parents=True, exist_ok=True)
    return n

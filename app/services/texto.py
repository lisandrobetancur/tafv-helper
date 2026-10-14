"""Normalización de texto para buscar y filtrar sin tildes ni mayúsculas ("Fémur" = "femur")."""
from __future__ import annotations

import re
import unicodedata


def normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto or "")
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", texto).strip().lower()


def clave_orden(texto: str) -> str:
    """Orden natural: rellena los números con ceros ("parcial 9" < "parcial 10")."""
    return re.sub(r"\d+", lambda m: m.group(0).zfill(12), normalizar(texto))

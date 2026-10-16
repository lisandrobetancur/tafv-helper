"""Utilidades compartidas por las herramientas de carga de material (tools/carga/).

Se ejecutan desde la raíz del proyecto con el Python del entorno, p. ej.:
    .venv/bin/python tools/carga/inspeccionar.py data/fuentes/oxigenoterapia/hbo/hojas/HBO.xlsx
Para trabajar sobre otra carpeta de datos (pruebas), define BIBLIOTECA_DATOS antes de ejecutar.
"""
from __future__ import annotations

import re
import sys
import unicodedata
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))


def sin_tildes(texto: str) -> str:
    t = unicodedata.normalize("NFKD", str(texto))
    return "".join(c for c in t if not unicodedata.combining(c))


def palabras(texto: str) -> set[str]:
    """Palabras en minúsculas y sin tildes; sirve para comparar contenido sin depender del formato."""
    return set(re.findall(r"[a-z0-9]+", sin_tildes(texto).lower()))


def texto_comentario(comentario) -> str:
    """Texto de un comentario de Excel sin el encabezado que agrega Google Sheets (ID, autor, fecha)."""
    texto = comentario.text or ""
    if texto.startswith("======"):
        partes = texto.split(")\n", 1)
        if len(partes) == 2:
            return partes[1].strip()
    return texto.strip()


def autor_comentario(comentario) -> str:
    texto = comentario.text or ""
    m = re.search(r"\n([^\n]+?)\s+\(\d{4}-\d{2}-\d{2}", texto)
    return (m.group(1).strip() if m else (comentario.author or "")).strip()

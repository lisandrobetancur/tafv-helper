"""Mejora la legibilidad de una imagen sin cambiar su contenido: tamaño, contraste y nitidez.

    .venv/bin/python tools/carga/mejorar_imagen.py <entrada> <salida.png> [--comparacion antes-despues.png]

No recorta, no redibuja y no agrega nada. La original queda intacta en data/fuentes/; la mejorada se
carga solo si la usuaria la aprueba (mirando la comparación antes/después).
"""
from __future__ import annotations

import argparse
from pathlib import Path

import comun  # noqa: F401
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps

ANCHO_MINIMO = 1600


def mejorar(entrada: Path) -> Image.Image:
    img = ImageOps.exif_transpose(Image.open(entrada)).convert("RGB")
    if img.width < ANCHO_MINIMO:
        factor = ANCHO_MINIMO / img.width
        img = img.resize((ANCHO_MINIMO, round(img.height * factor)), Image.Resampling.LANCZOS)
    img = ImageOps.autocontrast(img, cutoff=1)
    img = ImageEnhance.Contrast(img).enhance(1.15)
    return img.filter(ImageFilter.UnsharpMask(radius=2, percent=140, threshold=3))


def comparacion(antes: Path, despues: Image.Image) -> Image.Image:
    a = Image.open(antes).convert("RGB")
    a = a.resize((despues.width, round(a.height * despues.width / a.width)), Image.Resampling.LANCZOS)
    margen = 48
    lienzo = Image.new("RGB", (a.width * 2 + 24, max(a.height, despues.height) + margen), "white")
    lienzo.paste(a, (0, margen))
    lienzo.paste(despues, (a.width + 24, margen))
    d = ImageDraw.Draw(lienzo)
    d.text((8, 12), "ANTES", fill="black")
    d.text((a.width + 32, 12), "DESPUÉS", fill="black")
    return lienzo


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("entrada", type=Path)
    ap.add_argument("salida", type=Path)
    ap.add_argument("--comparacion", type=Path)
    a = ap.parse_args()
    mejorada = mejorar(a.entrada)
    a.salida.parent.mkdir(parents=True, exist_ok=True)
    mejorada.save(a.salida)
    if a.comparacion:
        comparacion(a.entrada, mejorada).save(a.comparacion)
    print(f"Mejorada: {a.salida} ({mejorada.width}×{mejorada.height})")

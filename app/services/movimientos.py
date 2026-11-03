"""Diagnóstico por movimiento: los cinco movimientos con sus opciones y la imagen que va a la recopilación.

Los síntomas que se agregan viven solo en la página (cada vez empieza en 0). Lo que se quiera conservar se
manda a la recopilación, como copia fija: una imagen del diagrama y los síntomas en texto.
"""
from __future__ import annotations

import io
from functools import lru_cache

import pymupdf
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

from ..errores import ErrorUsuario

MAX_SINTOMAS = 200       # por movimiento
MAX_LARGO = 200          # de cada síntoma

# `lineas` es el texto de cada círculo, como en la hoja impresa; `opciones`, lo que ofrece el menú de su cuadro
MOVIMIENTOS: list[dict] = [
    {"id": "MADERA", "color": "#639922", "lado": "derecha",
     "lineas": ["H/VB", "OJOS", "LAGRIMAS", "TENDONES/UÑAS", "COLERA", "AGRIO"],
     "opciones": ["H/VB", "OJOS", "LAGRIMAS", "TENDONES/UÑAS", "COLERA", "AGRIO"]},
    {"id": "FUEGO", "color": "#D85A30", "lado": "derecha",
     "lineas": ["CZON/I.G", "LENGUA", "SUDOR", "VASOS/PIEL CARA", "ALEGRIA", "AMARGO"],
     "opciones": ["CZON/I.G", "LENGUA", "SUDOR", "VASOS/PIEL CARA", "ALEGRIA", "AMARGO"]},
    {"id": "TIERRA", "color": "#BA7517", "lado": "derecha",
     "lineas": ["BAZ/EST", "BOCA", "SALIVA CLARA", "CARNE Y 4", "EXTRE/LABIOS", "REFLEXION", "DULCE"],
     "opciones": ["BAZ/EST", "BOCA", "SALIVA CLARA", "CARNE Y 4 EXTRE/LABIOS", "REFLEXION", "DULCE"]},
    {"id": "METAL", "color": "#888780", "lado": "izquierda",
     "lineas": ["PUL/I.G", "NARIZ", "MOCOS", "PIEL/ VELLO", "TRISTEZA-PENA", "PICANTE"],
     "opciones": ["PUL/I.G", "NARIZ", "MOCOS", "PIEL/ VELLO", "TRISTEZA-PENA", "PICANTE"]},
    {"id": "AGUA", "color": "#378ADD", "lado": "izquierda",
     "lineas": ["RIÑ/VEJ", "OREJAS", "SALIVA ESPESA", "HUESOS-", "ARTIC/CABELLO", "MIEDO", "SALADO"],
     "opciones": ["RIÑ/VEJ", "OREJAS", "SALIVA ESPESA", "HUESOS-ARTIC/CABELLO", "MIEDO", "SALADO"]},
]
POR_ID = {m["id"]: m for m in MOVIMIENTOS}
FILAS = [["MADERA"], ["AGUA", "FUEGO"], ["METAL", "TIERRA"]]  # de arriba abajo, como el pentágono de la hoja


def validar(sintomas: dict) -> dict[str, list[str]]:
    """Deja solo síntomas limpios y sin repetir, en todos los movimientos. Falla si no hay ninguno."""
    limpios: dict[str, list[str]] = {m["id"]: [] for m in MOVIMIENTOS}
    if not isinstance(sintomas, dict):
        raise ErrorUsuario("No se entendieron los síntomas enviados.")
    for clave, lista in sintomas.items():
        if clave not in limpios or not isinstance(lista, list):
            raise ErrorUsuario("No se entendieron los síntomas enviados.")
        if len(lista) > MAX_SINTOMAS:
            raise ErrorUsuario(f"{clave} tiene demasiados síntomas (máximo {MAX_SINTOMAS}).")
        vistos = set()
        for s in lista:
            s = " ".join(str(s).split())[:MAX_LARGO]
            if s and s.casefold() not in vistos:
                vistos.add(s.casefold())
                limpios[clave].append(s)
    if not any(limpios.values()):
        raise ErrorUsuario("Agrega al menos un síntoma antes de recopilar.")
    return limpios


def mayores(sintomas: dict[str, list[str]]) -> set[str]:
    """Los movimientos con más síntomas (varios si hay empate; ninguno si todo está en 0)."""
    tope = max((len(v) for v in sintomas.values()), default=0)
    return {k for k, v in sintomas.items() if v and len(v) == tope} if tope else set()


# ------------------------------------------------------------------ imagen
ESCALA = 2
ANCHO, DIAMETRO, CAJA, CONECTOR = 760, 106, 200, 14
SEPARACION = {0: 0, 1: 112, 2: 6}    # hueco entre los dos grupos de cada fila
GRIS = ("#ffffff", "#e9e7dd", "#bdbbb0")
AZUL = ("#f4faff", "#bfdcf7", "#74afe6")


@lru_cache(maxsize=16)
def _fuente(tamano: float, negrita: bool = False) -> ImageFont.FreeTypeFont:
    """La Helvetica que trae PyMuPDF: está en todos los equipos y tiene tildes y Ñ (la de Pillow no)."""
    return ImageFont.truetype(io.BytesIO(pymupdf.Font("hebo" if negrita else "helv").buffer), int(tamano * ESCALA))


def _partir(texto: str, fuente, ancho: float) -> list[str]:
    """Parte el texto en líneas que quepan en `ancho`; una palabra muy larga también se corta."""
    lineas, actual = [], ""
    for palabra in texto.split():
        while fuente.getlength(palabra) > ancho:
            corte = len(palabra) - 1
            while corte > 1 and fuente.getlength(palabra[:corte]) > ancho:
                corte -= 1
            if actual:
                lineas.append(actual)
                actual = ""
            lineas.append(palabra[:corte])
            palabra = palabra[corte:]
        prueba = f"{actual} {palabra}".strip()
        if fuente.getlength(prueba) > ancho:
            lineas.append(actual)
            actual = palabra
        else:
            actual = prueba
    return [*lineas, actual] if actual else lineas


def _esfera(lienzo: Image.Image, x: float, y: float, colores: tuple[str, str, str]) -> None:
    """Dibuja un círculo en relieve: luz arriba a la izquierda y sombra debajo."""
    d = DIAMETRO * ESCALA
    sombra = Image.new("L", (d + 60, d + 60), 0)
    ImageDraw.Draw(sombra).ellipse((30, 30, d + 30, d + 30), fill=95)
    sombra = sombra.filter(ImageFilter.GaussianBlur(9))
    lienzo.paste("#000000", (int(x) - 30, int(y) - 30 + 10 * ESCALA // 2), sombra)
    degradado = Image.radial_gradient("L").resize((d * 2, d * 2))
    izquierda, arriba = int(d * .65), int(d * .72)
    degradado = degradado.crop((izquierda, arriba, izquierda + d, arriba + d))
    color = ImageOps.colorize(degradado, black=colores[0], mid=colores[1], white=colores[2], midpoint=120)
    mascara = Image.new("L", (d * 4, d * 4), 0)
    ImageDraw.Draw(mascara).ellipse((0, 0, d * 4 - 1, d * 4 - 1), fill=255)
    lienzo.paste(color, (int(x), int(y)), mascara.resize((d, d), Image.LANCZOS))


def _circulo(lienzo: Image.Image, m: dict, x: float, y: float, azul: bool) -> None:
    _esfera(lienzo, x, y, AZUL if azul else GRIS)
    dibujo = ImageDraw.Draw(lienzo)
    tinta = "#042c53" if azul else "#2c2c2a"
    alto = (12 + 2 + 11 * len(m["lineas"])) * ESCALA
    cx, cursor = x + DIAMETRO * ESCALA / 2, y + (DIAMETRO * ESCALA - alto) / 2
    dibujo.text((cx, cursor), m["id"], font=_fuente(12, True), fill=tinta, anchor="ma")
    cursor += 14 * ESCALA
    for linea in m["lineas"]:
        dibujo.text((cx, cursor), linea, font=_fuente(10), fill=tinta, anchor="ma")
        cursor += 11 * ESCALA


def _lineas_caja(sintomas: list[str]) -> list[list[str]]:
    return [_partir(s, _fuente(11), (CAJA - 32) * ESCALA) for s in sintomas]


def _alto_caja(sintomas: list[str]) -> int:
    return 38 + sum(len(ls) * 14 + 10 + 4 for ls in _lineas_caja(sintomas))


def _caja(lienzo: Image.Image, m: dict, sintomas: list[str], x: float, y: float) -> None:
    alto = _alto_caja(sintomas) * ESCALA
    ancho = CAJA * ESCALA
    dibujo = ImageDraw.Draw(lienzo)
    dibujo.rounded_rectangle((x, y, x + ancho, y + alto), radius=12 * ESCALA, fill=m["color"])
    dibujo.rounded_rectangle((x, y + 3 * ESCALA, x + ancho, y + alto), radius=12 * ESCALA, fill="#ffffff", outline="#d8d4cc", width=ESCALA)
    dibujo.text((x + 12 * ESCALA, y + 11 * ESCALA), m["id"], font=_fuente(12, True), fill="#1f1b17")
    n = str(len(sintomas))
    fondo, tinta = ("#dcebfa", "#0c447c") if sintomas else ("#f1efe8", "#6b645c")
    dibujo.rounded_rectangle((x + ancho - 42 * ESCALA, y + 10 * ESCALA, x + ancho - 12 * ESCALA, y + 26 * ESCALA),
                             radius=8 * ESCALA, fill=fondo)
    dibujo.text((x + ancho - 27 * ESCALA, y + 18 * ESCALA), n, font=_fuente(11), fill=tinta, anchor="mm")
    cursor = y + 34 * ESCALA
    for lineas in _lineas_caja(sintomas):
        alto_item = (len(lineas) * 14 + 10) * ESCALA
        dibujo.rounded_rectangle((x + 10 * ESCALA, cursor, x + ancho - 10 * ESCALA, cursor + alto_item),
                                 radius=6 * ESCALA, fill="#f4f3ee")
        for k, linea in enumerate(lineas):
            dibujo.text((x + 16 * ESCALA, cursor + (5 + k * 14) * ESCALA), linea, font=_fuente(11), fill="#1f1b17")
        cursor += alto_item + 4 * ESCALA


def imagen(sintomas: dict[str, list[str]], titulo: str) -> Image.Image:
    """El diagrama tal como se ve en pantalla: cada círculo con su cuadro al lado, unidos por una línea."""
    azules = mayores(sintomas)
    altos = [max(DIAMETRO, *(_alto_caja(sintomas[i]) for i in fila)) for fila in FILAS]
    lienzo = Image.new("RGB", (ANCHO * ESCALA, (46 + sum(altos) + 8 * len(FILAS) + 12) * ESCALA), "#ffffff")
    ImageDraw.Draw(lienzo).text((ANCHO * ESCALA / 2, 12 * ESCALA), titulo, font=_fuente(16, True), fill="#1f1b17", anchor="ma")
    y = 46
    for n, fila in enumerate(FILAS):
        grupo = CAJA + CONECTOR + DIAMETRO
        x = (ANCHO - grupo * 2 - SEPARACION[n]) / 2
        for k, mid in enumerate(fila):
            m = POR_ID[mid]
            if len(fila) == 1:                 # el círculo de arriba queda en el centro y su cuadro a la derecha
                xc, xb = (ANCHO - DIAMETRO) / 2, (ANCHO + DIAMETRO) / 2 + CONECTOR
            elif k == 0:
                xb, xc = x, x + CAJA + CONECTOR
            else:
                xc, xb = x + grupo + SEPARACION[n], x + grupo + SEPARACION[n] + DIAMETRO + CONECTOR
            medio = (y + DIAMETRO / 2) * ESCALA
            desde, hasta = (xb + CAJA, xc) if xb < xc else (xc + DIAMETRO, xb)
            ImageDraw.Draw(lienzo).line((desde * ESCALA, medio, hasta * ESCALA, medio), fill=m["color"], width=2 * ESCALA)
            _caja(lienzo, m, sintomas[mid], xb * ESCALA, y * ESCALA)
            _circulo(lienzo, m, xc * ESCALA, y * ESCALA, mid in azules)
        y += altos[n] + 8
    return lienzo

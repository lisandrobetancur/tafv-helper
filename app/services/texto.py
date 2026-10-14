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


def fragmentos_resaltados(texto: str, termino: str) -> list[tuple[str, bool]]:
    """Divide `texto` en trozos (texto, coincide) marcando cada aparición de `termino` (o de sus
    palabras), sin importar tildes ni mayúsculas. Sirve para resaltar con <mark> en las plantillas."""
    palabras = [p for p in normalizar(termino.replace('"', " ")).split() if len(p) > 1]
    if not texto or not palabras:
        return [(texto, False)]
    # Texto normalizado carácter a carácter, recordando a qué posición original corresponde
    plano, mapa = [], []
    for i, caracter in enumerate(texto):
        for c in normalizar(caracter) or (" " if caracter.isspace() else ""):
            plano.append(c)
            mapa.append(i)
    plano_txt = "".join(plano)
    marcas = [False] * len(texto)
    for palabra in sorted(set(palabras), key=len, reverse=True):
        inicio = plano_txt.find(palabra)
        while inicio != -1:
            for j in range(mapa[inicio], mapa[inicio + len(palabra) - 1] + 1):
                marcas[j] = True
            inicio = plano_txt.find(palabra, inicio + len(palabra))
    # Los espacios entre dos palabras resaltadas también se resaltan ("pies fríos" en un solo bloque)
    i = 0
    while i < len(texto):
        if not marcas[i] and texto[i] in " \t" and i > 0 and marcas[i - 1]:
            j = i
            while j < len(texto) and texto[j] in " \t":
                j += 1
            if j < len(texto) and marcas[j]:
                for k in range(i, j):
                    marcas[k] = True
            i = j
        else:
            i += 1
    trozos: list[tuple[str, bool]] = []
    for caracter, marcado in zip(texto, marcas):
        if trozos and trozos[-1][1] == marcado:
            trozos[-1] = (trozos[-1][0] + caracter, marcado)
        else:
            trozos.append((caracter, marcado))
    return trozos

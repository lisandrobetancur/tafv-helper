"""Compara la copia corregida de una tabla con la hoja original, palabra por palabra.

    .venv/bin/python tools/carga/comparar_tabla.py <plan.json>

Para cada tabla del plan cuyo archivo no es la hoja original, alinea las palabras de cada celda con las de la
celda original y lista todo cambio que no sea solo de tildes ni esté declarado en `correcciones`. Sirve para
detectar reemplazos hechos dentro de otra palabra (p. ej. «demas» → «demás» que convierte «demasiado» en
«demásiado») y correcciones sin declarar. Sale con código 1 si encuentra alguno.
"""
from __future__ import annotations

import difflib
import json
import re
import sys
from pathlib import Path

import comun  # noqa: F401
import openpyxl

from comun import sin_tildes

PALABRA = re.compile(r"\w+", re.UNICODE)


def _celdas(ruta: Path) -> dict[str, str]:
    ws = openpyxl.load_workbook(ruta, data_only=True).worksheets[0]
    return {c.coordinate: str(c.value) for f in ws.iter_rows() for c in f if c.value is not None}


def comparar(plan_ruta: Path) -> list[str]:
    plan = json.loads(plan_ruta.read_text(encoding="utf-8"))
    base = plan_ruta.parent
    declaradas = set()
    for original, corregido in plan.get("correcciones", {}).items():
        for a, b in zip(PALABRA.findall(original), PALABRA.findall(corregido)):
            declaradas.add((a.lower(), b.lower()))
        declaradas.add((original.lower(), corregido.lower()))
    hallazgos = []
    for t in plan.get("tablas", []):
        if not t["archivo"].startswith("tablas/"):
            continue
        copia = _celdas(base / t["archivo"])
        hoja = next((base / f for f in plan.get("fuentes", []) if f.startswith("hojas/")), None)
        if hoja is None:
            continue
        original = _celdas(hoja)
        # La copia puede empezar en otra fila (extraer_rango): se emparejan celdas por contenido parecido
        pendientes = dict(original)
        cambios_tilde: list[tuple[str, str, str, str]] = []   # (palabra original, nueva, celda copia, celda hoja)
        for celda, nuevo in copia.items():
            viejo_celda = max(pendientes, key=lambda k: difflib.SequenceMatcher(
                None, sin_tildes(pendientes[k]).lower(), sin_tildes(nuevo).lower()).ratio(), default=None)
            if viejo_celda is None:
                continue
            viejo = pendientes.pop(viejo_celda)
            a, b = PALABRA.findall(viejo), PALABRA.findall(nuevo)
            for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
                if op == "equal":
                    continue
                antes, despues = " ".join(a[i1:i2]), " ".join(b[j1:j2])
                if sin_tildes(antes).lower() == sin_tildes(despues).lower():
                    cambios_tilde += [(x, y, celda, viejo_celda) for x, y in zip(a[i1:i2], b[j1:j2]) if x != y]
                    continue  # solo tildes (se revisan abajo)
                if (antes.lower(), despues.lower()) in declaradas or any(
                        (x.lower(), y.lower()) in declaradas for x, y in zip(a[i1:i2], b[j1:j2])):
                    continue
                if any(antes.lower() in o.lower() and despues.lower() in c.lower()
                       for o, c in plan.get("correcciones", {}).items()):
                    continue
                hallazgos.append(f"{t['nombre']} · {celda} (hoja {viejo_celda}): «{antes}» → «{despues}»")
        # Una tilde que cae dentro de una palabra más larga: «demas» → «demás» aplicado a «demasiado» da «demásiado»
        cortas = {(x.lower(), y.lower()) for x, y, _, _ in cambios_tilde}
        for x, y, celda, viejo_celda in cambios_tilde:
            for cx, cy in cortas:
                resto = x.lower()[len(cx):]
                if (len(cx) < len(x) and x.lower().startswith(cx) and y.lower().startswith(cy) and cx != cy
                        and resto not in ("s", "es", "n", "mente")):   # plural, verbo o adverbio: misma tilde (cápsulas, están, fácilmente)
                    hallazgos.append(f"{t['nombre']} · {celda} (hoja {viejo_celda}): «{x}» → «{y}» "
                                     f"(¿la tilde de «{cy}» cayó dentro de otra palabra?)")
                    break
    return hallazgos


if __name__ == "__main__":
    resultado = comparar(Path(sys.argv[1]))
    for h in resultado:
        print(f"REVISAR  {h}")
    print("\nSIN CAMBIOS SOSPECHOSOS" if not resultado else f"\n{len(resultado)} CAMBIOS PARA REVISAR")
    sys.exit(1 if resultado else 0)

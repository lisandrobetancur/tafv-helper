"""Módulo Diagnóstico: caso clínico en texto libre -> diagnósticos y tratamiento según la tabla de jerarquización.

Dos pantallas: en /diagnostico se pega el caso; al analizarlo se pasa a /diagnostico/resultado, que lo entrega
como en los casos de clase (diagnósticos numerados y jerarquización con la prescripción de cada terapia).
"""
from __future__ import annotations

import sqlite3
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse

from ..db import obtener_db
from ..services import diagnostico_clinico as dxc
from ..web import pagina

router = APIRouter()
MIGAS = [{"texto": "Diagnóstico", "icono": "clipboard-plus"}]


@router.get("/diagnostico")
def pagina_caso(request: Request, con: sqlite3.Connection = Depends(obtener_db)):
    if "s" in request.query_params:   # dirección del antiguo «Diagnóstico por síntomas», hoy Acceso rápido
        return RedirectResponse("/acceso-rapido?" + urlencode(list(request.query_params.multi_items())), status_code=301)
    return pagina(request, con, "paginas/diagnostico_clinico.html", texto="", migas=MIGAS)


@router.post("/diagnostico")
async def editar_caso(request: Request, con: sqlite3.Connection = Depends(obtener_db)):
    """Vuelve a la pantalla del caso con el texto ya escrito («Editar el caso» desde el resultado)."""
    form = await request.form()
    return pagina(request, con, "paginas/diagnostico_clinico.html", texto=str(form.get("texto") or ""), migas=MIGAS)


@router.get("/diagnostico/resultado")
def resultado_sin_caso():
    return RedirectResponse("/diagnostico", status_code=303)


@router.post("/diagnostico/resultado")
async def resultado(request: Request, con: sqlite3.Connection = Depends(obtener_db)):
    form = await request.form()
    texto = str(form.get("texto") or "")
    elegidos = [str(v) for v in form.getlist("dx") if v] if form.get("ajustado") else None
    if not texto.strip() and not elegidos:
        return RedirectResponse("/diagnostico", status_code=303)
    res = dxc.analizar(con, texto, elegidos)
    return pagina(request, con, "paginas/diagnostico_clinico_resultado.html", resultado=res,
                  migas=[{"texto": "Diagnóstico", "url": "/diagnostico", "icono": "clipboard-plus"}, {"texto": "Resultado"}])

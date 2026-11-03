"""Módulo Diagnóstico: caso clínico en texto libre -> diagnósticos y tratamiento según la tabla de jerarquización."""
from __future__ import annotations

import sqlite3
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse

from ..db import obtener_db
from ..services import diagnostico_clinico as dxc
from ..web import pagina, parcial

router = APIRouter()
MIGAS = [{"texto": "Diagnóstico", "icono": "clipboard-plus"}]


@router.get("/diagnostico")
def pagina_diagnostico(request: Request, con: sqlite3.Connection = Depends(obtener_db)):
    if "s" in request.query_params:   # dirección del antiguo «Diagnóstico por síntomas», hoy Acceso rápido
        return RedirectResponse("/acceso-rapido?" + urlencode(list(request.query_params.multi_items())), status_code=301)
    return pagina(request, con, "paginas/diagnostico_clinico.html", resultado=None, texto="", migas=MIGAS)


@router.post("/diagnostico/resultado")
async def resultado(request: Request, con: sqlite3.Connection = Depends(obtener_db)):
    form = await request.form()
    texto = str(form.get("texto") or "")
    elegidos = [str(v) for v in form.getlist("dx") if v] if form.get("ajustado") else None
    res = dxc.analizar(con, texto, elegidos) if texto.strip() or elegidos else None
    return parcial(request, "parciales/diagnostico_clinico_resultado.html", resultado=res)

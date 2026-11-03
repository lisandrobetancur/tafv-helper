"""Módulo Diagnóstico: caso clínico en texto libre -> diagnósticos y tratamiento según la tabla de jerarquización.

Dos pantallas: en /diagnostico se pega el caso; al analizarlo se pasa a /diagnostico/resultado, que lo entrega
como en los casos de clase (diagnósticos numerados y jerarquización con la prescripción de cada terapia).
"""
from __future__ import annotations

import sqlite3
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import RedirectResponse

from ..db import obtener_db
from ..services import diagnostico_clinico as dxc
from ..services import diagnostico_ia as dia
from ..web import pagina

router = APIRouter()
MIGAS = [{"texto": "Diagnóstico", "icono": "clipboard-plus"}]


@router.get("/diagnostico")
def pagina_caso(request: Request, con: sqlite3.Connection = Depends(obtener_db)):
    if "s" in request.query_params:   # dirección del antiguo «Diagnóstico por síntomas», hoy Acceso rápido
        return RedirectResponse("/acceso-rapido?" + urlencode(list(request.query_params.multi_items())), status_code=301)
    return pagina(request, con, "paginas/diagnostico_clinico.html", texto="", migas=MIGAS, ia_disponible=dia.disponible(),
                  modelo=dia.NOMBRE_MODELO)


@router.post("/diagnostico")
async def editar_caso(request: Request, con: sqlite3.Connection = Depends(obtener_db)):
    """Vuelve a la pantalla del caso con el texto ya escrito («Editar el caso» desde el resultado)."""
    form = await request.form()
    return pagina(request, con, "paginas/diagnostico_clinico.html", texto=str(form.get("texto") or ""), migas=MIGAS,
                  ia_disponible=dia.disponible(), modelo=dia.NOMBRE_MODELO)


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
    # Con clave de Anthropic, el caso lo interpreta Fable; si no, o si falla, queda el análisis por reglas
    motor = "reglas" if elegidos is not None else str(form.get("motor") or ("ia" if dia.disponible() else "reglas"))
    ia, error_ia = None, ""
    if motor == "ia" and texto.strip() and not res.faltan_fuentes:
        ref, fuentes = dia.preparar(con, texto)
        try:
            ia = await run_in_threadpool(dia.consultar, ref, fuentes, texto, res)
        except dia.ErrorIA as e:
            error_ia = str(e)
    return pagina(request, con, "paginas/diagnostico_clinico_resultado.html", resultado=res, ia=ia, error_ia=error_ia,
                  ia_disponible=dia.disponible(), modelo=dia.NOMBRE_MODELO,
                  migas=[{"texto": "Diagnóstico", "url": "/diagnostico", "icono": "clipboard-plus"}, {"texto": "Resultado"}])

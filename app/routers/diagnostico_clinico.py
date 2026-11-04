"""Módulo Diagnóstico: caso clínico en texto libre -> diagnósticos y tratamiento según la tabla de jerarquización.

Es un módulo oculto: se ve solo escribiendo /5000 y desaparece al recargar (F5), pero el diagnóstico sigue guardado
hasta que la usuaria lo limpie con «Crear nuevo diagnóstico»: al volver a /5000 está tal como lo dejó.
"""
from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import RedirectResponse

from .. import config
from ..db import obtener_db
from ..errores import ErrorUsuario
from ..services import diagnostico_clinico as dxc
from ..services import recopilaciones as rec
from ..services.recopilaciones import obtener_rdb
from ..web import pagina, redirigir
from .recopilaciones import LOGO, _con_aviso, _descarga

router = APIRouter()
RUTA = config.RUTA_DIAGNOSTICO
WORD = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _resultado(con: sqlite3.Connection) -> dxc.Resultado | None:
    actual = dxc.leer_actual()
    return dxc.analizar(con, actual["texto"], actual.get("elegidos")) if actual else None


def _guardado(con: sqlite3.Connection) -> dxc.Resultado:
    r = _resultado(con)
    if r is None:
        raise ErrorUsuario("Primero analiza un caso.")
    return r


def _titulo(r: dxc.Resultado) -> str:
    return " ".join(f"Diagnóstico {r.paciente or r.motivo}".split())[:100]


@router.get(RUTA)
def modulo(request: Request, con: sqlite3.Connection = Depends(obtener_db)):
    respuesta = pagina(request, con, "paginas/diagnostico_clinico.html", resultado=_resultado(con),
                       migas=[{"texto": "Diagnóstico", "icono": "clipboard-plus"}])
    respuesta.headers["Cache-Control"] = "no-store"   # «Atrás» también pide la página: nunca un diagnóstico ya limpiado
    return respuesta


@router.post("/diagnostico/analizar")
async def analizar(request: Request):
    form = await request.form()
    texto = str(form.get("texto") or "")
    if texto.strip():
        dxc.guardar_actual(texto)
    return redirigir(request, RUTA)


@router.post("/diagnostico/ajustar")
async def ajustar(request: Request):
    """La usuaria quitó o agregó un diagnóstico: la jerarquización se rehace y el ajuste queda guardado."""
    form = await request.form()
    actual = dxc.leer_actual()
    if actual:
        dxc.guardar_actual(actual["texto"], [str(v) for v in form.getlist("dx") if v])
    return redirigir(request, RUTA)


@router.post("/diagnostico/nuevo")
def nuevo(request: Request):
    dxc.limpiar_actual()
    return redirigir(request, RUTA)


@router.post("/diagnostico/recopilar")
def recopilar(con: sqlite3.Connection = Depends(obtener_db), rcon: sqlite3.Connection = Depends(obtener_rdb)):
    r = _guardado(con)
    activa = rec.activa(rcon, crear_si_falta=True)
    rec.agregar_texto_propio(rcon, activa.id, _titulo(r), r.documento)
    n = rec.obtener(rcon, activa.id, False).num_fragmentos
    return _con_aviso(Response(status_code=204), f"El diagnóstico se agregó a «{activa.titulo}» ({n}).")


@router.get("/diagnostico/pdf")
def exportar_pdf(con: sqlite3.Connection = Depends(obtener_db)):
    r = _guardado(con)
    doc = rec.documento_suelto(_titulo(r), r.documento)
    return _descarga(rec.exportar_pdf(doc, LOGO), rec.nombre_archivo(doc, "pdf"), "application/pdf")


@router.get("/diagnostico/word")
def exportar_word(con: sqlite3.Connection = Depends(obtener_db)):
    r = _guardado(con)
    doc = rec.documento_suelto(_titulo(r), r.documento)
    return _descarga(rec.exportar_docx(doc, LOGO), rec.nombre_archivo(doc, "docx"), WORD)


@router.get("/diagnostico", include_in_schema=False)
@router.get("/diagnostico/resultado", include_in_schema=False)
def direccion_anterior():
    return RedirectResponse("/", status_code=303)

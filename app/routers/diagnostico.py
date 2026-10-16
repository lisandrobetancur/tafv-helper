"""Módulo Diagnóstico: independiente de las materias, consulta toda la biblioteca y guarda sus propios casos."""
from __future__ import annotations

import sqlite3
from urllib.parse import urlencode

from fastapi.responses import RedirectResponse
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import JSONResponse

from ..db import obtener_db
from ..services import casos as casos_srv
from ..services import diagnostico as dx
from ..services import notas as notas_srv
from ..services import papelera as pap
from ..web import pagina, parcial, redirigir

router = APIRouter()


def _entero(valor: str | None) -> int | None:
    return int(valor) if valor and valor.isdigit() else None


def _leer(params) -> list[dx.Sintoma]:
    return dx.preparar(params.getlist("s"), params.getlist("imp"))


def _caso_abierto(con: sqlite3.Connection, params) -> casos_srv.Caso | None:
    caso_id = _entero(params.get("caso"))
    if caso_id is None:
        return None
    try:
        return casos_srv.obtener(con, caso_id)
    except casos_srv.NoEncontrado:
        return None


@router.get("/acceso-rapido")
def pagina_diagnostico(request: Request, con: sqlite3.Connection = Depends(obtener_db)):
    sintomas = _leer(request.query_params)
    analisis = dx.analizar(con, sintomas) if sintomas else None
    return pagina(request, con, "paginas/diagnostico.html", analisis=analisis, sintomas=sintomas,
                  caso=_caso_abierto(con, request.query_params), casos=casos_srv.listar(con),
                  migas=[{"texto": "Acceso rápido", "icono": "stethoscope"}])


@router.get("/acceso-rapido/resultado")
def resultado(request: Request, con: sqlite3.Connection = Depends(obtener_db)):
    sintomas = _leer(request.query_params)
    analisis = dx.analizar(con, sintomas) if sintomas else None
    respuesta = parcial(request, "parciales/diagnostico_resultado.html", analisis=analisis,
                        caso=_caso_abierto(con, request.query_params))
    # La dirección de la página refleja el caso, para poder volver a él o guardarlo en favoritos del navegador
    respuesta.headers["HX-Replace-Url"] = "/acceso-rapido?" + urlencode(list(request.query_params.multi_items()))
    return respuesta


@router.get("/acceso-rapido/sugerencias")
def sugerencias(q: str = "", con: sqlite3.Connection = Depends(obtener_db)):
    return JSONResponse(dx.sugerencias(con, q))


# ------------------------------------------------------------------ casos
@router.post("/acceso-rapido/casos")
async def crear_caso(request: Request, con: sqlite3.Connection = Depends(obtener_db)):
    form = await request.form()
    sintomas = _leer(form)
    caso = casos_srv.crear(con, str(form.get("titulo") or ""), sintomas, str(form.get("conclusion") or ""))
    return redirigir(request, f"/acceso-rapido/casos/{caso.id}", "Caso guardado en Acceso rápido.")


@router.get("/acceso-rapido/casos/{caso_id}")
def ver_caso(request: Request, caso_id: int, con: sqlite3.Connection = Depends(obtener_db)):
    caso = casos_srv.obtener(con, caso_id)
    analisis = dx.analizar(con, caso.lista_sintomas)
    return pagina(request, con, "paginas/caso.html", caso=caso, analisis=analisis,
                  resumen_html=notas_srv.renderizar(caso.resumen, "markdown"),
                  migas=[{"texto": "Acceso rápido", "url": "/acceso-rapido", "icono": "stethoscope"},
                         {"texto": "Casos", "url": "/acceso-rapido#casos", "icono": "folder-open"}, {"texto": caso.titulo}])


@router.post("/acceso-rapido/casos/{caso_id}")
def editar_caso(request: Request, caso_id: int, titulo: str = Form(""), conclusion: str = Form(""),
                con: sqlite3.Connection = Depends(obtener_db)):
    caso = casos_srv.editar(con, caso_id, titulo, conclusion)
    return redirigir(request, f"/acceso-rapido/casos/{caso.id}", "Cambios guardados.")


@router.post("/acceso-rapido/casos/{caso_id}/sintomas")
async def actualizar_sintomas(request: Request, caso_id: int, con: sqlite3.Connection = Depends(obtener_db)):
    sintomas = _leer(await request.form())
    caso = casos_srv.actualizar_sintomas(con, caso_id, sintomas)
    return redirigir(request, f"/acceso-rapido/casos/{caso.id}", "Síntomas del caso actualizados.")


@router.get("/acceso-rapido/casos/{caso_id}/eliminar")
def confirmar_eliminar_caso(request: Request, caso_id: int, con: sqlite3.Connection = Depends(obtener_db)):
    caso = casos_srv.obtener(con, caso_id)
    return parcial(request, "parciales/modal_confirmar.html", titulo=f"¿Enviar «{caso.titulo}» a la papelera?",
                   detalle="Podrás restaurarlo desde la papelera mientras no la vacíes.",
                   accion=f"/acceso-rapido/casos/{caso.id}/eliminar", boton="Enviar a la papelera")


@router.post("/acceso-rapido/casos/{caso_id}/eliminar")
def eliminar_caso(request: Request, caso_id: int, con: sqlite3.Connection = Depends(obtener_db)):
    titulo = pap.enviar_caso(con, caso_id)
    return redirigir(request, "/acceso-rapido", f"«{titulo}» se envió a la papelera.")


@router.get("/diagnostico{resto:path}", include_in_schema=False)
def direccion_anterior(request: Request, resto: str = ""):
    """Las direcciones de antes del cambio de nombre llevan a «Acceso rápido» (favoritos, enlaces guardados)."""
    consulta = f"?{request.url.query}" if request.url.query else ""
    return RedirectResponse(f"/acceso-rapido{resto}{consulta}", status_code=301)

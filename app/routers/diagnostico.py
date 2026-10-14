"""Módulo Diagnóstico: independiente de las materias, consulta toda la biblioteca y guarda sus propios casos."""
from __future__ import annotations

import sqlite3
from urllib.parse import urlencode

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


def _leer(params) -> tuple[list[dx.Sintoma], bool]:
    return dx.preparar(params.getlist("s"), params.getlist("imp")), params.get("solo") == "1"


def _caso_abierto(con: sqlite3.Connection, params) -> casos_srv.Caso | None:
    caso_id = _entero(params.get("caso"))
    if caso_id is None:
        return None
    try:
        return casos_srv.obtener(con, caso_id)
    except casos_srv.NoEncontrado:
        return None


@router.get("/diagnostico")
def pagina_diagnostico(request: Request, con: sqlite3.Connection = Depends(obtener_db)):
    sintomas, solo = _leer(request.query_params)
    analisis = dx.analizar(con, sintomas, solo_sintomas=solo) if sintomas else None
    return pagina(request, con, "paginas/diagnostico.html", analisis=analisis, sintomas=sintomas, solo=solo,
                  caso=_caso_abierto(con, request.query_params), casos=casos_srv.listar(con),
                  migas=[{"texto": "Diagnóstico"}])


@router.get("/diagnostico/resultado")
def resultado(request: Request, con: sqlite3.Connection = Depends(obtener_db)):
    sintomas, solo = _leer(request.query_params)
    analisis = dx.analizar(con, sintomas, solo_sintomas=solo) if sintomas else None
    respuesta = parcial(request, "parciales/diagnostico_resultado.html", analisis=analisis,
                        caso=_caso_abierto(con, request.query_params))
    # La dirección de la página refleja el caso, para poder volver a él o guardarlo en favoritos del navegador
    respuesta.headers["HX-Replace-Url"] = "/diagnostico?" + urlencode(list(request.query_params.multi_items()))
    return respuesta


@router.get("/diagnostico/sugerencias")
def sugerencias(q: str = "", con: sqlite3.Connection = Depends(obtener_db)):
    return JSONResponse(dx.sugerencias(con, q))


# ------------------------------------------------------------------ casos
@router.post("/diagnostico/casos")
async def crear_caso(request: Request, con: sqlite3.Connection = Depends(obtener_db)):
    form = await request.form()
    sintomas, solo = _leer(form)
    caso = casos_srv.crear(con, str(form.get("titulo") or ""), sintomas, solo, str(form.get("conclusion") or ""))
    return redirigir(request, f"/diagnostico/casos/{caso.id}", "Caso guardado en Diagnóstico.")


@router.get("/diagnostico/casos/{caso_id}")
def ver_caso(request: Request, caso_id: int, con: sqlite3.Connection = Depends(obtener_db)):
    caso = casos_srv.obtener(con, caso_id)
    analisis = dx.analizar(con, caso.lista_sintomas, solo_sintomas=caso.solo)
    return pagina(request, con, "paginas/caso.html", caso=caso, analisis=analisis,
                  resumen_html=notas_srv.renderizar(caso.resumen, "markdown"),
                  migas=[{"texto": "Diagnóstico", "url": "/diagnostico"}, {"texto": caso.titulo}])


@router.post("/diagnostico/casos/{caso_id}")
def editar_caso(request: Request, caso_id: int, titulo: str = Form(""), conclusion: str = Form(""),
                con: sqlite3.Connection = Depends(obtener_db)):
    caso = casos_srv.editar(con, caso_id, titulo, conclusion)
    return redirigir(request, f"/diagnostico/casos/{caso.id}", "Cambios guardados.")


@router.post("/diagnostico/casos/{caso_id}/sintomas")
async def actualizar_sintomas(request: Request, caso_id: int, con: sqlite3.Connection = Depends(obtener_db)):
    sintomas, solo = _leer(await request.form())
    caso = casos_srv.actualizar_sintomas(con, caso_id, sintomas, solo)
    return redirigir(request, f"/diagnostico/casos/{caso.id}", "Síntomas del caso actualizados.")


@router.get("/diagnostico/casos/{caso_id}/eliminar")
def confirmar_eliminar_caso(request: Request, caso_id: int, con: sqlite3.Connection = Depends(obtener_db)):
    caso = casos_srv.obtener(con, caso_id)
    return parcial(request, "parciales/modal_confirmar.html", titulo=f"¿Enviar «{caso.titulo}» a la papelera?",
                   detalle="Podrás restaurarlo desde la papelera mientras no la vacíes.",
                   accion=f"/diagnostico/casos/{caso.id}/eliminar", boton="Enviar a la papelera")


@router.post("/diagnostico/casos/{caso_id}/eliminar")
def eliminar_caso(request: Request, caso_id: int, con: sqlite3.Connection = Depends(obtener_db)):
    titulo = pap.enviar_caso(con, caso_id)
    return redirigir(request, "/diagnostico", f"«{titulo}» se envió a la papelera.")

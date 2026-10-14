"""Módulo Diagnóstico: síntomas -> candidatos con evidencia, a partir del material de la biblioteca."""
from __future__ import annotations

import sqlite3
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import JSONResponse

from ..db import obtener_db
from ..errores import ErrorUsuario
from ..services import biblioteca as bib
from ..services import busqueda as bus
from ..services import diagnostico as dx
from ..services import notas as notas_srv
from ..web import pagina, parcial, redirigir

router = APIRouter()


def _entero(valor: str | None) -> int | None:
    return int(valor) if valor and valor.isdigit() else None


def _leer(params) -> tuple[list[dx.Sintoma], bus.Filtros, int | None, bool]:
    sintomas = dx.preparar(params.getlist("s"), params.getlist("imp"))
    filtros = bus.Filtros(materia=_entero(params.get("materia")))
    return sintomas, filtros, _entero(params.get("tabla")), params.get("solo") == "1"


def _opciones(con: sqlite3.Connection) -> dict:
    tablas = con.execute(
        """SELECT t.id, t.nombre, m.nombre AS materia FROM tablas t JOIN componentes c ON c.id = t.componente_id
           JOIN materias m ON m.id = c.materia_id
           WHERE t.papelera_id IS NULL AND c.papelera_id IS NULL AND m.papelera_id IS NULL
           ORDER BY m.orden, m.nombre, t.nombre""").fetchall()
    destinos = []
    for f in con.execute("""SELECT c.id FROM componentes c JOIN materias m ON m.id = c.materia_id
                            WHERE c.papelera_id IS NULL AND m.papelera_id IS NULL AND c.tipos LIKE '%notas%'
                            ORDER BY m.orden, c.orden"""):
        comp = bib.obtener_componente(con, f["id"])
        m = bib.obtener_materia(con, comp.materia_id)
        destinos.append((comp.id, " › ".join([m.nombre, *(a.nombre for a in bib.ancestros(con, comp)), comp.nombre])))
    return {"materias": bib.listar_materias(con, archivadas=None), "tablas": tablas, "destinos": destinos}


@router.get("/diagnostico")
def pagina_diagnostico(request: Request, con: sqlite3.Connection = Depends(obtener_db)):
    sintomas, filtros, tabla_id, solo = _leer(request.query_params)
    analisis = dx.analizar(con, sintomas, filtros, tabla_id, solo) if sintomas else None
    return pagina(request, con, "paginas/diagnostico.html", analisis=analisis, sintomas=sintomas, filtros=filtros,
                  tabla_id=tabla_id, solo=solo, migas=[{"texto": "Diagnóstico"}], **_opciones(con))


@router.get("/diagnostico/resultado")
def resultado(request: Request, con: sqlite3.Connection = Depends(obtener_db)):
    sintomas, filtros, tabla_id, solo = _leer(request.query_params)
    analisis = dx.analizar(con, sintomas, filtros, tabla_id, solo) if sintomas else None
    respuesta = parcial(request, "parciales/diagnostico_resultado.html", analisis=analisis, **_opciones(con))
    # La dirección de la página refleja el caso, para poder volver a él o guardarlo en favoritos del navegador
    respuesta.headers["HX-Replace-Url"] = "/diagnostico?" + urlencode(list(request.query_params.multi_items()))
    return respuesta


@router.get("/diagnostico/sugerencias")
def sugerencias(q: str = "", con: sqlite3.Connection = Depends(obtener_db)):
    return JSONResponse(dx.sugerencias(con, q))


@router.post("/diagnostico/guardar")
async def guardar(request: Request, con: sqlite3.Connection = Depends(obtener_db)):
    form = await request.form()
    sintomas, filtros, tabla_id, solo = _leer(form)
    componente_id = _entero(str(form.get("componente_id") or ""))
    if not sintomas:
        raise ErrorUsuario("Agrega al menos un síntoma antes de guardar el caso.")
    if not componente_id:
        raise ErrorUsuario("Elige en qué componente guardar el caso.")
    analisis = dx.analizar(con, sintomas, filtros, tabla_id, solo)
    titulo = " ".join(str(form.get("titulo") or "").split()) or "Caso: " + ", ".join(s.texto for s in sintomas)[:100]
    nota = notas_srv.crear(con, componente_id, titulo, dx.nota_markdown(analisis), "markdown", "caso, diagnóstico")
    return redirigir(request, f"/notas/{nota.id}", "Caso guardado como nota.")


from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Request

from ..db import obtener_db
from ..services import biblioteca as bib
from ..services import bloqueo
from ..services import papelera as pap
from ..web import pagina, parcial, redirigir, templates

router = APIRouter()


@router.get("/")
def inicio(request: Request, con: sqlite3.Connection = Depends(obtener_db)):
    return pagina(request, con, "paginas/inicio.html",
                  materias=bib.listar_materias(con), archivadas=bib.listar_materias(con, archivadas=True))


# -------------------------------------------------------------------- papelera
@router.get("/papelera")
def papelera(request: Request, con: sqlite3.Connection = Depends(obtener_db)):
    return pagina(request, con, "paginas/papelera.html", elementos=pap.listar(con), migas=[{"texto": "Papelera"}])


@router.post("/papelera/{pid}/restaurar")
def restaurar(request: Request, pid: int, con: sqlite3.Connection = Depends(obtener_db)):
    nombre = pap.restaurar(con, pid)
    return redirigir(request, "/papelera", f"«{nombre}» se restauró.")


@router.get("/papelera/{pid}/eliminar")
def confirmar_eliminar(request: Request, pid: int, con: sqlite3.Connection = Depends(obtener_db)):
    f = next((e for e in pap.listar(con) if e.id == pid), None)
    nombre = f.nombre if f else "este elemento"
    return parcial(request, "parciales/modal_confirmar.html", titulo=f"¿Eliminar «{nombre}» para siempre?",
                   detalle="Se borrarán también sus archivos. Esta acción no se puede deshacer.",
                   accion=f"/papelera/{pid}/eliminar", boton="Eliminar para siempre", peligro=True)


@router.post("/papelera/{pid}/eliminar")
def eliminar(request: Request, pid: int, con: sqlite3.Connection = Depends(obtener_db)):
    nombre = pap.eliminar_definitivo(con, pid)
    return redirigir(request, "/papelera", f"«{nombre}» se eliminó definitivamente.")


@router.get("/papelera/vaciar")
def confirmar_vaciar(request: Request, con: sqlite3.Connection = Depends(obtener_db)):
    n = pap.contar(con)
    return parcial(request, "parciales/modal_confirmar.html", titulo="¿Vaciar la papelera?",
                   detalle=f"Se borrarán para siempre {n} elemento{'s' if n != 1 else ''} y sus archivos. "
                           "Esta acción no se puede deshacer.",
                   accion="/papelera/vaciar", boton="Vaciar papelera", peligro=True)


@router.post("/papelera/vaciar")
def vaciar(request: Request, con: sqlite3.Connection = Depends(obtener_db)):
    n = pap.vaciar(con)
    return redirigir(request, "/papelera", f"Papelera vaciada ({n} elemento{'s' if n != 1 else ''}).")


# --------------------------------------------------------------------- bloqueo
@router.get("/bloqueo")
def aviso_bloqueo(request: Request):
    estado = request.app.state.bloqueo
    if estado.libre:
        return redirigir(request, "/")
    return templates.TemplateResponse(request, "paginas/bloqueo.html",
                                      {"equipo": estado.equipo, "desde": estado.desde.replace("T", " a las ")})


@router.post("/bloqueo/forzar")
def forzar_bloqueo(request: Request):
    request.app.state.bloqueo = bloqueo.adquirir(forzar=True)
    return redirigir(request, "/", "Abriste la biblioteca en este equipo. Recuerda no usarla en el otro a la vez.", "aviso")

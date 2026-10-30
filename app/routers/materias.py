from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Body, Depends, Form, Request

from ..db import obtener_db
from ..errores import ErrorUsuario
from ..services import biblioteca as bib
from ..services import explorar as exp
from ..services import papelera as pap
from ..web import aviso, pagina, parcial, redirigir

router = APIRouter(prefix="/materias")


@router.get("/nueva")
def formulario_nueva(request: Request):
    return parcial(request, "parciales/modal_materia.html", materia=None, valores={"color": "rojo", "icono": "book-open"})


@router.post("")
def crear(request: Request, nombre: str = Form(""), descripcion: str = Form(""), color: str = Form(""),
          icono: str = Form(""), con: sqlite3.Connection = Depends(obtener_db)):
    valores = {"nombre": nombre, "descripcion": descripcion, "color": color, "icono": icono}
    try:
        mid = bib.crear_materia(con, nombre, descripcion, color, icono)
    except ErrorUsuario as e:
        return parcial(request, "parciales/modal_materia.html", materia=None, valores=valores, error=e.mensaje)
    return redirigir(request, f"/materias/{mid}", f"Materia «{' '.join(nombre.split())}» creada.")


@router.post("/orden")
def reordenar(ids: list[int] = Body(..., embed=True), con: sqlite3.Connection = Depends(obtener_db)):
    bib.reordenar_materias(con, ids)
    return aviso("Orden guardado.")


@router.get("/{materia_id}")
def ver(request: Request, materia_id: int, con: sqlite3.Connection = Depends(obtener_db)):
    m = bib.obtener_materia(con, materia_id)
    return pagina(request, con, "paginas/materia.html", materia=m, componentes=bib.arbol(con, m.id),
                  migas=[{"texto": m.nombre, "icono": m.icono, "color": m.color_hex}], materia_activa=m.id)


@router.get("/{materia_id}/explorar")
def explorar(request: Request, materia_id: int, c: int | None = None, ver: str | None = None, con: sqlite3.Connection = Depends(obtener_db)):
    """Pestaña para leer y navegar todo el material de la materia (sin las herramientas de carga)."""
    m = bib.obtener_materia(con, materia_id)
    entradas = exp.indice(con, m.id)
    if c is None:  # por defecto, el primer componente con contenido
        c = next((e.componente.id for e in entradas if not e.vacio), entradas[0].componente.id if entradas else None)
    lectura = exp.leer(con, entradas, c, ver) if c is not None else None
    migas = [{"texto": m.nombre, "url": f"/materias/{m.id}", "icono": m.icono, "color": m.color_hex},
             {"texto": "Explorar", "icono": "book-open"}]
    return pagina(request, con, "paginas/explorar.html", materia=m, entradas=entradas, lectura=lectura,
                  migas=migas, materia_activa=m.id)


@router.get("/{materia_id}/editar")
def formulario_editar(request: Request, materia_id: int, con: sqlite3.Connection = Depends(obtener_db)):
    m = bib.obtener_materia(con, materia_id)
    return parcial(request, "parciales/modal_materia.html", materia=m,
                   valores={"nombre": m.nombre, "descripcion": m.descripcion, "color": m.color, "icono": m.icono})


@router.post("/{materia_id}")
def editar(request: Request, materia_id: int, nombre: str = Form(""), descripcion: str = Form(""),
           color: str = Form(""), icono: str = Form(""), con: sqlite3.Connection = Depends(obtener_db)):
    m = bib.obtener_materia(con, materia_id)
    valores = {"nombre": nombre, "descripcion": descripcion, "color": color, "icono": icono}
    try:
        bib.editar_materia(con, materia_id, nombre, descripcion, color, icono)
    except ErrorUsuario as e:
        return parcial(request, "parciales/modal_materia.html", materia=m, valores=valores, error=e.mensaje)
    return redirigir(request, f"/materias/{materia_id}", "Cambios guardados.")


@router.post("/{materia_id}/en-busqueda")
def en_busqueda(request: Request, materia_id: int, activo: bool = Form(False), con: sqlite3.Connection = Depends(obtener_db)):
    m = bib.poner_en_busqueda(con, materia_id, activo)
    return redirigir(request, f"/materias/{materia_id}",
                     f"«{m.nombre}» {'ahora sale' if activo else 'ya no sale'} en la búsqueda y en Acceso rápido.")


@router.post("/{materia_id}/archivar")
def archivar(request: Request, materia_id: int, archivar: bool = Form(True), con: sqlite3.Connection = Depends(obtener_db)):
    m = bib.archivar_materia(con, materia_id, archivar)
    if archivar:
        return redirigir(request, "/", f"«{m.nombre}» se archivó. La encuentras al final del inicio.")
    return redirigir(request, f"/materias/{materia_id}", f"«{m.nombre}» vuelve a estar activa.")


@router.get("/{materia_id}/eliminar")
def confirmar_eliminar(request: Request, materia_id: int, con: sqlite3.Connection = Depends(obtener_db)):
    m = bib.obtener_materia(con, materia_id)
    return parcial(request, "parciales/modal_confirmar.html",
                   titulo=f"¿Enviar «{m.nombre}» a la papelera?",
                   detalle=_detalle(con.execute("SELECT COUNT(*) FROM componentes WHERE materia_id=? AND papelera_id IS NULL",
                                                (m.id,)).fetchone()[0], bib.contar_elementos_materia(con, m.id)),
                   accion=f"/materias/{m.id}/eliminar", boton="Enviar a la papelera")


@router.post("/{materia_id}/eliminar")
def eliminar(request: Request, materia_id: int, con: sqlite3.Connection = Depends(obtener_db)):
    nombre = pap.enviar_materia(con, materia_id)
    return redirigir(request, "/", f"«{nombre}» se envió a la papelera. Puedes restaurarla desde allí.")


def _detalle(componentes: int, elementos: int) -> str:
    partes = []
    if componentes:
        partes.append(f"{componentes} componente{'s' if componentes != 1 else ''}")
    if elementos:
        partes.append(f"{elementos} elemento{'s' if elementos != 1 else ''}")
    contenido = f"Incluye {' y '.join(partes)}. " if partes else ""
    return contenido + "Todo se moverá a la papelera y podrás restaurarlo mientras no la vacíes."

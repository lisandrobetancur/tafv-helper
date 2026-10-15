from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Body, Depends, Form, Request

from ..config import PROFUNDIDAD_MAXIMA
from ..db import obtener_db
from ..errores import ErrorUsuario
from ..services import biblioteca as bib
from ..services import papelera as pap
from ..services import imagenes as servicio_imagenes
from ..services import notas as servicio_notas
from ..services import pdfs as servicio_pdfs
from ..services import tablas as tab
from ..web import aviso, pagina, parcial, redirigir

router = APIRouter()


def _url(c) -> str:
    return f"/componentes/{c.id}"


@router.get("/materias/{materia_id}/componentes/nuevo")
def formulario_nuevo(request: Request, materia_id: int, padre: int | None = None,
                     con: sqlite3.Connection = Depends(obtener_db)):
    m = bib.obtener_materia(con, materia_id)
    padre_c = bib.obtener_componente(con, padre) if padre else None
    return parcial(request, "parciales/modal_componente.html", materia=m, padre=padre_c, componente=None,
                   valores={"tipos": ["excel", "pdf", "imagenes", "notas"]})


@router.post("/materias/{materia_id}/componentes")
def crear(request: Request, materia_id: int, nombre: str = Form(""), descripcion: str = Form(""),
          tipos: list[str] = Form(default=[]), padre_id: int | None = Form(None),
          con: sqlite3.Connection = Depends(obtener_db)):
    m = bib.obtener_materia(con, materia_id)
    try:
        cid = bib.crear_componente(con, materia_id, padre_id, nombre, descripcion, tipos)
    except ErrorUsuario as e:
        padre_c = bib.obtener_componente(con, padre_id) if padre_id else None
        return parcial(request, "parciales/modal_componente.html", materia=m, padre=padre_c, componente=None,
                       valores={"nombre": nombre, "descripcion": descripcion, "tipos": tipos}, error=e.mensaje)
    que = "Subcomponente" if padre_id else "Componente"
    return redirigir(request, f"/componentes/{cid}", f"{que} «{' '.join(nombre.split())}» creado.")


@router.post("/componentes/orden")
def reordenar(materia_id: int = Body(...), padre_id: int | None = Body(None), ids: list[int] = Body(...),
              con: sqlite3.Connection = Depends(obtener_db)):
    bib.reordenar_componentes(con, materia_id, padre_id, ids)
    return aviso("Orden guardado.")


@router.get("/componentes/{componente_id}")
def ver(request: Request, componente_id: int, con: sqlite3.Connection = Depends(obtener_db)):
    c = bib.obtener_componente(con, componente_id)
    m = bib.obtener_materia(con, c.materia_id)
    cadena = bib.ancestros(con, c)
    nivel = len(cadena) + 1
    migas = [{"texto": m.nombre, "url": f"/materias/{m.id}"}]
    migas += [{"texto": a.nombre, "url": _url(a)} for a in cadena]
    migas.append({"texto": c.nombre})
    tablas = tab.listar(con, c.id) if "excel" in c.tipos else []
    from ..services import etiquetas as etq
    return pagina(request, con, "paginas/componente.html", materia=m, componente=c, ancestros=cadena,
                  subcomponentes=bib.arbol(con, m.id, c.id, nivel + 1), nivel=nivel,
                  puede_anidar=nivel < PROFUNDIDAD_MAXIMA, migas=migas, materia_activa=m.id,
                  tablas=tablas, etiquetas_tablas=etq.de_varios(con, "tabla", [t.id for t in tablas]),
                  pdfs=servicio_pdfs.listar(con, c.id) if "pdf" in c.tipos else [],
                  imagenes=servicio_imagenes.listar(con, c.id) if "imagenes" in c.tipos else [],
                  etiquetas_usadas=servicio_imagenes.etiquetas_del_componente(con, c.id) if "imagenes" in c.tipos else [],
                  notas=servicio_notas.listar(con, c.id) if "notas" in c.tipos else [])


@router.get("/componentes/{componente_id}/editar")
def formulario_editar(request: Request, componente_id: int, con: sqlite3.Connection = Depends(obtener_db)):
    c = bib.obtener_componente(con, componente_id)
    m = bib.obtener_materia(con, c.materia_id)
    return parcial(request, "parciales/modal_componente.html", materia=m, padre=None, componente=c,
                   valores={"nombre": c.nombre, "descripcion": c.descripcion, "tipos": c.tipos})


@router.post("/componentes/{componente_id}")
def editar(request: Request, componente_id: int, nombre: str = Form(""), descripcion: str = Form(""),
           tipos: list[str] = Form(default=[]), con: sqlite3.Connection = Depends(obtener_db)):
    c = bib.obtener_componente(con, componente_id)
    try:
        bib.editar_componente(con, componente_id, nombre, descripcion, tipos)
    except ErrorUsuario as e:
        m = bib.obtener_materia(con, c.materia_id)
        return parcial(request, "parciales/modal_componente.html", materia=m, padre=None, componente=c,
                       valores={"nombre": nombre, "descripcion": descripcion, "tipos": tipos}, error=e.mensaje)
    return redirigir(request, _url(c), "Cambios guardados.")


@router.get("/componentes/{componente_id}/eliminar")
def confirmar_eliminar(request: Request, componente_id: int, con: sqlite3.Connection = Depends(obtener_db)):
    c = bib.obtener_componente(con, componente_id)
    subs = len(bib.descendientes(con, c.id))
    elementos = bib.contar_elementos_componente(con, c.id) + sum(
        bib.contar_elementos_componente(con, d) for d in bib.descendientes(con, c.id))
    partes = []
    if subs:
        partes.append(f"{subs} subcomponente{'s' if subs != 1 else ''}")
    if elementos:
        partes.append(f"{elementos} elemento{'s' if elementos != 1 else ''}")
    detalle = (f"Incluye {' y '.join(partes)}. " if partes else "") + \
        "Todo se moverá a la papelera y podrás restaurarlo mientras no la vacíes."
    return parcial(request, "parciales/modal_confirmar.html", titulo=f"¿Enviar «{c.nombre}» a la papelera?",
                   detalle=detalle, accion=f"/componentes/{c.id}/eliminar", boton="Enviar a la papelera")


@router.post("/componentes/{componente_id}/eliminar")
def eliminar(request: Request, componente_id: int, con: sqlite3.Connection = Depends(obtener_db)):
    nombre, materia_id, padre_id = pap.enviar_componente(con, componente_id)
    destino = f"/componentes/{padre_id}" if padre_id else f"/materias/{materia_id}"
    return redirigir(request, destino, f"«{nombre}» se envió a la papelera.")

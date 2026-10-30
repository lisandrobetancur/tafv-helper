"""Favoritos, etiquetas de filas y PDF, modo repaso, mantenimiento y respaldos."""
from __future__ import annotations

import json
import sqlite3

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import FileResponse

from .. import db
from ..config import rutas
from ..db import obtener_db
from ..errores import ErrorUsuario
from ..services import biblioteca as bib
from ..services import busqueda as bus
from ..services import etiquetas as etq
from ..services import favoritos as fav
from ..services import imagenes as img_srv
from ..services import miniaturas, ocr, pdfs, repaso, respaldos
from ..services import tablas as tab
from ..services.bloqueo import nombre_equipo
from ..web import pagina, parcial, redirigir
from .tablas import _migas_componente, guardar_subida

router = APIRouter()


# ================================================================ favoritos
@router.post("/favoritos/{tipo}/{ref_id}")
def alternar_favorito(request: Request, tipo: str, ref_id: int, con: sqlite3.Connection = Depends(obtener_db)):
    activo = fav.alternar(con, tipo, ref_id)
    respuesta = parcial(request, "parciales/estrella.html", tipo=tipo, ref_id=ref_id, activo=activo)
    respuesta.headers["HX-Trigger"] = json.dumps({"aviso": {"mensaje": "Agregado a favoritos." if activo else "Quitado de favoritos.",
                                                            "tipo": "exito"}}, ensure_ascii=False)
    return respuesta


@router.post("/favoritos/limpiar")
def limpiar_favoritos(request: Request, con: sqlite3.Connection = Depends(obtener_db)):
    fav.limpiar_favoritos(con)
    return redirigir(request, "/", "Se quitaron todos los favoritos.")


@router.post("/recientes/limpiar")
def limpiar_recientes(request: Request, con: sqlite3.Connection = Depends(obtener_db)):
    fav.limpiar_recientes(con)
    return redirigir(request, "/", "Se limpió la lista de abiertos recientemente.")


# ========================================== etiquetas de filas, PDF y tablas
@router.post("/etiquetas/{tipo}/{ref_id}")
def guardar_etiquetas(request: Request, tipo: str, ref_id: int, etiquetas: str = Form(""),
                      con: sqlite3.Connection = Depends(obtener_db)):
    if tipo == "fila":
        tab.obtener_fila(con, ref_id)
    elif tipo == "pdf":
        pdfs.obtener(con, ref_id)
    elif tipo == "tabla":
        tab.obtener(con, ref_id)
    else:
        raise ErrorUsuario("Este elemento no admite etiquetas aquí.")
    nombres = etq.asignar(con, tipo, ref_id, etiquetas)
    etq.limpiar_huerfanas(con)
    respuesta = parcial(request, "parciales/etiquetas_editor.html", tipo=tipo, ref_id=ref_id, etiquetas=nombres)
    respuesta.headers["HX-Trigger"] = json.dumps({"aviso": {"mensaje": "Etiquetas guardadas.", "tipo": "exito"}}, ensure_ascii=False)
    return respuesta


# =============================================================== modo repaso
@router.get("/tablas/{tabla_id}/repaso")
def configurar_repaso(request: Request, tabla_id: int, con: sqlite3.Connection = Depends(obtener_db)):
    t = tab.obtener(con, tabla_id)
    comp = bib.obtener_componente(con, t.componente_id)
    otras = [c["clave"] for c in t.columnas if c["clave"] != t.columna_titulo]
    return pagina(request, con, "paginas/repaso_configurar.html", tabla=t, resumen=repaso.resumen(con, t.id),
                  cuales=repaso.CUALES, frente=t.columna_titulo, reverso=otras[0] if otras else "",
                  materia_activa=comp.materia_id,
                  migas=_migas_componente(con, comp.id, "excel") + [{"texto": t.nombre, "url": f"/tablas/{t.id}", "icono": "table"},
                                                                    {"texto": "Repaso", "icono": "graduation-cap"}])


@router.get("/tablas/{tabla_id}/repaso/sesion")
def sesion_repaso(request: Request, tabla_id: int, frente: str = "", reverso: str = "", cuales: str = "todas",
                  barajar: bool = False, imagenes: bool = False, con: sqlite3.Connection = Depends(obtener_db)):
    t = tab.obtener(con, tabla_id)
    tarjetas = repaso.tarjetas(con, t, frente, reverso, cuales if cuales in repaso.CUALES else "todas", barajar, imagenes)
    comp = bib.obtener_componente(con, t.componente_id)
    return pagina(request, con, "paginas/repaso.html", tabla=t, tarjetas=tarjetas,
                  nombre_frente=t.nombre_columna(frente), nombre_reverso=t.nombre_columna(reverso),
                  materia_activa=comp.materia_id,
                  migas=_migas_componente(con, comp.id, "excel") + [{"texto": t.nombre, "url": f"/tablas/{t.id}", "icono": "table"},
                                                                    {"texto": "Repaso", "url": f"/tablas/{t.id}/repaso", "icono": "graduation-cap"},
                                                                    {"texto": "Sesión"}])


@router.post("/repaso/{fila_id}")
def marcar_tarjeta(fila_id: int, estado: str = Form(...), con: sqlite3.Connection = Depends(obtener_db)):
    repaso.marcar(con, fila_id, estado)
    return {"ok": True}


@router.post("/tablas/{tabla_id}/repaso/reiniciar")
def reiniciar_repaso(request: Request, tabla_id: int, con: sqlite3.Connection = Depends(obtener_db)):
    tab.obtener(con, tabla_id)
    repaso.reiniciar(con, tabla_id)
    return redirigir(request, f"/tablas/{tabla_id}/repaso", "Se borraron las marcas de «lo sé» y «repasar» de esta tabla.")


# ============================================================= mantenimiento
@router.get("/mantenimiento")
def mantenimiento(request: Request, con: sqlite3.Connection = Depends(obtener_db)):
    documentos = con.execute("SELECT COUNT(*) FROM busqueda").fetchone()[0]
    errores_ocr = con.execute("SELECT COUNT(*) FROM pdf_paginas WHERE ocr_error IS NOT NULL AND ocr_pendiente = 0").fetchone()[0] + \
        con.execute("SELECT COUNT(*) FROM imagenes WHERE ocr_estado = 'error'").fetchone()[0]
    return pagina(request, con, "paginas/mantenimiento.html", respaldos=respaldos.listar(),
                  tamano=respaldos.tamano_biblioteca(), documentos=documentos, equipo=nombre_equipo(),
                  carpeta=str(rutas.datos), errores_ocr=errores_ocr,
                  ocr_pendiente=pdfs.ocr_pendiente_total(con) + img_srv.ocr_pendientes(con),
                  migas=[{"texto": "Mantenimiento", "icono": "settings"}])


@router.post("/mantenimiento/indice")
def reconstruir_indice(request: Request, con: sqlite3.Connection = Depends(obtener_db)):
    n = bus.reconstruir(con)
    return redirigir(request, "/mantenimiento", f"Índice de búsqueda reconstruido ({n} elementos).")


@router.post("/mantenimiento/miniaturas")
def regenerar_miniaturas(request: Request):
    miniaturas.regenerar_todas()
    return redirigir(request, "/mantenimiento", "Miniaturas borradas: se volverán a crear al verlas.")


@router.post("/mantenimiento/ocr")
def reintentar_ocr(request: Request, con: sqlite3.Connection = Depends(obtener_db)):
    n = con.execute("UPDATE pdf_paginas SET ocr_pendiente=1, ocr_error=NULL WHERE ocr_error IS NOT NULL").rowcount
    n += con.execute("UPDATE imagenes SET ocr_estado='pendiente', ocr_error=NULL WHERE ocr_estado='error'").rowcount
    ocr.avisar_trabajo()
    return redirigir(request, "/mantenimiento", f"Se reintentará el OCR de {n} elemento{'s' if n != 1 else ''}.")


# ================================================================ respaldos
@router.post("/respaldos")
def crear_respaldo(request: Request):
    r = respaldos.crear()
    return redirigir(request, "/mantenimiento", f"Respaldo creado: {r.nombre} ({r.tamano}).")


@router.get("/respaldos/{nombre}")
def descargar_respaldo(nombre: str):
    ruta = respaldos.obtener(nombre)
    return FileResponse(ruta, media_type="application/zip", filename=ruta.name)


def _restaurar(request: Request, ruta) -> object:
    estado_ocr = request.app.state.ocr_activo
    previo = respaldos.restaurar(ruta, antes_de_cambiar=ocr.detener)
    if estado_ocr:
        ocr.iniciar(db.conectar)
    return redirigir(request, "/", f"Biblioteca restaurada. Por si acaso, el estado anterior quedó guardado en {previo.nombre}.")


@router.get("/respaldos/{nombre}/restaurar")
def confirmar_restaurar(request: Request, nombre: str):
    respaldos.obtener(nombre)
    return parcial(request, "parciales/modal_confirmar.html", titulo=f"¿Restaurar «{nombre}»?",
                   detalle="La biblioteca actual se reemplazará por la de este respaldo. Antes se guardará "
                           "automáticamente un respaldo del estado actual, por si necesitas volver atrás.",
                   accion=f"/respaldos/{nombre}/restaurar", boton="Restaurar", peligro=True)


@router.post("/respaldos/{nombre}/restaurar")
def restaurar_respaldo(request: Request, nombre: str):
    return _restaurar(request, respaldos.obtener(nombre))


@router.post("/respaldos/subir")
async def restaurar_desde_archivo(request: Request, archivo: UploadFile = File(...)):
    if not (archivo.filename or "").lower().endswith(".zip"):
        raise ErrorUsuario("Elige un archivo .zip de respaldo.")
    tmp = await guardar_subida(archivo, 20 * 1024 * 1024 * 1024)
    try:
        return _restaurar(request, tmp)
    finally:
        tmp.unlink(missing_ok=True)


@router.get("/respaldos/{nombre}/eliminar")
def confirmar_eliminar_respaldo(request: Request, nombre: str):
    respaldos.obtener(nombre)
    return parcial(request, "parciales/modal_confirmar.html", titulo=f"¿Eliminar el respaldo «{nombre}»?",
                   detalle="Se borrará este archivo de respaldo. Tu biblioteca no cambia.",
                   accion=f"/respaldos/{nombre}/eliminar", boton="Eliminar respaldo", peligro=True)


@router.post("/respaldos/{nombre}/eliminar")
def eliminar_respaldo(request: Request, nombre: str):
    respaldos.eliminar(nombre)
    return redirigir(request, "/mantenimiento", "Respaldo eliminado.")

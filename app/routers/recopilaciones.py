"""Recopilaciones: capturar fragmentos desde cualquier página, ordenarlos, revisarlos y exportarlos."""
from __future__ import annotations

import io
import json
import sqlite3
from urllib.parse import quote

from fastapi import APIRouter, Body, Depends, Form, Request
from fastapi.responses import FileResponse, HTMLResponse, Response

from .. import config
from ..db import obtener_db
from ..errores import ErrorUsuario
from ..services import pdfs as pdf_srv
from ..services import recopilaciones as rec
from ..services.recopilaciones import obtener_rdb
from ..web import pagina, parcial, redirigir

router = APIRouter()
LOGO = config.STATIC_DIR / "marca" / "logo-corpas.png"


def _con_aviso(respuesta: Response, mensaje: str, tipo: str = "exito", cerrar_modal: bool = False) -> Response:
    disparos = {"aviso": {"mensaje": mensaje, "tipo": tipo}, "recopilacion-cambio": True}
    if cerrar_modal:
        disparos["cerrar-modal"] = True
    # ensure_ascii: los títulos pueden traer caracteres que no caben en una cabecera HTTP (—, ›…)
    respuesta.headers["HX-Trigger"] = json.dumps(disparos)
    return respuesta


def _lista(request: Request, rcon: sqlite3.Connection, rid: int, mensaje: str | None = None) -> Response:
    r = rec.obtener(rcon, rid)
    respuesta = parcial(request, "parciales/recopilacion_lista.html", recopilacion=r)
    return _con_aviso(respuesta, mensaje, cerrar_modal=True) if mensaje else respuesta


# ================================================================== páginas
@router.get("/recopilaciones")
def listar(request: Request, con: sqlite3.Connection = Depends(obtener_db), rcon: sqlite3.Connection = Depends(obtener_rdb)):
    return pagina(request, con, "paginas/recopilaciones.html", recopilaciones=rec.listar(rcon), activa_id=rec.activa_id(rcon),
                  migas=[{"texto": "Recopilaciones", "icono": "clipboard-list"}])


@router.get("/recopilaciones/nueva")
def nueva(request: Request):
    return parcial(request, "parciales/modal_recopilacion.html", accion="/recopilaciones", titulo="Nueva recopilación",
                   recopilacion=None)


@router.post("/recopilaciones")
def crear(request: Request, titulo: str = Form(""), descripcion: str = Form(""),
          rcon: sqlite3.Connection = Depends(obtener_rdb)):
    r = rec.crear(rcon, titulo, descripcion)
    return redirigir(request, f"/recopilaciones/{r.id}", f"Recopilación «{r.titulo}» creada. Lo que agregues irá aquí.")


@router.get("/recopilaciones/activa")
def ir_a_activa(request: Request, rcon: sqlite3.Connection = Depends(obtener_rdb)):
    r = rec.activa(rcon)
    return redirigir(request, f"/recopilaciones/{r.id}" if r else "/recopilaciones")


@router.get("/recopilaciones/{rid}")
def ver(request: Request, rid: int, con: sqlite3.Connection = Depends(obtener_db),
        rcon: sqlite3.Connection = Depends(obtener_rdb)):
    r = rec.obtener(rcon, rid)
    return pagina(request, con, "paginas/recopilacion.html", recopilacion=r, es_activa=rec.activa_id(rcon) == r.id,
                  migas=[{"texto": "Recopilaciones", "url": "/recopilaciones", "icono": "clipboard-list"}, {"texto": r.titulo}])


@router.post("/recopilaciones/{rid}/activar")
def activar(request: Request, rid: int, rcon: sqlite3.Connection = Depends(obtener_rdb)):
    r = rec.obtener(rcon, rid, False)
    rec.activar(rcon, rid)
    destino = request.headers.get("HX-Current-URL", "")
    return redirigir(request, "/recopilaciones" if destino.rstrip("/").endswith("/recopilaciones") else f"/recopilaciones/{rid}",
                     f"Lo que agregues desde ahora irá a «{r.titulo}».")


@router.get("/recopilaciones/{rid}/editar")
def editar_form(request: Request, rid: int, rcon: sqlite3.Connection = Depends(obtener_rdb)):
    return parcial(request, "parciales/modal_recopilacion.html", accion=f"/recopilaciones/{rid}", titulo="Cambiar nombre y descripción",
                   recopilacion=rec.obtener(rcon, rid, False))


@router.post("/recopilaciones/{rid}")
def editar(request: Request, rid: int, titulo: str = Form(""), descripcion: str = Form(""),
           rcon: sqlite3.Connection = Depends(obtener_rdb)):
    rec.editar(rcon, rid, titulo, descripcion)
    return redirigir(request, f"/recopilaciones/{rid}", "Cambios guardados.")


@router.get("/recopilaciones/{rid}/eliminar")
def confirmar_eliminar(request: Request, rid: int, rcon: sqlite3.Connection = Depends(obtener_rdb)):
    r = rec.obtener(rcon, rid, False)
    return parcial(request, "parciales/modal_confirmar.html", titulo=f"¿Eliminar «{r.titulo}»?",
                   detalle=f"Se borrará esta recopilación con sus {r.num_fragmentos} fragmentos. No se puede deshacer. "
                           "El material de la biblioteca no cambia.",
                   accion=f"/recopilaciones/{rid}/eliminar", boton="Eliminar recopilación", peligro=True)


@router.post("/recopilaciones/{rid}/eliminar")
def eliminar(request: Request, rid: int, rcon: sqlite3.Connection = Depends(obtener_rdb)):
    rec.eliminar(rcon, rid)
    return redirigir(request, "/recopilaciones", "Recopilación eliminada.")


# ============================================================ fragmentos
@router.post("/recopilaciones/{rid}/orden")
def ordenar(rid: int, ids: list[int] = Body(..., embed=True), rcon: sqlite3.Connection = Depends(obtener_rdb)):
    rec.ordenar(rcon, rid, ids)
    return {"ok": True}


@router.post("/fragmentos/{fid}/mover")
def mover(request: Request, fid: int, paso: int = Form(...), rcon: sqlite3.Connection = Depends(obtener_rdb)):
    return _lista(request, rcon, rec.mover(rcon, fid, paso))


@router.post("/fragmentos/{fid}/eliminar")
def quitar(request: Request, fid: int, rcon: sqlite3.Connection = Depends(obtener_rdb)):
    return _lista(request, rcon, rec.eliminar_fragmento(rcon, fid), "Fragmento quitado.")


@router.get("/fragmentos/{fid}/editar")
def editar_fragmento_form(request: Request, fid: int, rcon: sqlite3.Connection = Depends(obtener_rdb)):
    return parcial(request, "parciales/modal_fragmento.html", fragmento=rec.obtener_fragmento(rcon, fid), tamanos=rec.TAMANOS)


@router.post("/fragmentos/{fid}")
def editar_fragmento(request: Request, fid: int, titulo: str = Form(""), comentario: str = Form(""),
                     contenido: str | None = Form(None), tamano: str | None = Form(None),
                     rcon: sqlite3.Connection = Depends(obtener_rdb)):
    fr = rec.editar_fragmento(rcon, fid, titulo, comentario, contenido, tamano)
    return _lista(request, rcon, fr.recopilacion_id, "Fragmento guardado.")


@router.get("/recopilaciones/{rid}/texto")
def texto_propio_form(request: Request, rid: int, tipo: str = "texto", rcon: sqlite3.Connection = Depends(obtener_rdb)):
    rec.obtener(rcon, rid, False)
    return parcial(request, "parciales/modal_fragmento.html", fragmento=None, nuevo=tipo if tipo in ("texto", "seccion") else "texto",
                   recopilacion_id=rid, tamanos=rec.TAMANOS)


@router.post("/recopilaciones/{rid}/texto")
def agregar_texto_propio(request: Request, rid: int, titulo: str = Form(""), contenido: str = Form(""),
                         rcon: sqlite3.Connection = Depends(obtener_rdb)):
    rec.agregar_texto_propio(rcon, rid, titulo, contenido)
    return _lista(request, rcon, rid, "Texto agregado al final.")


@router.post("/recopilaciones/{rid}/seccion")
def agregar_seccion(request: Request, rid: int, titulo: str = Form(""), comentario: str = Form(""),
                    rcon: sqlite3.Connection = Depends(obtener_rdb)):
    fid = rec.agregar_seccion(rcon, rid, titulo)
    if comentario.strip():
        rec.editar_fragmento(rcon, fid, titulo, comentario)
    return _lista(request, rcon, rid, "Sección agregada al final.")


@router.get("/recopilaciones/imagenes/{nombre}")
def imagen(nombre: str):
    ruta = rec.ruta_imagen(nombre)
    if not ruta.exists():
        return HTMLResponse(status_code=404)
    return FileResponse(ruta, media_type="image/png", headers={"Cache-Control": "private, max-age=86400"})


# ======================================================= vista previa y exportar
@router.get("/recopilaciones/{rid}/vista-previa")
def vista_previa(request: Request, rid: int, con: sqlite3.Connection = Depends(obtener_db),
                 rcon: sqlite3.Connection = Depends(obtener_rdb)):
    r = rec.obtener(rcon, rid)
    return pagina(request, con, "paginas/recopilacion_vista.html", recopilacion=r,
                  documento=rec.documento_html(r, lambda n: f"/recopilaciones/imagenes/{n}", "/static/marca/logo-corpas.png"),
                  migas=[{"texto": "Recopilaciones", "url": "/recopilaciones", "icono": "clipboard-list"},
                         {"texto": r.titulo, "url": f"/recopilaciones/{r.id}"}, {"texto": "Vista previa", "icono": "eye"}])


def _descarga(contenido: bytes, nombre: str, tipo: str) -> Response:
    return Response(contenido, media_type=tipo,
                    headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(nombre)}"})


@router.get("/recopilaciones/{rid}/pdf")
def exportar_pdf(rid: int, rcon: sqlite3.Connection = Depends(obtener_rdb)):
    r = rec.obtener(rcon, rid)
    if not r.fragmentos:
        raise ErrorUsuario("La recopilación está vacía: agrega algo antes de exportarla.")
    return _descarga(rec.exportar_pdf(r, LOGO), rec.nombre_archivo(r, "pdf"), "application/pdf")


@router.get("/recopilaciones/{rid}/word")
def exportar_word(rid: int, rcon: sqlite3.Connection = Depends(obtener_rdb)):
    r = rec.obtener(rcon, rid)
    if not r.fragmentos:
        raise ErrorUsuario("La recopilación está vacía: agrega algo antes de exportarla.")
    return _descarga(rec.exportar_docx(r, LOGO), rec.nombre_archivo(r, "docx"),
                     "application/vnd.openxmlformats-officedocument.wordprocessingml.document")


# ================================================================ captura
@router.get("/recopilacion/contador")
def contador(request: Request, rcon: sqlite3.Connection = Depends(obtener_rdb)):
    return parcial(request, "parciales/recopilacion_contador.html", activa=rec.activa(rcon))


def _agregar_uno(con: sqlite3.Connection, rcon: sqlite3.Connection, rid: int, fuente: str, ref_id: int, campo: str = "",
                 texto: str = "", titulo: str = "", pagina: int | None = None, recorte: str = "") -> str:
    """Agrega un fragmento a la recopilación `rid` y devuelve qué se agregó (para el aviso)."""
    if fuente == "fila":
        rec.agregar_fila(con, rcon, ref_id, rid)
        return "La ficha"
    if fuente == "campo":
        rec.agregar_campo(con, rcon, ref_id, campo, rid)
        return "El campo"
    if fuente == "nota":
        rec.agregar_nota(con, rcon, ref_id, rid)
        return "La nota"
    if fuente.startswith("texto:"):
        rec.agregar_texto(con, rcon, texto, fuente.split(":", 1)[1], ref_id, titulo, rid, pagina)
        return "El texto subrayado"
    if fuente in ("imagen", "imagen_fila", "pdf"):
        rec.agregar_imagen(con, rcon, fuente, ref_id, rid, pagina, recorte, titulo)
        return "El recorte" if recorte.strip() else ("La página" if fuente == "pdf" else "La imagen")
    raise ErrorUsuario("No se reconoce qué quieres agregar.")


@router.post("/recopilacion/agregar")
def agregar(fuente: str = Form(...), ref_id: int = Form(...), campo: str = Form(""), texto: str = Form(""),
            titulo: str = Form(""), pagina: int | None = Form(None), recorte: str = Form(""),
            con: sqlite3.Connection = Depends(obtener_db), rcon: sqlite3.Connection = Depends(obtener_rdb)):
    """fuente: fila | campo | nota | texto:<tipo> | imagen | imagen_fila | pdf (página o recorte)."""
    r = rec.activa(rcon, crear_si_falta=True)
    que = _agregar_uno(con, rcon, r.id, fuente, ref_id, campo, texto, titulo, pagina, recorte)
    n = rec.obtener(rcon, r.id, False).num_fragmentos
    return _con_aviso(Response(status_code=204), f"{que} se agregó a «{r.titulo}» ({n}).", cerrar_modal=True)


@router.post("/recopilacion/agregar-varios")
def agregar_varios(elementos: list[dict] = Body(..., embed=True), con: sqlite3.Connection = Depends(obtener_db),
                   rcon: sqlite3.Connection = Depends(obtener_rdb)):
    """Lo marcado con casillas (de una o varias páginas), en el orden en que se marcó.
    Cada elemento: {fuente: fila | nota | imagen | imagen_fila | pdf, ref_id, pagina?}."""
    if not elementos:
        raise ErrorUsuario("No hay nada seleccionado.")
    if len(elementos) > 500:
        raise ErrorUsuario("Son demasiados elementos de una vez (máximo 500).")
    r = rec.activa(rcon, crear_si_falta=True)
    agregados, fallidos = 0, []
    for e in elementos:
        try:
            fuente = str(e.get("fuente", ""))
            if fuente not in ("fila", "nota", "imagen", "imagen_fila", "pdf"):
                raise ErrorUsuario("No se reconoce qué quieres agregar.")
            pagina = int(e["pagina"]) if e.get("pagina") not in (None, "") else None
            _agregar_uno(con, rcon, r.id, fuente, int(e.get("ref_id")), pagina=pagina)
            agregados += 1
        except (ErrorUsuario, TypeError, ValueError):
            fallidos.append(str(e.get("titulo") or "un elemento"))
    if not agregados:
        raise ErrorUsuario("No se pudo agregar ninguno de los elementos seleccionados (ya no existen o están vacíos).")
    mensaje = f"Se {'agregó 1 elemento' if agregados == 1 else f'agregaron {agregados} elementos'} a «{r.titulo}»."
    if fallidos:
        mensaje += f" No se {'pudo' if len(fallidos) == 1 else 'pudieron'} agregar: {', '.join(fallidos[:5])}{'…' if len(fallidos) > 5 else ''}."
    return _con_aviso(Response(status_code=200), mensaje, "aviso" if fallidos else "exito")


@router.get("/recopilacion/recortar")
def recortar(request: Request, fuente: str, ref_id: int, pagina: int = 1, con: sqlite3.Connection = Depends(obtener_db),
             rcon: sqlite3.Connection = Depends(obtener_rdb)):
    """Ventana para marcar el rectángulo que se quiere guardar de una imagen o una página de PDF."""
    if fuente == "imagen":
        src, paginas = f"/imagenes/{ref_id}/archivo", 0
    elif fuente == "imagen_fila":
        src, paginas = f"/imagenes-fila/{ref_id}/archivo", 0
    elif fuente == "pdf":
        paginas = pdf_srv.obtener(con, ref_id).paginas
        pagina = min(max(pagina, 1), paginas)
        src = f"/recopilacion/pdf/{ref_id}/pagina"
    else:
        raise ErrorUsuario("Este elemento no se puede recortar.")
    rec.origen_de(con, fuente, ref_id, pagina if fuente == "pdf" else None)   # comprueba que exista
    activa = rec.activa(rcon)
    return parcial(request, "parciales/modal_recorte.html", fuente=fuente, ref_id=ref_id, src=src, pagina=pagina,
                   paginas=paginas, activa=activa)


@router.get("/recopilacion/pdf/{pdf_id}/pagina")
def pagina_pdf(pdf_id: int, n: int = 1, con: sqlite3.Connection = Depends(obtener_db)):
    imagen = rec.imagen_fuente(con, "pdf", pdf_id, n, dpi=110)
    salida = io.BytesIO()
    imagen.save(salida, "PNG")
    return Response(salida.getvalue(), media_type="image/png", headers={"Cache-Control": "private, max-age=3600"})

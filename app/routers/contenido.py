"""Imágenes sueltas (galería con OCR opcional) y notas de un componente."""
from __future__ import annotations

import json
import sqlite3

from fastapi import APIRouter, Body, Depends, File, Form, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse

from ..db import obtener_db
from ..errores import ErrorUsuario, NoEncontrado
from ..services import biblioteca as bib
from ..services import imagenes as img_srv
from ..services import miniaturas
from ..services import notas as notas_srv
from ..services import papelera as pap
from ..services.imagenes_fila import MAX_BYTES
from ..web import aviso, pagina, parcial, redirigir
from .tablas import _migas_componente, guardar_subida

router = APIRouter()


# ===================================================================== galería
def _galeria(request: Request, con: sqlite3.Connection, componente_id: int, etiqueta: str = "",
             mensaje: str | None = None, tipo: str = "exito"):
    respuesta = parcial(request, "parciales/contenido_imagenes.html", componente=bib.obtener_componente(con, componente_id),
                        imagenes=img_srv.listar(con, componente_id, etiqueta), etiqueta_activa=etiqueta,
                        etiquetas_usadas=img_srv.etiquetas_del_componente(con, componente_id))
    if mensaje:
        respuesta.headers["HX-Trigger"] = json.dumps({"aviso": {"mensaje": mensaje, "tipo": tipo}, "ocr-actualizado": True},
                                                     ensure_ascii=False)
    return respuesta


@router.get("/componentes/{componente_id}/imagenes")
def galeria(request: Request, componente_id: int, etiqueta: str = "", con: sqlite3.Connection = Depends(obtener_db)):
    return _galeria(request, con, componente_id, etiqueta)


@router.post("/componentes/{componente_id}/imagenes")
async def subir_imagenes(request: Request, componente_id: int, archivos: list[UploadFile] = File(default=[]),
                         titulos: list[str] = Form(default=[]), descripciones: list[str] = Form(default=[]),
                         etiquetas: list[str] = Form(default=[]), extraer_texto: bool = Form(False),
                         con: sqlite3.Connection = Depends(obtener_db)):
    bib.obtener_componente(con, componente_id)
    if not archivos:
        raise ErrorUsuario("Elige al menos una imagen.")
    if len(titulos) != len(archivos) or not all(" ".join(t.split()) for t in titulos):
        raise ErrorUsuario("Escribe un nombre descriptivo para cada imagen.")
    relleno = [""] * len(archivos)
    agregadas, avisos = 0, []
    for archivo, titulo, desc, etq in zip(archivos, titulos, descripciones + relleno, etiquetas + relleno):
        try:
            tmp = await guardar_subida(archivo, MAX_BYTES)
            try:
                _, nota = img_srv.agregar(con, componente_id, archivo.filename or "imagen", tmp, titulo, desc, etq, extraer_texto)
            finally:
                tmp.unlink(missing_ok=True)
            agregadas += 1
            if nota:
                avisos.append(nota)
        except ErrorUsuario as e:
            avisos.append(e.mensaje)
    mensaje = ("1 imagen agregada." if agregadas == 1 else f"{agregadas} imágenes agregadas.") if agregadas \
        else "No se agregó ninguna imagen."
    if agregadas and extraer_texto:
        mensaje += " Su texto se está leyendo con OCR en segundo plano."
    if avisos:
        mensaje += " " + " ".join(avisos)
    return _galeria(request, con, componente_id, "", mensaje, "exito" if agregadas and not avisos else "aviso" if agregadas else "error")


@router.post("/componentes/{componente_id}/imagenes/orden")
def ordenar(componente_id: int, ids: list[int] = Body(..., embed=True), con: sqlite3.Connection = Depends(obtener_db)):
    img_srv.reordenar(con, componente_id, ids)
    return aviso("Orden guardado.")


@router.get("/imagenes/{imagen_id}")
def ver_imagen(request: Request, imagen_id: int, con: sqlite3.Connection = Depends(obtener_db)):
    img = img_srv.obtener(con, imagen_id)
    comp = bib.obtener_componente(con, img.componente_id)
    vecinas = img_srv.listar(con, comp.id)
    ids = [i.id for i in vecinas]
    pos = ids.index(img.id) if img.id in ids else 0
    return pagina(request, con, "paginas/imagen.html", imagen=img, componente=comp, materia_activa=comp.materia_id,
                  anterior=ids[pos - 1] if pos > 0 else None, siguiente=ids[pos + 1] if pos + 1 < len(ids) else None,
                  migas=_migas_componente(con, comp.id) + [{"texto": img.titulo}])


@router.post("/imagenes/{imagen_id}")
def editar_imagen(request: Request, imagen_id: int, titulo: str = Form(""), descripcion: str = Form(""),
                  etiquetas: str = Form(""), con: sqlite3.Connection = Depends(obtener_db)):
    img_srv.editar(con, imagen_id, titulo, descripcion, etiquetas)
    return redirigir(request, f"/imagenes/{imagen_id}", "Cambios guardados.")


@router.post("/imagenes/{imagen_id}/ocr")
def pedir_ocr(request: Request, imagen_id: int, con: sqlite3.Connection = Depends(obtener_db)):
    img_srv.pedir_ocr(con, imagen_id)
    respuesta = parcial(request, "parciales/imagen_ocr.html", imagen=img_srv.obtener(con, imagen_id))
    respuesta.headers["HX-Trigger"] = json.dumps({"ocr-actualizado": True})
    return respuesta


@router.get("/imagenes/{imagen_id}/ocr")
def estado_ocr(request: Request, imagen_id: int, con: sqlite3.Connection = Depends(obtener_db)):
    return parcial(request, "parciales/imagen_ocr.html", imagen=img_srv.obtener(con, imagen_id))


@router.get("/imagenes/{imagen_id}/insignia")
def insignia_ocr(request: Request, imagen_id: int, con: sqlite3.Connection = Depends(obtener_db)):
    return parcial(request, "parciales/imagen_insignia.html", img=img_srv.obtener(con, imagen_id))


@router.get("/imagenes/{imagen_id}/archivo")
def archivo_imagen(imagen_id: int, con: sqlite3.Connection = Depends(obtener_db)):
    ruta = img_srv.ruta(con, img_srv.obtener(con, imagen_id))
    if not ruta.exists():
        raise NoEncontrado("El archivo de la imagen")
    return FileResponse(ruta, headers={"Cache-Control": "private, max-age=3600"})


@router.get("/imagenes/{imagen_id}/miniatura")
def miniatura_imagen(imagen_id: int, con: sqlite3.Connection = Depends(obtener_db)):
    img = img_srv.obtener(con, imagen_id)
    ruta = img_srv.ruta(con, img)
    mini = miniaturas.obtener(ruta, img.hash) if ruta.exists() else None
    if mini is None:
        return FileResponse(ruta) if ruta.exists() else HTMLResponse(status_code=404)
    return FileResponse(mini, media_type="image/webp", headers={"Cache-Control": "private, max-age=86400"})


@router.get("/imagenes/{imagen_id}/eliminar")
def confirmar_eliminar_imagen(request: Request, imagen_id: int, con: sqlite3.Connection = Depends(obtener_db)):
    img = img_srv.obtener(con, imagen_id)
    return parcial(request, "parciales/modal_confirmar.html", titulo=f"¿Enviar «{img.titulo}» a la papelera?",
                   detalle="Podrás restaurarla desde la papelera mientras no la vacíes.",
                   accion=f"/imagenes/{img.id}/eliminar", boton="Enviar a la papelera")


@router.post("/imagenes/{imagen_id}/eliminar")
def eliminar_imagen(request: Request, imagen_id: int, con: sqlite3.Connection = Depends(obtener_db)):
    titulo, componente_id = pap.enviar_imagen(con, imagen_id)
    return redirigir(request, f"/componentes/{componente_id}#imagenes", f"«{titulo}» se envió a la papelera.")


# ======================================================================== notas
def _editor(request: Request, con: sqlite3.Connection, componente_id: int, nota=None, valores=None, error=None):
    comp = bib.obtener_componente(con, componente_id)
    valores = valores or ({"titulo": nota.titulo, "contenido": nota.contenido, "formato": nota.formato,
                           "etiquetas": ", ".join(nota.etiquetas)} if nota else
                          {"titulo": "", "contenido": "", "formato": "markdown", "etiquetas": ""})
    migas = _migas_componente(con, comp.id) + ([{"texto": nota.titulo, "url": f"/notas/{nota.id}"}, {"texto": "Editar"}]
                                               if nota else [{"texto": "Nueva nota"}])
    return pagina(request, con, "paginas/nota_editar.html", componente=comp, nota=nota, valores=valores, error=error,
                  formatos=notas_srv.FORMATOS, vista_previa=notas_srv.renderizar(valores["contenido"], valores["formato"]),
                  materia_activa=comp.materia_id, migas=migas)


@router.get("/componentes/{componente_id}/notas/nueva")
def nueva_nota(request: Request, componente_id: int, con: sqlite3.Connection = Depends(obtener_db)):
    return _editor(request, con, componente_id)


@router.post("/componentes/{componente_id}/notas")
def crear_nota(request: Request, componente_id: int, titulo: str = Form(""), contenido: str = Form(""),
               formato: str = Form("markdown"), etiquetas: str = Form(""), con: sqlite3.Connection = Depends(obtener_db)):
    try:
        nota = notas_srv.crear(con, componente_id, titulo, contenido, formato, etiquetas)
    except ErrorUsuario as e:
        return _editor(request, con, componente_id, None,
                       {"titulo": titulo, "contenido": contenido, "formato": formato, "etiquetas": etiquetas}, e.mensaje)
    return redirigir(request, f"/notas/{nota.id}", "Nota guardada.")


@router.post("/notas/vista-previa", response_class=HTMLResponse)
def vista_previa(contenido: str = Form(""), formato: str = Form("markdown")):
    return HTMLResponse(notas_srv.renderizar(contenido, formato if formato in notas_srv.FORMATOS else "markdown")
                        or '<p class="text-tenue">La vista previa aparecerá aquí.</p>')


@router.get("/notas/{nota_id}")
def ver_nota(request: Request, nota_id: int, con: sqlite3.Connection = Depends(obtener_db)):
    nota = notas_srv.obtener(con, nota_id)
    comp = bib.obtener_componente(con, nota.componente_id)
    return pagina(request, con, "paginas/nota.html", nota=nota, html=notas_srv.renderizar(nota.contenido, nota.formato),
                  materia_activa=comp.materia_id, migas=_migas_componente(con, comp.id) + [{"texto": nota.titulo}])


@router.get("/notas/{nota_id}/editar")
def editar_nota_form(request: Request, nota_id: int, con: sqlite3.Connection = Depends(obtener_db)):
    nota = notas_srv.obtener(con, nota_id)
    return _editor(request, con, nota.componente_id, nota)


@router.post("/notas/{nota_id}")
def editar_nota(request: Request, nota_id: int, titulo: str = Form(""), contenido: str = Form(""),
                formato: str = Form("markdown"), etiquetas: str = Form(""), con: sqlite3.Connection = Depends(obtener_db)):
    nota = notas_srv.obtener(con, nota_id)
    try:
        notas_srv.editar(con, nota_id, titulo, contenido, formato, etiquetas)
    except ErrorUsuario as e:
        return _editor(request, con, nota.componente_id, nota,
                       {"titulo": titulo, "contenido": contenido, "formato": formato, "etiquetas": etiquetas}, e.mensaje)
    return redirigir(request, f"/notas/{nota_id}", "Nota guardada.")


@router.get("/notas/{nota_id}/eliminar")
def confirmar_eliminar_nota(request: Request, nota_id: int, con: sqlite3.Connection = Depends(obtener_db)):
    nota = notas_srv.obtener(con, nota_id)
    return parcial(request, "parciales/modal_confirmar.html", titulo=f"¿Enviar «{nota.titulo}» a la papelera?",
                   detalle="Podrás restaurarla desde la papelera mientras no la vacíes.",
                   accion=f"/notas/{nota.id}/eliminar", boton="Enviar a la papelera")


@router.post("/notas/{nota_id}/eliminar")
def eliminar_nota(request: Request, nota_id: int, con: sqlite3.Connection = Depends(obtener_db)):
    titulo, componente_id = pap.enviar_nota(con, nota_id)
    return redirigir(request, f"/componentes/{componente_id}#notas", f"«{titulo}» se envió a la papelera.")

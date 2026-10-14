"""PDF: carga con nombre descriptivo, visor (PDF.js) en la página exacta y estado del OCR."""
from __future__ import annotations

import json
import sqlite3

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse

from ..db import obtener_db
from ..errores import ErrorUsuario, NoEncontrado
from ..services import biblioteca as bib
from ..services import papelera as pap
from ..services import pdfs
from ..services.texto import fragmentos_resaltados
from ..web import pagina, parcial, redirigir
from .tablas import _migas_componente, guardar_subida

router = APIRouter()


def _lista(request: Request, con: sqlite3.Connection, componente_id: int, mensaje: str | None = None, tipo: str = "exito"):
    respuesta = parcial(request, "parciales/contenido_pdf.html", componente=bib.obtener_componente(con, componente_id),
                        pdfs=pdfs.listar(con, componente_id))
    disparos: dict = {"ocr-actualizado": True}
    if mensaje:
        disparos["aviso"] = {"mensaje": mensaje, "tipo": tipo}
    respuesta.headers["HX-Trigger"] = json.dumps(disparos, ensure_ascii=False)
    return respuesta


@router.post("/componentes/{componente_id}/pdfs")
async def subir_pdfs(request: Request, componente_id: int, archivos: list[UploadFile] = File(default=[]),
                     titulos: list[str] = Form(default=[]), con: sqlite3.Connection = Depends(obtener_db)):
    bib.obtener_componente(con, componente_id)
    if not archivos:
        raise ErrorUsuario("Elige al menos un PDF.")
    if len(titulos) != len(archivos) or not all(" ".join(t.split()) for t in titulos):
        raise ErrorUsuario("Escribe un nombre descriptivo para cada PDF.")
    agregados, escaneadas, avisos = 0, 0, []
    for archivo, titulo in zip(archivos, titulos):
        try:
            tmp = await guardar_subida(archivo, pdfs.MAX_BYTES)
            try:
                pdf, nota = pdfs.agregar(con, componente_id, archivo.filename or "documento.pdf", tmp, titulo)
            finally:
                tmp.unlink(missing_ok=True)
            agregados += 1
            escaneadas += pdf.ocr_pendientes
            if nota:
                avisos.append(nota)
        except ErrorUsuario as e:
            avisos.append(e.mensaje)
    mensaje = ("1 PDF agregado." if agregados == 1 else f"{agregados} PDF agregados.") if agregados else "No se agregó ningún PDF."
    if escaneadas:
        mensaje += (" 1 página escaneada se está leyendo" if escaneadas == 1 else
                    f" {escaneadas} páginas escaneadas se están leyendo") + \
            " con OCR en segundo plano; puedes seguir usando la biblioteca."
    if avisos:
        mensaje += " " + " ".join(avisos)
    return _lista(request, con, componente_id, mensaje, "exito" if agregados and not avisos else "aviso" if agregados else "error")


@router.get("/pdfs/{pdf_id}")
def ver_pdf(request: Request, pdf_id: int, buscar: str = "",
            con: sqlite3.Connection = Depends(obtener_db)):
    pdf = pdfs.obtener(con, pdf_id)
    numero = request.query_params.get("pagina", "")
    numero = int(numero) if numero.isdigit() and 1 <= int(numero) <= pdf.paginas else None
    pag = pdfs.pagina(con, pdf.id, numero) if numero else None
    # En páginas escaneadas el visor no puede resaltar (no hay capa de texto): se muestra el texto reconocido
    texto_ocr = fragmentos_resaltados(pag["texto"], buscar) if pag is not None and pag["origen"] == "ocr" else None
    comp = bib.obtener_componente(con, pdf.componente_id)
    return pagina(request, con, "paginas/pdf.html", pdf=pdf, numero=numero, buscar=buscar.strip(), texto_ocr=texto_ocr,
                  materia_activa=comp.materia_id, migas=_migas_componente(con, comp.id) + [{"texto": pdf.titulo}])


@router.get("/pdfs/{pdf_id}/archivo")
def archivo_pdf(pdf_id: int, con: sqlite3.Connection = Depends(obtener_db)):
    pdf = pdfs.obtener(con, pdf_id)
    ruta = pdfs.ruta(con, pdf)
    if not ruta.exists():
        raise NoEncontrado("El archivo del PDF")
    return FileResponse(ruta, media_type="application/pdf", content_disposition_type="inline", filename=ruta.name)


@router.get("/pdfs/{pdf_id}/descargar")
def descargar_pdf(pdf_id: int, con: sqlite3.Connection = Depends(obtener_db)):
    pdf = pdfs.obtener(con, pdf_id)
    return FileResponse(pdfs.ruta(con, pdf), media_type="application/pdf", filename=pdfs.ruta(con, pdf).name)


@router.get("/pdfs/{pdf_id}/miniatura")
def miniatura_pdf(pdf_id: int, con: sqlite3.Connection = Depends(obtener_db)):
    mini = pdfs.miniatura(con, pdfs.obtener(con, pdf_id))
    if mini is None:
        return HTMLResponse(status_code=404)
    return FileResponse(mini, media_type="image/webp", headers={"Cache-Control": "private, max-age=86400"})


@router.get("/pdfs/{pdf_id}/estado")
def estado_pdf(request: Request, pdf_id: int, con: sqlite3.Connection = Depends(obtener_db)):
    return parcial(request, "parciales/pdf_estado.html", pdf=pdfs.obtener(con, pdf_id))


@router.post("/pdfs/{pdf_id}/ocr")
def ocr_completo(request: Request, pdf_id: int, con: sqlite3.Connection = Depends(obtener_db)):
    n = pdfs.pedir_ocr_completo(con, pdf_id)
    return redirigir(request, f"/pdfs/{pdf_id}", f"Se volverán a leer {n} páginas con OCR en segundo plano.")


@router.post("/pdfs/{pdf_id}/reintentar")
def reintentar(request: Request, pdf_id: int, con: sqlite3.Connection = Depends(obtener_db)):
    n = pdfs.reintentar_errores(con, pdf_id)
    return redirigir(request, f"/pdfs/{pdf_id}", f"Se reintentará el OCR de {n} página{'s' if n != 1 else ''}.")


@router.get("/pdfs/{pdf_id}/renombrar")
def formulario_renombrar(request: Request, pdf_id: int, con: sqlite3.Connection = Depends(obtener_db)):
    pdf = pdfs.obtener(con, pdf_id)
    return parcial(request, "parciales/modal_nombre.html", titulo="Cambiar nombre del PDF",
                   accion=f"/pdfs/{pdf.id}/renombrar", valor=pdf.titulo)


@router.post("/pdfs/{pdf_id}/renombrar")
def renombrar(request: Request, pdf_id: int, nombre: str = Form(""), con: sqlite3.Connection = Depends(obtener_db)):
    try:
        pdfs.renombrar(con, pdf_id, nombre)
    except ErrorUsuario as e:
        return parcial(request, "parciales/modal_nombre.html", titulo="Cambiar nombre del PDF",
                       accion=f"/pdfs/{pdf_id}/renombrar", valor=nombre, error=e.mensaje)
    return redirigir(request, f"/pdfs/{pdf_id}", "Nombre actualizado.")


@router.get("/pdfs/{pdf_id}/eliminar")
def confirmar_eliminar(request: Request, pdf_id: int, con: sqlite3.Connection = Depends(obtener_db)):
    pdf = pdfs.obtener(con, pdf_id)
    return parcial(request, "parciales/modal_confirmar.html", titulo=f"¿Enviar «{pdf.titulo}» a la papelera?",
                   detalle="Podrás restaurarlo desde la papelera mientras no la vacíes.",
                   accion=f"/pdfs/{pdf.id}/eliminar", boton="Enviar a la papelera")


@router.post("/pdfs/{pdf_id}/eliminar")
def eliminar(request: Request, pdf_id: int, con: sqlite3.Connection = Depends(obtener_db)):
    titulo, componente_id = pap.enviar_pdf(con, pdf_id)
    return redirigir(request, f"/componentes/{componente_id}", f"«{titulo}» se envió a la papelera.")


@router.get("/ocr/estado")
def estado_ocr(request: Request, con: sqlite3.Connection = Depends(obtener_db)):
    return parcial(request, "parciales/ocr_estado.html", pendientes=pdfs.ocr_pendiente_total(con))

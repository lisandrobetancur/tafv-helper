"""Utilidades compartidas por los routers: plantillas, avisos (toasts) y respuestas para HTMX."""
from __future__ import annotations

import json
import sqlite3
from typing import Any
from urllib.parse import quote, unquote

from fastapi import Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

from . import config
from .services import biblioteca as bib
from .services import papelera as pap

templates = Jinja2Templates(directory=config.TEMPLATES_DIR)
templates.env.globals.update(
    NOMBRE_APP=config.NOMBRE_APP,
    INSTITUCION=config.INSTITUCION,
    COLORES=config.COLORES_MATERIA,
    COLOR_POR_ID=config.COLOR_POR_ID,
    ICONOS=config.ICONOS_MATERIA,
    TIPOS=config.TIPOS_CONTENIDO,
    PROFUNDIDAD_MAXIMA=config.PROFUNDIDAD_MAXIMA,
    CASOS_ACTIVOS=config.CASOS_ACTIVOS,
)


def _version_estaticos() -> str:
    """Cambia cuando cambia el CSS/JS, para que el navegador no use una copia vieja."""
    archivos = [config.STATIC_DIR / "css" / "app.css", config.STATIC_DIR / "js" / "app.js"]
    return str(int(max((a.stat().st_mtime for a in archivos if a.exists()), default=0)))


def _imagenes_carrusel(imagenes: list, tipo: str) -> list[dict[str, str]]:
    """Datos para la macro `carrusel`: imágenes de un componente ("imagenes") o de una ficha ("imagenes-fila")."""
    if tipo == "imagenes":
        return [{"src": f"/imagenes/{i.id}/archivo", "miniatura": f"/imagenes/{i.id}/miniatura", "titulo": i.titulo,
                 "pie": i.descripcion, "url": f"/imagenes/{i.id}",
                 "recortar": f"/recopilacion/recortar?fuente=imagen&ref_id={i.id}",
                 "seleccion": {"fuente": "imagen", "ref_id": i.id, "titulo": i.titulo, "pagina": None}} for i in imagenes]
    return [{"src": f"/imagenes-fila/{i.id}/archivo", "miniatura": f"/imagenes-fila/{i.id}/miniatura", "titulo": i.titulo,
             "pie": i.pie, "recortar": f"/recopilacion/recortar?fuente=imagen_fila&ref_id={i.id}",
             "seleccion": {"fuente": "imagen_fila", "ref_id": i.id, "titulo": i.titulo, "pagina": None}} for i in imagenes]


templates.env.globals["version_estaticos"] = _version_estaticos
templates.env.globals["imagenes_carrusel"] = _imagenes_carrusel
templates.env.globals["TIPOS_PAPELERA"] = {
    "materia": {"nombre": "Materia", "icono": "graduation-cap"},
    "componente": {"nombre": "Componente", "icono": "folder"},
    "tabla": {"nombre": "Tabla", "icono": "file-spreadsheet"},
    "imagen_fila": {"nombre": "Imagen de una ficha", "icono": "image"},
    "archivo": {"nombre": "Archivo", "icono": "file-text"},
    "pdf": {"nombre": "PDF", "icono": "file-text"},
    "imagen": {"nombre": "Imagen", "icono": "image"},
    "nota": {"nombre": "Nota", "icono": "sticky-note"},
    "caso": {"nombre": "Caso de acceso rápido", "icono": "stethoscope"},
}

COOKIE_AVISO = "aviso"


def es_htmx(request: Request) -> bool:
    return request.headers.get("HX-Request") == "true" and request.headers.get("HX-Boosted") != "true"


def contexto_comun(request: Request, con: sqlite3.Connection, **extra: Any) -> dict[str, Any]:
    """Datos que necesita el layout en todas las páginas (barra lateral, avisos)."""
    aviso = None
    crudo = request.cookies.get(COOKIE_AVISO)
    if crudo:
        try:
            aviso = json.loads(unquote(crudo))
        except ValueError:
            aviso = None
    return {
        "request": request,
        "materias_menu": bib.listar_materias(con),
        "en_papelera": pap.contar(con),
        "aviso_inicial": aviso,
        **extra,
    }


def pagina(request: Request, con: sqlite3.Connection, plantilla: str, **contexto: Any) -> HTMLResponse:
    respuesta = templates.TemplateResponse(request, plantilla, contexto_comun(request, con, **contexto))
    if request.cookies.get(COOKIE_AVISO):
        respuesta.delete_cookie(COOKIE_AVISO)  # el aviso ya se mostró
    return respuesta


def parcial(request: Request, plantilla: str, **contexto: Any) -> HTMLResponse:
    return templates.TemplateResponse(request, plantilla, {"request": request, **contexto})


def redirigir(request: Request, url: str, aviso: str | None = None, tipo: str = "exito") -> Response:
    """Navega a `url` mostrando un aviso al llegar (funciona con y sin HTMX)."""
    if es_htmx(request):
        respuesta: Response = Response(status_code=200, headers={"HX-Redirect": url})
    else:
        respuesta = RedirectResponse(url, status_code=303)
    if aviso:
        respuesta.set_cookie(COOKIE_AVISO, quote(json.dumps({"mensaje": aviso, "tipo": tipo}, ensure_ascii=False)),
                             max_age=30, samesite="lax", httponly=False)
    return respuesta


def aviso(mensaje: str, tipo: str = "exito", estado: int = 200, cuerpo: str = "") -> Response:
    """Respuesta HTMX que solo muestra un aviso (no cambia la página)."""
    headers = {"HX-Trigger": json.dumps({"aviso": {"mensaje": mensaje, "tipo": tipo}}, ensure_ascii=False)}
    if not cuerpo:
        headers["HX-Reswap"] = "none"
    return HTMLResponse(cuerpo, status_code=estado, headers=headers)

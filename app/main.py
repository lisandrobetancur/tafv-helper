"""Aplicación FastAPI: arranque, bloqueo entre equipos y manejo de errores."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import config, db
from .errores import ErrorUsuario
from .registro import configurar_registro
from .routers import componentes, contenido, materias, paginas, pdfs as rutas_pdfs, tablas
from .services import bloqueo, imagenes, importacion, ocr, pdfs  # noqa: F401 (registran sus fuentes de OCR)
from .web import aviso, es_htmx, templates

log = logging.getLogger(__name__)

MENSAJE_INESPERADO = ("Ocurrió un problema inesperado. Intenta de nuevo; si se repite, "
                      "cierra y vuelve a abrir la biblioteca.")


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    configurar_registro()
    db.inicializar()
    importacion.limpiar_viejas()
    app.state.bloqueo = bloqueo.adquirir()
    log.info("Biblioteca iniciada en %s", bloqueo.nombre_equipo())
    if app.state.ocr_activo:
        ocr.iniciar(db.conectar)  # reanuda el OCR pendiente en segundo plano
    try:
        yield
    finally:
        ocr.detener()
        bloqueo.liberar()
        log.info("Biblioteca cerrada")


def crear_app(ocr_activo: bool = True) -> FastAPI:
    app = FastAPI(title=config.NOMBRE_APP, lifespan=ciclo_de_vida, docs_url=None, redoc_url=None)
    app.state.ocr_activo = ocr_activo
    app.mount("/static", StaticFiles(directory=config.STATIC_DIR), name="static")

    @app.middleware("http")
    async def control_de_bloqueo(request: Request, call_next):
        """Si la biblioteca está abierta en otro equipo, todo lleva al aviso de bloqueo."""
        estado = getattr(request.app.state, "bloqueo", None)
        ruta = request.url.path
        if estado and not estado.libre and not ruta.startswith(("/static", "/bloqueo", "/favicon")):
            if request.headers.get("HX-Request"):
                return Response(headers={"HX-Redirect": "/bloqueo"})
            return RedirectResponse("/bloqueo", status_code=303)
        return await call_next(request)

    @app.exception_handler(ErrorUsuario)
    async def error_usuario(request: Request, exc: ErrorUsuario):
        if es_htmx(request):
            return aviso(exc.mensaje, "error", estado=exc.estado)
        return templates.TemplateResponse(request, "paginas/error.html",
                                          {"mensaje": exc.mensaje, "estado": exc.estado}, status_code=exc.estado)

    @app.exception_handler(StarletteHTTPException)
    async def error_http(request: Request, exc: StarletteHTTPException):
        mensaje = "Esta página no existe." if exc.status_code == 404 else "No se pudo completar la acción."
        if es_htmx(request):
            return aviso(mensaje, "error", estado=exc.status_code)
        return templates.TemplateResponse(request, "paginas/error.html",
                                          {"mensaje": mensaje, "estado": exc.status_code}, status_code=exc.status_code)

    @app.exception_handler(Exception)
    async def error_inesperado(request: Request, exc: Exception):
        log.exception("Error inesperado en %s %s", request.method, request.url.path)
        if es_htmx(request):
            return aviso(MENSAJE_INESPERADO, "error", estado=500)
        return HTMLResponse(templates.get_template("paginas/error.html").render(
            request=request, mensaje=MENSAJE_INESPERADO, estado=500), status_code=500)

    @app.get("/favicon.ico", include_in_schema=False)
    def favicon():
        return FileResponse(config.STATIC_DIR / "marca" / "logo-corpas.png", media_type="image/png")

    app.include_router(paginas.router)
    app.include_router(materias.router)
    app.include_router(componentes.router)
    app.include_router(tablas.router)
    app.include_router(rutas_pdfs.router)
    app.include_router(contenido.router)
    return app


app = crear_app()

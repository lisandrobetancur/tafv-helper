"""Aplicación FastAPI: arranque, bloqueo entre equipos y manejo de errores."""
from __future__ import annotations

import logging
from datetime import date, timedelta
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import config, db
from .errores import ErrorUsuario
from .registro import configurar_registro
from .routers import busqueda, componentes, contenido, diagnostico, diagnostico_clinico, extras, materias, paginas, pdfs as rutas_pdfs, recopilaciones, tablas
from .services import bloqueo, imagenes, importacion, licencia, ocr, pdfs  # noqa: F401 (registran sus fuentes de OCR)
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


def crear_app(ocr_activo: bool = True, exigir_licencia: bool = True) -> FastAPI:
    app = FastAPI(title=config.NOMBRE_APP, lifespan=ciclo_de_vida, docs_url=None, redoc_url=None)
    app.state.ocr_activo = ocr_activo
    app.state.licencia_valida = not exigir_licencia
    app.state.licencia_revisar_el = date.max if not exigir_licencia else date.min
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

    @app.middleware("http")
    async def control_de_licencia(request: Request, call_next):
        """Sin una licencia válida para este equipo, todo lleva a la pantalla de activación.
        Una licencia permanente se comprueba una vez por sesión; una temporal, cada día (puede vencer)."""
        ruta = request.url.path
        estado = request.app.state
        if not estado.licencia_valida or estado.licencia_revisar_el <= date.today():
            if not ruta.startswith(("/static", "/licencia", "/favicon")):
                actual = licencia.estado_actual()
                estado.licencia_valida = actual.valida
                estado.licencia_revisar_el = (date.max if not actual.temporal else date.today() + timedelta(days=1))
                if not actual.valida:
                    if request.headers.get("HX-Request"):
                        return Response(headers={"HX-Redirect": "/licencia"})
                    return RedirectResponse("/licencia", status_code=303)
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
    app.include_router(busqueda.router)
    app.include_router(diagnostico_clinico.router)  # antes que materias: su dirección es /materias/8001
    app.include_router(materias.router)
    app.include_router(componentes.router)
    app.include_router(tablas.router)
    app.include_router(rutas_pdfs.router)
    app.include_router(contenido.router)
    app.include_router(extras.router)
    app.include_router(diagnostico.router)
    app.include_router(recopilaciones.router)
    return app


app = crear_app()

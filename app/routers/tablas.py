"""Excel/CSV: asistente de importación, vista de tabla, ficha de fila e imágenes por fila."""
from __future__ import annotations

import json
import os
import shutil
import sqlite3
import tempfile
from pathlib import Path

from fastapi import APIRouter, Body, Depends, File, Form, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, Response

from ..config import rutas
from ..db import obtener_db
from ..errores import ErrorUsuario, NoEncontrado
from ..services import biblioteca as bib
from ..services import hojas as lector
from ..services import imagenes_fila as imf
from ..services import importacion as imp
from ..services import miniaturas
from ..services import papelera as pap
from ..services import tablas as tab
from ..web import aviso, pagina, parcial, redirigir

router = APIRouter()
MAX_EXCEL = 200 * 1024 * 1024


async def guardar_subida(archivo: UploadFile, limite: int) -> Path:
    """Copia el archivo subido a un temporal dentro de data/cache (mismo disco que el destino)."""
    carpeta = rutas.cache / "subidas"
    carpeta.mkdir(parents=True, exist_ok=True)
    descriptor, nombre = tempfile.mkstemp(dir=carpeta, suffix=Path(archivo.filename or "").suffix.lower())
    os.close(descriptor)   # si queda abierto, Windows no deja borrar ni mover el temporal
    tmp = Path(nombre)
    total = 0
    with tmp.open("wb") as destino:
        while bloque := await archivo.read(1024 * 1024):
            total += len(bloque)
            if total > limite:
                destino.close()
                tmp.unlink(missing_ok=True)
                raise ErrorUsuario(f"«{archivo.filename}» supera el tamaño máximo ({limite // (1024 * 1024)} MB).")
            destino.write(bloque)
    if total == 0:
        tmp.unlink(missing_ok=True)
        raise ErrorUsuario(f"«{archivo.filename}» está vacío.")
    return tmp


def _migas_componente(con: sqlite3.Connection, componente_id: int, seccion: str | None = None) -> list[dict]:
    """Ruta Materia › (subcomponentes) › Componente [› Sección]. La sección (excel, pdf, notas,
    imagenes) enlaza a su pestaña del componente, para volver justo a la lista de donde se vino."""
    from ..config import TIPOS_CONTENIDO
    c = bib.obtener_componente(con, componente_id)
    m = bib.obtener_materia(con, c.materia_id)
    migas = [{"texto": m.nombre, "url": f"/materias/{m.id}", "icono": m.icono, "color": m.color_hex}]
    migas += [{"texto": a.nombre, "url": f"/componentes/{a.id}", "icono": "folder"} for a in bib.ancestros(con, c)]
    migas.append({"texto": c.nombre, "url": f"/componentes/{c.id}", "icono": "folder-open"})
    if seccion in TIPOS_CONTENIDO:
        info = TIPOS_CONTENIDO[seccion]
        migas.append({"texto": "Excel" if seccion == "excel" else info["nombre"],
                      "url": f"/componentes/{c.id}#{seccion}", "icono": info["icono"]})
    return migas


# ===================================================================== asistente
def _paso(request: Request, con: sqlite3.Connection, estado: imp.Estado, numero: int, error: str | None = None):
    """Dibuja el paso `numero` del asistente."""
    contexto: dict = {"estado": estado, "error": error, "paso": numero}
    if numero in (3, 4):
        hojas = imp.hojas(estado)
        indice = estado.hoja_actual
        hoja = hojas[indice]
        anterior = None
        if estado.es_reemplazo:
            t = tab.obtener(con, estado.tabla_id)
            anterior = {"columnas": t.columnas, "columna_titulo": t.columna_titulo, "columna_clave": t.columna_clave,
                        "fila_encabezado": t.fila_encabezado, "dos_filas": t.dos_filas}
        cfg = imp.config_sugerida(estado, indice, hoja, anterior)
        if str(indice) not in estado.config:  # se guarda para los pasos siguientes
            estado.poner_config(indice, cfg)
            imp.guardar(estado)
        contexto.update(hoja=hoja, indice=indice, cfg=cfg,
                        columnas=lector.columnas(hoja, cfg.fila_encabezado, cfg.dos_filas),
                        vista=hoja.filas[:14], ancho_vista=min(hoja.num_columnas, 10))
    elif numero == 5:
        hojas = imp.hojas(estado)
        resumen = []
        for i in estado.seleccion:
            cfg = estado.config_hoja(i)
            regs = lector.registros(hojas[i], cfg.fila_encabezado, cfg.dos_filas, cfg.columnas)
            nombres = {c.indice: c.nombre for c in lector.columnas(hojas[i], cfg.fila_encabezado, cfg.dos_filas)}
            resumen.append({"hoja": hojas[i].nombre, "nombre": cfg.nombre_tabla, "filas": len(regs),
                            "columnas": len(cfg.columnas), "titulo": nombres.get(cfg.titulo, "")})
        contexto["resumen"] = resumen
        if estado.es_reemplazo:
            contexto["reemplazo"] = tab.previsualizar_reemplazo(con, estado)
    return parcial(request, f"parciales/importar/paso{numero}.html", **contexto)


@router.get("/componentes/{componente_id}/importar")
def asistente_nuevo(request: Request, componente_id: int, con: sqlite3.Connection = Depends(obtener_db)):
    c = bib.obtener_componente(con, componente_id)
    return parcial(request, "parciales/importar/marco.html", componente=c, tabla=None, paso=1, estado=None)


@router.get("/tablas/{tabla_id}/actualizar")
def asistente_actualizar(request: Request, tabla_id: int, con: sqlite3.Connection = Depends(obtener_db)):
    t = tab.obtener(con, tabla_id)
    c = bib.obtener_componente(con, t.componente_id)
    return parcial(request, "parciales/importar/marco.html", componente=c, tabla=t, paso=1, estado=None)


@router.post("/importar")
async def asistente_subir(request: Request, componente_id: int = Form(...), tabla_id: int | None = Form(None),
                          nombre: str = Form(""), archivo: UploadFile | None = File(None),
                          con: sqlite3.Connection = Depends(obtener_db)):
    c = bib.obtener_componente(con, componente_id)
    t = tab.obtener(con, tabla_id) if tabla_id else None
    try:
        if archivo is None or not archivo.filename:
            raise ErrorUsuario("Elige un archivo de Excel o CSV.")
        tmp = await guardar_subida(archivo, MAX_EXCEL)
        try:
            estado = imp.crear(con, componente_id, archivo.filename, tmp, nombre, tabla_id=tabla_id)
        finally:
            tmp.unlink(missing_ok=True)
    except ErrorUsuario as e:
        return parcial(request, "parciales/importar/paso1.html", componente=c, tabla=t, paso=1, estado=None,
                       error=e.mensaje, nombre=nombre)
    con_datos = [i for i, h in enumerate(estado.hojas) if h["filas"]]
    if estado.es_reemplazo or len(con_datos) == 1:
        if estado.es_reemplazo:  # por defecto, la hoja con el mismo nombre que la tabla tenía
            mismo = next((i for i, h in enumerate(estado.hojas) if h["nombre"] == t.hoja and h["filas"]), con_datos[0])
            estado.seleccion = [mismo]
            imp.guardar(estado)
            if len(con_datos) > 1:
                return _paso(request, con, estado, 2)
        return _paso(request, con, estado, 3)
    return _paso(request, con, estado, 2)


@router.get("/importar/{token}/paso/{numero}")
def asistente_ir(request: Request, token: str, numero: int, con: sqlite3.Connection = Depends(obtener_db)):
    estado = imp.cargar(token)
    if numero in (3, 4) and not estado.seleccion:
        numero = 2
    return _paso(request, con, estado, max(2, min(numero, 5)))


@router.post("/importar/{token}/hojas")
def asistente_hojas(request: Request, token: str, seleccion: list[int] = Form(default=[]),
                    con: sqlite3.Connection = Depends(obtener_db)):
    estado = imp.cargar(token)
    validas = [i for i in seleccion if 0 <= i < len(estado.hojas) and estado.hojas[i]["filas"]]
    if not validas:
        return _paso(request, con, estado, 2, "Elige al menos una hoja con datos.")
    if estado.es_reemplazo:
        validas = validas[:1]
    estado.seleccion, estado.actual = validas, 0
    imp.guardar(estado)
    return _paso(request, con, estado, 3)


@router.post("/importar/{token}/encabezado")
def asistente_encabezado(request: Request, token: str, fila_encabezado: int = Form(1), dos_filas: bool = Form(False),
                         con: sqlite3.Connection = Depends(obtener_db)):
    estado = imp.cargar(token)
    indice = estado.hoja_actual
    hoja = imp.hojas(estado)[indice]
    fila_encabezado = max(1, min(fila_encabezado, max(1, hoja.num_filas)))
    base = estado.config_hoja(indice)
    if (base.fila_encabezado, base.dos_filas) == (fila_encabezado, dos_filas):
        return _paso(request, con, estado, 4)
    # Cambió el encabezado: las columnas se recalculan
    cols = lector.columnas(hoja, fila_encabezado, dos_filas)
    indices = {c.indice for c in cols}
    titulo = base.titulo if base.titulo in indices else lector.columna_titulo_sugerida(cols)
    elegidas = [i for i in base.columnas if i in indices] or [c.indice for c in cols]
    estado.poner_config(indice, imp.ConfigHoja(fila_encabezado, dos_filas, elegidas, titulo, base.clave, base.nombre_tabla))
    imp.guardar(estado)
    return _paso(request, con, estado, 4)


@router.post("/importar/{token}/columnas")
def asistente_columnas(request: Request, token: str, columnas: list[int] = Form(default=[]),
                       titulo: int | None = Form(None), clave: str = Form(""), nombre_tabla: str = Form(""),
                       con: sqlite3.Connection = Depends(obtener_db)):
    estado = imp.cargar(token)
    indice = estado.hoja_actual
    cfg = estado.config_hoja(indice)
    cfg.columnas, cfg.titulo = columnas, titulo
    cfg.clave = int(clave) if clave.isdigit() else None
    cfg.nombre_tabla = " ".join(nombre_tabla.split())[:80]
    estado.poner_config(indice, cfg)
    imp.guardar(estado)
    error = None
    if not cfg.nombre_tabla:
        error = "Escribe un nombre descriptivo para la tabla."
    elif not columnas:
        error = "Elige al menos una columna para importar."
    elif titulo is None or titulo not in columnas:
        error = "Elige cuál columna es el título de cada ficha (debe estar marcada para importar)."
    if error:
        return _paso(request, con, estado, 4, error)
    if estado.actual < len(estado.seleccion) - 1:
        estado.actual += 1
        imp.guardar(estado)
        return _paso(request, con, estado, 3)
    return _paso(request, con, estado, 5)


@router.post("/importar/{token}/anterior")
def asistente_anterior(request: Request, token: str, con: sqlite3.Connection = Depends(obtener_db)):
    """Desde el paso 3 de una hoja que no es la primera, vuelve al paso 4 de la hoja anterior."""
    estado = imp.cargar(token)
    if estado.actual > 0:
        estado.actual -= 1
        imp.guardar(estado)
        return _paso(request, con, estado, 4)
    return _paso(request, con, estado, 2)


@router.post("/importar/{token}/confirmar")
def asistente_confirmar(request: Request, token: str, con: sqlite3.Connection = Depends(obtener_db)):
    estado = imp.cargar(token)
    if estado.es_reemplazo:
        r = tab.reemplazar(con, estado)
        partes = [f"{r.actualizadas} actualizadas", f"{r.nuevas} nuevas"]
        if r.eliminadas:
            partes.append(f"{r.eliminadas} quitadas")
        if r.conservadas:
            partes.append(f"{r.conservadas} conservadas por tener imágenes")
        return redirigir(request, f"/tablas/{estado.tabla_id}", "Tabla actualizada: " + ", ".join(partes) + ".")
    ids = tab.importar(con, estado)
    texto = "Tabla importada." if len(ids) == 1 else f"{len(ids)} tablas importadas."
    return redirigir(request, f"/tablas/{ids[0]}", texto)


@router.post("/importar/{token}/cancelar")
def asistente_cancelar(token: str):
    imp.descartar(token)
    return Response(status_code=204)


# ===================================================================== tablas
def _consulta_desde(request: Request, t) -> tab.Consulta:
    p = request.query_params
    def entero(nombre: str, defecto: int) -> int:
        try:
            return int(p.get(nombre, defecto))
        except ValueError:
            return defecto
    filtros = {k[2:]: v for k, v in p.items() if k.startswith("f_") and v.strip()}
    return tab.Consulta(q=p.get("q", ""), filtros=filtros, orden=p.get("orden", ""), desc=p.get("desc") == "1",
                        solo_imagenes=p.get("imgs") == "1", pagina=entero("pagina", 1), por_pagina=entero("por_pagina", 50))


@router.get("/tablas/{tabla_id}")
def ver_tabla(request: Request, tabla_id: int, con: sqlite3.Connection = Depends(obtener_db)):
    t = tab.obtener(con, tabla_id)
    consulta = _consulta_desde(request, t)
    filas, total = tab.consultar(con, t, consulta)
    columnas = sorted(t.columnas, key=lambda c: c["clave"] != t.columna_titulo)  # el título primero
    contexto = dict(tabla=t, filas=filas, total=total, consulta=consulta, columnas=columnas,
                    paginas=max(1, -(-total // consulta.por_pagina)), por_pagina_opciones=tab.POR_PAGINA)
    if request.headers.get("HX-Target") == "region-tabla":
        return parcial(request, "parciales/tabla_region.html", **contexto)
    c = bib.obtener_componente(con, t.componente_id)
    from ..services import favoritos as fav
    fav.registrar_visita(con, "tabla", t.id)
    from ..services import etiquetas as etq
    return pagina(request, con, "paginas/tabla.html", **contexto, componente=c, etiquetas=etq.de(con, "tabla", t.id),
                  migas=_migas_componente(con, c.id, "excel") + [{"texto": t.nombre, "icono": "table"}], materia_activa=c.materia_id)


@router.get("/tablas/{tabla_id}/descargar")
def descargar_tabla(tabla_id: int, con: sqlite3.Connection = Depends(obtener_db)):
    t = tab.obtener(con, tabla_id)
    ruta = bib.carpeta_componente(con, bib.obtener_componente(con, t.componente_id)) / t.archivo
    if not ruta.exists():
        raise NoEncontrado("El archivo original")
    return FileResponse(ruta, filename=ruta.name)


@router.get("/tablas/{tabla_id}/renombrar")
def formulario_renombrar(request: Request, tabla_id: int, con: sqlite3.Connection = Depends(obtener_db)):
    t = tab.obtener(con, tabla_id)
    return parcial(request, "parciales/modal_nombre.html", titulo="Cambiar nombre de la tabla",
                   accion=f"/tablas/{t.id}/renombrar", valor=t.nombre)


@router.post("/tablas/{tabla_id}/renombrar")
def renombrar_tabla(request: Request, tabla_id: int, nombre: str = Form(""), con: sqlite3.Connection = Depends(obtener_db)):
    try:
        tab.renombrar(con, tabla_id, nombre)
    except ErrorUsuario as e:
        return parcial(request, "parciales/modal_nombre.html", titulo="Cambiar nombre de la tabla",
                       accion=f"/tablas/{tabla_id}/renombrar", valor=nombre, error=e.mensaje)
    return redirigir(request, f"/tablas/{tabla_id}", "Nombre actualizado.")


@router.get("/tablas/{tabla_id}/titulo")
def formulario_titulo(request: Request, tabla_id: int, con: sqlite3.Connection = Depends(obtener_db)):
    t = tab.obtener(con, tabla_id)
    ejemplos = {c["clave"]: [r[0] for r in con.execute(
        "SELECT json_extract(valores, '$.' || ?) FROM filas WHERE tabla_id=? ORDER BY posicion LIMIT 3", (c["clave"], t.id))]
        for c in t.columnas}
    return parcial(request, "parciales/modal_titulo.html", tabla=t, ejemplos=ejemplos)


@router.post("/tablas/{tabla_id}/titulo")
def cambiar_titulo(request: Request, tabla_id: int, clave: str = Form(""), con: sqlite3.Connection = Depends(obtener_db)):
    t = tab.cambiar_titulo(con, tabla_id, clave)
    nombre = next(c["nombre"] for c in t.columnas if c["clave"] == clave)
    return redirigir(request, f"/tablas/{t.id}", f"Las fichas ahora se titulan con «{nombre}».")


@router.get("/tablas/{tabla_id}/eliminar")
def confirmar_eliminar_tabla(request: Request, tabla_id: int, con: sqlite3.Connection = Depends(obtener_db)):
    t = tab.obtener(con, tabla_id)
    detalle = f"Tiene {t.num_filas} filas" + (f" y {t.num_imagenes} imágenes" if t.num_imagenes else "") + \
        ". Podrás restaurarla desde la papelera mientras no la vacíes."
    return parcial(request, "parciales/modal_confirmar.html", titulo=f"¿Enviar «{t.nombre}» a la papelera?",
                   detalle=detalle, accion=f"/tablas/{t.id}/eliminar", boton="Enviar a la papelera")


@router.post("/tablas/{tabla_id}/eliminar")
def eliminar_tabla(request: Request, tabla_id: int, con: sqlite3.Connection = Depends(obtener_db)):
    nombre, componente_id = pap.enviar_tabla(con, tabla_id)
    return redirigir(request, f"/componentes/{componente_id}", f"«{nombre}» se envió a la papelera.")


@router.get("/tablas/{tabla_id}/huerfanas/eliminar")
def confirmar_huerfanas(request: Request, tabla_id: int, con: sqlite3.Connection = Depends(obtener_db)):
    t = tab.obtener(con, tabla_id)
    return parcial(request, "parciales/modal_confirmar.html",
                   titulo=f"¿Quitar {t.num_huerfanas} fila{'s' if t.num_huerfanas != 1 else ''} que ya no están en el Excel?",
                   detalle="Se conservaron porque tenían imágenes. Sus imágenes se moverán a la papelera.",
                   accion=f"/tablas/{t.id}/huerfanas/eliminar", boton="Quitar filas")


@router.post("/tablas/{tabla_id}/huerfanas/eliminar")
def eliminar_huerfanas(request: Request, tabla_id: int, con: sqlite3.Connection = Depends(obtener_db)):
    n = tab.eliminar_huerfanas(con, tabla_id)
    return redirigir(request, f"/tablas/{tabla_id}", f"Se quitaron {n} fila{'s' if n != 1 else ''}.")


# ======================================================================= fichas
@router.get("/filas/{fila_id}")
def ver_fila(request: Request, fila_id: int, con: sqlite3.Connection = Depends(obtener_db)):
    fila = tab.obtener_fila(con, fila_id)
    t = tab.obtener(con, fila.tabla_id)
    c = bib.obtener_componente(con, t.componente_id)
    anterior, siguiente = tab.vecinas(con, fila)
    from ..services import etiquetas as etq
    from ..services import favoritos as fav
    fav.registrar_visita(con, "fila", fila.id)
    return pagina(request, con, "paginas/fila.html", fila=fila, tabla=t, imagenes=imf.listar(con, fila.id),
                  favorito=fav.es_favorito(con, "fila", fila.id), etiquetas=etq.de(con, "fila", fila.id),
                  anterior=anterior, siguiente=siguiente, materia_activa=c.materia_id,
                  migas=_migas_componente(con, c.id, "excel") + [{"texto": t.nombre, "url": f"/tablas/{t.id}", "icono": "table",
                                                                  "tabla": t.id},
                                                                 {"texto": fila.titulo, "icono": "list"}])


def _galeria(request: Request, con: sqlite3.Connection, fila_id: int, mensaje: str | None = None, tipo: str = "exito"):
    respuesta = parcial(request, "parciales/galeria_fila.html", fila=tab.obtener_fila(con, fila_id),
                        imagenes=imf.listar(con, fila_id))
    if mensaje:
        respuesta.headers["HX-Trigger"] = json.dumps({"aviso": {"mensaje": mensaje, "tipo": tipo},
                                                      "cerrar-modal": True}, ensure_ascii=False)
    return respuesta


@router.post("/filas/{fila_id}/imagenes")
async def subir_imagenes(request: Request, fila_id: int, archivos: list[UploadFile] = File(default=[]),
                         titulos: list[str] = Form(default=[]), pies: list[str] = Form(default=[]),
                         con: sqlite3.Connection = Depends(obtener_db)):
    tab.obtener_fila(con, fila_id)
    if not archivos:
        raise ErrorUsuario("Elige al menos una imagen.")
    if len(titulos) != len(archivos) or not all(" ".join(t.split()) for t in titulos):
        raise ErrorUsuario("Escribe un nombre descriptivo para cada imagen.")
    agregadas, avisos = 0, []
    for archivo, titulo, pie in zip(archivos, titulos, pies + [""] * len(archivos)):
        try:
            tmp = await guardar_subida(archivo, imf.MAX_BYTES)
            try:
                img, nota = imf.agregar(con, fila_id, archivo.filename or "imagen", tmp, titulo, pie)
            finally:
                tmp.unlink(missing_ok=True)
            agregadas += img is not None
            if nota:
                avisos.append(nota)
        except ErrorUsuario as e:
            avisos.append(e.mensaje)
    mensaje = ("1 imagen agregada." if agregadas == 1 else f"{agregadas} imágenes agregadas."
               if agregadas else "No se agregó ninguna imagen.")
    if avisos:
        mensaje += " " + " ".join(avisos)
    return _galeria(request, con, fila_id, mensaje, "exito" if agregadas and not avisos else "aviso" if agregadas else "error")


@router.post("/filas/{fila_id}/imagenes/orden")
def ordenar_imagenes(fila_id: int, ids: list[int] = Body(..., embed=True), con: sqlite3.Connection = Depends(obtener_db)):
    imf.reordenar(con, fila_id, ids)
    return aviso("Orden guardado.")


@router.get("/imagenes-fila/{imagen_id}/editar")
def formulario_imagen(request: Request, imagen_id: int, con: sqlite3.Connection = Depends(obtener_db)):
    return parcial(request, "parciales/modal_imagen.html", imagen=imf.obtener(con, imagen_id))


@router.post("/imagenes-fila/{imagen_id}")
def editar_imagen(request: Request, imagen_id: int, titulo: str = Form(""), pie: str = Form(""),
                  con: sqlite3.Connection = Depends(obtener_db)):
    img = imf.obtener(con, imagen_id)
    try:
        imf.editar(con, imagen_id, titulo, pie)
    except ErrorUsuario as e:
        respuesta = parcial(request, "parciales/modal_imagen.html", imagen=img, error=e.mensaje,
                            valores={"titulo": titulo, "pie": pie})
        respuesta.headers.update({"HX-Retarget": "closest dialog", "HX-Reswap": "outerHTML"})
        return respuesta
    return _galeria(request, con, img.fila_id, "Imagen actualizada.")


@router.post("/imagenes-fila/{imagen_id}/eliminar")
def eliminar_imagen(request: Request, imagen_id: int, con: sqlite3.Connection = Depends(obtener_db)):
    img = imf.enviar_a_papelera(con, imagen_id)
    return _galeria(request, con, img.fila_id, f"«{img.titulo}» se envió a la papelera.")


@router.get("/imagenes-fila/{imagen_id}/archivo")
def archivo_imagen(imagen_id: int, con: sqlite3.Connection = Depends(obtener_db)):
    img = imf.obtener(con, imagen_id)
    ruta = imf.ruta(con, img)
    if not ruta.exists():
        raise NoEncontrado("El archivo de la imagen")
    return FileResponse(ruta, headers={"Cache-Control": "private, max-age=3600"})


@router.get("/imagenes-fila/{imagen_id}/miniatura")
def miniatura_imagen(imagen_id: int, con: sqlite3.Connection = Depends(obtener_db)):
    img = imf.obtener(con, imagen_id)
    ruta = imf.ruta(con, img)
    mini = miniaturas.obtener(ruta, img.hash) if ruta.exists() else None
    if mini is None:
        return FileResponse(ruta) if ruta.exists() else HTMLResponse(status_code=404)
    return FileResponse(mini, media_type="image/webp", headers={"Cache-Control": "private, max-age=86400"})

"""Carga en la biblioteca lo que describe un plan (notas, imágenes, tablas de Excel y PDF) de un componente.

    .venv/bin/python tools/carga/cargar.py <plan.json> --prueba       # sobre una copia temporal de data/
    .venv/bin/python tools/carga/cargar.py <plan.json>                # de verdad (hace un respaldo antes)
    .venv/bin/python tools/carga/cargar.py <plan.json> --reemplazar   # actualiza lo que ya existe con el mismo título

Formato del plan (rutas relativas a la carpeta del plan; ver .claude/skills/cargar-material/plan.md):
{
  "materia": "Oxigenoterapia",
  "componente": "HBO",                         # subcomponentes: "Parcial 1 › Atlas"
  "crear_componente": {"tipos": ["excel", "imagenes", "notas"], "descripcion": ""},   # opcional
  "fuentes": ["hojas/HBO.xlsx"],               # lo que se audita al final
  "correcciones": {"Comprension": "Compresión"},
  "omitidos": [{"celda": "HBO!Z1", "motivo": "…"}],
  "notas":    [{"titulo": "…", "archivo": "notas/….md", "celdas": ["A1:E16"], "etiquetas": ""}],
  "imagenes": [{"archivo": "imagenes/HBO - A36.png", "titulo": "…", "descripcion": "…", "celda": "A36"}],
  "tablas":   [{"archivo": "hojas/….xlsx", "nombre": "…", "columna_titulo": "Nombre", "etiquetas": "Flores de Bach"}],
  "pdfs":     [{"archivo": "pdf/….pdf", "titulo": "…"}]
}
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import comun  # noqa: F401


def _args():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan", type=Path)
    ap.add_argument("--prueba", action="store_true", help="cargar sobre una copia temporal de data/")
    ap.add_argument("--reemplazar", action="store_true", help="actualizar elementos existentes con el mismo título")
    return ap.parse_args()


ARGS = _args()
if ARGS.prueba:  # antes de importar la app: la carpeta de datos se fija al importarla
    origen = Path(os.environ.get("BIBLIOTECA_DATOS", comun.RAIZ / "data"))
    copia = Path(tempfile.mkdtemp(prefix="carga-prueba-")) / "data"
    shutil.copytree(origen, copia, ignore=shutil.ignore_patterns("respaldos", "cache", "logs", ".en_uso"))
    os.environ["BIBLIOTECA_DATOS"] = str(copia)

from app import db  # noqa: E402
from app.errores import ErrorUsuario  # noqa: E402
from app.services import biblioteca as bib  # noqa: E402
from app.services import etiquetas as etq  # noqa: E402
from app.services import imagenes, notas, pdfs, respaldos, tablas  # noqa: E402
from app.services import hojas as lector  # noqa: E402
from app.services import importacion as imp  # noqa: E402
from app.services.texto import normalizar  # noqa: E402
import resolver  # noqa: E402


def _materia(con, nombre: str) -> int:
    mid = resolver.materia_id(con, nombre)
    if mid is None:
        raise SystemExit(f"No existe la materia «{nombre}». Créala en la app (o revisa el nombre) antes de cargar.")
    return mid


def _componente(con, materia_id: int, ruta: str, crear: dict | None) -> int:
    padre = None
    partes = resolver.partes_componente(ruta)
    for i, nombre in enumerate(partes):
        hallado = resolver.buscar_hijo(con, materia_id, padre, nombre)
        if hallado is None:
            if crear is None:
                raise SystemExit(f"No existe el componente «{nombre}». Agrega \"crear_componente\" al plan o créalo en la app.")
            ultimo = i == len(partes) - 1
            hallado = bib.crear_componente(con, materia_id, padre, nombre, crear.get("descripcion", "") if ultimo else "",
                                           crear.get("tipos", []) if ultimo else [])
            print(f"  componente creado: {nombre}")
        padre = hallado
    return padre


def _asegurar_tipo(con, componente_id: int, tipo: str) -> None:
    c = bib.obtener_componente(con, componente_id)
    if tipo not in c.tipos:
        bib.editar_componente(con, c.id, c.nombre, c.descripcion, [*c.tipos, tipo])


def _limpiar_version_anterior(con, tabla_id: int, nombre: str) -> None:
    """Al recargar una tabla, la app deja el Excel anterior en la papelera y guarda el nuevo como «… (2).xlsx».
    Ese Excel anterior es una copia generada por la carga (la fuente sigue en data/fuentes/): se elimina y el
    nuevo recupera el nombre limpio."""
    from app.services import papelera
    for f in con.execute("SELECT id FROM papelera WHERE tipo='archivo' AND nombre LIKE ?",
                         (f"%(versión anterior de «{nombre}»)",)).fetchall():
        papelera.eliminar_definitivo(con, f["id"])
    t = tablas.obtener(con, tabla_id)
    carpeta = bib.carpeta_componente(con, bib.obtener_componente(con, t.componente_id))
    actual = carpeta / t.archivo
    limpio = actual.with_name(re.sub(r" \(\d+\)(?=\.\w+$)", "", actual.name))
    if actual != limpio and not limpio.exists():
        actual.rename(limpio)
        con.execute("UPDATE tablas SET archivo=? WHERE id=?", (f"excel/{limpio.name}", tabla_id))


def _contenido_nota(base: Path, n: dict) -> str:
    if "archivo" in n:
        return (base / n["archivo"]).read_text(encoding="utf-8")
    return n["contenido"]


def cargar(plan_ruta: Path, reemplazar: bool) -> dict:
    plan = json.loads(plan_ruta.read_text(encoding="utf-8"))
    base = plan_ruta.parent
    con = db.conectar()
    mid = _materia(con, plan["materia"])
    cid = _componente(con, mid, plan["componente"], plan.get("crear_componente"))
    hecho = {"plan": str(plan_ruta), "fecha": datetime.now().isoformat(timespec="seconds"), "componente_id": cid,
             "notas": [], "imagenes": [], "tablas": [], "pdfs": []}

    if plan.get("notas"):
        _asegurar_tipo(con, cid, "notas")
    for n in plan.get("notas", []):
        contenido = _contenido_nota(base, n).strip() + "\n"
        previa = con.execute("SELECT id FROM notas WHERE componente_id=? AND titulo=? AND papelera_id IS NULL",
                             (cid, n["titulo"])).fetchone()
        if previa and not reemplazar:
            raise SystemExit(f"Ya existe la nota «{n['titulo']}». Usa --reemplazar para actualizarla.")
        nota = (notas.editar(con, previa["id"], n["titulo"], contenido, "markdown", n.get("etiquetas", "")) if previa
                else notas.crear(con, cid, n["titulo"], contenido, "markdown", n.get("etiquetas", "")))
        hecho["notas"].append(nota.id)
        print(f"  nota {'actualizada' if previa else 'creada'}: {nota.titulo}")

    if plan.get("imagenes"):
        _asegurar_tipo(con, cid, "imagenes")
    for i in plan.get("imagenes", []):
        archivo = base / i["archivo"]
        previa = con.execute("SELECT id FROM imagenes WHERE componente_id=? AND titulo=? AND papelera_id IS NULL",
                             (cid, i["titulo"])).fetchone()
        if previa and not reemplazar:
            raise SystemExit(f"Ya existe la imagen «{i['titulo']}». Usa --reemplazar para actualizarla.")
        if previa:
            img = imagenes.editar(con, previa["id"], i["titulo"], i.get("descripcion", ""), i.get("etiquetas", ""))
        else:
            img, aviso = imagenes.agregar(con, cid, archivo.name, archivo, i["titulo"], i.get("descripcion", ""),
                                          i.get("etiquetas", ""), extraer_texto=bool(i.get("ocr")))
            if aviso:
                print(f"  aviso: {aviso}")
        hecho["imagenes"].append(img.id)
        print(f"  imagen {'actualizada' if previa else 'agregada'}: {img.titulo}")

    if plan.get("tablas"):
        _asegurar_tipo(con, cid, "excel")
    for t in plan.get("tablas", []):
        archivo = base / t["archivo"]
        temporal = Path(tempfile.mkdtemp()) / archivo.name
        shutil.copy2(archivo, temporal)
        previa = con.execute("SELECT id FROM tablas WHERE componente_id=? AND nombre=? AND papelera_id IS NULL",
                             (cid, t["nombre"])).fetchone()
        if previa and not reemplazar:
            raise SystemExit(f"Ya existe la tabla «{t['nombre']}». Usa --reemplazar para actualizarla.")
        estado = imp.crear(con, cid, archivo.name, temporal, t["nombre"], tabla_id=previa["id"] if previa else None)
        hojas = imp.hojas(estado)
        indice = next((k for k, h in enumerate(hojas) if h.nombre == t.get("hoja")), estado.seleccion[0] if estado.seleccion else 0)
        estado.seleccion = [indice]
        anterior = None
        if previa:
            ta = tablas.obtener(con, previa["id"])
            anterior = {"columnas": ta.columnas, "columna_titulo": ta.columna_titulo, "columna_clave": ta.columna_clave}
        cfg = imp.config_sugerida(estado, indice, hojas[indice], anterior)
        if "fila_encabezado" in t:
            cfg.fila_encabezado = t["fila_encabezado"]
        cols = lector.columnas(hojas[indice], cfg.fila_encabezado, cfg.dos_filas)
        cfg.columnas = [c.indice for c in cols]
        if t.get("columna_titulo"):
            elegida = next((c.indice for c in cols if normalizar(c.nombre) == normalizar(t["columna_titulo"])), None)
            if elegida is None:
                raise SystemExit(f"La tabla «{t['nombre']}» no tiene la columna «{t['columna_titulo']}».")
            cfg.titulo = elegida
        cfg.nombre_tabla = t["nombre"]
        estado.poner_config(indice, cfg)
        imp.guardar(estado)
        if previa:
            print(f"  tabla actualizada: {t['nombre']} {tablas.reemplazar(con, estado)}")
            ids = [previa["id"]]
            _limpiar_version_anterior(con, previa["id"], t["nombre"])
        else:
            ids = tablas.importar(con, estado)
            print(f"  tabla importada: {t['nombre']}")
        if "etiquetas" in t:
            for tid in ids:
                etq.asignar(con, "tabla", tid, t["etiquetas"])
        hecho["tablas"] += ids

    if plan.get("pdfs"):
        _asegurar_tipo(con, cid, "pdf")
    for p in plan.get("pdfs", []):
        archivo = base / p["archivo"]
        previo = con.execute("SELECT id, hash FROM pdfs WHERE componente_id=? AND titulo=? AND papelera_id IS NULL",
                             (cid, p["titulo"])).fetchone()
        if previo:
            from app.services import almacenamiento as alm
            if previo["hash"] == alm.hash_archivo(archivo):  # ya está cargado ese mismo PDF: no se duplica
                hecho["pdfs"].append(previo["id"])
                print(f"  pdf sin cambios: {p['titulo']}")
                continue
            raise SystemExit(f"Ya existe un PDF «{p['titulo']}» con otro contenido. Cámbialo en la app o usa otro título.")
        temporal = Path(tempfile.mkdtemp()) / archivo.name
        shutil.copy2(archivo, temporal)
        pdf, aviso = pdfs.agregar(con, cid, archivo.name, temporal, p["titulo"])
        hecho["pdfs"].append(pdf.id)
        print(f"  pdf agregado: {pdf.titulo}" + (f" ({aviso})" if aviso else ""))
    return hecho


def main() -> None:
    from app.config import rutas
    if ARGS.prueba:
        print(f"PRUEBA sobre una copia: BIBLIOTECA_DATOS={rutas.datos}")
    else:
        print(f"Respaldo previo: {respaldos.crear('antes-de-cargar').nombre}")
    try:
        hecho = cargar(ARGS.plan, ARGS.reemplazar)
    except ErrorUsuario as e:
        raise SystemExit(f"Error: {e.mensaje}") from e
    if not ARGS.prueba:
        carpeta = ARGS.plan.parent / "cargas"
        carpeta.mkdir(exist_ok=True)
        (carpeta / f"{datetime.now():%Y-%m-%d_%H-%M-%S}.json").write_text(json.dumps(hecho, ensure_ascii=False, indent=2), "utf-8")
    print(json.dumps(hecho, ensure_ascii=False))
    if ARGS.prueba:
        print(f"\nPara auditar la prueba: BIBLIOTECA_DATOS={rutas.datos} .venv/bin/python tools/carga/auditar.py {ARGS.plan}")


if __name__ == "__main__":
    main()
    sys.exit(0)

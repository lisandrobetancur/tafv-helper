"""Fase 6: favoritos, recientes, etiquetas en filas/PDF, modo repaso, respaldos y mantenimiento."""
from __future__ import annotations

import sqlite3
import zipfile
from pathlib import Path

import pymupdf
import pytest
from openpyxl import Workbook
from PIL import Image

from app import config, db
from app.errores import ErrorUsuario
from app.services import biblioteca as bib
from app.services import busqueda as bus
from app.services import etiquetas as etq
from app.services import favoritos as fav
from app.services import imagenes_fila as imf
from app.services import importacion as imp
from app.services import notas as notas_srv
from app.services import papelera as pap
from app.services import pdfs, repaso, respaldos
from app.services import tablas as tab


@pytest.fixture()
def base(con: sqlite3.Connection, tmp_path: Path) -> dict:
    ids: dict = {}
    ids["materia"] = bib.crear_materia(con, "Farmacología", "", "verde", "pill")
    ids["comp"] = bib.crear_componente(con, ids["materia"], None, "Antibióticos", "", ["excel", "pdf", "notas"])
    wb = Workbook()
    ws = wb.active
    ws.append(["Fármaco", "Mecanismo", "Efecto adverso"])
    for fila in [["Amoxicilina", "Inhibe la pared celular", "Diarrea"], ["Gentamicina", "Inhibe la subunidad 30S", "Ototoxicidad"],
                 ["Vancomicina", "Inhibe la pared celular", "Síndrome del hombre rojo"]]:
        ws.append(fila)
    wb.save(tmp_path / "antibioticos.xlsx")
    tmp = tmp_path / "subida.xlsx"
    tmp.write_bytes((tmp_path / "antibioticos.xlsx").read_bytes())
    estado = imp.crear(con, ids["comp"], "antibioticos.xlsx", tmp, "Antibióticos")
    estado.poner_config(0, imp.config_sugerida(estado, 0, imp.hojas(estado)[0]))
    imp.guardar(estado)
    [ids["tabla"]] = tab.importar(con, estado)
    filas = tab.consultar(con, tab.obtener(con, ids["tabla"]), tab.Consulta())[0]
    ids["filas"] = {f.titulo: f.id for f in filas}
    doc = pymupdf.open()
    doc.new_page().insert_text((72, 100), "Betalactámicos", fontsize=12)
    doc.save(tmp_path / "guia.pdf")
    ids["pdf"] = pdfs.agregar(con, ids["comp"], "guia.pdf", tmp_path / "guia.pdf", "Guía de antibióticos")[0].id
    ids["nota"] = notas_srv.crear(con, ids["comp"], "Resumen", "Espectro").id
    return ids


# ------------------------------------------------------------- favoritos
def test_favoritos(con, base) -> None:
    amox = base["filas"]["Amoxicilina"]
    assert fav.alternar(con, "fila", amox) is True and fav.es_favorito(con, "fila", amox)
    assert fav.alternar(con, "pdf", base["pdf"]) is True
    lista = fav.favoritos(con)
    assert [(e.tipo, e.titulo) for e in lista] == [("pdf", "Guía de antibióticos"), ("fila", "Amoxicilina")]
    assert lista[1].url == f"/filas/{amox}" and lista[1].ubicacion == "Farmacología › Antibióticos"
    # filtro de la búsqueda
    assert [r.tipo for r in bus.buscar(con, "inhibe", bus.Filtros(favoritos=True)).resultados] == ["fila"]
    assert fav.alternar(con, "fila", amox) is False
    with pytest.raises(ErrorUsuario):
        fav.alternar(con, "materia", base["materia"])
    # lo que va a la papelera desaparece de la lista; lo borrado del todo se limpia solo
    pap.enviar_pdf(con, base["pdf"])
    assert fav.favoritos(con) == []
    pap.vaciar(con)
    assert con.execute("SELECT COUNT(*) FROM favoritos").fetchone()[0] == 0


def test_recientes(con, base) -> None:
    for tipo, ref in [("fila", base["filas"]["Amoxicilina"]), ("pdf", base["pdf"]), ("nota", base["nota"]),
                      ("fila", base["filas"]["Amoxicilina"])]:
        fav.registrar_visita(con, tipo, ref)
    assert [e.titulo for e in fav.recientes(con)] == ["Amoxicilina", "Resumen", "Guía de antibióticos"]
    for i in range(fav.MAX_RECIENTES + 10):
        fav.registrar_visita(con, "tabla", 1000 + i)
    assert con.execute("SELECT COUNT(*) FROM recientes").fetchone()[0] == fav.MAX_RECIENTES
    # Limpiar la lista no toca los elementos
    assert fav.limpiar_recientes(con) == fav.MAX_RECIENTES
    assert fav.recientes(con) == [] and fav.favoritos(con) == []
    assert con.execute("SELECT COUNT(*) FROM filas WHERE id=?", (base["filas"]["Amoxicilina"],)).fetchone()[0] == 1


def test_limpiar_recientes_desde_inicio(cliente) -> None:
    from app import db
    from app.services import biblioteca as bib
    from app.services import notas as notas_srv
    con = db.conectar()
    mid = bib.crear_materia(con, "Anatomía", "", "azul", "bone")
    cid = bib.crear_componente(con, mid, None, "Parcial", "", ["notas"])
    nota = notas_srv.crear(con, cid, "Resumen", "texto")
    cliente.get(f"/notas/{nota.id}")
    inicio = cliente.get("/").text
    assert "Abiertos recientemente" in inicio and 'hx-post="/recientes/limpiar"' in inicio
    r = cliente.post("/recientes/limpiar", headers={"HX-Request": "true"})
    assert r.headers["HX-Redirect"] == "/"
    assert con.execute("SELECT COUNT(*) FROM recientes").fetchone()[0] == 0
    assert "Abiertos recientemente" not in cliente.get("/").text

    cliente.post(f"/favoritos/nota/{nota.id}", headers={"HX-Request": "true"})
    assert 'hx-post="/favoritos/limpiar"' in cliente.get("/").text
    r = cliente.post("/favoritos/limpiar", headers={"HX-Request": "true"})
    assert r.headers["HX-Redirect"] == "/"
    assert con.execute("SELECT COUNT(*) FROM favoritos").fetchone()[0] == 0
    assert notas_srv.obtener(con, nota.id).titulo == "Resumen"          # la nota sigue ahí
    con.close()


# ------------------------------------------------------------- etiquetas
def test_etiquetas_en_filas_y_pdf_buscables(con, base) -> None:
    etq.asignar(con, "fila", base["filas"]["Gentamicina"], "aminoglucósido, examen")
    etq.asignar(con, "pdf", base["pdf"], "examen")
    assert bus.buscar(con, "aminoglucosido").resultados[0].titulo.striptags() == "Gentamicina"
    assert {r.tipo for r in bus.buscar(con, "betalactamicos", bus.Filtros(etiqueta="Examen")).resultados} == {"pagina"}
    assert {r.tipo for r in bus.buscar(con, "examen").resultados} == {"fila", "pdf"}
    etq.asignar(con, "fila", base["filas"]["Gentamicina"], "")
    etq.limpiar_huerfanas(con)
    assert bus.buscar(con, "aminoglucosido").total == 0


def test_etiquetas_de_tabla(con, base) -> None:
    """La etiqueta de una tabla la clasifica y vale para todas sus fichas al filtrar."""
    etq.asignar(con, "tabla", base["tabla"], "infectología")
    etq.asignar(con, "nota", base["nota"], "Infectologia")                  # misma etiqueta (sin importar tildes)
    con_texto = bus.buscar(con, "inhibe", bus.Filtros(etiqueta="infectología"))
    assert {r.titulo.striptags() for r in con_texto.resultados} == {"Amoxicilina", "Gentamicina", "Vancomicina"}
    assert bus.buscar(con, "infectologia").resultados[0].tipo == "tabla"   # la etiqueta se busca como texto
    relacionado = bus.buscar(con, "", bus.Filtros(etiqueta="Infectología"))  # sin texto: todo lo relacionado
    assert relacionado.total == 5 and [r.tipo for r in relacionado.resultados][:2] == ["tabla", "fila"]
    assert {r.tipo for r in relacionado.resultados} == {"tabla", "fila", "nota"}
    assert bus.buscar(con, "", bus.Filtros()).total == 0                     # sin texto ni etiqueta: nada
    pap.enviar_tabla(con, base["tabla"])
    assert {r.tipo for r in bus.buscar(con, "", bus.Filtros(etiqueta="infectología")).resultados} == {"nota"}
    pap.vaciar(con)
    assert con.execute("SELECT COUNT(*) FROM etiquetas_elemento WHERE tipo='tabla'").fetchone()[0] == 0


# ---------------------------------------------------------------- repaso
def test_repaso(con, base, tmp_path: Path) -> None:
    t = tab.obtener(con, base["tabla"])
    frente, reverso = t.claves[0], t.claves[2]
    Image.new("RGB", (30, 30), "red").save(tmp_path / "i.png")
    imf.agregar(con, base["filas"]["Vancomicina"], "i.png", tmp_path / "i.png", "Eritema")
    cartas = repaso.tarjetas(con, t, frente, reverso, barajar=False)
    assert [(c["frente"], c["reverso"]) for c in cartas][:2] == [("Amoxicilina", "Diarrea"), ("Gentamicina", "Ototoxicidad")]
    assert cartas[2]["imagenes"][0]["titulo"] == "Eritema"
    repaso.marcar(con, base["filas"]["Amoxicilina"], "lo_se")
    repaso.marcar(con, base["filas"]["Gentamicina"], "repasar")
    assert [c["frente"] for c in repaso.tarjetas(con, t, frente, reverso, "repasar")] == ["Gentamicina"]
    assert [c["frente"] for c in repaso.tarjetas(con, t, frente, reverso, "sin_marcar")] == ["Vancomicina"]
    assert repaso.resumen(con, t.id) == {"total": 3, "lo_se": 1, "repasar": 1, "sin_marcar": 1}
    with pytest.raises(ErrorUsuario):
        repaso.tarjetas(con, t, frente, frente)
    with pytest.raises(ErrorUsuario):
        repaso.marcar(con, base["filas"]["Amoxicilina"], "quizas")
    repaso.reiniciar(con, t.id)
    assert repaso.resumen(con, t.id)["sin_marcar"] == 3


# -------------------------------------------------------------- respaldos
def test_respaldo_y_restauracion(con, base, datos: Path) -> None:
    con.close()
    r = respaldos.crear()
    assert r.ruta.exists() and r.ruta.parent == datos / "respaldos"
    with zipfile.ZipFile(r.ruta) as z:
        nombres = z.namelist()
    assert "biblioteca.db" in nombres and "respaldo.json" in nombres
    assert "archivos/farmacologia/antibioticos/pdf/Guía de antibióticos.pdf" in nombres
    assert not any(n.startswith(("cache/", "respaldos/", "logs/")) for n in nombres)

    # Cambios después del respaldo: una materia nueva y el PDF a la papelera
    c2 = db.conectar()
    bib.crear_materia(c2, "Fisiología", "", "azul", "activity")
    pap.enviar_pdf(c2, base["pdf"])
    c2.close()
    previo = respaldos.restaurar(r.ruta)
    assert previo.nombre.startswith("antes-de-restaurar-")

    c3 = db.conectar()
    try:
        assert [m.nombre for m in bib.listar_materias(c3)] == ["Farmacología"]
        assert pdfs.ruta(c3, pdfs.obtener(c3, base["pdf"])).exists()
        assert bus.buscar(c3, "betalactamicos").total == 1          # el índice viene con la BD
        assert c3.execute("PRAGMA journal_mode").fetchone()[0] == "delete"
    finally:
        c3.close()
    assert len(respaldos.listar()) == 2


def test_restaurar_rechaza_zip_malicioso_o_ajeno(datos: Path, tmp_path: Path) -> None:
    malo = tmp_path / "malo.zip"
    with zipfile.ZipFile(malo, "w") as z:
        z.writestr("respaldo.json", "{}")
        z.writestr("biblioteca.db", "x")
        z.writestr("../../fuera.txt", "x")
    with pytest.raises(ErrorUsuario, match="rutas no válidas"):
        respaldos.restaurar(malo)
    ajeno = tmp_path / "ajeno.zip"
    with zipfile.ZipFile(ajeno, "w") as z:
        z.writestr("fotos/a.jpg", "x")
    with pytest.raises(ErrorUsuario, match="no es un respaldo"):
        respaldos.restaurar(ajeno)
    (tmp_path / "no.zip").write_text("hola")
    with pytest.raises(ErrorUsuario, match="ZIP válido"):
        respaldos.restaurar(tmp_path / "no.zip")
    assert respaldos.listar() == []   # no llegó a hacer nada


# ------------------------------------------------------------------- web
def test_web(cliente, base) -> None:
    amox = base["filas"]["Amoxicilina"]
    r = cliente.post(f"/favoritos/fila/{amox}", headers={"HX-Request": "true"})
    assert "fill-current" in r.text and "Agregado a favoritos" in r.headers["HX-Trigger"]
    assert "Amoxicilina" in cliente.get(f"/filas/{amox}").text
    inicio = cliente.get("/").text
    assert "Abiertos recientemente" in inicio and "Favoritos" in inicio
    r = cliente.post(f"/etiquetas/fila/{amox}", data={"etiquetas": "penicilina"}, headers={"HX-Request": "true"})
    assert "penicilina" in r.text
    r = cliente.post(f"/etiquetas/tabla/{base['tabla']}", data={"etiquetas": "antibióticos"}, headers={"HX-Request": "true"})
    assert "antibióticos" in r.text and "/buscar?etiqueta=antibi" in r.text
    assert "antibióticos" in cliente.get(f"/tablas/{base['tabla']}").text
    assert "antibióticos" in cliente.get(f"/componentes/{base['comp']}").text
    assert "con la etiqueta" in cliente.get("/buscar", params={"etiqueta": "antibióticos"}).text
    t = tab.obtener(db.conectar(), base["tabla"])
    sesion = cliente.get(f"/tablas/{t.id}/repaso/sesion", params={"frente": t.claves[0], "reverso": t.claves[1], "barajar": "true"})
    assert "Amoxicilina" in sesion.text and 'x-data="repaso(' in sesion.text
    assert cliente.post(f"/repaso/{amox}", data={"estado": "lo_se"}).json() == {"ok": True}
    m = cliente.get("/mantenimiento").text
    assert "Crear respaldo ahora" in m and "Reconstruir índice" in m
    assert cliente.post("/mantenimiento/indice", headers={"HX-Request": "true"}).headers["HX-Redirect"] == "/mantenimiento"
    assert cliente.post("/respaldos", headers={"HX-Request": "true"}).status_code == 200
    nombre = respaldos.listar()[0].nombre
    assert cliente.get(f"/respaldos/{nombre}").headers["content-type"] == "application/zip"
    assert cliente.get("/respaldos/../../etc/passwd").status_code == 404


def test_respaldos_en_el_mismo_segundo_no_se_pisan(con, base, monkeypatch) -> None:
    from datetime import datetime as dt

    class Fijo(dt):
        @classmethod
        def now(cls, tz=None):
            return dt(2026, 10, 29, 21, 52, 45)
    monkeypatch.setattr(respaldos, "datetime", Fijo)
    a, b = respaldos.crear("antes-de-cargar"), respaldos.crear("antes-de-cargar")
    assert a.nombre == "antes-de-cargar-2026-10-29_21-52-45.zip"
    assert b.nombre == "antes-de-cargar-2026-10-29_21-52-45-2.zip"
    assert {r.nombre for r in respaldos.listar()} >= {a.nombre, b.nombre}

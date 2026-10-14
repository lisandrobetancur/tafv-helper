"""Fase 5: búsqueda global (FTS5) sin tildes, por prefijo y frase, sincronizada y rápida."""
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

import pymupdf
import pytest
from PIL import Image

from app.services import biblioteca as bib
from app.services import busqueda as bus
from app.services import imagenes as img_srv
from app.services import imagenes_fila as imf
from app.services import importacion as imp
from app.services import notas as notas_srv
from app.services import papelera as pap
from app.services import pdfs
from app.services import tablas as tab


@pytest.fixture()
def biblioteca(con: sqlite3.Connection, tmp_path: Path) -> dict:
    """Una biblioteca pequeña con un poco de todo."""
    from openpyxl import Workbook
    ids: dict = {}
    ids["anatomia"] = bib.crear_materia(con, "Anatomía", "Huesos y músculos", "azul", "bone")
    ids["cardio"] = bib.crear_materia(con, "Cardiología", "Corazón", "rojo", "heart-pulse")
    ids["parcial"] = bib.crear_componente(con, ids["anatomia"], None, "Parcial 1", "", ["excel", "pdf", "imagenes", "notas"])
    ids["sub"] = bib.crear_componente(con, ids["anatomia"], ids["parcial"], "Miembro superior", "", ["notas"])
    ids["ecg"] = bib.crear_componente(con, ids["cardio"], None, "Electrocardiograma", "", ["notas"])

    wb = Workbook()
    ws = wb.active
    ws.append(["Hueso", "Región", "Notas"])
    ws.append(["Fémur", "Miembro inferior", "El hueso más largo del cuerpo"])
    ws.append(["Húmero", "Miembro superior", "Articula con la escápula"])
    wb.save(tmp_path / "huesos.xlsx")
    tmp = tmp_path / "subida.xlsx"
    tmp.write_bytes((tmp_path / "huesos.xlsx").read_bytes())
    estado = imp.crear(con, ids["parcial"], "huesos.xlsx", tmp, "Atlas de huesos")
    estado.poner_config(0, imp.config_sugerida(estado, 0, imp.hojas(estado)[0]))
    imp.guardar(estado)
    [ids["tabla"]] = tab.importar(con, estado)
    ids["femur"] = tab.consultar(con, tab.obtener(con, ids["tabla"]), tab.Consulta(q="femur"))[0][0].id

    doc = pymupdf.open()
    doc.new_page().insert_text((72, 100), "Introducción general", fontsize=12)
    doc.new_page().insert_text((72, 100), "La cardiología estudia el corazón y el nervio vago.", fontsize=12)
    doc.save(tmp_path / "apuntes.pdf")
    ids["pdf"] = pdfs.agregar(con, ids["parcial"], "apuntes.pdf", tmp_path / "apuntes.pdf", "Apuntes de clase")[0].id

    Image.new("RGB", (40, 40), "red").save(tmp_path / "a.png")
    ids["imagen"] = img_srv.agregar(con, ids["parcial"], "a.png", tmp_path / "a.png", "Lámina de la rodilla",
                                    descripcion="Meniscos y ligamentos", etiquetas="examen")[0].id
    Image.new("RGB", (40, 40), "blue").save(tmp_path / "b.png")
    ids["img_fila"] = imf.agregar(con, ids["femur"], "b.png", tmp_path / "b.png", "Radiografía AP", "Trocánter mayor visible")[0].id
    ids["nota"] = notas_srv.crear(con, ids["sub"], "Plexo braquial", "Raíces C5 a T1; **nervio radial**.", etiquetas="examen").id
    notas_srv.crear(con, ids["ecg"], "Ondas del ECG", "Onda P, complejo QRS y onda T.")
    return ids


def tipos(respuesta: bus.Respuesta) -> list[tuple[str, str]]:
    return [(r.tipo, str(r.titulo).replace("<mark>", "").replace("</mark>", "")) for r in respuesta.resultados]


def test_sin_tildes_ni_mayusculas(con, biblioteca) -> None:
    for q in ("femur", "FEMUR", "Fémur", "fÉmUr"):
        assert ("fila", "Fémur") in tipos(bus.buscar(con, q))


def test_titulo_exacto_primero(con, biblioteca) -> None:
    assert bus.buscar(con, "femur").resultados[0].tipo == "fila"


def test_prefijo_y_frase(con, biblioteca) -> None:
    r = bus.buscar(con, "cardio")
    assert ("materia", "Cardiología") in tipos(r) and ("pagina", "Apuntes de clase") in tipos(r)
    assert ("componente", "Electrocardiograma") not in tipos(r)        # prefijo: "cardio" no está al inicio de la palabra
    assert ("componente", "Electrocardiograma") in tipos(bus.buscar(con, "electro"))
    assert tipos(bus.buscar(con, '"nervio radial"')) == [("nota", "Plexo braquial")]
    assert tipos(bus.buscar(con, '"radial nervio"')) == []
    assert bus.buscar(con, "hueso largo").total == 1                   # todas las palabras deben estar


def test_busca_en_todo_y_enlaza_al_contenido(con, biblioteca) -> None:
    ids = biblioteca
    pagina = next(r for r in bus.buscar(con, "vago").resultados)
    assert (pagina.tipo, pagina.sub) == ("pagina", 2) and pagina.url.startswith(f"/pdfs/{ids['pdf']}?pagina=2&buscar=vago")
    assert "<mark>vago</mark>" in str(pagina.fragmento) and pagina.detalle == "PDF · página 2"
    img = bus.buscar(con, "meniscos").resultados[0]
    assert img.tipo == "imagen" and img.url.startswith(f"/imagenes/{ids['imagen']}")
    img_fila = bus.buscar(con, "trocanter").resultados[0]
    assert img_fila.tipo == "imagen_fila" and img_fila.url.startswith(f"/filas/{ids['femur']}?buscar=trocanter&imagen=")
    assert img_fila.detalle == "Imagen de la ficha «Fémur»"
    fila = bus.buscar(con, "escapula").resultados[0]
    assert fila.tipo == "fila" and fila.detalle == "Fila de «Atlas de huesos»" and "<mark>escápula</mark>" in str(fila.fragmento)
    assert {r.tipo for r in bus.buscar(con, "examen").resultados} == {"imagen", "nota"}   # por etiqueta
    assert "<mark>" in str(bus.buscar(con, "plexo").resultados[0].titulo)


def test_agrupado_por_materia_y_componente(con, biblioteca) -> None:
    g = bus.buscar(con, "nervio").grupos
    rutas = {(x.materia, x.ruta) for x in g}
    assert ("Anatomía", "Parcial 1 › Miembro superior") in rutas and ("Anatomía", "Parcial 1") in rutas


def test_sincronizado_al_editar_y_ocr(con, biblioteca, tmp_path: Path) -> None:
    ids = biblioteca
    notas_srv.editar(con, ids["nota"], "Plexo cervical", "Raíces C1 a C4", "markdown", "")
    assert bus.buscar(con, "braquial").total == 0 and bus.buscar(con, "cervical").total == 1
    assert bus.buscar(con, "examen").total == 1            # quitó la etiqueta de la nota
    img_srv.editar(con, ids["imagen"], "Lámina de la rodilla", "Meniscos", "anatomía, repaso")
    assert bus.buscar(con, "repaso").resultados[0].tipo == "imagen"
    con.execute("UPDATE pdf_paginas SET texto='Texto leído por OCR: miocardio' WHERE pdf_id=? AND numero=1", (ids["pdf"],))
    assert bus.buscar(con, "miocardio").resultados[0].sub == 1
    bib.editar_materia(con, ids["cardio"], "Cardiología clínica", "", "rojo", "heart-pulse")
    assert ("materia", "Cardiología clínica") in tipos(bus.buscar(con, "clinica"))


def test_papelera_excluye_y_restaurar_devuelve(con, biblioteca) -> None:
    ids = biblioteca
    pap.enviar_pdf(con, ids["pdf"])
    assert bus.buscar(con, "vago").total == 0
    pap.restaurar(con, pap.listar(con)[0].id)
    assert bus.buscar(con, "vago").total == 1
    pap.enviar_componente(con, ids["parcial"])              # también se lleva su subcomponente
    assert bus.buscar(con, "plexo").total == 0 and bus.buscar(con, "femur").total == 0
    pap.vaciar(con)
    restantes = {r[0] for r in con.execute("SELECT tipo FROM busqueda")}
    assert restantes == {"materia", "componente", "nota"}   # solo Anatomía, Cardiología, ECG y su nota


def test_filtros(con, biblioteca) -> None:
    ids = biblioteca
    assert {r.tipo for r in bus.buscar(con, "nervio", bus.Filtros(categorias=["pdf"])).resultados} == {"pagina"}
    assert bus.buscar(con, "onda", bus.Filtros(materia=ids["anatomia"])).total == 0
    assert bus.buscar(con, "onda", bus.Filtros(materia=ids["cardio"])).total == 1
    con_sub = bus.buscar(con, "nervio", bus.Filtros(componente=ids["parcial"]))   # incluye subcomponentes
    assert {r.tipo for r in con_sub.resultados} == {"pagina", "nota"}
    assert [r.tipo for r in bus.buscar(con, "rodilla", bus.Filtros(etiqueta="EXAMEN")).resultados] == ["imagen"]
    r = bus.buscar(con, "nervio")
    assert r.por_categoria == {"pdf": 1, "notas": 1}


def test_reconstruir_indice(con, biblioteca) -> None:
    antes = con.execute("SELECT COUNT(*) FROM busqueda").fetchone()[0]
    con.execute("DELETE FROM busqueda")
    assert bus.buscar(con, "femur").total == 0
    assert bus.reconstruir(con) == antes
    assert bus.buscar(con, "femur").total == 1


def test_consultas_raras_no_fallan(con, biblioteca) -> None:
    for q in ('"', "* OR (", "AND", "a", "NEAR(", "'", "100%", "¿?", "-"):
        bus.buscar(con, q)  # no debe lanzar errores


def test_rapida_con_decenas_de_miles(con, biblioteca) -> None:
    ids = biblioteca
    palabras = ["arteria", "vena", "nervio", "músculo", "tendón", "ligamento", "hueso", "cartílago", "órgano", "glándula"]
    lote = []
    for i in range(30_000):
        valores = {"c1": f"Estructura {i}", "c2": f"{palabras[i % 10]} número {i}", "c3": f"Descripción detallada {i} " * 3}
        lote.append((ids["tabla"], 1000 + i, None, f"Estructura {i}", "", json.dumps(valores, ensure_ascii=False), "{}", "{}", ""))
    con.execute("BEGIN")
    con.executemany("""INSERT INTO filas (tabla_id, posicion, fila_origen, titulo, clave_norm, valores, valores_norm,
                       valores_orden, texto_norm) VALUES (?,?,?,?,?,?,?,?,?)""", lote)
    con.execute("COMMIT")
    assert con.execute("SELECT COUNT(*) FROM busqueda").fetchone()[0] > 30_000
    for q in ("tendon", "glandula numero 2999", '"estructura 12345"', "desc", "cartilago"):
        inicio = time.perf_counter()
        r = bus.buscar(con, q)
        ms = (time.perf_counter() - inicio) * 1000
        print(f"  {q!r}: {r.total} resultados en {ms:.1f} ms")
        assert r.total > 0 and ms < 200, (q, ms)


def test_web(cliente, biblioteca) -> None:
    pagina = cliente.get("/buscar", params={"q": "femur"}).text
    assert "Fémur" in pagina and "Atlas de huesos" in pagina and "resultado" in pagina
    zona = cliente.get("/buscar", params={"q": "nervio", "tipo": "pdf"}, headers={"HX-Request": "true", "HX-Target": "zona-resultados"}).text
    assert "página 2" in zona and "Plexo" not in zona and 'hx-swap-oob="true"' in zona
    rapida = cliente.get("/buscar/rapida", params={"q": "plexo"}).text
    assert "<mark>Plexo</mark>" in rapida and 'data-resultado' in rapida
    assert "Sin resultados" in cliente.get("/buscar/rapida", params={"q": "zzzz"}).text

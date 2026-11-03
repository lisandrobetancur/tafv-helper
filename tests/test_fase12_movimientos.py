"""Fase 12: diagnóstico por movimiento (círculos y cuadros de síntomas, con copia a la recopilación)."""
from __future__ import annotations

import io
import json
import sqlite3

import pymupdf
import pytest
from docx import Document
from fastapi.testclient import TestClient
from PIL import Image

from app.errores import ErrorUsuario
from app.services import biblioteca as bib
from app.services import movimientos as mov
from app.services import recopilaciones as rec


def _componente(con: sqlite3.Connection, tipos: list[str] | None = None) -> int:
    materia = bib.crear_materia(con, "Acupuntura", "", "rojo", "dna")
    return bib.crear_componente(con, materia, None, "Diagnóstico por movimiento", "", tipos or ["movimientos"])


def test_cada_movimiento_tiene_sus_opciones_de_la_hoja():
    assert [m["id"] for m in mov.MOVIMIENTOS] == ["MADERA", "FUEGO", "TIERRA", "METAL", "AGUA"]
    assert "TENDONES/UÑAS" in mov.POR_ID["MADERA"]["opciones"]
    assert "HUESOS-ARTIC/CABELLO" in mov.POR_ID["AGUA"]["opciones"]
    assert "CARNE Y 4 EXTRE/LABIOS" in mov.POR_ID["TIERRA"]["opciones"]
    assert all(len(m["opciones"]) == 6 for m in mov.MOVIMIENTOS)


def test_validar_limpia_y_no_repite():
    limpios = mov.validar({"AGUA": ["  Saliva   espesa ", "saliva espesa", ""], "FUEGO": ["Cara roja"]})
    assert limpios["AGUA"] == ["Saliva espesa"]
    assert limpios["FUEGO"] == ["Cara roja"]
    assert limpios["METAL"] == []


@pytest.mark.parametrize("malo", [{}, {"AGUA": []}, {"OTRO": ["x"]}, {"AGUA": "x"}, []])
def test_validar_rechaza(malo):
    with pytest.raises(ErrorUsuario):
        mov.validar(malo)


def test_mayores_con_empate_y_en_cero():
    base = {m["id"]: [] for m in mov.MOVIMIENTOS}
    assert mov.mayores(base) == set()
    assert mov.mayores({**base, "AGUA": ["a"], "FUEGO": ["b", "c"]}) == {"FUEGO"}
    assert mov.mayores({**base, "AGUA": ["a"], "FUEGO": ["b"]}) == {"AGUA", "FUEGO"}


def test_imagen_crece_con_los_sintomas_y_aguanta_textos_largos():
    base = {m["id"]: [] for m in mov.MOVIMIENTOS}
    poco = mov.imagen({**base, "AGUA": ["Saliva espesa"]}, "Diagnóstico por movimiento")
    mucho = mov.imagen({**base, "AGUA": [f"Síntoma {i}" for i in range(30)] + ["x" * 200]}, "Diagnóstico por movimiento")
    assert poco.width == mucho.width
    assert mucho.height > poco.height


def test_la_fuente_de_la_imagen_tiene_tildes_y_enie():
    fuente = mov._fuente(16)
    sin_glifo = bytes(fuente.getmask("\uffff"))
    for letra in "áéíóúÑñ":
        assert bytes(fuente.getmask(letra)) != sin_glifo, letra
    assert fuente.getlength("ó") > 0 and bytes(fuente.getmask("ó")) != bytes(fuente.getmask("o"))


def test_el_componente_muestra_los_cinco_movimientos_en_cero(cliente: TestClient, con: sqlite3.Connection):
    html = cliente.get(f"/componentes/{_componente(con)}").text
    assert html.count("mov-circulo") == 5 and html.count("mov-cuadro") == 5
    assert "Recopilar" in html and "TRISTEZA-PENA" in html
    assert 'x-text="total(&#39;MADERA&#39;)">0<' in html or "x-text=\"total('MADERA')\">0<" in html


def test_otros_componentes_no_lo_muestran(cliente: TestClient, con: sqlite3.Connection):
    html = cliente.get(f"/componentes/{_componente(con, ['notas'])}").text
    assert "mov-circulo" not in html


def test_editar_el_componente_conserva_el_tipo(con: sqlite3.Connection):
    cid = _componente(con)
    bib.editar_componente(con, cid, "Diagnóstico por movimiento", "Con descripción", ["movimientos"])
    assert bib.obtener_componente(con, cid).tipos == ["movimientos"]


def test_recopilar_guarda_copia_fija_y_se_exporta(cliente: TestClient, con: sqlite3.Connection):
    cid = _componente(con)
    r = cliente.post("/recopilacion/movimientos", json={"componente_id": cid, "sintomas": {
        "MADERA": ["OJOS", "Vértigo"], "AGUA": ["Saliva espesa"]}})
    assert r.status_code == 200
    assert "se agregaron" in json.loads(r.headers["HX-Trigger"])["aviso"]["mensaje"]

    rcon = rec.conectar()
    rid = rec.activa(rcon).id
    imagen, campos = rec.obtener(rcon, rid).fragmentos
    assert imagen.tipo == "imagen" and imagen.titulo == "Diagnóstico por movimiento"
    assert imagen.origen == "Acupuntura › Diagnóstico por movimiento"
    assert Image.open(rec.ruta_imagen(imagen.archivo)).width > 0
    assert campos.tipo == "campos"
    assert campos.campos == [["MADERA (2)", "OJOS\nVértigo"], ["AGUA (1)", "Saliva espesa"]]

    bib.editar_componente(con, cid, "Otro nombre", "", ["movimientos"])       # es copia: no cambia
    recop = rec.obtener(rcon, rid)
    assert recop.fragmentos[0].titulo == "Diagnóstico por movimiento"

    texto = "".join(p.get_text() for p in pymupdf.open(stream=rec.exportar_pdf(recop), filetype="pdf"))
    assert "Vértigo" in texto and "MADERA (2)" in texto
    doc = Document(io.BytesIO(rec.exportar_docx(recop)))
    assert any("Vértigo" in p.text for p in doc.paragraphs) and doc.inline_shapes
    rcon.close()


def test_recopilar_vacio_avisa_y_no_agrega(cliente: TestClient, con: sqlite3.Connection):
    r = cliente.post("/recopilacion/movimientos", json={"componente_id": _componente(con), "sintomas": {"AGUA": []}})
    assert r.status_code == 400 and "Agrega al menos" in r.text
    rcon = rec.conectar()
    assert rec.obtener(rcon, rec.activa(rcon).id).fragmentos == []
    rcon.close()


def test_recopilar_de_otro_componente_falla(cliente: TestClient, con: sqlite3.Connection):
    r = cliente.post("/recopilacion/movimientos", json={"componente_id": _componente(con, ["notas"]), "sintomas": {"AGUA": ["x"]}})
    assert r.status_code == 400 and "no tiene diagn" in r.text

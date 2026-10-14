"""Fase 3: PDF con texto por página, OCR de páginas escaneadas, miniatura y papelera."""
from __future__ import annotations

import io
import sqlite3
import time
from pathlib import Path

import pymupdf
import pytest
from PIL import Image, ImageDraw, ImageFont

from app import db
from app.errores import ErrorUsuario
from app.services import biblioteca as bib
from app.services import ocr
from app.services import papelera as pap
from app.services import pdfs

FUENTE = next((p for p in ("/System/Library/Fonts/Supplemental/Arial.ttf", "C:/Windows/Fonts/arial.ttf",
                           "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf") if Path(p).exists()), None)


def pdf_texto(ruta: Path) -> Path:
    doc = pymupdf.open()
    for texto in ["Capítulo 1: El fémur es el hueso más largo.", "Capítulo 2: La tibia soporta el peso.",
                  "Capítulo 3: Articulación de la rodilla y meniscos."]:
        doc.new_page().insert_text((72, 100), texto, fontsize=14)
    doc.save(ruta)
    return ruta


def pdf_escaneado(ruta: Path) -> Path:
    """Una página de texto normal y otra que es solo una imagen (como un escáner)."""
    img = Image.new("RGB", (1600, 400), "white")
    fuente = ImageFont.truetype(FUENTE, 54) if FUENTE else ImageFont.load_default(size=54)
    ImageDraw.Draw(img).text((60, 80), "Fisiología renal: la nefrona", fill="black", font=fuente)
    ImageDraw.Draw(img).text((60, 220), "filtra la sangre y forma orina.", fill="black", font=fuente)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    doc = pymupdf.open()
    doc.new_page().insert_text((72, 100), "Página con texto digital sobre el riñón.", fontsize=14)
    pag = doc.new_page()
    pag.insert_image(pymupdf.Rect(36, 36, 576, 171), stream=buf.getvalue())
    doc.save(ruta)
    return ruta


def preparar(con: sqlite3.Connection) -> int:
    mid = bib.crear_materia(con, "Fisiología", "", "verde", "activity")
    return bib.crear_componente(con, mid, None, "Guías", "", ["pdf"])


def subir(con, tmp_path: Path, cid: int, origen: Path, titulo: str):
    tmp = tmp_path / f"subida-{origen.name}"
    tmp.write_bytes(origen.read_bytes())
    return pdfs.agregar(con, cid, origen.name, tmp, titulo)


def test_pdf_con_texto(con, tmp_path: Path, datos: Path) -> None:
    cid = preparar(con)
    pdf, aviso = subir(con, tmp_path, cid, pdf_texto(tmp_path / "huesos_v2.pdf"), "Apuntes de huesos")
    assert aviso is None and pdf.paginas == 3 and pdf.ocr_pendientes == 0
    assert pdf.archivo == "pdf/Apuntes de huesos.pdf"
    assert (datos / "archivos" / "fisiologia" / "guias" / "pdf" / "Apuntes de huesos.pdf").exists()
    p2 = pdfs.pagina(con, pdf.id, 2)
    assert "tibia" in p2["texto"] and p2["origen"] == "texto" and "tibia soporta" in p2["texto_norm"]
    assert "articulacion de la rodilla" in pdfs.pagina(con, pdf.id, 3)["texto_norm"]   # sin tildes
    assert pdfs.miniatura(con, pdf).exists()
    assert bib.contar_elementos_componente(con, cid) == 1

    _, aviso = subir(con, tmp_path, cid, tmp_path / "huesos_v2.pdf", "Copia")
    assert "mismo archivo" in aviso


def test_validaciones(con, tmp_path: Path) -> None:
    cid = preparar(con)
    origen = pdf_texto(tmp_path / "a.pdf")
    with pytest.raises(ErrorUsuario, match="nombre descriptivo"):
        subir(con, tmp_path, cid, origen, "  ")
    (tmp_path / "falso.pdf").write_bytes(b"no soy un pdf")
    with pytest.raises(ErrorUsuario, match="no es un PDF"):
        subir(con, tmp_path, cid, tmp_path / "falso.pdf", "Falso")
    doc = pymupdf.open(origen)
    doc.save(tmp_path / "clave.pdf", encryption=pymupdf.PDF_ENCRYPT_AES_256, user_pw="1234", owner_pw="1234")
    with pytest.raises(ErrorUsuario, match="contraseña"):
        subir(con, tmp_path, cid, tmp_path / "clave.pdf", "Con clave")


def test_ocr_de_pagina_escaneada(con, tmp_path: Path) -> None:
    cid = preparar(con)
    pdf, _ = subir(con, tmp_path, cid, pdf_escaneado(tmp_path / "escaneo.pdf"), "Riñón escaneado")
    assert pdf.ocr_pendientes == 1 and pdf.ocr_progreso == 0           # solo la 2.ª página
    assert pdfs.ocr_pendiente_total(con) == 1
    assert pdfs.procesar_una_pagina(con) is True
    assert pdfs.procesar_una_pagina(con) is False                       # cola vacía
    p = pdfs.pagina(con, pdf.id, 2)
    assert p["origen"] == "ocr" and "nefrona" in p["texto_norm"] and "fisiologia renal" in p["texto_norm"]
    pdf = pdfs.obtener(con, pdf.id)
    assert pdf.ocr_pendientes == 0 and pdf.ocr_hechas == 1 and pdf.ocr_progreso == 100


def test_ocr_en_segundo_plano(datos: Path, tmp_path: Path) -> None:
    con = db.conectar()
    try:
        cid = preparar(con)
        pdf, _ = subir(con, tmp_path, cid, pdf_escaneado(tmp_path / "e.pdf"), "Escaneo")
        ocr.iniciar(db.conectar)
        limite = time.time() + 60
        while pdfs.obtener(con, pdf.id).ocr_pendientes and time.time() < limite:
            time.sleep(0.2)
        assert pdfs.obtener(con, pdf.id).ocr_hechas == 1
    finally:
        ocr.detener()
        con.close()


def test_ocr_completo_y_papelera(con, tmp_path: Path, datos: Path) -> None:
    cid = preparar(con)
    pdf, _ = subir(con, tmp_path, cid, pdf_texto(tmp_path / "a.pdf"), "Apuntes")
    assert pdfs.pedir_ocr_completo(con, pdf.id) == 3 and pdfs.obtener(con, pdf.id).ocr_pendientes == 3

    pdf = pdfs.renombrar(con, pdf.id, "Apuntes de anatomía")
    assert pdf.archivo == "pdf/Apuntes de anatomía.pdf" and pdfs.ruta(con, pdf).exists()

    pap.enviar_pdf(con, pdf.id)
    assert pdfs.listar(con, cid) == [] and pdfs.ocr_pendiente_total(con) == 0  # en la papelera no se procesa
    assert not (datos / "archivos" / "fisiologia" / "guias" / "pdf" / "Apuntes de anatomía.pdf").exists()
    [e] = pap.listar(con)
    assert e.tipo == "pdf"
    pap.restaurar(con, e.id)
    assert pdfs.ruta(con, pdfs.obtener(con, pdf.id)).exists()

    pap.enviar_pdf(con, pdf.id)
    pap.vaciar(con)
    assert con.execute("SELECT COUNT(*) FROM pdf_paginas").fetchone()[0] == 0
    assert list((datos / "papelera").iterdir()) == []


def test_pdf_desde_la_web(cliente, tmp_path: Path) -> None:
    from app.services import biblioteca as bib2
    con = db.conectar()
    cid = preparar(con)
    con.close()
    datos_pdf = pdf_texto(tmp_path / "a.pdf").read_bytes()
    r = cliente.post(f"/componentes/{cid}/pdfs", headers={"HX-Request": "true"},
                     files=[("archivos", ("guia_lab.pdf", datos_pdf, "application/pdf"))], data={"titulos": "Guía de laboratorio"})
    assert r.status_code == 200 and "Guía de laboratorio" in r.text and "1 PDF agregado" in r.headers["HX-Trigger"]
    r = cliente.post(f"/componentes/{cid}/pdfs", headers={"HX-Request": "true"},
                     files=[("archivos", ("x.pdf", datos_pdf, "application/pdf"))], data={"titulos": " "})
    assert "nombre descriptivo" in r.headers["HX-Trigger"]
    pagina = cliente.get("/pdfs/1?pagina=2&buscar=tibia").text
    assert "viewer.html?file=/pdfs/1/archivo#page=2&amp;search=tibia" in pagina
    assert cliente.get("/pdfs/1/archivo").headers["content-type"] == "application/pdf"
    assert cliente.get("/pdfs/1/miniatura").headers["content-type"] == "image/webp"

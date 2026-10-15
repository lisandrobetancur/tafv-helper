"""Fase 4: imágenes sueltas (etiquetas, OCR opcional) y notas (Markdown seguro)."""
from __future__ import annotations

import io
import sqlite3
from pathlib import Path

import pytest
from PIL import Image, ImageDraw, ImageFont

from app.errores import ErrorUsuario
from app.services import biblioteca as bib
from app.services import etiquetas as etq
from app.services import imagenes as img_srv
from app.services import notas as notas_srv
from app.services import papelera as pap

FUENTE = next((p for p in ("/System/Library/Fonts/Supplemental/Arial.ttf", "C:/Windows/Fonts/arial.ttf",
                           "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf") if Path(p).exists()), None)


def imagen(ruta: Path, texto: str = "", color: str = "white") -> Path:
    img = Image.new("RGB", (1400, 300), color)
    if texto:
        fuente = ImageFont.truetype(FUENTE, 60) if FUENTE else ImageFont.load_default(size=60)
        ImageDraw.Draw(img).text((50, 110), texto, fill="black", font=fuente)
    img.save(ruta, "PNG")
    return ruta


def preparar(con: sqlite3.Connection) -> int:
    mid = bib.crear_materia(con, "Anatomía", "", "azul", "bone")
    return bib.crear_componente(con, mid, None, "Atlas", "", ["imagenes", "notas"])


def subir(con, tmp_path, cid, origen: Path, titulo: str, **kw):
    tmp = tmp_path / f"subida-{origen.name}"
    tmp.write_bytes(origen.read_bytes())
    return img_srv.agregar(con, cid, origen.name, tmp, titulo, **kw)


# ------------------------------------------------------------------- etiquetas
def test_separar_etiquetas() -> None:
    assert etq.separar("radiografía, Fémur ,fémur;  #rodilla , ") == ["radiografía", "Fémur", "rodilla"]


# --------------------------------------------------------------------- imágenes
def test_imagenes_con_etiquetas_y_filtro(con, tmp_path: Path, datos: Path) -> None:
    cid = preparar(con)
    a, aviso = subir(con, tmp_path, cid, imagen(tmp_path / "IMG_001.png"), "Corte sagital: rodilla",
                     descripcion="Vista lateral", etiquetas="rodilla, RM")
    assert aviso is None and a.archivo == "imagenes/Corte sagital - rodilla.png" and a.etiquetas == ["RM", "rodilla"]
    assert (datos / "archivos" / "anatomia" / "atlas" / a.archivo).exists()
    b, _ = subir(con, tmp_path, cid, imagen(tmp_path / "b.png", color="#ddeeff"), "Fémur", etiquetas="Rodilla")
    assert [i.titulo for i in img_srv.listar(con, cid, "RODILLA")] == ["Corte sagital: rodilla", "Fémur"]  # sin tildes ni mayúsculas
    assert [i.titulo for i in img_srv.listar(con, cid, "rm")] == ["Corte sagital: rodilla"]
    assert img_srv.etiquetas_del_componente(con, cid) == [("RM", 1), ("rodilla", 2)]
    _, aviso = subir(con, tmp_path, cid, tmp_path / "IMG_001.png", "Repetida")
    assert "misma imagen" in aviso

    editada = img_srv.editar(con, a.id, "Rodilla en RM", "Vista lateral T1", "rodilla")
    assert editada.archivo == "imagenes/Rodilla en RM.png" and img_srv.ruta(con, editada).exists()
    img_srv.reordenar(con, cid, [b.id, a.id])
    assert img_srv.listar(con, cid)[0].id == b.id

    with pytest.raises(ErrorUsuario, match="nombre descriptivo"):
        subir(con, tmp_path, cid, tmp_path / "b.png", "   ")


def test_ocr_de_imagen(con, tmp_path: Path) -> None:
    cid = preparar(con)
    a, _ = subir(con, tmp_path, cid, imagen(tmp_path / "lamina.png", "Músculo cuádriceps femoral"), "Lámina", extraer_texto=True)
    assert a.ocr_estado == "pendiente" and img_srv.ocr_pendientes(con) == 1
    assert img_srv.procesar_una_imagen(con) is True and img_srv.procesar_una_imagen(con) is False
    a = img_srv.obtener(con, a.id)
    assert a.ocr_estado == "listo" and "cuádriceps" in a.texto_ocr.lower()
    b, _ = subir(con, tmp_path, cid, imagen(tmp_path / "blanca.png", color="#fafafa"), "Sin texto")
    assert b.ocr_estado == "no"
    img_srv.pedir_ocr(con, b.id)
    img_srv.procesar_una_imagen(con)
    b = img_srv.obtener(con, b.id)
    assert b.ocr_estado == "listo" and b.texto_ocr == ""


def test_imagen_papelera_y_etiquetas_huerfanas(con, tmp_path: Path, datos: Path) -> None:
    cid = preparar(con)
    a, _ = subir(con, tmp_path, cid, imagen(tmp_path / "a.png"), "Rótula", etiquetas="única")
    pap.enviar_imagen(con, a.id)
    assert img_srv.listar(con, cid) == [] and not (datos / "archivos" / "anatomia" / "atlas" / a.archivo).exists()
    pap.restaurar(con, pap.listar(con)[0].id)
    assert img_srv.ruta(con, img_srv.obtener(con, a.id)).exists()
    pap.enviar_imagen(con, a.id)
    pap.vaciar(con)
    assert con.execute("SELECT COUNT(*) FROM etiquetas").fetchone()[0] == 0


# ------------------------------------------------------------------------ notas
def test_notas_markdown_seguro(con) -> None:
    cid = preparar(con)
    n = notas_srv.crear(con, cid, "Ciclo cardíaco", "# Fases\n\n- **Sístole**\n- Diástole\n\n| A | B |\n|---|---|\n| 1 | 2 |\n\n<script>alert(1)</script>",
                        "markdown", "examen, corazón")
    html = notas_srv.renderizar(n.contenido, n.formato)
    assert "<h1>Fases</h1>" in html and "<strong>Sístole</strong>" in html and "<table>" in html
    assert "<script>" not in html and "&lt;script&gt;" in html           # HTML incrustado escapado
    assert n.etiquetas == ["corazón", "examen"]
    assert "Sístole" in n.extracto and "#" not in n.extracto and "**" not in n.extracto
    plano = notas_srv.renderizar("Línea 1\n<b>no</b>", "texto")
    assert "&lt;b&gt;" in plano
    n2 = notas_srv.editar(con, n.id, "Ciclo cardíaco (repaso)", "Texto", "texto", "")
    assert n2.titulo == "Ciclo cardíaco (repaso)" and n2.etiquetas == []
    with pytest.raises(ErrorUsuario, match="título"):
        notas_srv.crear(con, cid, " ", "x")
    assert bib.contar_elementos_componente(con, cid) == 1


def test_nota_papelera(con) -> None:
    cid = preparar(con)
    n = notas_srv.crear(con, cid, "Dudas", "¿Qué es la precarga?")
    pap.enviar_nota(con, n.id)
    assert notas_srv.listar(con, cid) == []
    pap.restaurar(con, pap.listar(con)[0].id)
    assert [x.titulo for x in notas_srv.listar(con, cid)] == ["Dudas"]


# -------------------------------------------------------------------------- web
def test_web_imagenes_y_notas(cliente, tmp_path: Path) -> None:
    from app import db
    con = db.conectar()
    cid = preparar(con)
    con.close()
    buf = io.BytesIO()
    Image.new("RGB", (60, 40), "red").save(buf, "PNG")
    r = cliente.post(f"/componentes/{cid}/imagenes", headers={"HX-Request": "true"},
                     files=[("archivos", ("a.png", buf.getvalue(), "image/png"))],
                     data={"titulos": "Rótula", "descripciones": "frente", "etiquetas": "rodilla"})
    assert r.status_code == 200 and "Rótula" in r.text and 'id="contenido-imagenes"' in r.text
    assert "rodilla" in cliente.get(f"/componentes/{cid}/imagenes?etiqueta=RODILLA").text
    assert cliente.get("/imagenes/1").status_code == 200
    assert cliente.get("/imagenes/1/miniatura").headers["content-type"] == "image/webp"

    r = cliente.post(f"/componentes/{cid}/notas", data={"titulo": "Resumen", "contenido": "**clave**", "formato": "markdown"},
                     follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/notas/1"
    r = cliente.post(f"/componentes/{cid}/notas", data={"titulo": "Otra", "contenido": "x", "formato": "markdown",
                                                       "siguiente": "nueva"}, follow_redirects=False)
    assert r.headers["location"] == f"/componentes/{cid}/notas/nueva"      # «Guardar y escribir otra»
    assert "<strong>clave</strong>" in cliente.get("/notas/1").text
    assert "<em>hola</em>" in cliente.post("/notas/vista-previa", data={"contenido": "*hola*", "formato": "markdown"}).text
    pagina = cliente.get(f"/componentes/{cid}").text
    assert "Resumen" in pagina and "Rótula" in pagina

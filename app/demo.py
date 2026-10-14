"""Biblioteca de demostración: `python -m app.demo [--reiniciar] [--solo-crear] [--puerto 8766]`.

Crea en la carpeta demo/ (separada de data/: nunca se mezcla con los datos reales) una
biblioteca de ejemplo de medicina con Excel, PDF (con una página escaneada que se lee con OCR),
imágenes, notas y favoritos, y la abre en el navegador.
"""
from __future__ import annotations

import argparse
import io
import shutil
import sys
import tempfile
from pathlib import Path

from .config import ROOT, usar_datos

CARPETA = ROOT / "demo" / "data"

HUESOS = [
    ("Fémur", "Miembro inferior", "Largo", "Coxal, tibia, rótula", "Hueso más largo y resistente del cuerpo"),
    ("Tibia", "Miembro inferior", "Largo", "Fémur, peroné, astrágalo", "Soporta la mayor parte del peso de la pierna"),
    ("Peroné", "Miembro inferior", "Largo", "Tibia, astrágalo", "Forma el maléolo lateral"),
    ("Rótula", "Miembro inferior", "Sesamoideo", "Fémur", "El sesamoideo más grande; dentro del tendón del cuádriceps"),
    ("Húmero", "Miembro superior", "Largo", "Escápula, cúbito, radio", "Su cuello quirúrgico se fractura con frecuencia"),
    ("Radio", "Miembro superior", "Largo", "Húmero, cúbito, carpo", "Fractura de Colles en su extremo distal"),
    ("Cúbito", "Miembro superior", "Largo", "Húmero, radio", "El olécranon forma el codo"),
    ("Escápula", "Cintura escapular", "Plano", "Húmero, clavícula", "La cavidad glenoidea recibe la cabeza del húmero"),
    ("Clavícula", "Cintura escapular", "Largo", "Esternón, escápula", "El hueso que más se fractura"),
    ("Escafoides", "Carpo", "Corto", "Radio, semilunar, trapecio", "Riesgo de necrosis avascular tras fractura"),
    ("Esternón", "Tórax", "Plano", "Clavículas, costillas", "Manubrio, cuerpo y apófisis xifoides"),
    ("Atlas", "Columna cervical", "Irregular", "Occipital, axis", "C1: no tiene cuerpo vertebral"),
]

ANTIBIOTICOS = [
    ("Amoxicilina", "Betalactámico (penicilina)", "Inhibe la síntesis de la pared celular", "Diarrea, alergia"),
    ("Ceftriaxona", "Betalactámico (cefalosporina 3.ª gen.)", "Inhibe la síntesis de la pared celular", "Barro biliar"),
    ("Vancomicina", "Glucopéptido", "Inhibe la síntesis de la pared celular", "Síndrome del hombre rojo, nefrotoxicidad"),
    ("Gentamicina", "Aminoglucósido", "Inhibe la subunidad 30S del ribosoma", "Ototoxicidad, nefrotoxicidad"),
    ("Azitromicina", "Macrólido", "Inhibe la subunidad 50S del ribosoma", "Prolongación del QT"),
    ("Ciprofloxacino", "Fluoroquinolona", "Inhibe la ADN girasa", "Tendinopatía"),
    ("Doxiciclina", "Tetraciclina", "Inhibe la subunidad 30S del ribosoma", "Fotosensibilidad, tinción dental"),
    ("Metronidazol", "Nitroimidazol", "Daña el ADN bacteriano", "Efecto antabús con alcohol"),
]


def _excel(filas: list[tuple], encabezados: list[str], titulo: str) -> bytes:
    from openpyxl import Workbook
    from openpyxl.styles import Font
    wb = Workbook()
    ws = wb.active
    ws.title = titulo
    ws.append(encabezados)
    for c in ws[1]:
        c.font = Font(bold=True)
    for f in filas:
        ws.append(list(f))
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _fuente(tamano: int):
    """Una fuente con tildes y ñ (la de Pillow por defecto no las tiene)."""
    from PIL import ImageFont
    for ruta in ("/System/Library/Fonts/Supplemental/Arial.ttf", "/Library/Fonts/Arial.ttf",
                 "C:/Windows/Fonts/arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if Path(ruta).exists():
            return ImageFont.truetype(ruta, tamano)
    return ImageFont.load_default(size=tamano)


def _imagen(texto: str, color: str, subtitulo: str = "") -> bytes:
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (1200, 800), color)
    d = ImageDraw.Draw(img)
    d.ellipse((350, 180, 850, 680), outline="white", width=14)
    d.line((600, 180, 600, 680), fill="white", width=6)
    d.text((60, 50), texto, fill="white", font=_fuente(64))
    if subtitulo:
        d.text((60, 700), subtitulo, fill="white", font=_fuente(40))
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def _pdf() -> bytes:
    import pymupdf
    from PIL import Image, ImageDraw
    doc = pymupdf.open()
    paginas = [
        "Guía de práctica: miembro inferior\n\nObjetivos: identificar los huesos del miembro inferior y sus articulaciones.",
        "Articulación de la rodilla\n\nFormada por el fémur, la tibia y la rótula. Los meniscos medial y lateral\n"
        "amortiguan la carga. Ligamentos cruzados anterior y posterior.",
        "Tobillo y pie\n\nEl astrágalo articula con la tibia y el peroné (mortaja tibioperonea).",
    ]
    for texto in paginas:
        doc.new_page().insert_text((60, 80), texto, fontsize=13)
    # Una página "escaneada" (solo imagen) para ver el OCR en segundo plano
    img = Image.new("RGB", (1600, 500), "white")
    d = ImageDraw.Draw(img)
    fuente = _fuente(58)
    d.text((60, 90), "Página escaneada: cadera", fill="black", font=fuente)
    d.text((60, 260), "El acetábulo recibe la cabeza del fémur.", fill="black", font=fuente)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    doc.new_page().insert_image(pymupdf.Rect(36, 60, 576, 229), stream=buf.getvalue())
    return doc.tobytes()


def crear() -> None:
    from . import db
    from .services import biblioteca as bib
    from .services import favoritos as fav
    from .services import imagenes, imagenes_fila, importacion, notas, pdfs, tablas

    usar_datos(CARPETA)
    db.inicializar()
    con = db.conectar()
    tmp = Path(tempfile.mkdtemp())
    try:
        def archivo(nombre: str, datos: bytes) -> Path:
            ruta = tmp / nombre
            ruta.write_bytes(datos)
            return ruta

        def importar(componente: int, nombre: str, datos: bytes, titulo: str) -> int:
            estado = importacion.crear(con, componente, nombre, archivo(nombre, datos), titulo)
            estado.poner_config(0, importacion.config_sugerida(estado, 0, importacion.hojas(estado)[0]))
            importacion.guardar(estado)
            return tablas.importar(con, estado)[0]

        ana = bib.crear_materia(con, "Anatomía (demostración)", "Huesos, articulaciones y músculos", "azul", "bone")
        huesos = bib.crear_componente(con, ana, None, "Huesos", "Atlas y guías de práctica", ["excel", "pdf", "imagenes", "notas"])
        inferior = bib.crear_componente(con, ana, huesos, "Miembro inferior", "", ["imagenes", "notas"])
        t = importar(huesos, "atlas_huesos.xlsx",
                     _excel(HUESOS, ["Hueso", "Región", "Tipo", "Articula con", "Dato clave"], "Huesos"), "Atlas de huesos")
        femur = tablas.consultar(con, tablas.obtener(con, t), tablas.Consulta(q="femur"))[0][0]
        imagenes_fila.agregar(con, femur.id, "femur.png", archivo("femur.png", _imagen("Fémur", "#2e86c1", "Vista anterior")),
                              "Fémur, vista anterior", "Cabeza, cuello y trocánteres")
        fav.alternar(con, "fila", femur.id)
        pdf, _ = pdfs.agregar(con, huesos, "guia.pdf", archivo("guia.pdf", _pdf()), "Guía de práctica: miembro inferior")
        imagenes.agregar(con, inferior, "rodilla.png", archivo("rodilla.png", _imagen("Rodilla", "#7a3b3b", "Meniscos y ligamentos")),
                         "Rodilla: meniscos y ligamentos", "Corte esquemático", "rodilla, articulaciones", extraer_texto=True)
        notas.crear(con, huesos, "Mnemotecnia de los huesos del carpo",
                    "## Carpo\n\n*«**E**l **S**apo **P**iensa **P**ero **T**odavía **T**iene **G**anas de **G**ritar»*\n\n"
                    "| Fila proximal | Fila distal |\n|---|---|\n| Escafoides | Trapecio |\n| Semilunar | Trapezoide |\n"
                    "| Piramidal | Grande |\n| Pisiforme | Ganchoso |", etiquetas="mnemotecnia, examen")
        notas.crear(con, inferior, "Dudas para la próxima clase", "- ¿Por qué el ligamento cruzado anterior se lesiona más?\n- Repasar la mortaja tibioperonea.")

        far = bib.crear_materia(con, "Farmacología (demostración)", "Antimicrobianos", "verde", "pill")
        anti = bib.crear_componente(con, far, None, "Antibióticos", "", ["excel", "notas"])
        importar(anti, "antibioticos.xlsx", _excel(ANTIBIOTICOS, ["Fármaco", "Grupo", "Mecanismo", "Efectos adversos"], "Antibióticos"),
                 "Antibióticos principales")
        notas.crear(con, anti, "Resumen de mecanismos", "**Pared celular:** betalactámicos y glucopéptidos.\n\n"
                                                         "**Ribosoma:** aminoglucósidos y tetraciclinas (30S), macrólidos (50S).")
        fav.alternar(con, "pdf", pdf.id)
    finally:
        con.close()
        shutil.rmtree(tmp, ignore_errors=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Biblioteca de demostración")
    parser.add_argument("--reiniciar", action="store_true", help="borra la demostración y la vuelve a crear")
    parser.add_argument("--solo-crear", action="store_true", help="crea los datos sin abrir la aplicación")
    parser.add_argument("--puerto", type=int, default=8766)
    args = parser.parse_args()

    if args.reiniciar and CARPETA.exists():
        shutil.rmtree(CARPETA.parent / "data")
    if not (CARPETA / "biblioteca.db").exists():
        print(f"Creando la biblioteca de demostración en {CARPETA}…", flush=True)
        crear()
    if args.solo_crear:
        print("Listo.")
        return
    usar_datos(CARPETA)
    sys.argv = [sys.argv[0], "--puerto", str(args.puerto)]
    print("Abriendo la DEMOSTRACIÓN (no son tus datos reales).", flush=True)
    from .__main__ import main as iniciar
    iniciar()


if __name__ == "__main__":
    main()

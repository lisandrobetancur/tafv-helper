"""Corrige ortografía en tablas/Macerados Florales.xlsx (la copia extraída de A3:F46). Idempotente sobre una extracción nueva."""
import re
import sys
import openpyxl

ruta = sys.argv[1]
CAMBIOS = {
    "D1": [("Indicacion", "Indicación")],
    "E1": [("Caracteristico", "Característico")],
    "F2": [("Timido", "Tímido"), ("facilamente", "fácilmente")],
    "F6": [("pánicoTerror", "pánico Terror")],
    "D7": [("Por que dudan de si mismos", "Porque dudan de sí mismos")],
    "D8": [("animo", "ánimo")],
    "D9": [("animicamente", "anímicamente")],
    "D10": [("rumbo.Para", "rumbo. Para"), ("por que quieren", "porque quieren"), ("vocacion", "vocación")],
    "D11": [("aprece", "parece")],
    "E11": [("distraida", "distraída"), ("concentracion", "concentración")],
    "F11": [("energia", "energía"), ("Desatencion", "Desatención"), ("interes", "interés")],
    "E12": [("leccion", "lección")],
    "E13": [("pasado.Nostalgico", "pasado. Nostálgico"), ("melancolico", "melancólico")],
    "F13": [("frecuente.En", "frecuente. En")],
    "E15": [("Aceptacion", "Aceptación"), ("desmotivacion", "desmotivación")],
    "D16": [("estan centradas en si mismo", "están centradas en sí mismo")],
    "D19": [("demas", "demás")],
    "E21": [("trauma.Hay", "trauma. Hay")],
    "E25": [("otros.Idealista", "otros. Idealista")],
    "E26": [("empatia", "empatía")],
    "D27": [("desánimo.Para", "desánimo. Para"), ("si mismas", "sí mismas"), ("facilmente", "fácilmente")],
    "D28": [("confian en si mismos", "confían en sí mismos")],
    "D31": [("Par las personas", "Para las personas")],
    "D32": [("anticipado.Para", "anticipado. Para"), ("dia a dia", "día a día")],
    "D33": [("las persons", "las personas"), ("esten", "estén")],
    "D37": [("detras de una mascara", "detrás de una máscara")],
    "D38": [("demas", "demás"), ("volviendose", "volviéndose"), ("atencion", "atención")],
    "C42": [("Tension", "Tensión")],
}

wb = openpyxl.load_workbook(ruta)
ws = wb.active
for celda, pares in CAMBIOS.items():
    v = ws[celda].value
    for a, b in pares:
        if a not in v:
            raise SystemExit(f"{celda}: no está «{a}»")
        v = v.replace(a, b, 1)
    ws[celda].value = v
espacios = []
for fila in ws.iter_rows():
    for c in fila:
        if isinstance(c.value, str):
            n = re.sub(r" {2,}", " ", c.value)          # dobles espacios
            n = re.sub(r" *\n *", "\n", n).strip()      # espacios junto a saltos y al inicio/fin
            if n != c.value:
                espacios.append(c.coordinate)
                c.value = n
wb.save(ruta)
print("espacios limpiados en:", espacios)

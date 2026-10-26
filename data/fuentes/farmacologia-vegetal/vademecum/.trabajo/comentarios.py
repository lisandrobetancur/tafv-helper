import sys, json, re
sys.path.insert(0, "tools/carga")
import comun, openpyxl
from pathlib import Path
from comun import texto_comentario, autor_comentario
D = Path(sys.argv[1])
ws = openpyxl.load_workbook(D/"hojas/Farmacologia Vegetal.xlsx", data_only=True).worksheets[0]
tb = openpyxl.load_workbook(D/"tablas/Farmacología vegetal.xlsx").active   # nombres ya corregidos
corr_texto = {"Anotacion:": "Anotación:", "La accion fitoterapeutica": "La acción fitoterapéutica",
              "sequiterpenos": "sesquiterpenos", "del Arandano": "del Arándano", "arabinosido": "arabinósido"}
def limpiar(t):
    for a, b in corr_texto.items():
        t = t.replace(a, b)
    out = []
    for l in [re.sub(r" {2,}", " ", l).strip() for l in t.split("\n")]:
        if out and out[-1] and l and l[0].islower() and not re.match(r"^[a-z]\)", l):
            out[-1] += " " + l
        else:
            out.append(l)
    return out
bloques = []
for fila in ws.iter_rows():
    for c in fila:
        if not c.comment: continue
        a = autor_comentario(c.comment)
        a = "Luis Fernando Lenis" if a == "Luis fernando Lenis" else a
        ls = limpiar(texto_comentario(c.comment))
        q = [f"> Comentario de {a}: {ls[0]}"] + [("> " + l) if l else ">" for l in ls[1:]]
        bloques.append(f"**{tb.cell(c.row, 3).value.strip()} · {tb.cell(3, c.column).value}** (celda {c.coordinate}):\n" + "\n".join(q))
(D/"notas/Comentarios - Farmacología vegetal.md").write_text("\n\n".join(bloques) + "\n", encoding="utf-8")
print(len(bloques))

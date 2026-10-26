"""Divide las notas v1 (agrupadas con ###) en una nota por recuadro con el encabezado general entre paréntesis."""
import json, re
from pathlib import Path
base = Path(__file__).resolve().parents[1]
v1 = base / ".trabajo/notas-v1"
C = " - Campo Magnético"

def secciones(texto, nivel_re):
    """[(titulo, cuerpo)] cortando en líneas que cumplen nivel_re."""
    out, tit, buf = [], None, []
    for linea in texto.splitlines():
        m = re.match(nivel_re, linea)
        if m:
            if tit is not None or "".join(buf).strip():
                out.append((tit, "\n".join(buf).strip()))
            tit, buf = m.group(1).strip(), []
        else:
            buf.append(linea)
    out.append((tit, "\n".join(buf).strip()))
    return out

def limpio(t):
    return t.rstrip(":").strip()

notas = []
def agregar(titulo, cuerpo, celdas):
    assert len(titulo) <= 120, titulo
    archivo = f"notas/{titulo.replace('/', '-')}.md"
    notas.append({"titulo": titulo, "archivo": archivo, "celdas": celdas, "_cuerpo": cuerpo})

# 1. Acciones del Campo Magnético Polarizante (A1:J59): numerales (cada uno con su celda de color)
filas_acc = ["A3:J4", "A5:J7", "A8:J8", "A9:J16", "A17:J25", "A26:J33", "A34:J39", "A40:J40", "A41:J52", "A53:J53", "A54:J57", "A58:J58", "A59:J59"]
t = (v1 / f"Acciones del Campo Magnético Polarizante{C}.md").read_text()
secs = [s for s in secciones(t, r"^### (.*)$") if s[0]]
assert len(secs) == 13
for (tit, cuerpo), celdas in zip(secs, filas_acc):
    agregar(f"{limpio(tit)} (Acciones del Campo Magnético Polarizante){C}", cuerpo, ["A1:J2", celdas])

# 2 y 3. Tablas (un solo recuadro cada una)
for nombre, celdas in [("Indicaciones de los Campos Magnéticos Polarizantes", "L1:R16"), ("Polaridad de los Campos Magnéticos", "L18:R30")]:
    agregar(nombre + C, (v1 / f"{nombre}{C}.md").read_text().strip(), [celdas])

# 4. Fichas T1:U73
fichas = ["T2:U3", "T5:U8", "T10:U13", "T15:U18", "T20:U24", "T26:U30", "T32:U35", "T37:U40", "T42:U45", "T47:U50", "T52:U56", "T58:U62", "T64:U67", "T69:U73"]
t = (v1 / f"Ordenamiento de CMP según Etiología{C}.md").read_text()
secs = [s for s in secciones(t, r"^### (.*)$") if s[0]]
assert len(secs) == 14
for (tit, cuerpo), celdas in zip(secs, fichas):
    agregar(f"{limpio(tit)} (Ordenamiento de CMP según Etiología){C}", cuerpo, ["T1:U1", celdas])

# 5. Cómo formular campos magnéticos (W1:Y21)
filas_w = ["W2:Y4", "W5:Y7", "W8:Y10", "W11:Y12", "W13:Y15", "W16:Y18", "W19:Y20", "W21:Y21"]
t = (v1 / f"Cómo formular campos magnéticos{C}.md").read_text()
secs = [s for s in secciones(t, r"^### (.*)$") if s[0]]
assert len(secs) == 8
for (tit, cuerpo), celdas in zip(secs, filas_w):
    agregar(f"{limpio(tit)} (Cómo formular campos magnéticos){C}", cuerpo, ["W1:Y1", celdas])

# 6. Tips (L53:R136)
inicios = [54,55,56,57,58,59,60,61,62,63,64,68,80,87,91,95,104,112,121,127,130,131,132,133,134,135,136]
fines = [i - 1 for i in inicios[1:]] + [136]
t = (v1 / f"Tips de Tratamiento Metabólico-Campos Magnéticos{C}.md").read_text()
secs = [s for s in secciones(t, r"^### (.*)$") if s[0]]
assert len(secs) == len(inicios), len(secs)
for (tit, cuerpo), a, b in zip(secs, inicios, fines):
    agregar(f"{limpio(tit)} (Tips de Tratamiento Metabólico-Campos Magnéticos){C}", cuerpo, ["L53:R53", f"L{a}:R{b}"])

# 7. Tratamiento Metabólico (A61:J130): numerales y recuadros «Sistema Celular» / «Inmunidad Humoral»
t = (v1 / f"Tratamiento Metabólico{C}.md").read_text()
t = t.replace("#### Sistema Celular", "### Sistema Celular").replace("#### Inmunidad Humoral", "### Inmunidad Humoral")
secs = [s for s in secciones(t, r"^### (.*)$") if s[0]]
celdas_tm = ["A62:J63", "A64:J71", "A72:J75", "A76:J85", "A86:J90", "A91:J130"]
assert len(secs) == 6, [s[0] for s in secs]
for (tit, cuerpo), celdas in zip(secs, celdas_tm):
    cuerpo = re.sub(r"^#### ", "### ", cuerpo, flags=re.M)
    agregar(f"{limpio(tit)} (Tratamiento Metabólico){C}", cuerpo, ["A61:J61", celdas])

carpeta = base / "notas"
for f in carpeta.glob("*.md"):
    f.unlink()
for n in notas:
    (base / n["archivo"]).write_text(n.pop("_cuerpo") + "\n", encoding="utf-8")
plan = json.loads((base / "plan.json").read_text())
plan["notas"] = notas
(base / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(len(notas), "notas")
for n in notas: print(" ", n["titulo"])

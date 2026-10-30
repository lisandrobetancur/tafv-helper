import json, re, unicodedata, docx
from pathlib import Path
B = Path("data/fuentes/notas/casos")
plan = json.loads((B/"plan.json").read_text())
st = lambda t: "".join(c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn")
pal = lambda t: re.findall(r"[a-z0-9]+", st(t).lower())
corr = set(w for k in plan["correcciones"] for w in pal(k))
d = docx.Document(str(B/"documentos/Notas casos.docx"))
malos = 0
for n in plan["notas"]:
    a, b = map(int, n["parrafos"].split("-"))
    texto = n["titulo"] + " " + (B/n["archivo"]).read_text()
    have = set(pal(texto))
    for i in range(a, b+1):
        falt = set(pal(d.paragraphs[i-1].text)) - have - corr
        if falt: malos += 1; print(n["titulo"], i, falt)
# rangos contiguos y completos
r = [tuple(map(int, n["parrafos"].split("-"))) for n in plan["notas"]]
assert r[0][0] == 1 and r[-1][1] == len(d.paragraphs) and all(r[k][1]+1 == r[k+1][0] for k in range(len(r)-1))
print("párrafos sin cubrir:", malos, "| notas:", len(plan["notas"]))

import docx, sys
from docx.oxml.ns import qn
d = docx.Document("data/fuentes/notas/casos/documentos/Notas casos.docx")
for i, p in enumerate(d.paragraphs, 1):
    pPr = p._p.pPr
    num = ""
    if pPr is not None and pPr.numPr is not None:
        n = pPr.numPr
        num = f"[num {n.numId.val if n.numId is not None else '?'}/{n.ilvl.val if n.ilvl is not None else 0}]"
    runs = [r for r in p.runs if r.text.strip()]
    b = ""
    if runs:
        bs = [bool(r.bold) for r in runs]
        b = "B" if all(bs) else ("b" if any(bs) else "")
    st = "N" if p.style.name == "Normal" else ("S" if p.style.name == "No Spacing" else p.style.name)
    print(f"{i:4} {st}{b:1}{num} {p.text!r}")

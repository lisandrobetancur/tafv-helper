import re, shutil, openpyxl, sys
R = {"Area":"Área","anatomica":"anatómica","Neuralterapeutico":"Neuralterapéutico","Trigemino":"Trigémino",
     "Disfuncion":"Disfunción","cronico":"crónico","cronica":"crónica","parasimpatico":"parasimpático",
     "autonomo":"autónomo","vertebra":"vértebra"}
src, dst = "hojas/Ganglios.xlsx", "tablas/Ganglios.xlsx"
shutil.copy(src, dst)
wb = openpyxl.load_workbook(dst); ws = wb.active
for row in ws.iter_rows():
    for c in row:
        if isinstance(c.value, str):
            v = c.value
            for a, b in R.items():
                v = re.sub(rf"(?<!\w){a}(?!\w)", b, v)
            if v != c.value:
                print(c.coordinate, repr(c.value), "->", repr(v)); c.value = v
wb.save(dst)

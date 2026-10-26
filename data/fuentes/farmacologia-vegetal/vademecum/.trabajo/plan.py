import json, sys
from pathlib import Path
D = Path(sys.argv[1])
G = "Otros medicamentos en homeopatía"
rec = [("Tos seca", "A149:A157", ["Trumex", "Hepar Sulphur", "Phosphorus", "Sambucus", "Aconitum", "Belladona", "Allium Cepa", "Ferrum Phosphoricum"]),
       ("Tos Húmeda", "A159:A165", ["Dulcamara", "Pulsatilla", "Kalium Carbonicum", "Ipeca", "Hydrastis", "Stannum"]),
       ("Agravación con el frío", "A167:A174", ["Aconitum", "Hepar Sulphur", "Phosphorus", "Rumex", "Silicea", "Causticum", "Kalium Carbonicum"]),
       ("Agravación con el calor", "A176:A185", ["Iodum", "Ipeca", "Allium Cepa", "Antimonio Tartaricum", "Bryonia", "Lycopodium", "Pulsatilla", "Dulcamara", "Calcarea Carbonica"]),
       ("Agravación del Calor al Frío", "A187:A190", ["Rumex", "Phosphorus", "Calcarea Carbonica"]),
       ("Agravación del frío al calor", "A192:A196", ["Bryonia", "Pulsatilla", "Iodum", "Bromum"])]
notas_h = []
for enc, rango, items in rec:
    t = f"{enc} ({G}) - Vademecum"
    (D/f"notas/{t}.md").write_text("".join(f"- {i}\n" for i in items), encoding="utf-8")
    notas_h.append({"titulo": t, "archivo": f"notas/{t}.md", "celdas": ["A146", rango]})
plan = json.loads((D/"plan.json").read_text())
plan["notas"] = [n for n in plan["notas"] if not n["titulo"].startswith(G)]
i = next(k for k, n in enumerate(plan["notas"]) if n["titulo"].startswith("Alfa"))
plan["notas"][i:i] = notas_h
letras = json.load(open(D/".trabajo/letras.json"))
plan["correcciones"] = {"20 gotas/nohe": "20 gotas/noche", "Kallium Carbonicum": "Kalium Carbonicum",
                        "sequiterpenos": "sesquiterpenos", **letras}
(D/"plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(len(plan["correcciones"]), [n["titulo"] for n in plan["notas"]])

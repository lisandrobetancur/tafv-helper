"""Prueba de humo para GitHub Actions: con la app ya corriendo sobre los datos reales del repositorio,
abre las páginas principales, agrega material a una recopilación y la exporta a PDF y Word.

Uso: python .github/humo.py http://127.0.0.1:8799
(Solo corre en la máquina temporal de GitHub; no se usa en los equipos de la usuaria.)
"""
import json
import re
import sys
import time
import urllib.parse
import urllib.request

BASE = sys.argv[1].rstrip("/")


def pedir(ruta: str, datos: dict | None = None, json_: dict | None = None) -> tuple:
    cuerpo, cabeceras = None, {"HX-Request": "true"}
    if datos is not None:
        cuerpo = urllib.parse.urlencode(datos).encode()
    if json_ is not None:
        cuerpo, cabeceras["Content-Type"] = json.dumps(json_).encode(), "application/json"
    with urllib.request.urlopen(urllib.request.Request(BASE + ruta, data=cuerpo, headers=cabeceras), timeout=120) as r:
        return r.status, r.headers, r.read()   # cabeceras sin distinguir mayúsculas


for _ in range(120):          # esperar a que arranque
    try:
        pedir("/static/marca/logo-corpas.png")
        break
    except Exception:
        time.sleep(1)
else:
    sys.exit("La app no arrancó")

for ruta in ("/", "/recopilaciones", "/recopilacion/contador", "/acceso-rapido"):
    assert pedir(ruta)[0] == 200, ruta

# Algunas fichas y notas reales desde la búsqueda
_, _, html = pedir("/buscar?q=a")
texto = html.decode("utf-8")
filas = list(dict.fromkeys(re.findall(r'href="/filas/(\d+)', texto)))[:5]
notas = list(dict.fromkeys(re.findall(r'href="/notas/(\d+)', texto)))[:3]
assert filas, "no se encontraron fichas en los datos"
for f in filas[:2]:
    assert pedir("/recopilacion/agregar", {"fuente": "fila", "ref_id": f})[0] == 204
elementos = [{"fuente": "fila", "ref_id": int(f), "titulo": f"fila {f}"} for f in filas[2:]] + \
            [{"fuente": "nota", "ref_id": int(n), "titulo": f"nota {n}"} for n in notas]
if elementos:
    estado, cab, _ = pedir("/recopilacion/agregar-varios", json_={"elementos": elementos})
    assert estado == 200, cab
    print(json.loads(cab["HX-Trigger"])["aviso"]["mensaje"].encode("ascii", "replace").decode())

_, _, html = pedir("/recopilaciones")
rid = re.search(r'href="/recopilaciones/(\d+)"', html.decode("utf-8")).group(1)
assert pedir(f"/recopilaciones/{rid}")[0] == 200
assert pedir(f"/recopilaciones/{rid}/vista-previa")[0] == 200
_, cab, pdf = pedir(f"/recopilaciones/{rid}/pdf")
assert pdf[:5] == b"%PDF-" and len(pdf) > 2000, "PDF inválido"
_, cab, docx = pedir(f"/recopilaciones/{rid}/word")
assert docx[:2] == b"PK" and len(docx) > 5000, "Word inválido"
print(f"OK: {len(filas[:2]) + len(elementos)} fragmentos · PDF {len(pdf)} bytes · Word {len(docx)} bytes")

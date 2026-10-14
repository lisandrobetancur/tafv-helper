"""Arma app/static/vendor/lucide/sprite.svg a partir de los SVG de Lucide en tools/lucide-svg/.

Uso (solo en desarrollo, al agregar íconos):
    python tools/construir_sprite.py
Los íconos se descargan de https://unpkg.com/lucide-static@1.56.0/icons/<nombre>.svg (licencia ISC).
"""
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ORIGEN = RAIZ / "tools" / "lucide-svg"
DESTINO = RAIZ / "app" / "static" / "vendor" / "lucide" / "sprite.svg"

simbolos = []
for svg in sorted(ORIGEN.glob("*.svg")):
    texto = svg.read_text(encoding="utf-8")
    interior = re.search(r"<svg[^>]*>(.*)</svg>", texto, re.S).group(1)
    interior = re.sub(r"\s+", " ", interior).strip()
    simbolos.append(f'<symbol id="{svg.stem}" viewBox="0 0 24 24">{interior}</symbol>')

DESTINO.write_text(
    '<svg xmlns="http://www.w3.org/2000/svg"><!-- Lucide v1.56.0, licencia ISC: ver LICENSE -->'
    + "".join(simbolos) + "</svg>\n",
    encoding="utf-8",
)
print(f"{len(simbolos)} íconos -> {DESTINO.relative_to(RAIZ)}")

# Plan de carga (`plan.json`)

Uno por componente, en `data/fuentes/<materia>/<componente>/plan.json`. Las rutas son relativas a esa
carpeta. Lo escribe el agente extractor-material; lo leen `cargar.py` y `auditar.py`.

```json
{
  "materia": "Oxigenoterapia",
  "componente": "HBO",
  "crear_componente": {"tipos": ["excel", "imagenes", "notas"], "descripcion": ""},
  "fuentes": ["hojas/HBO.xlsx"],
  "correcciones": {
    "Comprension": "Compresión",
    "Esferositosis": "Esferocitosis",
    "Doxorrubacina": "Doxorrubicina"
  },
  "omitidos": [
    {"celda": "HBO!Z1", "motivo": "celda con un espacio, sin texto"},
    {"archivo": "imagenes/HBO - A152.png", "motivo": "la usuaria pidió convertirla en la nota «…»"}
  ],
  "notas": [
    {"titulo": "Complicaciones - HBO", "archivo": "notas/Complicaciones - HBO.md", "celdas": ["F1:G6", "L1:M7"]}
  ],
  "tablas": [
    {"archivo": "tablas/Protocolo Corpas - HBO.xlsx", "nombre": "Protocolo Corpas - HBO",
     "columna_titulo": "Seccion", "celdas": ["A2:C15"]}
  ],
  "imagenes": [
    {"archivo": "imagenes/HBO - A36.png", "titulo": "Indicaciones ECHM tipo 1 - HBO", "celda": "A36",
     "descripcion": "INDICACIONES TIPO 1 – …\nCONDICIÓN | NIVEL EVIDENCIA | NIVEL CONSENSO\n…"},
    {"archivo": "imagenes-mejoradas/HBO - O1.png", "fuente": "imagenes/HBO - O1.png", "titulo": "…", "descripcion": "…"}
  ],
  "pdfs": [
    {"archivo": "pdf/Material.pdf", "titulo": "Material de Oxigenoterapia"}
  ]
}
```

Campos:
- `materia`, `componente`: nombres como en la app (sin importar tildes o mayúsculas). Subcomponentes:
  `"Parcial 1 › Atlas"`. `crear_componente` solo si la usuaria confirmó crearlo.
- `fuentes`: archivos de la hoja que se auditan celda por celda.
- `correcciones`: texto original → texto corregido, para cada cambio de letras. Los cambios que solo agregan
  o quitan tildes no hace falta declararlos.
- `omitidos`: lo que no se carga, con motivo. `celda` admite rangos (`"HBO!A1:B3"`).
- `notas[].celdas`, `tablas[].celdas`, `imagenes[].celda`: de dónde sale cada elemento (para la revisión).
- `tablas[].columna_titulo`: encabezado tal como está en el Excel de la tabla. `fila_encabezado` (1, 2…) si
  no es la primera fila con datos.
- `imagenes[].fuente`: la original cuando se carga una versión mejorada (la auditoría compara el OCR con ella).
- `etiquetas` (opcional) en notas e imágenes: separadas por comas, solo si la usuaria las pidió.

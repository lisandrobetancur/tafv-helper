---
name: cargar-material
description: Carga material de estudio (Excel, imágenes, PDF) en la Biblioteca de Estudio de este proyecto, de forma fiel y verificada. Úsalo cuando la usuaria entregue archivos para una materia o componente («carga este Excel en Oxigenoterapia», «te paso los archivos de Homeopatía», «sube estas imágenes a HBO»), o pida rehacer o revisar una carga.
---

# Cargar material en la Biblioteca

La usuaria entrega archivos y espera que **toda** su información quede en la app, tal cual, sin pérdidas
ni interpretaciones, y que los originales queden guardados en `data/fuentes/`. Sigue estos pasos en orden.
Las reglas de contenido están en [reglas.md](reglas.md) y el formato del plan en [plan.md](plan.md):
léelos antes de empezar.

Herramientas (desde la raíz del proyecto, con `.venv/bin/python`): `tools/carga/preparar_fuentes.py`,
`inspeccionar.py`, `extraer_rango.py`, `mejorar_imagen.py`, `cargar.py`, `auditar.py`. Cada una explica su
uso con `--help`.

## 1. Entender el pedido
- Identifica la **materia** y a qué **componente** va cada archivo u hoja. Si un Excel tiene varias hojas,
  pregunta (si no está claro) a qué componente va cada una; cada hoja termina en su propio archivo.
- Si la materia no existe, pídele a la usuaria que la cree en la app (color e ícono son suyos). Un componente
  que no existe se puede crear desde el plan (`crear_componente`), pero confirma el nombre antes.
- Mira qué hay ya cargado en ese componente (`sqlite3 data/biblioteca.db`). Si hay contenido, pregunta si
  se reemplaza, se agrega al lado o se cancela. Nunca borres nada de la usuaria.

## 2. Guardar y separar las fuentes
```bash
.venv/bin/python tools/carga/preparar_fuentes.py <archivos> --materia "<Materia>" --hoja "<Hoja>=<Componente>" ...
```
Deja el original intacto en `data/fuentes/<materia>/_originales/`, cada hoja como archivo propio en
`data/fuentes/<materia>/<componente>/hojas/`, las imágenes del Excel en `imagenes/` (nombradas por su celda
ancla) y una descripción de bloques en `inspeccion-<hoja>.txt`. Los archivos de `data/fuentes/` no se editan
nunca después.

## 3. Extraer (un agente por componente)
Lanza un agente **extractor-material** por componente (pueden ir en paralelo). Pásale la carpeta
`data/fuentes/<materia>/<componente>/`, la materia, el componente y cualquier decisión de la usuaria.
Cada uno escribe `plan.json`, `notas/*.md`, `tablas/*.xlsx` y `preguntas.md` en esa carpeta, y no carga nada.

Revisa lo que devuelve: lee el plan, algunas notas y `preguntas.md`. No aceptes un plan que una, divida,
resuma o complete información (ver reglas.md).

## 4. Preguntar a la usuaria lo que no está claro
Con `AskUserQuestion`, reúne las dudas en pocas preguntas:
- **Imagen poco comprensible** (texto borroso, cortado o ilegible): pregunta si la mejoras o si la conviertes
  en notas. Si elige mejorar:
  `tools/carga/mejorar_imagen.py <original> <carpeta>/imagenes-mejoradas/<nombre>.png --comparacion <carpeta>/imagenes-mejoradas/<nombre> - comparación.png`,
  envíale la comparación (`SendUserFile`) y carga la mejorada solo si la aprueba (en el plan: `archivo` = la
  mejorada, `fuente` = la original). Si elige notas, transcribe su contenido en una nota y declara la imagen en
  `omitidos` con ese motivo (o cárgala igual si también la quiere ver).
- Ambigüedades de estructura (¿esto es una tabla o recuadros?, ¿a qué encabezado pertenece este bloque?).
- La lista de **correcciones de ortografía** del plan, para que la confirme si son muchas o dudosas.

## 5. Cargar: primero en una copia, después de verdad
```bash
.venv/bin/python tools/carga/cargar.py data/fuentes/<materia>/<componente>/plan.json --prueba
BIBLIOTECA_DATOS=<copia que indica> .venv/bin/python tools/carga/auditar.py <plan.json>
```
Si hay tablas corregidas en `tablas/`, corre también `tools/carga/comparar_tabla.py <plan.json>`: compara palabra por
palabra con la hoja original y marca reemplazos caídos dentro de otra palabra («demas» → «demás» que deja
«demásiado») o correcciones sin declarar. Corrige con reemplazos de palabra completa, nunca de subcadenas.

Si la auditoría de la prueba sale CORRECTO, carga de verdad (hace un respaldo antes y guarda en `cargas/` qué se creó):
```bash
.venv/bin/python tools/carga/cargar.py data/fuentes/<materia>/<componente>/plan.json   # --reemplazar si la usuaria lo pidió
```
La app puede estar abierta: escribe en la misma base de datos.

## 6. Verificar (agente independiente)
Lanza un agente **verificador-carga** por componente cargado. Revisa por su cuenta las fuentes contra la
app (incluido mirar cada imagen y compararla con su descripción) y corre `auditar.py --ocr`. Si encuentra
algo, corrígelo (edita el plan, vuelve a cargar con `--reemplazar`) y vuelve a verificar hasta que esté limpio.

## 7. Informar
Dile a la usuaria, en pocas líneas: qué quedó en cada componente (notas, tablas, imágenes, PDF), las
correcciones de ortografía hechas, lo que se declaró en `omitidos` y por qué, y que los originales están en
`data/fuentes/<materia>/`. Recuérdale que `data/` no va a GitHub: la copia ella a mano (con la app cerrada).

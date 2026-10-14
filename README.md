# Biblioteca de Estudio

Aplicación **local** (sin servidor externo ni internet tras instalarla) para organizar y buscar material
de estudio de medicina por **materias › componentes › subcomponentes**: tablas de Excel/CSV con imágenes
por fila, PDF (con OCR de páginas escaneadas), imágenes sueltas y notas, con búsqueda global sin tildes.

Pensada para 3 equipos (Mac Apple Silicon, Mac Intel y Windows) que comparten la misma carpeta
(copiándola o por una carpeta sincronizada), usada en un solo equipo a la vez.

> **Para la usuaria:** la guía paso a paso está en [INSTALACION.md](INSTALACION.md).

## Arquitectura

| Capa | Tecnología |
|---|---|
| Servidor | Python 3.11–3.13, FastAPI + Uvicorn, en `127.0.0.1` |
| Interfaz | Plantillas Jinja2 + HTMX (navegación y fragmentos) + Alpine.js (interacción local) |
| Estilos | Tailwind CSS 4 compilado con el binario standalone; el CSS compilado se versiona (no hace falta Node) |
| Librerías front | Locales en `app/static/vendor/`: HTMX, Alpine, SortableJS, sprite de Lucide, PDF.js (visor) |
| Datos | SQLite (`journal_mode=DELETE`) con migraciones por `PRAGMA user_version` |
| Búsqueda | FTS5 (`unicode61 remove_diacritics 2`, prefijos) sincronizado con triggers |
| Excel/CSV | openpyxl + `csv` (celdas combinadas, fechas "como se ven", CSV con separador/codificación detectados) |
| PDF | PyMuPDF: texto por página, miniaturas y render para OCR |
| OCR | RapidOCR + onnxruntime, modelo de reconocimiento latino (español) en `modelos/ocr/` |
| Imágenes | Pillow (validación y miniaturas WebP en caché) |

### Estructura de carpetas

```
app/
  __main__.py        python -m app: puerto libre (8765 por defecto) + abre el navegador
  main.py            FastAPI: arranque, bloqueo entre equipos, OCR en segundo plano, errores amables
  config.py          rutas (todas relativas a la carpeta del proyecto), colores, íconos, tipos
  db.py              conexión SQLite y migraciones (lista MIGRACIONES)
  indice_sql.py      SQL del índice FTS5: vistas doc_<tipo> + triggers generados desde TIPOS
  demo.py            python -m app.demo: biblioteca de ejemplo en demo/
  models/            dataclasses de las filas de la BD
  routers/           rutas HTTP (páginas y fragmentos HTMX)
  services/          lógica: biblioteca, almacenamiento, papelera, hojas, importacion, tablas,
                     imagenes_fila, pdfs, ocr, imagenes, notas, etiquetas, busqueda, favoritos,
                     repaso, respaldos, bloqueo, miniaturas, diagnostico, casos
  templates/         base.html, macros.html, paginas/, parciales/
  static/            src/app.css (fuente Tailwind), css/app.css (compilado), js/app.js, vendor/, marca/
data/                (no va en git) biblioteca.db, archivos/, papelera/, respaldos/, cache/, logs/
modelos/ocr/         (no va en git) modelos ONNX del OCR; los descarga `instalar`
tests/               pytest, una suite por fase
tools/               compilar_css.(sh|bat), construir_sprite.py (+ binario de Tailwind, no versionado)
instalador.py        instalar/iniciar (solo biblioteca estándar); lo llaman los .command y .bat
```

Archivos de la usuaria, legibles y relativos a `data/`:

```
data/archivos/<materia>/<componente>/<subcomponente>/
    excel/<nombre descriptivo>.xlsx
    pdf/<nombre descriptivo>.pdf
    imagenes/<nombre descriptivo>.png
    imagenes-filas/<título de la fila> - <nombre descriptivo>.jpg
```

### Decisiones importantes

- **Portabilidad:** en la BD solo hay rutas relativas (`/` como separador); la carpeta de un componente
  se calcula a partir de los *slugs*, así que renombrar mueve la carpeta sin tocar los registros.
  `journal_mode=DELETE` evita archivos `-wal/-shm` al copiar o sincronizar. Nombres de archivo saneados
  para Windows (caracteres prohibidos, nombres reservados).
- **Bloqueo:** `data/.en_uso` guarda equipo, hora y PID. Otro equipo ve un aviso con opción de forzar;
  el mismo equipo lo retoma (cierre inesperado).
- **Esquema dinámico:** cada tabla guarda sus columnas en JSON y cada fila sus valores en JSON
  (`valores`, `valores_norm` para filtrar sin tildes, `valores_orden` para orden natural).
- **Índice de búsqueda:** un solo FTS5 `busqueda`. Cada tipo tiene una vista `doc_<tipo>` y triggers de
  alta/baja/cambio generados en `indice_sql.py` (también para cambios de etiquetas). `rowid = código ×
  10^12 + id`. Lo que está en la papelera se excluye al consultar. «Reconstruir índice» en Mantenimiento.
- **OCR en segundo plano:** cola persistente en la BD (`pdf_paginas.ocr_pendiente`, `imagenes.ocr_estado`)
  procesada por un hilo; se reanuda al reiniciar. Cada servicio registra su «fuente» de trabajos.
- **Papelera:** materias/componentes mueven su carpeta a `data/papelera/`; tablas y notas son lógicas;
  PDF e imágenes mueven su archivo. Vaciar borra sin dejar huérfanos.
- **Respaldos:** ZIP con copia en caliente de la BD (API `backup` de SQLite) + `archivos/` + `papelera/`.
  Restaurar valida rutas (anti *zip slip*) e integridad, hace un respaldo automático previo y migra.
- **Diagnóstico por síntomas:** repertorización determinista sobre las filas de las tablas. Cada síntoma
  se busca con FTS5 (prefijos, sin tildes) y se verifica por columna (opcionalmente solo columnas cuyo
  nombre contiene «síntoma/signo/característico…»); los candidatos se ordenan por síntomas cubiertos
  (los «importantes» pesan el doble) con evidencia (columna + línea resaltada), síntomas faltantes,
  «otros rasgos para confirmar», matriz comparativa y fuentes de apoyo (PDF, notas, imágenes). Sin IA:
  todo sale del material y se muestra su origen. Es un módulo independiente de las materias: siempre
  revisa todas, arma un ranking por materia (ninguna queda tapada por otra) y guarda sus propios casos
  en la tabla `casos` (síntomas, conclusión y foto del análisis; van a la papelera como el resto).
- **Seguridad de contenido:** todo el texto del Excel se escapa; el Markdown de las notas no admite HTML;
  las subidas se validan por contenido (Pillow/PyMuPDF), no por extensión.
- **Mac Intel:** onnxruntime ≥ 1.24 no publica wheels x86_64 para macOS; `requirements.txt` fija la 1.23.2
  allí con marcadores de entorno (por eso en Mac Intel se usa Python ≤ 3.13).

## Desarrollo

```bash
python3.13 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m app.services.ocr          # modelos de OCR en modelos/ocr
.venv/bin/python -m app --puerto 8765          # o: python instalador.py iniciar
.venv/bin/python -m pytest                     # todas las pruebas
```

- **Datos aparte para probar:** `BIBLIOTECA_DATOS=/ruta/temporal .venv/bin/python -m app` o la demo
  (`python -m app.demo`, carpeta `demo/`, puerto 8766).
- **CSS:** coloca el binario standalone de Tailwind 4.3.3 en `tools/tailwindcss` (`tailwindcss.exe` en
  Windows) y ejecuta `tools/compilar_css.sh --watch` mientras editas plantillas. Versiona `app/static/css/app.css`.
- **Íconos:** descarga el SVG de `https://unpkg.com/lucide-static@1.56.0/icons/<nombre>.svg` a
  `tools/lucide-svg/` y ejecuta `python tools/construir_sprite.py`. Uso en plantillas: `icono("nombre")`.
- **Migraciones:** agrega un elemento al final de `db.MIGRACIONES` (nunca edites uno ya publicado). Si cambia
  qué se indexa, actualiza `indice_sql.TIPOS` y usa `indice_sql.recrear()` en la migración nueva.
- **Registro:** `data/logs/app.log` (rotativo).

## Licencias de terceros

HTMX (0BSD), Alpine.js (MIT), SortableJS (MIT), Lucide (ISC), PDF.js (Apache-2.0), Tailwind CSS (MIT),
RapidOCR (Apache-2.0) y modelos PaddleOCR (Apache-2.0). El escudo pertenece a la Fundación Universitaria
Juan N. Corpas y se usa solo como identificación de esta herramienta de estudio.

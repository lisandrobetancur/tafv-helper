# Biblioteca de Estudio

Aplicación **local** (sin servidor externo ni internet tras instalarla) para organizar y buscar material
de estudio de medicina por **materias › componentes › subcomponentes**: tablas de Excel/CSV con imágenes
por fila, PDF (con OCR de páginas escaneadas), imágenes sueltas y notas, con búsqueda global sin tildes.

Pensada para 3 equipos (Mac Apple Silicon, Mac Intel y Windows) que comparten la misma carpeta
(copiándola o por una carpeta sincronizada), usada en un solo equipo a la vez.

> **Para la usuaria:** la guía paso a paso está en [INSTALACION.md](INSTALACION.md).

## Instalación y ejecución

Se necesita **Python 3.11, 3.12 o 3.13** (se recomienda la **3.13**) y **Git** para descargar el proyecto. La
instalación se hace **una vez por computador** y necesita internet; después la app funciona sin conexión.

El repositorio incluye los datos de la biblioteca (`data/biblioteca.db`, `data/archivos/` y `data/fuentes/`), así
que al clonarlo ya viene todo el material cargado. Los modelos del OCR (`modelos/`) y el entorno de Python
(`.venv/`) no van en Git: los crea `instalar`.

### macOS (con Homebrew)

Sirve para Mac con procesador Apple (M1, M2, M3, M4…) y para Mac con Intel.

1. **Instalar Homebrew** (si no lo tienes). Abre **Terminal** (⌘ + Espacio → «Terminal») y pega:

   ```bash
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```

   Pide tu contraseña del Mac y puede instalar las herramientas de línea de comandos de Xcode. Al terminar,
   **sigue las instrucciones de «Next steps»** que muestra (en Mac con procesador Apple son dos líneas que
   agregan `/opt/homebrew/bin` al PATH). Cierra y vuelve a abrir Terminal, y comprueba con `brew --version`.

2. **Instalar Python 3.13 y Git:**

   ```bash
   brew install python@3.13 git
   ```

   Comprueba con `python3.13 --version`. En un Mac con **Intel** no uses la 3.14: el OCR aún no es compatible.

3. **Descargar el proyecto** (en la carpeta que prefieras, por ejemplo Documentos):

   ```bash
   cd ~/Documents
   git clone https://github.com/lisandrobetancur/tafv-helper.git
   cd tafv-helper
   ```

4. **Instalar las dependencias de la app** (crea `.venv`, instala `requirements.txt` y descarga el OCR):

   ```bash
   python3.13 instalador.py instalar
   ```

   También se puede hacer doble clic en `instalar.command` desde el Finder. Si macOS dice que no se puede
   verificar el desarrollador o que no tienes permiso, mira «Si el Mac no te deja abrir el archivo» en
   [INSTALACION.md](INSTALACION.md) (o ejecuta `chmod +x instalar.command iniciar.command`).

5. **Ejecutar la biblioteca:**

   ```bash
   python3.13 instalador.py iniciar
   ```

   O doble clic en `iniciar.command`. Se abre el navegador en **http://127.0.0.1:8765** (si el puerto está
   ocupado usa el siguiente libre y lo muestra en la terminal). Para cerrarla, cierra la ventana de Terminal o
   pulsa Ctrl + C.

> Si `brew upgrade` actualiza Python, `iniciar` detecta que el entorno quedó roto y lo reinstala solo.

### Windows

1. **Instalar Python 3.13 y Git.** Abre **PowerShell** (botón Inicio → escribe «PowerShell») y ejecuta:

   ```powershell
   winget install -e --id Python.Python.3.13
   winget install -e --id Git.Git
   ```

   Cierra y vuelve a abrir PowerShell, y comprueba con `py -3.13 --version` y `git --version`.

   **Sin winget** (Windows antiguos): descarga «Windows installer (64-bit)» de Python 3.13 desde
   https://www.python.org/downloads/windows/ y, **antes de pulsar «Install Now»**, marca **«Add python.exe to
   PATH»**. Git se descarga de https://git-scm.com/download/win (las opciones por defecto sirven).

2. **Descargar el proyecto** (por ejemplo en Documentos):

   ```powershell
   cd $HOME\Documents
   git clone https://github.com/lisandrobetancur/tafv-helper.git
   cd tafv-helper
   ```

3. **Instalar las dependencias de la app:**

   ```powershell
   py -3.13 instalador.py instalar
   ```

   O doble clic en `instalar.bat` desde el Explorador. Si aparece «Windows protegió su PC», pulsa
   «Más información» → «Ejecutar de todas formas».

4. **Ejecutar la biblioteca:**

   ```powershell
   py -3.13 instalador.py iniciar
   ```

   O doble clic en `iniciar.bat`. Se abre el navegador en **http://127.0.0.1:8765**. Para cerrarla, cierra la
   ventana negra o pulsa Ctrl + C.

### Actualizar y compartir los datos entre computadores

- **Traer lo último** (código y datos) antes de usar la biblioteca en un computador:

  ```bash
  git pull
  ```

  Si cambiaron las dependencias, `iniciar` lo detecta y reinstala solo.
- **Subir los cambios** después de cargar o editar material, **con la app cerrada**:

  ```bash
  git add -A
  git commit -m "Actualiza la biblioteca"
  git push
  ```

- `data/biblioteca.db` es un solo archivo binario y Git no puede combinar cambios hechos en dos computadores:
  **modifica la biblioteca en un solo computador a la vez** y haz `git pull` antes de empezar en otro.
- No van en Git (quedan solo en cada computador): `data/respaldos/`, `data/cache/`, `data/logs/`,
  `data/papelera/` y el bloqueo `data/.en_uso`.

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
                     repaso, respaldos, bloqueo, miniaturas, diagnostico, casos, explorar
  templates/         base.html, macros.html, paginas/, parciales/
  static/            src/app.css (fuente Tailwind), css/app.css (compilado), js/app.js, vendor/, marca/
data/                biblioteca.db, archivos/ y fuentes/ van en git; papelera/, respaldos/, cache/ y logs/ no
modelos/ocr/         (no va en git) modelos ONNX del OCR; los descarga `instalar`
tests/               pytest, una suite por fase
tools/               compilar_css.(sh|bat), construir_sprite.py (+ binario de Tailwind, no versionado)
tools/carga/         carga fiel de material: preparar_fuentes, inspeccionar, extraer_rango, mejorar_imagen,
                     cargar (plan.json), auditar (fuentes vs. biblioteca) y verificar_acceso_rapido
                     (cada fila, nota e imagen vigente aparece como candidata en Acceso rápido)
.claude/            skill «cargar-material» (reglas y formato del plan) y agentes extractor-material y
                     verificador-carga, para Claude Code
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
- **Explorar:** cada materia tiene dos pestañas: «Componentes y carga» (organizar y subir material) y
  «Explorar» (solo lectura): índice de todos los componentes a la izquierda y, a la derecha, lo
  elegido de a un elemento (el carrusel de imágenes, una nota, una tabla o un PDF), con anterior/siguiente que
  recorren toda la materia.
  Las imágenes se ven en carrusel (también en la pestaña Imágenes y en las fichas, con opción de cuadrícula).
- **Carga de material con Claude Code:** el skill `.claude/skills/cargar-material` define las reglas (texto literal,
  solo ortografía declarada, nada unido, dividido ni rellenado; recuadros → una nota por encabezado; bloques
  tabulares con encabezado → tabla de Excel; cada hoja → su propio archivo; imágenes con su texto transcrito).
  Los originales quedan en `data/fuentes/<materia>/` (entran en los respaldos); `tools/carga/cargar.py` carga un
  `plan.json` (con respaldo previo y modo `--prueba`) y `auditar.py` comprueba celda por celda que todo coincida.
- **Acceso rápido por síntomas** (en el código, módulo `diagnostico`; la interfaz no usa esa palabra):
  repertorización determinista. Son candidatos las filas de las tablas, las notas y las imágenes (descripción
  y OCR). Cada síntoma se busca con FTS5 (prefijos, sin tildes) y se verifica en
  cualquier columna de la fila, o por renglón y título en notas e imágenes (siempre se busca en todo). Se ordenan por síntomas cubiertos (los «importantes» pesan el doble;
  a igualdad, primero quien tiene el síntoma en su título) con evidencia (columna o renglón resaltado),
  síntomas faltantes, «otros rasgos para confirmar», comparación del mejor candidato de cada materia
  (identificado por el ícono de la materia) y lo que dicen los PDF. Sin IA: todo sale del material y se
  muestra su origen. Es independiente de las materias: siempre revisa todas, arma un ranking por materia
  (ninguna queda tapada por otra) y guarda sus propios casos en la tabla `casos` (síntomas, conclusión y
  foto del análisis; van a la papelera como el resto). Las direcciones son `/acceso-rapido…`; las antiguas
  `/diagnostico…` redirigen.
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

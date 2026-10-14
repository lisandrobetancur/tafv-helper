# TAFV Helper

Aplicación web local para consultar `data/excel/Estudio homeopatia.xlsx`.
El Excel se usa **solo como lectura**: la app nunca lo modifica.

## Ejecutar (macOS, Windows y Linux)

Requisito: Python 3.10 o superior.

| Sistema | Comando |
|---|---|
| macOS / Linux | `./run.sh` |
| Windows | doble clic en `run.bat` (o `py run.py`) |
| Cualquiera | `python run.py [--port 8000] [--no-browser]` |

La primera vez crea `.venv` e instala las dependencias; luego abre http://127.0.0.1:8000.

## Módulo «Estudio homeopatía»
- **Estudio homeopatía**: pestaña *Registros* (tabla paginada y con scroll, con todas las columnas del Excel, ordenable, clic en una fila para ver la ficha completa) y pestaña *Filtros* (dos filtros con autocompletado: *Medicamento* (busca en medicamento y nombre en latín) y *Síntomas* (busca en sistemas, síntomas mentales, generales y particulares)).
- **Formulación**: la hoja tal cual, solo lectura.
- **Imágenes** (lo único que se "edita"; el Excel nunca se modifica): en la pestaña *Registros* cada fila tiene un botón *Agregar* y, desde la ficha del registro, se pueden arrastrar, ver y eliminar imágenes. En la pestaña *Filtros* solo se pueden ver: el ícono *Ver imagen* abre un modal con botón ✕ (y flechas si hay varias). Se guardan en `data/attachments/<id>/` y sus metadatos en `data/attachments.db`.

## Notas
- El menú lateral se puede replegar a una barra de íconos con el botón circular de su borde; el navegador recuerda la elección.
- Si cambias el Excel, usa el botón **Recargar Excel**.
- El id de cada registro sale del nombre del medicamento. Si renombras un medicamento en el Excel, sus imágenes quedarán huérfanas en `data/attachments/<id-anterior>/`.
- El archivo no contiene fechas reales: todo se trata como texto. Si Excel convirtió en fecha un valor digitado (p. ej. `6-7`), la app lo muestra como se digitó, sin que tengas que corregir el Excel.
- **Campos dinámicos:** las columnas no están fijas en el código. Se leen de los encabezados de la hoja «Estudio homeopatia» (fila 1; si la fila 2 repite los encabezados se trata como subencabezado y se combina, p. ej. «Otros Sintomas · Caracteristico»). Si el archivo trae menos o más columnas, la tabla, la ficha y los anchos se ajustan solos. Los filtros se construyen según los encabezados: *Medicamento* (columnas con «medicamento» o «latín») y *Síntomas* (columnas con «síntoma»), más *Otros síntomas* (columna «Otros síntomas»), que se oculta en la tabla de resultados de *Filtros* pero se ve en *Registros* y en la ficha; si no hay ninguno reconocible aparece una búsqueda general.
- **Rango de columnas:** por defecto se leen de la B a la O (`B:O`). Para cambiarlo: `EXCEL_COLUMNS="B:Q" ./run.sh` (macOS/Linux), `set EXCEL_COLUMNS=B:Q` y luego `run.bat` (Windows), o `B:` para leer todas hasta la última con datos. La hoja «Homeopatia» se omite.

## Pruebas
```
.venv/bin/pip install -r requirements-dev.txt     # Windows: .venv\Scripts\pip
.venv/bin/python -m pytest                        # Windows: .venv\Scripts\python -m pytest
```

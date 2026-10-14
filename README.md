# Biblioteca de Estudio

Aplicación local (FastAPI + HTMX + Alpine + Tailwind compilado) para organizar material de estudio de
medicina por **materias › componentes › subcomponentes**: Excel/CSV, PDF (con OCR), imágenes y notas,
con búsqueda global sin tildes.

> En construcción por fases. La documentación completa (arquitectura e instalación paso a paso) llega en la fase 7.

## Desarrollo rápido

```bash
python3.13 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m app            # abre http://127.0.0.1:8765
.venv/bin/python -m pytest         # pruebas
tools/compilar_css.sh --watch      # recompila el CSS al editar plantillas (necesita tools/tailwindcss)
```

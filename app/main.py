from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .attachments import MAX_BYTES, AttachmentStore
from .excel_repo import DEFAULT_COLUMNS, ExcelRepo

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
EXCEL_PATH = Path(os.environ.get("EXCEL_PATH", DATA_DIR / "excel" / "Estudio homeopatia.xlsx"))

# Rango de columnas del Excel que se leen ("B:O", o "B:" para todas hasta la última con datos)
EXCEL_COLUMNS = os.environ.get("EXCEL_COLUMNS", DEFAULT_COLUMNS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.repo = ExcelRepo(EXCEL_PATH, EXCEL_COLUMNS)
    app.state.store = AttachmentStore(DATA_DIR / "attachments", DATA_DIR / "attachments.db")
    yield


app = FastAPI(title="TAFV Helper", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=BASE_DIR / "app" / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "app" / "templates")
templates.env.globals["excel_name"] = EXCEL_PATH.name


def repo(request: Request) -> ExcelRepo:
    return request.app.state.repo


def store(request: Request) -> AttachmentStore:
    return request.app.state.store


def public(rec: dict, counts: dict[str, int]) -> dict:
    out = {k: v for k, v in rec.items() if k != "_norm"}
    out["adjuntos"] = counts.get(rec["id"], 0)
    return out


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return FileResponse(BASE_DIR / "app" / "static" / "img" / "logo-corpas.png", media_type="image/png")


# ------------------------------------------------------------------ páginas
@app.get("/")
def home(request: Request):
    from fastapi.responses import RedirectResponse
    return RedirectResponse("/estudio-homeopatia")


@app.get("/estudio-homeopatia")
def page_estudio(request: Request):
    return templates.TemplateResponse(request, "estudio.html", {"active": "estudio"})


@app.get("/formulacion")
def page_formulacion(request: Request):
    return templates.TemplateResponse(
        request, "formulacion.html",
        {"active": "formulacion", "table": repo(request).formulacion},
    )


# ---------------------------------------------------------------------- API
@app.get("/api/meta")
def api_meta(request: Request):
    r = repo(request)
    return {
        "fields": [{k: f[k] for k in ("key", "label", "letter", "width", "hide_in_filters")} for f in r.fields],
        "filters": [{k: f[k] for k in ("key", "label", "placeholder")} for f in r.filters],
        "total": len(r.records),
        "columns": r.columns,
        "loaded_at": r.loaded_at.isoformat(timespec="seconds") if r.loaded_at else None,
    }


@app.get("/api/records")
def api_records(request: Request):
    """Sin parámetros devuelve todo; con parámetros filtra (el Excel no se toca)."""
    params = request.query_params
    found = repo(request).search(dict(params))
    counts = store(request).counts()
    return {"total": len(repo(request).records), "records": [public(r, counts) for r in found]}


@app.get("/api/suggest")
def api_suggest(request: Request, field: str, q: str = ""):
    try:
        return repo(request).suggest(field, q)
    except KeyError:
        raise HTTPException(400, "Campo no permitido")


@app.post("/api/reload")
def api_reload(request: Request):
    repo(request).load()
    return {"total": len(repo(request).records)}


def _record_or_404(request: Request, record_id: str) -> dict:
    rec = repo(request).by_id.get(record_id)
    if rec is None:
        raise HTTPException(404, "Registro no encontrado")
    return rec


@app.get("/api/records/{record_id}/attachments")
def api_list_attachments(request: Request, record_id: str):
    _record_or_404(request, record_id)
    return store(request).list(record_id)


@app.post("/api/records/{record_id}/attachments")
async def api_add_attachments(request: Request, record_id: str, files: list[UploadFile] = File(...)):
    _record_or_404(request, record_id)
    added, errors = [], []
    for f in files:
        data = await f.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            errors.append(f"{f.filename}: supera {MAX_BYTES // (1024 * 1024)} MB")
            continue
        try:
            added.append(store(request).add(record_id, f.filename or "imagen", data))
        except ValueError as e:
            errors.append(f"{f.filename}: {e}")
    return {"added": added, "errors": errors}


@app.get("/api/attachments/{attachment_id}/file")
def api_attachment_file(request: Request, attachment_id: str):
    info = store(request).file_info(attachment_id)
    if info is None or not info[0].exists():
        raise HTTPException(404, "Archivo no encontrado")
    return FileResponse(info[0], media_type=info[1], headers={"X-Content-Type-Options": "nosniff"})


@app.delete("/api/attachments/{attachment_id}")
def api_delete_attachment(request: Request, attachment_id: str):
    if not store(request).delete(attachment_id):
        raise HTTPException(404, "Archivo no encontrado")
    return {"ok": True}

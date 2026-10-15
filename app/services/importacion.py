"""Estado del asistente de importación de Excel/CSV.

El archivo subido y sus hojas ya leídas se guardan en data/cache/importaciones/<token>/
mientras dura el asistente (así cada paso no vuelve a abrir el Excel). Se borra al terminar
o, si se abandona, al iniciar la app al día siguiente.
"""
from __future__ import annotations

import json
import secrets
import shutil
import sqlite3
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from ..config import rutas
from ..errores import ErrorUsuario
from . import almacenamiento as alm
from . import hojas as lector
from .texto import normalizar

NOMBRES_GENERICOS = {"sheet1", "hoja1", "hoja 1", "sheet 1", "datos", "data"}


@dataclass
class ConfigHoja:
    fila_encabezado: int
    dos_filas: bool
    columnas: list[int]
    titulo: int | None
    clave: int | None
    nombre_tabla: str


@dataclass
class Estado:
    token: str
    componente_id: int
    tabla_id: int | None            # si es una actualización de una tabla existente
    archivo_original: str
    nombre: str                     # nombre descriptivo que escribe la usuaria al subirlo
    hash: str
    hojas: list[dict]               # [{"nombre", "filas", "columnas"}]
    seleccion: list[int] = field(default_factory=list)
    actual: int = 0                 # posición dentro de `seleccion` en los pasos 3 y 4
    config: dict[str, dict] = field(default_factory=dict)
    duplicado_de: str | None = None
    etiquetas: str = ""             # etiquetas para las tablas nuevas (opcional, separadas por comas)

    @property
    def es_reemplazo(self) -> bool:
        return self.tabla_id is not None

    @property
    def hoja_actual(self) -> int:
        return self.seleccion[self.actual]

    def config_hoja(self, indice: int) -> ConfigHoja:
        return ConfigHoja(**self.config[str(indice)])

    def poner_config(self, indice: int, cfg: ConfigHoja) -> None:
        self.config[str(indice)] = asdict(cfg)


def _carpeta(token: str) -> Path:
    if not token.isalnum():
        raise ErrorUsuario("La importación no es válida. Vuelve a empezar.")
    return rutas.cache / "importaciones" / token


def nombre_sugerido(nombre_archivo: str) -> str:
    """"atlas_miembro-superior.xlsx" -> "atlas miembro superior" (punto de partida editable)."""
    return " ".join(Path(nombre_archivo).stem.replace("_", " ").replace("-", " ").split())[:80]


def crear(con: sqlite3.Connection, componente_id: int, nombre_original: str, datos_archivo: Path,
          nombre_descriptivo: str, tabla_id: int | None = None, etiquetas: str = "") -> Estado:
    """Guarda el archivo subido, lo lee y crea el estado del asistente."""
    descriptivo = " ".join((nombre_descriptivo or "").split())[:80]
    if not descriptivo:
        raise ErrorUsuario("Escribe un nombre descriptivo para el archivo.")
    nombre = alm.sanear_nombre_archivo(nombre_original or "archivo")
    if Path(nombre).suffix.lower() not in lector.EXTENSIONES | {".xls"}:
        raise ErrorUsuario("Formato no compatible. Sube un archivo de Excel (.xlsx) o CSV.")
    token = secrets.token_hex(8)
    carpeta = _carpeta(token)
    carpeta.mkdir(parents=True, exist_ok=True)
    destino = carpeta / f"original{Path(nombre).suffix.lower()}"
    shutil.move(str(datos_archivo), destino)
    try:
        leidas = lector.leer_archivo(destino, nombre)
    except Exception:
        shutil.rmtree(carpeta, ignore_errors=True)
        raise
    hash_ = alm.hash_archivo(destino)
    (carpeta / "hojas.json").write_text(json.dumps([{"nombre": h.nombre, "filas": h.filas} for h in leidas],
                                                   ensure_ascii=False), encoding="utf-8")
    duplicado = con.execute(
        "SELECT nombre FROM tablas WHERE hash = ? AND componente_id = ? AND papelera_id IS NULL", (hash_, componente_id)
    ).fetchone()
    estado = Estado(token=token, componente_id=componente_id, tabla_id=tabla_id, archivo_original=nombre,
                    nombre=descriptivo, hash=hash_,
                    hojas=[{"nombre": h.nombre, "filas": h.num_filas, "columnas": h.num_columnas} for h in leidas],
                    duplicado_de=duplicado["nombre"] if duplicado and not tabla_id else None,
                    etiquetas=(etiquetas or "").strip()[:300])
    con_datos = [i for i, h in enumerate(leidas) if h.filas]
    estado.seleccion = con_datos[:1] if len(con_datos) > 1 else con_datos
    guardar(estado)
    return estado


def cargar(token: str) -> Estado:
    archivo = _carpeta(token) / "estado.json"
    if not archivo.exists():
        raise ErrorUsuario("La importación caducó o ya terminó. Vuelve a subir el archivo.", 410)
    return Estado(**json.loads(archivo.read_text(encoding="utf-8")))


def guardar(estado: Estado) -> None:
    (_carpeta(estado.token) / "estado.json").write_text(json.dumps(asdict(estado), ensure_ascii=False), encoding="utf-8")


def hojas(estado: Estado) -> list[lector.Hoja]:
    datos = json.loads((_carpeta(estado.token) / "hojas.json").read_text(encoding="utf-8"))
    return [lector.Hoja(d["nombre"], d["filas"]) for d in datos]


def archivo_subido(estado: Estado) -> Path:
    return next(_carpeta(estado.token).glob("original.*"))


def descartar(token: str) -> None:
    shutil.rmtree(_carpeta(token), ignore_errors=True)


def limpiar_viejas(horas: int = 24) -> None:
    base = rutas.cache / "importaciones"
    if not base.exists():
        return
    limite = time.time() - horas * 3600
    for carpeta in base.iterdir():
        if carpeta.is_dir() and carpeta.stat().st_mtime < limite:
            shutil.rmtree(carpeta, ignore_errors=True)


# ---------------------------------------------------------- valores sugeridos
def config_sugerida(estado: Estado, indice: int, hoja: lector.Hoja, anterior: dict | None = None) -> ConfigHoja:
    """Configuración inicial de una hoja. En actualizaciones parte de la de la tabla existente."""
    if str(indice) in estado.config:
        return estado.config_hoja(indice)
    # El encabezado se detecta siempre en el archivo nuevo (puede tener otra estructura);
    # de la tabla anterior solo se reutilizan las columnas, por nombre.
    fila = lector.detectar_encabezado(hoja)
    dos = lector.parece_subencabezado(hoja, fila)
    cols = lector.columnas(hoja, fila, dos)
    # Nombre de la tabla: el descriptivo; si el archivo tiene varias hojas, se le agrega la hoja
    # (al actualizar una tabla se respeta tal cual el nombre escrito)
    nombre = estado.nombre
    if not anterior and len(estado.hojas) > 1 and normalizar(hoja.nombre) not in NOMBRES_GENERICOS:
        nombre = f"{estado.nombre} · {hoja.nombre}"
    if anterior:  # mismas columnas (por nombre) que la tabla existente
        previas = {normalizar(c["nombre"]): c["clave"] for c in anterior["columnas"]}
        elegidas = [c.indice for c in cols if normalizar(c.nombre) in previas] or [c.indice for c in cols]
        por_clave = {previas[normalizar(c.nombre)]: c.indice for c in cols if normalizar(c.nombre) in previas}
        titulo = por_clave.get(anterior["columna_titulo"], lector.columna_titulo_sugerida(cols))
        clave = por_clave.get(anterior["columna_clave"]) if anterior["columna_clave"] else None
    else:
        elegidas = [c.indice for c in cols]
        titulo, clave = lector.columna_titulo_sugerida(cols), None
    return ConfigHoja(fila, dos, elegidas, titulo, clave, nombre[:80])

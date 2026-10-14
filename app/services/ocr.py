"""Reconocimiento de texto (OCR) con RapidOCR, en segundo plano.

- Modelos en <proyecto>/modelos/ocr/ (viajan con la carpeta: funciona sin internet).
  Se usa el reconocedor "latin" (español: tildes, ñ, ¿?) y, si no está descargado,
  el modelo incluido en el paquete, que también reconoce español.
- Cola persistente: las páginas pendientes se marcan en la base de datos, así que si la
  app se cierra a mitad, el OCR continúa donde iba al volver a abrirla.

Descargar los modelos (lo hace `instalar`): python -m app.services.ocr
"""
from __future__ import annotations

import logging
import shutil
import sqlite3
import threading
from collections.abc import Callable
from pathlib import Path

from ..config import ROOT

log = logging.getLogger(__name__)

MODELOS_DIR = ROOT / "modelos" / "ocr"
MODELO_LATINO = "latin_PP-OCRv5_rec_mobile.onnx"
RESOLUCION_PDF = 200  # ppp al convertir páginas escaneadas en imagen
LADO_MAXIMO = 3000


# ------------------------------------------------------------------ motor
_motor = None
_motor_lock = threading.Lock()


def _parametros(latino: bool) -> dict:
    from rapidocr.utils.typings import LangRec, ModelType, OCRVersion
    params: dict = {"Global.log_level": "error", "Global.model_root_dir": str(MODELOS_DIR)}
    if latino:
        params |= {"Rec.lang_type": LangRec.LATIN, "Rec.ocr_version": OCRVersion.PPOCRV5,
                   "Rec.model_type": ModelType.MOBILE}
    return params


def _copiar_modelos_incluidos() -> None:
    """Los modelos de detección incluidos en el paquete se copian a modelos/ocr (sin descargar)."""
    import rapidocr
    origen = Path(rapidocr.__file__).parent / "models"
    MODELOS_DIR.mkdir(parents=True, exist_ok=True)
    for modelo in origen.glob("*.onnx"):
        destino = MODELOS_DIR / modelo.name
        if not destino.exists():
            shutil.copy2(modelo, destino)


def preparar_modelos() -> str:
    """Deja los modelos listos dentro del proyecto (descarga el latino si hay internet)."""
    _copiar_modelos_incluidos()
    if not (MODELOS_DIR / MODELO_LATINO).exists():
        from PIL import Image, ImageDraw, ImageFont
        from rapidocr import RapidOCR
        # RapidOCR descarga el modelo la primera vez que reconoce texto: se le da una muestra
        muestra = Image.new("RGB", (900, 120), "white")
        ImageDraw.Draw(muestra).text((20, 30), "Prueba de lectura: fémur", fill="black",
                                     font=ImageFont.load_default(size=48))
        RapidOCR(params=_parametros(latino=True))(muestra)
    return "latino" if (MODELOS_DIR / MODELO_LATINO).exists() else "incluido"


def motor():
    """Motor de OCR (se crea una sola vez; es costoso)."""
    global _motor
    with _motor_lock:
        if _motor is None:
            from rapidocr import RapidOCR
            _copiar_modelos_incluidos()
            latino = (MODELOS_DIR / MODELO_LATINO).exists()
            if not latino:
                log.warning("Modelo OCR latino no disponible; se usa el incluido en el paquete")
            _motor = RapidOCR(params=_parametros(latino))
        return _motor


def reconocer(imagen) -> str:
    """Texto de una imagen (ruta, bytes, PIL.Image o arreglo), línea por línea en orden de lectura."""
    from PIL import Image
    if isinstance(imagen, (str, Path)):
        with Image.open(imagen) as abierta:
            imagen = abierta.copy()
    if isinstance(imagen, Image.Image):  # RapidOCR la convierte igual que un archivo
        imagen = imagen.convert("RGB")
        if max(imagen.size) > LADO_MAXIMO:
            imagen.thumbnail((LADO_MAXIMO, LADO_MAXIMO))
    resultado = motor()(imagen)
    return _ordenar_lineas(resultado.boxes, resultado.txts) if resultado.txts else ""


def _ordenar_lineas(cajas, textos) -> str:
    """Agrupa los fragmentos que están a la misma altura en una línea, de arriba abajo y de izquierda a derecha."""
    piezas = []
    for caja, texto in zip(cajas, textos):
        ys = [p[1] for p in caja]
        xs = [p[0] for p in caja]
        piezas.append((min(ys), max(ys), min(xs), texto))
    piezas.sort(key=lambda p: (p[0], p[2]))
    lineas: list[list] = []
    for arriba, abajo, izquierda, texto in piezas:
        centro = (arriba + abajo) / 2
        if lineas and abs(centro - lineas[-1][0]) < (abajo - arriba) * 0.6:
            lineas[-1][1].append((izquierda, texto))
        else:
            lineas.append([centro, [(izquierda, texto)]])
    return "\n".join(" ".join(t for _, t in sorted(partes)) for _, partes in lineas)


# ------------------------------------------------------------- trabajador
# Cada "fuente" de trabajos es una función (conexión) -> bool que procesa UN trabajo
# pendiente y devuelve True, o False si no le queda nada. Las registran los servicios.
Fuente = Callable[[sqlite3.Connection], bool]
_fuentes: list[Fuente] = []
_hay_trabajo = threading.Event()
_detener = threading.Event()
_hilo: threading.Thread | None = None


def registrar_fuente(fuente: Fuente) -> None:
    if fuente not in _fuentes:
        _fuentes.append(fuente)


def avisar_trabajo() -> None:
    """Despierta al trabajador (p. ej. al subir un PDF escaneado)."""
    _hay_trabajo.set()


def _bucle(conectar: Callable[[], sqlite3.Connection]) -> None:
    con = conectar()
    try:
        while not _detener.is_set():
            hizo_algo = False
            for fuente in list(_fuentes):
                if _detener.is_set():
                    break
                try:
                    hizo_algo = fuente(con) or hizo_algo
                except Exception:
                    log.exception("Error en el OCR en segundo plano")
            if not hizo_algo:
                _hay_trabajo.wait(timeout=30)
                _hay_trabajo.clear()
    finally:
        con.close()


def iniciar(conectar: Callable[[], sqlite3.Connection]) -> None:
    global _hilo
    if _hilo and _hilo.is_alive():
        return
    _detener.clear()
    _hilo = threading.Thread(target=_bucle, args=(conectar,), name="ocr", daemon=True)
    _hilo.start()
    avisar_trabajo()


def detener(espera: float = 5) -> None:
    _detener.set()
    _hay_trabajo.set()
    if _hilo:
        _hilo.join(timeout=espera)


if __name__ == "__main__":
    print("Preparando los modelos de OCR en", MODELOS_DIR)
    try:
        usado = preparar_modelos()
        print("Listo. Modelo de reconocimiento:", "latino (español)" if usado == "latino" else "incluido")
    except Exception as e:  # sin internet: se usará el incluido
        print("No se pudo descargar el modelo latino (¿sin internet?). Se usará el incluido.", e)

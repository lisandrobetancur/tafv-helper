"""Registro de actividad en data/logs/app.log (rotativo)."""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from .config import rutas


def configurar_registro() -> None:
    rutas.logs.mkdir(parents=True, exist_ok=True)
    raiz = logging.getLogger()
    if any(getattr(h, "_biblioteca", False) for h in raiz.handlers):
        return
    archivo = RotatingFileHandler(rutas.logs / "app.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    archivo.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    archivo._biblioteca = True  # type: ignore[attr-defined]
    raiz.addHandler(archivo)
    raiz.setLevel(logging.INFO)

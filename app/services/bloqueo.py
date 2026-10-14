"""Archivo de bloqueo data/.en_uso: evita usar la biblioteca en dos equipos a la vez.

La carpeta se comparte entre equipos (copiándola o sincronizándola); si dos
equipos la modifican al mismo tiempo los cambios de uno se pierden. Al
iniciar se escribe el nombre del equipo y la hora; si otro equipo ya la
tiene abierta se avisa y se puede forzar.
"""
from __future__ import annotations

import json
import logging
import os
import platform
import socket
from dataclasses import dataclass
from datetime import datetime

from ..config import rutas

log = logging.getLogger(__name__)


def nombre_equipo() -> str:
    return platform.node() or socket.gethostname() or "este equipo"


@dataclass
class EstadoBloqueo:
    libre: bool
    equipo: str = ""
    desde: str = ""


def leer() -> dict | None:
    try:
        return json.loads(rutas.bloqueo.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def adquirir(forzar: bool = False) -> EstadoBloqueo:
    """Toma el bloqueo. Si lo tiene otro equipo y no se fuerza, devuelve quién lo tiene."""
    actual = leer()
    if actual and actual.get("equipo") != nombre_equipo() and not forzar:
        return EstadoBloqueo(libre=False, equipo=actual.get("equipo", "otro equipo"), desde=actual.get("inicio", ""))
    if actual and forzar:
        log.warning("Bloqueo forzado; lo tenía %s desde %s", actual.get("equipo"), actual.get("inicio"))
    rutas.datos.mkdir(parents=True, exist_ok=True)
    rutas.bloqueo.write_text(
        json.dumps({"equipo": nombre_equipo(), "inicio": datetime.now().isoformat(timespec="seconds"), "pid": os.getpid()},
                   ensure_ascii=False),
        encoding="utf-8",
    )
    return EstadoBloqueo(libre=True)


def liberar() -> None:
    """Libera el bloqueo solo si es nuestro."""
    actual = leer()
    if actual and actual.get("equipo") == nombre_equipo() and actual.get("pid") == os.getpid():
        try:
            rutas.bloqueo.unlink()
        except OSError:
            pass

"""Inicia la biblioteca: `python -m app [--puerto 8765] [--sin-navegador]`.

Usa el puerto indicado (por defecto 8765) o, si está ocupado, el siguiente libre,
y abre el navegador cuando el servidor está listo.
"""
from __future__ import annotations

import argparse
import os
import socket
import threading
import time
import urllib.request
import webbrowser

import uvicorn

from .config import PUERTO_POR_DEFECTO


def puerto_libre(preferido: int, intentos: int = 20) -> int:
    for puerto in range(preferido, preferido + intentos):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if os.name != "nt":
                # Igual que Uvicorn: un puerto recién liberado (TIME_WAIT) se puede reutilizar.
                # En Windows esta opción permitiría "robar" un puerto en uso, así que no se usa.
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind(("127.0.0.1", puerto))
                return puerto
            except OSError:
                continue
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:  # cualquiera libre
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def abrir_cuando_este_listo(url: str) -> None:
    for _ in range(120):
        try:
            urllib.request.urlopen(url + "static/marca/logo-corpas.png", timeout=1)
            webbrowser.open(url)
            return
        except Exception:
            time.sleep(0.5)


def main() -> None:
    parser = argparse.ArgumentParser(description="Biblioteca de Estudio")
    parser.add_argument("--puerto", type=int, default=PUERTO_POR_DEFECTO)
    parser.add_argument("--sin-navegador", action="store_true")
    args = parser.parse_args()

    puerto = puerto_libre(args.puerto)
    url = f"http://127.0.0.1:{puerto}/"
    if puerto != args.puerto:
        print(f"El puerto {args.puerto} está ocupado; se usa el {puerto}.")
    print(f"\n  Biblioteca de Estudio abierta en {url}\n  Para cerrarla, cierra esta ventana o pulsa Ctrl+C.\n")
    if not args.sin_navegador:
        threading.Thread(target=abrir_cuando_este_listo, args=(url,), daemon=True).start()
    uvicorn.run("app.main:app", host="127.0.0.1", port=puerto, log_level="warning")


if __name__ == "__main__":
    main()

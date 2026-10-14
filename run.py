#!/usr/bin/env python3
"""Lanzador multiplataforma (macOS / Windows / Linux), solo biblioteca estándar.

Crea .venv la primera vez, instala dependencias cuando cambia requirements.txt,
arranca el servidor en 127.0.0.1 y abre el navegador.
    python run.py [--port 8000] [--no-browser]
"""
import argparse
import hashlib
import os
import subprocess
import sys
import threading
import time
import urllib.request
import venv
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"
REQS = ROOT / "requirements.txt"
STAMP = VENV / ".requirements.sha256"
PY = VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def ensure_env() -> None:
    if sys.version_info < (3, 10):
        sys.exit("Se requiere Python 3.10 o superior.")
    if not PY.exists():
        print("Creando entorno virtual (.venv)…")
        venv.EnvBuilder(with_pip=True).create(VENV)
    digest = hashlib.sha256(REQS.read_bytes()).hexdigest()
    if not STAMP.exists() or STAMP.read_text().strip() != digest:
        print("Instalando dependencias…")
        subprocess.check_call([str(PY), "-m", "pip", "install", "--quiet", "-r", str(REQS)])
        STAMP.write_text(digest)


def open_when_ready(url: str) -> None:
    for _ in range(120):
        try:
            urllib.request.urlopen(url + "api/meta", timeout=1)
            webbrowser.open(url)
            return
        except Exception:
            time.sleep(0.5)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8000)))
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args()

    ensure_env()
    url = f"http://127.0.0.1:{args.port}/"
    if not args.no_browser:
        threading.Thread(target=open_when_ready, args=(url,), daemon=True).start()
    print(f"Servidor en {url}  (Ctrl+C para detener)")
    try:
        subprocess.call(
            [str(PY), "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(args.port)],
            cwd=ROOT,
        )
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()

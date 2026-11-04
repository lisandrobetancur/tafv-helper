"""Versión de escritorio de la Biblioteca de Estudio: la misma app, en una ventana propia y sin instalar Python.

Es el punto de entrada del ejecutable que arma PyInstaller (ver escritorio/). Al abrirse:
1. Usa una carpeta de datos del usuario, que sí admite escritura (la del programa instalado no):
   - Windows: %APPDATA%\\Biblioteca de Estudio
   - Mac:     ~/Library/Application Support/Biblioteca de Estudio
   La primera vez la llena con la biblioteca incluida en el instalador (base de datos y archivos) y los modelos
   del OCR. Nunca sobrescribe una biblioteca que ya exista: al instalar una versión nueva, los datos se conservan.
2. Arranca el servidor local (127.0.0.1, sin internet) en un puerto libre.
3. Abre la ventana. Al cerrarla, se cierra todo.

Para probar sin empaquetar: `python escritorio.py` (con `--navegador` usa el navegador en vez de la ventana).
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
import threading
import time
import urllib.request
from pathlib import Path

NOMBRE = "Biblioteca de Estudio"
EMPAQUETADO = getattr(sys, "frozen", False)
# Archivos que viajan con el programa: dentro del paquete de PyInstaller, o la carpeta del proyecto al probar
RECURSOS = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))


def carpeta_usuario() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
    return base / NOMBRE


def _copiar_si_falta(origen: Path, destino: Path) -> None:
    if not origen.exists():
        return
    if origen.is_dir():
        for archivo in origen.rglob("*"):
            if archivo.is_file():
                final = destino / archivo.relative_to(origen)
                if not final.exists():
                    final.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(archivo, final)
    elif not destino.exists():
        destino.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(origen, destino)


def preparar_carpetas() -> tuple[Path, Path]:
    """Carpeta de datos y de modelos del OCR. Fuera del paquete, al probar, se usan las del proyecto."""
    if not EMPAQUETADO and not os.environ.get("BIBLIOTECA_ESCRITORIO_CARPETA_USUARIO"):
        return RECURSOS / "data", RECURSOS / "modelos" / "ocr"
    usuario = carpeta_usuario()
    datos, modelos = usuario / "data", usuario / "modelos" / "ocr"
    iniciales = RECURSOS / "datos_iniciales"
    if not (datos / "biblioteca.db").exists():                 # primera vez: la biblioteca incluida
        _copiar_si_falta(iniciales / "biblioteca.db", datos / "biblioteca.db")
        _copiar_si_falta(iniciales / "archivos", datos / "archivos")
    _copiar_si_falta(RECURSOS / "modelos" / "ocr", modelos)    # modelos nuevos de una versión nueva
    return datos, modelos


def puerto_libre() -> int:
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def esperar(url: str, segundos: float = 60) -> bool:
    limite = time.monotonic() + segundos
    while time.monotonic() < limite:
        try:
            urllib.request.urlopen(url + "static/marca/logo-corpas.png", timeout=1)
            return True
        except Exception:  # noqa: BLE001 - todavía arrancando
            time.sleep(0.2)
    return False


def main() -> None:
    parser = argparse.ArgumentParser(description=NOMBRE)
    parser.add_argument("--navegador", action="store_true", help="abrir en el navegador en vez de una ventana")
    parser.add_argument("--sin-ventana", action="store_true", help="solo el servidor (pruebas del empaquetado)")
    args = parser.parse_args()

    datos, modelos = preparar_carpetas()
    os.environ["BIBLIOTECA_DATOS"] = str(datos)          # antes de importar la app: config lee estas variables
    os.environ["BIBLIOTECA_MODELOS"] = str(modelos)

    import uvicorn
    from app.main import app

    puerto = puerto_libre()
    url = f"http://127.0.0.1:{puerto}/"
    servidor = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=puerto, log_level="warning"))
    hilo = threading.Thread(target=servidor.run, daemon=True)
    hilo.start()
    if not esperar(url):
        sys.exit("La biblioteca no pudo arrancar. Revisa los registros en " + str(datos / "logs"))
    print(f"{NOMBRE} en {url}", flush=True)

    if args.sin_ventana or args.navegador:
        if args.navegador:
            import webbrowser
            webbrowser.open(url)
        try:
            while hilo.is_alive():
                time.sleep(0.5)
        except KeyboardInterrupt:
            pass
    else:
        try:
            import webview
        except ImportError:                               # sin la librería de ventanas: el navegador
            import webbrowser
            webbrowser.open(url)
            hilo.join()
            return
        webview.settings["ALLOW_DOWNLOADS"] = True                   # respaldos, PDF y Word de recopilaciones
        webview.settings["OPEN_EXTERNAL_LINKS_IN_BROWSER"] = True
        webview.create_window(NOMBRE, url, width=1360, height=880, min_size=(900, 600), text_select=True)
        webview.start(private_mode=False)                            # guarda el tema y las preferencias
    servidor.should_exit = True
    hilo.join(timeout=10)


if __name__ == "__main__":
    main()

"""Instalación y arranque de la Biblioteca de Estudio (solo biblioteca estándar de Python).

Lo usan instalar.command / iniciar.command (Mac) e instalar.bat / iniciar.bat (Windows):
    python instalador.py instalar   -> crea .venv, instala dependencias y prepara el OCR
    python instalador.py iniciar    -> comprueba el entorno (lo repara si hace falta) y abre la biblioteca

El entorno .venv es propio de cada equipo: si se copió la carpeta desde otro sistema
(p. ej. de un Mac a Windows) o el entorno se rompió (p. ej. tras actualizar Python),
se detecta y se vuelve a crear.
"""
from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
import venv
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
VENV = RAIZ / ".venv"
MARCA = VENV / "biblioteca-entorno.json"
WINDOWS = os.name == "nt"
PY_VENV = VENV / ("Scripts/python.exe" if WINDOWS else "bin/python")
MAC_INTEL = sys.platform == "darwin" and platform.machine() == "x86_64"


def decir(texto: str = "") -> None:
    try:
        print(texto, flush=True)
    except UnicodeEncodeError:  # consola de Windows sin UTF-8 (p. ej. salida redirigida): ✓ y ✖ se reemplazan
        codificacion = sys.stdout.encoding or "ascii"
        print(texto.encode(codificacion, "replace").decode(codificacion), flush=True)


def titulo(texto: str) -> None:
    decir()
    decir("=" * 60)
    decir(f"  {texto}")
    decir("=" * 60)


def fallar(texto: str) -> None:
    decir()
    decir("  ✖ " + texto.replace("\n", "\n    "))
    decir()
    sys.exit(1)


# ------------------------------------------------------------- comprobaciones
def comprobar_python() -> None:
    v = sys.version_info
    if v < (3, 11):
        fallar(f"Este Python es la versión {v.major}.{v.minor}; se necesita la 3.11, 3.12 o 3.13.\n"
               "Instala Python 3.13 desde https://www.python.org/downloads/ (lee INSTALACION.md).")
    if MAC_INTEL and v >= (3, 14):
        fallar("En un Mac con procesador Intel se necesita Python 3.11, 3.12 o 3.13 (la 3.14 aún no es compatible\n"
               "con el lector de texto OCR). Instala Python 3.13 desde https://www.python.org/downloads/")
    try:
        import sqlite3
        sqlite3.connect(":memory:").execute("CREATE VIRTUAL TABLE t USING fts5(x)")
    except Exception:
        fallar("El Python instalado no incluye el buscador de texto (SQLite FTS5).\n"
               "Instala Python desde https://www.python.org/downloads/ (el instalador oficial lo incluye).")


def firma() -> dict:
    """Identifica el sistema para el que se creó el .venv."""
    return {"sistema": sys.platform, "arquitectura": platform.machine(),
            "python": f"{sys.version_info.major}.{sys.version_info.minor}",
            "requisitos": (RAIZ / "requirements.txt").read_text(encoding="utf-8")}


def entorno_valido() -> tuple[bool, str]:
    if not PY_VENV.exists():
        return False, "no existe" if not VENV.exists() else "se creó en otro sistema"
    try:
        marca = json.loads(MARCA.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False, "está incompleto"
    actual = firma()
    if (marca.get("sistema"), marca.get("arquitectura")) != (actual["sistema"], actual["arquitectura"]):
        return False, f"se creó en otro equipo ({marca.get('sistema')}, {marca.get('arquitectura')})"
    if marca.get("python") != actual["python"]:
        return False, f"se creó con Python {marca.get('python')}"
    if marca.get("requisitos") != actual["requisitos"]:
        return False, "las dependencias cambiaron"
    try:  # p. ej. tras actualizar Python con Homebrew el entorno queda roto
        subprocess.run([str(PY_VENV), "-c", "import fastapi, pymupdf, rapidocr"], check=True,
                       capture_output=True, timeout=120)
    except (OSError, subprocess.SubprocessError):
        return False, "está dañado"
    return True, ""


# ------------------------------------------------------------------ instalar
def instalar() -> None:
    titulo("Biblioteca de Estudio · Instalación")
    comprobar_python()
    decir(f"  Python {platform.python_version()} ({sys.platform}, {platform.machine()}) ✓")

    valido, motivo = entorno_valido()
    if VENV.exists() and not valido:
        decir(f"  El entorno de Python del proyecto {motivo}: se volverá a crear.")
        shutil.rmtree(VENV, ignore_errors=True)
    if not PY_VENV.exists():
        decir("  Creando el entorno de Python (.venv)…")
        venv.EnvBuilder(with_pip=True, clear=True).create(VENV)

    decir("  Instalando los componentes (la primera vez tarda unos minutos)…")
    pip = [str(PY_VENV), "-m", "pip", "--disable-pip-version-check"]
    try:
        subprocess.run(pip + ["install", "--upgrade", "pip"], check=True, capture_output=True)
        subprocess.run(pip + ["install", "-r", str(RAIZ / "requirements.txt")], check=True)
    except subprocess.CalledProcessError:
        fallar("No se pudieron instalar los componentes. Comprueba la conexión a internet y vuelve a\n"
               "ejecutar «instalar». Si se repite, revisa la sección de problemas de INSTALACION.md.")

    decir("  Preparando el lector de texto (OCR) en español…")
    r = subprocess.run([str(PY_VENV), "-m", "app.services.ocr"], cwd=RAIZ, capture_output=True, text=True)
    decir("    " + (r.stdout.strip().splitlines() or ["Listo."])[-1])

    MARCA.write_text(json.dumps(firma(), ensure_ascii=False, indent=2), encoding="utf-8")
    titulo("¡Listo! Ya puedes abrir la biblioteca con «iniciar».")


# ------------------------------------------------------------------- iniciar
def iniciar(argumentos: list[str]) -> None:
    comprobar_python()
    valido, motivo = entorno_valido()
    if not valido:
        decir(f"El entorno de Python del proyecto {motivo}. Se instalará primero (solo esta vez).")
        instalar()
    titulo("Biblioteca de Estudio")
    decir("  Se abrirá en tu navegador. Para cerrarla, cierra esta ventana.")
    os.chdir(RAIZ)
    comando = [str(PY_VENV), "-m", "app", *argumentos]
    if WINDOWS:
        sys.exit(subprocess.call(comando))
    os.execv(str(PY_VENV), comando)


if __name__ == "__main__":
    if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    accion = sys.argv[1] if len(sys.argv) > 1 else "iniciar"
    try:
        if accion == "instalar":
            instalar()
        elif accion == "iniciar":
            iniciar(sys.argv[2:])
        else:
            fallar("Uso: python instalador.py [instalar | iniciar]")
    except KeyboardInterrupt:
        decir("\nCancelado.")

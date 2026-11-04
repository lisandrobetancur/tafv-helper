"""Construye la versión de escritorio e instalador para el sistema en que se ejecuta.

    python escritorio/construir.py            (desde la carpeta del proyecto, con requirements-escritorio.txt instalado)

Pasos:
1. Comprueba que el programa tenga la clave pública de licencias (si no, ningún equipo podría activarlo).
2. Prepara build/recursos-escritorio: la biblioteca inicial (copia consistente de data/biblioteca.db y data/archivos),
   los modelos del OCR y los íconos.
3. Arma el programa con PyInstaller (dist/Biblioteca de Estudio/ o dist/Biblioteca de Estudio.app).
4. Arma el instalador:
   - Windows: dist/Instalador-Biblioteca-de-Estudio.exe con Inno Setup (gratis; si no está instalado, queda la carpeta).
   - Mac: firma «ad hoc» (gratis; necesaria en Mac con procesador Apple) y dist/Biblioteca-de-Estudio.dmg.
"""
from __future__ import annotations

import os
import shutil
import sqlite3
import subprocess
import sys
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
RECURSOS = RAIZ / "build" / "recursos-escritorio"
DIST = RAIZ / "dist"
NOMBRE = "Biblioteca de Estudio"
VERSION = os.environ.get("BIBLIOTECA_VERSION") or date.today().strftime("%Y.%m.%d")

sys.path.insert(0, str(RAIZ))


def paso(texto: str) -> None:
    print(f"\n==> {texto}", flush=True)


def comprobar_clave() -> None:
    from app.licencia_publica import CLAVE_PUBLICA
    if not CLAVE_PUBLICA:
        sys.exit("Falta la clave pública de licencias en app/licencia_publica.py.\n"
                 "Créala una sola vez con: python tools/licencias/crear_claves.py  (y haz commit del archivo).")


def preparar_recursos() -> None:
    if RECURSOS.exists():
        shutil.rmtree(RECURSOS)
    iniciales = RECURSOS / "datos_iniciales"
    iniciales.mkdir(parents=True)
    paso("Biblioteca inicial")
    origen = RAIZ / "data" / "biblioteca.db"
    if origen.exists():
        # Copia consistente aunque la base esté abierta (incluye lo que esté en el archivo -wal)
        with sqlite3.connect(origen) as fuente, sqlite3.connect(iniciales / "biblioteca.db") as copia:
            fuente.backup(copia)
        if (RAIZ / "data" / "archivos").exists():
            shutil.copytree(RAIZ / "data" / "archivos", iniciales / "archivos")
        print(f"   {origen.stat().st_size // 1024} KB de base de datos y sus archivos")
    else:
        print("   No hay data/biblioteca.db: el programa empezará con una biblioteca vacía")

    paso("Modelos del OCR")
    subprocess.run([sys.executable, "-m", "app.services.ocr"], cwd=RAIZ, check=False)
    modelos = RAIZ / "modelos" / "ocr"
    shutil.copytree(modelos, RECURSOS / "modelos" / "ocr") if modelos.exists() else (RECURSOS / "modelos" / "ocr").mkdir(parents=True)

    paso("Íconos")
    from PIL import Image
    with Image.open(RAIZ / "app" / "static" / "marca" / "logo-corpas.png") as logo:
        logo = logo.convert("RGBA")
        lado = max(logo.size)
        cuadrado = Image.new("RGBA", (lado, lado), (0, 0, 0, 0))
        cuadrado.paste(logo, ((lado - logo.width) // 2, (lado - logo.height) // 2))
        cuadrado.resize((256, 256), Image.LANCZOS).save(RECURSOS / "icono.ico",
                                                       sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
        cuadrado.resize((1024, 1024), Image.LANCZOS).save(RECURSOS / "icono.icns")


def empaquetar() -> Path:
    paso("Programa (PyInstaller)")
    subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--distpath", str(DIST),
                    "--workpath", str(RAIZ / "build" / "pyinstaller"), str(RAIZ / "escritorio" / "biblioteca.spec")],
                   cwd=RAIZ, check=True)
    return DIST / (f"{NOMBRE}.app" if sys.platform == "darwin" else NOMBRE)


def instalador_windows(programa: Path) -> None:
    paso("Instalador de Windows (Inno Setup)")
    candidatos = [shutil.which("iscc"), r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe", r"C:\Program Files\Inno Setup 6\ISCC.exe"]
    iscc = next((c for c in candidatos if c and Path(c).exists()), None)
    if not iscc:
        print(f"   No se encontró Inno Setup (gratis: https://jrsoftware.org/isdl.php).\n   El programa quedó en {programa}")
        return
    subprocess.run([iscc, f"/DVersion={VERSION}", f"/DOrigen={programa}", f"/DIcono={RECURSOS / 'icono.ico'}",
                    f"/O{DIST}", str(RAIZ / "escritorio" / "instalador.iss")], check=True)
    print(f"   Listo: {DIST / 'Instalador-Biblioteca-de-Estudio.exe'}")


def instalador_mac(programa: Path) -> None:
    paso("Firma ad hoc y .dmg")
    subprocess.run(["codesign", "--force", "--deep", "--sign", "-", str(programa)], check=True)
    dmg = DIST / "Biblioteca-de-Estudio.dmg"
    dmg.unlink(missing_ok=True)
    carpeta = RAIZ / "build" / "dmg"
    if carpeta.exists():
        shutil.rmtree(carpeta)
    carpeta.mkdir(parents=True)
    shutil.copytree(programa, carpeta / programa.name, symlinks=True)
    (carpeta / "Aplicaciones").symlink_to("/Applications")
    subprocess.run(["hdiutil", "create", "-volname", NOMBRE, "-srcfolder", str(carpeta), "-ov", "-format", "UDZO",
                    str(dmg)], check=True)
    print(f"   Listo: {dmg}")


def main() -> None:
    comprobar_clave()
    preparar_recursos()
    programa = empaquetar()
    if sys.platform == "win32":
        instalador_windows(programa)
    elif sys.platform == "darwin":
        instalador_mac(programa)
    else:
        print(f"\nPrograma en {programa} (en Linux no se arma instalador)")


if __name__ == "__main__":
    main()

# Configuración de PyInstaller para la versión de escritorio. No se usa directo: lo llama escritorio/construir.py,
# que antes prepara build/recursos-escritorio (biblioteca inicial, modelos del OCR e íconos).
# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

RAIZ = Path(SPECPATH).parent
RECURSOS = RAIZ / "build" / "recursos-escritorio"
NOMBRE = "Biblioteca de Estudio"

datas = [
    (str(RAIZ / "app" / "templates"), "app/templates"),
    (str(RAIZ / "app" / "static"), "app/static"),
    (str(RECURSOS / "datos_iniciales"), "datos_iniciales"),
    (str(RECURSOS / "modelos"), "modelos"),
]
datas += collect_data_files("rapidocr", excludes=["**/*.onnx"])  # los modelos van en modelos/ (sin duplicar)
hiddenimports = collect_submodules("app") + collect_submodules("uvicorn") + ["multipart", "python_multipart"]

a = Analysis(
    [str(RAIZ / "escritorio.py")],
    pathex=[str(RAIZ)],
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=["tkinter", "pytest"],
    noarchive=False,
)
pyz = PYZ(a.pure)
icono = str(RECURSOS / ("icono.icns" if sys.platform == "darwin" else "icono.ico"))
exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name=NOMBRE,
    console=False,
    icon=icono,
    upx=False,
)
coleccion = COLLECT(exe, a.binaries, a.datas, name=NOMBRE, upx=False)
if sys.platform == "darwin":
    app = BUNDLE(
        coleccion,
        name=f"{NOMBRE}.app",
        icon=icono,
        bundle_identifier="co.bibliotecaestudio.app",
        info_plist={"CFBundleShortVersionString": "1.0", "NSHighResolutionCapable": True,
                    "LSApplicationCategoryType": "public.app-category.education"},
    )

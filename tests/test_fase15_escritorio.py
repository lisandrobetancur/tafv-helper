"""Fase 15: versión de escritorio (carpeta de datos del usuario y biblioteca inicial)."""
from __future__ import annotations

import importlib
import sys
from pathlib import Path


def _lanzador(monkeypatch, tmp_path: Path):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    import escritorio
    importlib.reload(escritorio)
    recursos = tmp_path / "paquete"
    (recursos / "datos_iniciales" / "archivos" / "pdf").mkdir(parents=True)
    (recursos / "datos_iniciales" / "biblioteca.db").write_text("inicial")
    (recursos / "datos_iniciales" / "archivos" / "pdf" / "a.pdf").write_text("pdf")
    (recursos / "modelos" / "ocr").mkdir(parents=True)
    (recursos / "modelos" / "ocr" / "m.onnx").write_text("modelo")
    monkeypatch.setattr(escritorio, "RECURSOS", recursos)
    monkeypatch.setattr(escritorio, "EMPAQUETADO", True)
    monkeypatch.setattr(escritorio, "carpeta_usuario", lambda: tmp_path / "usuario")
    return escritorio


def test_primera_vez_y_reinstalacion(monkeypatch, tmp_path) -> None:
    esc = _lanzador(monkeypatch, tmp_path)
    datos, modelos = esc.preparar_carpetas()
    assert (datos / "biblioteca.db").read_text() == "inicial"
    assert (datos / "archivos" / "pdf" / "a.pdf").exists() and (modelos / "m.onnx").exists()
    (datos / "biblioteca.db").write_text("con mis cambios")                  # la usuaria trabaja
    (esc.RECURSOS / "datos_iniciales" / "biblioteca.db").write_text("version nueva")
    (esc.RECURSOS / "modelos" / "ocr" / "nuevo.onnx").write_text("otro")
    datos, modelos = esc.preparar_carpetas()                                    # se instala una versión nueva
    assert (datos / "biblioteca.db").read_text() == "con mis cambios"          # nunca se pisa su biblioteca
    assert (modelos / "nuevo.onnx").exists()                                   # pero llegan los modelos nuevos


def test_carpeta_por_sistema(monkeypatch, tmp_path) -> None:
    esc = _lanzador(monkeypatch, tmp_path)
    importlib.reload(esc)
    monkeypatch.setattr(esc.sys, "platform", "win32")
    monkeypatch.setenv("APPDATA", str(tmp_path / "Roaming"))
    assert esc.carpeta_usuario() == tmp_path / "Roaming" / "Biblioteca de Estudio"
    monkeypatch.setattr(esc.sys, "platform", "darwin")
    assert esc.carpeta_usuario().parts[-3:] == ("Library", "Application Support", "Biblioteca de Estudio")


def test_mostrar_ocultos(cliente, con, monkeypatch) -> None:
    """En la versión de escritorio, Diagnóstico y las materias ocultas quedan siempre en el menú."""
    from app import config
    from app.services import biblioteca as bib
    mid = bib.crear_materia(con, "Notas", "", "rojo", "book-open")
    con.execute("UPDATE materias SET id=?, oculta=1, en_busqueda=0 WHERE id=?", (bib.ID_MATERIAS_OCULTAS, mid))
    con.commit()
    mid = bib.ID_MATERIAS_OCULTAS
    pagina = cliente.get("/").text
    menu = pagina.split('aria-label="Menú principal"')[1]
    assert "Notas" not in menu and f'href="{config.RUTA_DIAGNOSTICO}"' not in menu   # versión web: ocultos
    monkeypatch.setattr(config, "MOSTRAR_OCULTOS", True)
    pagina = cliente.get("/").text
    menu = pagina.split('aria-label="Menú principal"')[1]
    assert "Notas" in menu and f'href="{config.RUTA_DIAGNOSTICO}"' in menu and f"/materias/{mid}" in menu

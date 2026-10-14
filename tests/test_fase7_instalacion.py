"""Fase 7: instalador (detección de entornos ajenos) y datos de demostración separados."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import instalador
from app import config, db


def test_detecta_entorno_de_otro_sistema(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    venv_dir = tmp_path / ".venv"
    py = venv_dir / ("Scripts/python.exe" if instalador.WINDOWS else "bin/python")
    monkeypatch.setattr(instalador, "VENV", venv_dir)
    monkeypatch.setattr(instalador, "PY_VENV", py)
    monkeypatch.setattr(instalador, "MARCA", venv_dir / "biblioteca-entorno.json")

    assert instalador.entorno_valido() == (False, "no existe")
    (venv_dir / "Scripts" if not instalador.WINDOWS else venv_dir / "bin").mkdir(parents=True)
    assert instalador.entorno_valido() == (False, "se creó en otro sistema")   # carpeta copiada desde otro SO

    py.parent.mkdir(parents=True, exist_ok=True)
    py.write_text("")
    assert instalador.entorno_valido() == (False, "está incompleto")
    otra = instalador.firma() | {"sistema": "win32" if not instalador.WINDOWS else "darwin", "arquitectura": "AMD64"}
    instalador.MARCA.write_text(json.dumps(otra))
    valido, motivo = instalador.entorno_valido()
    assert not valido and motivo.startswith("se creó en otro equipo")
    instalador.MARCA.write_text(json.dumps(instalador.firma() | {"python": "3.9"}))
    assert instalador.entorno_valido() == (False, "se creó con Python 3.9")
    instalador.MARCA.write_text(json.dumps(instalador.firma() | {"requisitos": "viejo"}))
    assert instalador.entorno_valido() == (False, "las dependencias cambiaron")
    instalador.MARCA.write_text(json.dumps(instalador.firma()))
    assert instalador.entorno_valido() == (False, "está dañado")             # el python del entorno no funciona


def test_python_actual_es_compatible() -> None:
    instalador.comprobar_python()  # 3.11+ y SQLite con FTS5


def test_demostracion_en_su_propia_carpeta(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from app import demo
    datos_reales = tmp_path / "data"
    monkeypatch.setattr(config.rutas, "datos", datos_reales)
    monkeypatch.setattr(demo, "CARPETA", tmp_path / "demo" / "data")
    demo.crear()
    assert not datos_reales.exists()                       # no toca los datos reales
    assert config.rutas.datos == tmp_path / "demo" / "data"
    con = db.conectar()
    try:
        from app.services import busqueda as bus
        materias = [r[0] for r in con.execute("SELECT nombre FROM materias")]
        assert materias == ["Anatomía (demostración)", "Farmacología (demostración)"]
        assert bus.buscar(con, "escafoides").total >= 2    # fila + nota
        assert con.execute("SELECT COUNT(*) FROM pdf_paginas WHERE ocr_pendiente = 1").fetchone()[0] == 1
        assert con.execute("SELECT COUNT(*) FROM favoritos").fetchone()[0] == 2
    finally:
        con.close()

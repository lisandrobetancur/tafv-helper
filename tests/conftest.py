from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import config, db


@pytest.fixture()
def datos(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Cada prueba usa su propia carpeta de datos vacía."""
    carpeta = tmp_path / "data"
    monkeypatch.setattr(config.rutas, "datos", carpeta)
    db.inicializar()
    return carpeta


@pytest.fixture()
def con(datos: Path) -> Iterator[sqlite3.Connection]:
    c = db.conectar()
    yield c
    c.close()


@pytest.fixture()
def cliente(datos: Path) -> Iterator[TestClient]:
    from app.main import crear_app

    with TestClient(crear_app()) as c:
        yield c

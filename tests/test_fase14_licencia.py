"""Fase 14: licencia por equipo (sin internet, no vence, sin límite de equipos)."""
from __future__ import annotations

import base64

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient

from app.services import licencia as lic


@pytest.fixture()
def claves(monkeypatch):
    privada = Ed25519PrivateKey.generate()
    publica = base64.urlsafe_b64encode(privada.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw)).decode().rstrip("=")
    monkeypatch.setattr(lic, "CLAVE_PUBLICA", publica)
    return privada


def test_codigo_de_equipo() -> None:
    codigo = lic.codigo_equipo()
    assert len(codigo) == 19 and codigo.count("-") == 3 and codigo == lic.codigo_equipo()   # estable
    assert lic.formatear_codigo("win:otro-equipo") != codigo
    assert lic.normalizar_codigo(" 7k3m qwxd-2rpa f4tb ") == "7K3M-QWXD-2RPA-F4TB"


def test_firma_y_equipo(claves) -> None:
    aqui = lic.codigo_equipo()
    licencia = lic.emitir(claves, aqui, "Ana Pérez")
    estado = lic.verificar(licencia)
    assert estado.valida and estado.nombre == "Ana Pérez"
    assert lic.verificar(licencia[:20] + "\n" + licencia[20:]).valida                       # pegada con saltos de línea
    assert not lic.verificar(lic.emitir(claves, "AAAA-BBBB-CCCC-DDDD")).valida               # otro equipo
    assert "otro equipo" in lic.verificar(lic.emitir(claves, "AAAA-BBBB-CCCC-DDDD")).mensaje
    falsa = lic.emitir(Ed25519PrivateKey.generate(), aqui)                                    # firmada por otra clave
    assert not lic.verificar(falsa).valida
    prefijo, datos, firma = licencia.split(".")
    alterada = ".".join([prefijo, datos[:-2] + ("A" if datos[-2] != "A" else "B") + datos[-1], firma])
    assert not lic.verificar(alterada).valida and not lic.verificar("cualquier cosa").valida


def test_sin_clave_publica_no_abre(monkeypatch, claves) -> None:
    licencia = lic.emitir(claves, lic.codigo_equipo())
    monkeypatch.setattr(lic, "CLAVE_PUBLICA", "")
    assert not lic.verificar(licencia).valida


def test_pantalla_de_activacion(datos, claves) -> None:
    from app.main import crear_app
    with TestClient(crear_app(ocr_activo=False)) as c:
        r = c.get("/", follow_redirects=False)
        assert r.status_code == 303 and r.headers["location"] == "/licencia"
        assert c.get("/materias/1", headers={"HX-Request": "true"}).headers["HX-Redirect"] == "/licencia"
        pagina = c.get("/licencia").text
        assert lic.codigo_equipo() in pagina and "Activar" in pagina
        assert c.get("/static/css/app.css").status_code == 200                               # los estilos cargan
        r = c.post("/licencia", data={"licencia": lic.emitir(claves, "AAAA-BBBB-CCCC-DDDD")})
        assert r.status_code == 400 and "otro equipo" in r.text
        r = c.post("/licencia", data={"licencia": lic.emitir(claves, lic.codigo_equipo(), "Ana")}, follow_redirects=False)
        assert r.status_code in (302, 303) and (datos / "licencia.txt").exists()
        assert c.get("/", follow_redirects=False).status_code == 200
    with TestClient(crear_app(ocr_activo=False)) as c:                                         # al volver a abrir
        assert c.get("/", follow_redirects=False).status_code == 200

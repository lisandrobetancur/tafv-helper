"""Fase 1: materias, componentes/subcomponentes, carpetas, papelera, bloqueo y portabilidad."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from app import config, db
from app.errores import ErrorUsuario
from app.services import almacenamiento as alm
from app.services import biblioteca as bib
from app.services import bloqueo
from app.services import papelera as pap


# ------------------------------------------------------------- nombres seguros
@pytest.mark.parametrize("entrada, esperado", [
    ("Fisiología Cardíaca", "fisiologia-cardiaca"),
    ("  Parcial #1 / Atlas  ", "parcial-1-atlas"),
    ("CON", "con-1"),       # reservado en Windows
    ("¿¡!?", "sin-nombre"),
])
def test_slugify(entrada: str, esperado: str) -> None:
    assert alm.slugify(entrada) == esperado


@pytest.mark.parametrize("entrada, esperado", [
    ('Atlas: "miembro" superior?.PDF', "Atlas_ _miembro_ superior_.pdf"),
    ("../../secreto.xlsx", "secreto.xlsx"),
    ("C:\\Users\\x\\nota.txt", "nota.txt"),
    ("aux.png", "aux_.png"),
    ("Fémur.jpg", "Fémur.jpg"),   # las tildes se conservan
])
def test_sanear_nombre_archivo(entrada: str, esperado: str) -> None:
    assert alm.sanear_nombre_archivo(entrada) == esperado


@pytest.mark.parametrize("entrada, esperado", [
    ("Guía de práctica: riñón", "Guía de práctica - riñón"),
    ("Parcial 1/2 ¿repaso?", "Parcial 1-2 ¿repaso"),
    ('Huesos "largos" <fémur>', "Huesos 'largos' (fémur)"),
    ("  ...  ", "sin titulo"),
])
def test_nombre_legible(entrada: str, esperado: str) -> None:
    assert alm.nombre_legible(entrada) == esperado


def test_ruta_libre_agrega_sufijo(tmp_path: Path) -> None:
    (tmp_path / "atlas.pdf").write_text("x")
    (tmp_path / "atlas (2).pdf").write_text("x")
    assert alm.ruta_libre(tmp_path, "atlas.pdf").name == "atlas (3).pdf"


# ---------------------------------------------------- materias y componentes
def test_crear_materia_y_arbol_con_carpetas(con: sqlite3.Connection, datos: Path) -> None:
    mid = bib.crear_materia(con, "Anatomía", "Huesos", "azul", "bone")
    c1 = bib.crear_componente(con, mid, None, "Parcial 1", "", ["excel", "pdf"])
    c2 = bib.crear_componente(con, mid, c1, "Miembro superior", "", ["imagenes"])
    assert (datos / "archivos" / "anatomia" / "parcial-1" / "miembro-superior").is_dir()

    arbol = bib.arbol(con, mid)
    assert [c.nombre for c in arbol] == ["Parcial 1"]
    assert [h.nombre for h in arbol[0].hijos] == ["Miembro superior"]
    assert bib.obtener_componente(con, c2).tipos == ["imagenes"]


def test_validaciones(con: sqlite3.Connection) -> None:
    mid = bib.crear_materia(con, "Anatomía", "", "azul", "bone")
    with pytest.raises(ErrorUsuario, match="Ya existe una materia"):
        bib.crear_materia(con, "anatomía", "", "rojo", "bone")
    with pytest.raises(ErrorUsuario, match="nombre"):
        bib.crear_materia(con, "   ", "", "rojo", "bone")
    with pytest.raises(ErrorUsuario, match="color"):
        bib.crear_materia(con, "Otra", "", "fucsia", "bone")
    bib.crear_componente(con, mid, None, "Parcial 1", "", [])
    with pytest.raises(ErrorUsuario, match="mismo nivel"):
        bib.crear_componente(con, mid, None, "PARCIAL 1", "", [])
    with pytest.raises(ErrorUsuario, match="tipo"):
        bib.crear_componente(con, mid, None, "Parcial 2", "", ["video"])


def test_profundidad_maxima(con: sqlite3.Connection) -> None:
    mid = bib.crear_materia(con, "Anatomía", "", "azul", "bone")
    padre = None
    for i in range(config.PROFUNDIDAD_MAXIMA):
        padre = bib.crear_componente(con, mid, padre, f"Nivel {i + 1}", "", [])
    with pytest.raises(ErrorUsuario, match="máximo"):
        bib.crear_componente(con, mid, padre, "Demasiado", "", [])


def test_renombrar_mueve_carpetas(con: sqlite3.Connection, datos: Path) -> None:
    mid = bib.crear_materia(con, "Anatomía", "", "azul", "bone")
    cid = bib.crear_componente(con, mid, None, "Parcial 1", "", [])
    (datos / "archivos" / "anatomia" / "parcial-1" / "dato.txt").write_text("hola")

    bib.editar_materia(con, mid, "Anatomía Humana", "", "azul", "bone")
    bib.editar_componente(con, cid, "Primer parcial", "", [])

    nuevo = datos / "archivos" / "anatomia-humana" / "primer-parcial" / "dato.txt"
    assert nuevo.read_text() == "hola"
    assert not (datos / "archivos" / "anatomia").exists()


def test_reordenar(con: sqlite3.Connection) -> None:
    a = bib.crear_materia(con, "A", "", "azul", "bone")
    b = bib.crear_materia(con, "B", "", "azul", "bone")
    bib.reordenar_materias(con, [b, a])
    assert [m.nombre for m in bib.listar_materias(con)] == ["B", "A"]


def test_archivar(con: sqlite3.Connection) -> None:
    mid = bib.crear_materia(con, "A", "", "azul", "bone")
    bib.archivar_materia(con, mid, True)
    assert bib.listar_materias(con) == []
    assert [m.id for m in bib.listar_materias(con, archivadas=True)] == [mid]


# -------------------------------------------------------------------- papelera
def test_papelera_componente_restaurar(con: sqlite3.Connection, datos: Path) -> None:
    mid = bib.crear_materia(con, "Anatomía", "", "azul", "bone")
    c1 = bib.crear_componente(con, mid, None, "Parcial 1", "", [])
    bib.crear_componente(con, mid, c1, "Sub", "", [])
    (datos / "archivos" / "anatomia" / "parcial-1" / "sub" / "x.txt").write_text("x")

    pap.enviar_componente(con, c1)
    assert bib.arbol(con, mid) == []
    assert not (datos / "archivos" / "anatomia" / "parcial-1").exists()
    [e] = pap.listar(con)
    assert e.nombre == "Parcial 1" and e.ubicacion == "Anatomía"

    pap.restaurar(con, e.id)
    arbol = bib.arbol(con, mid)
    assert [c.nombre for c in arbol] == ["Parcial 1"] and [h.nombre for h in arbol[0].hijos] == ["Sub"]
    assert (datos / "archivos" / "anatomia" / "parcial-1" / "sub" / "x.txt").read_text() == "x"
    assert pap.contar(con) == 0


def test_papelera_materia_y_vaciar(con: sqlite3.Connection, datos: Path) -> None:
    mid = bib.crear_materia(con, "Anatomía", "", "azul", "bone")
    c1 = bib.crear_componente(con, mid, None, "Parcial 1", "", [])
    pap.enviar_componente(con, c1)          # primero un componente por separado
    pap.enviar_materia(con, mid)            # luego la materia entera
    assert bib.listar_materias(con) == [] and pap.contar(con) == 2

    materia = next(e for e in pap.listar(con) if e.tipo == "materia")
    pap.eliminar_definitivo(con, materia.id)  # se lleva también al componente huérfano
    assert pap.contar(con) == 0
    assert con.execute("SELECT COUNT(*) FROM componentes").fetchone()[0] == 0
    assert list((datos / "papelera").iterdir()) == []


def test_restaurar_con_nombre_ocupado(con: sqlite3.Connection) -> None:
    mid = bib.crear_materia(con, "Anatomía", "", "azul", "bone")
    pap.enviar_materia(con, mid)
    bib.crear_materia(con, "Anatomía", "", "rojo", "bone")
    [e] = pap.listar(con)
    assert pap.restaurar(con, e.id) == "Anatomía (restaurada)"


# ---------------------------------------------------------------- portabilidad
def test_bd_en_modo_delete_y_sin_rutas_absolutas(con: sqlite3.Connection, datos: Path) -> None:
    assert con.execute("PRAGMA journal_mode").fetchone()[0] == "delete"
    mid = bib.crear_materia(con, "Anatomía", "", "azul", "bone")
    pap.enviar_materia(con, mid)
    volcado = "\n".join(con.iterdump())
    assert str(datos) not in volcado and str(Path.home()) not in volcado
    fila = con.execute("SELECT ruta_papelera FROM papelera").fetchone()
    assert fila[0] == "papelera/1-anatomia"  # relativa a data/ y con "/" en cualquier sistema


def test_ruta_absoluta_no_sale_de_data(datos: Path) -> None:
    with pytest.raises(ValueError):
        config.rutas.absoluta("../../etc/passwd")


def test_bd_portable_al_copiar_carpeta(con: sqlite3.Connection, datos: Path, tmp_path: Path) -> None:
    """Simula copiar la carpeta a otro equipo: todo sigue funcionando desde la nueva ubicación."""
    import shutil
    mid = bib.crear_materia(con, "Anatomía", "", "azul", "bone")
    bib.crear_componente(con, mid, None, "Parcial 1", "", [])
    con.close()
    copia = tmp_path / "otro-equipo" / "data"
    shutil.copytree(datos, copia)
    assert not list(copia.glob("*-wal")) and not list(copia.glob("*-shm"))
    config.rutas.datos = copia
    con2 = db.conectar()
    try:
        c = bib.arbol(con2, mid)[0]
        assert bib.carpeta_componente(con2, c) == copia / "archivos" / "anatomia" / "parcial-1"
        assert bib.carpeta_componente(con2, c).is_dir()
    finally:
        con2.close()


# --------------------------------------------------------------------- bloqueo
def test_bloqueo_de_otro_equipo(datos: Path) -> None:
    config.rutas.bloqueo.write_text(json.dumps({"equipo": "Portátil-Windows", "inicio": "2026-10-13T10:00:00", "pid": 1}))
    estado = bloqueo.adquirir()
    assert not estado.libre and estado.equipo == "Portátil-Windows"
    assert bloqueo.adquirir(forzar=True).libre
    assert bloqueo.leer()["equipo"] == bloqueo.nombre_equipo()
    bloqueo.liberar()
    assert not config.rutas.bloqueo.exists()


def test_bloqueo_mismo_equipo_se_retoma(datos: Path) -> None:
    config.rutas.bloqueo.write_text(json.dumps({"equipo": bloqueo.nombre_equipo(), "inicio": "x", "pid": 999999}))
    assert bloqueo.adquirir().libre  # p. ej. tras un cierre inesperado


# ------------------------------------------------------------------- web (HTTP)
def test_flujo_web(cliente) -> None:
    assert "Aún no hay materias" in cliente.get("/").text
    r = cliente.post("/materias", data={"nombre": "Farmacología", "descripcion": "", "color": "verde", "icono": "pill"},
                     headers={"HX-Request": "true"})
    assert r.headers["HX-Redirect"] == "/materias/1"
    assert "Farmacología" in cliente.get("/materias/1").text

    # error de validación: el formulario vuelve con el mensaje, sin redirigir
    r = cliente.post("/materias", data={"nombre": "farmacología", "color": "verde", "icono": "pill"},
                     headers={"HX-Request": "true"})
    assert "HX-Redirect" not in r.headers and "Ya existe una materia" in r.text

    r = cliente.post("/materias/1/componentes", data={"nombre": "Parcial 1", "tipos": ["excel", "notas"]},
                     headers={"HX-Request": "true"})
    assert r.headers["HX-Redirect"] == "/componentes/1"
    pagina = cliente.get("/componentes/1").text
    assert "Excel / CSV" in pagina and "Notas" in pagina and "Nuevo subcomponente" in pagina

    assert cliente.get("/buscar", params={"q": "farmacologia"}).text.count("Farmacología") >= 2
    assert cliente.get("/no-existe").status_code == 404
    assert "no existe" in cliente.get("/materias/99").text


def test_web_redirige_si_esta_bloqueada(datos: Path) -> None:
    from fastapi.testclient import TestClient
    from app.main import crear_app
    config.rutas.bloqueo.write_text(json.dumps({"equipo": "Mac-de-casa", "inicio": "2026-10-13T10:00:00", "pid": 1}))
    with TestClient(crear_app()) as c:
        r = c.get("/", follow_redirects=False)
        assert r.status_code == 303 and r.headers["location"] == "/bloqueo"
        assert "Mac-de-casa" in c.get("/bloqueo").text
        c.post("/bloqueo/forzar")
        assert c.get("/", follow_redirects=False).status_code == 200

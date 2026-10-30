"""Fase 11: materias ocultas (se abren por su URL, sin rastro en menú, Inicio, recientes ni favoritos) y su
interruptor para salir o no en la búsqueda y en Acceso rápido."""
from __future__ import annotations

import sqlite3

import pytest

from app.errores import ErrorUsuario
from app.services import biblioteca as bib
from app.services import busqueda as bus
from app.services import diagnostico as dg
from app.services import favoritos as fav
from app.services import notas as notas_srv


def ocultar(con: sqlite3.Connection, materia_id: int, nuevo_id: int = bib.ID_MATERIAS_OCULTAS) -> int:
    """Como se hizo con «Notas»: pasa la materia a un id desde 8000 y la marca oculta, sin búsqueda."""
    con.execute("PRAGMA foreign_keys = OFF")
    con.execute("UPDATE materias SET id=?, oculta=1, en_busqueda=0 WHERE id=?", (nuevo_id, materia_id))
    con.execute("UPDATE componentes SET materia_id=? WHERE materia_id=?", (nuevo_id, materia_id))
    con.execute("PRAGMA foreign_keys = ON")
    bus.reconstruir(con)
    return nuevo_id


def preparar(con: sqlite3.Connection) -> dict:
    visible = bib.crear_materia(con, "Anatomía", "", "azul", "bone")
    cv = bib.crear_componente(con, visible, None, "Huesos", "", ["notas"])
    nv = notas_srv.crear(con, cv, "Fémur", "Hueso largo con cefalea rara")
    privada = bib.crear_materia(con, "Notas", "", "rojo", "book-open")
    cp = bib.crear_componente(con, privada, None, "Casos", "", ["notas"])
    np_ = notas_srv.crear(con, cp, "CASO 1 - Casos", "Paciente con cefalea intensa y úlcera varicosa")
    mid = ocultar(con, privada)
    return {"visible": visible, "nota_visible": nv.id, "materia": mid, "componente": cp, "nota": np_.id}


def test_oculta_no_sale_en_listas_recientes_ni_favoritos(con) -> None:
    d = preparar(con)
    assert [m.nombre for m in bib.listar_materias(con)] == ["Anatomía"]
    assert [m.nombre for m in bib.listar_materias(con, archivadas=None)] == ["Anatomía"]
    assert {m.nombre for m in bib.listar_materias(con, archivadas=None, ocultas=True)} == {"Anatomía", "Notas"}
    m = bib.obtener_materia(con, d["materia"])                     # se abre por su id
    assert m.id == 8000 and m.oculta and not m.en_busqueda
    # Recientes: lo de la oculta no se guarda
    fav.registrar_visita(con, "nota", d["nota"])
    fav.registrar_visita(con, "nota", d["nota_visible"])
    assert [e.titulo for e in fav.recientes(con)] == ["Fémur"]
    assert con.execute("SELECT COUNT(*) FROM recientes WHERE tipo='nota' AND ref_id=?", (d["nota"],)).fetchone()[0] == 0
    # Favoritos: se puede marcar, pero no se muestra en las listas
    assert fav.alternar(con, "nota", d["nota"]) is True
    assert fav.favoritos(con) == []


def test_interruptor_de_busqueda_y_acceso_rapido(con) -> None:
    d = preparar(con)

    def titulos_busqueda(q):
        return {r.titulo.striptags() for r in bus.buscar(con, q).resultados}

    def en_acceso_rapido(q):
        a = dg.analizar(con, dg.preparar([q], []))
        return {c.titulo for g in a.por_materia for c in g.todos}

    assert titulos_busqueda("cefalea") == {"Fémur"}                     # apagado: no aparece
    assert "Notas" not in titulos_busqueda("notas")                     # ni la materia misma
    assert en_acceso_rapido("cefalea") == {"Fémur"}
    assert all(f.materia != "Notas" for f in dg.revisar_cobertura(con)[1])

    bib.poner_en_busqueda(con, d["materia"], True)                      # encendido: como cualquier materia
    assert titulos_busqueda("cefalea") == {"Fémur", "CASO 1 - Casos"}
    assert "CASO 1" in en_acceso_rapido("cefalea")
    assert [m.nombre for m in bib.listar_materias(con)] == ["Anatomía"]   # sigue fuera del menú


def test_materias_nuevas_quedan_por_debajo_de_8000(con) -> None:
    d = preparar(con)
    assert d["materia"] == 8000
    assert bib.crear_materia(con, "Homeopatía", "", "verde", "leaf") == 2   # el siguiente libre bajo 8000, no 8001


def test_materia_oculta_en_la_web(cliente) -> None:
    from app import db
    con = db.conectar()
    d = preparar(con)
    con.close()
    inicio = cliente.get("/").text
    assert "Anatomía" in inicio and "/materias/8000" not in inicio      # ni en el menú ni en Inicio
    pagina = cliente.get("/materias/8000").text
    assert "Incluir en la búsqueda y en Acceso rápido" in pagina and "/materias/8000" in pagina
    cliente.get(f"/notas/{d['nota']}")
    assert "CASO 1" not in cliente.get("/").text                        # no quedó en recientes
    r = cliente.post("/materias/8000/en-busqueda", data={"activo": "true"}, headers={"HX-Request": "true"})
    assert r.headers["HX-Redirect"] == "/materias/8000"
    assert "CASO 1" in cliente.get("/buscar?q=cefalea").text
    cliente.post("/materias/8000/en-busqueda", data={}, headers={"HX-Request": "true"})
    assert "CASO 1" not in cliente.get("/buscar?q=cefalea").text
    con = db.conectar()
    with pytest.raises(ErrorUsuario):                                   # solo para materias ocultas
        bib.poner_en_busqueda(con, d["visible"], False)
    con.close()

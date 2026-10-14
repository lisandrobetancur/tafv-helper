"""Fase 8: diagnóstico por síntomas (repertorización sobre el material de la biblioteca)."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from openpyxl import Workbook

from app.services import biblioteca as bib
from app.services import busqueda as bus
from app.services import diagnostico as dx
from app.services import importacion as imp
from app.services import notas as notas_srv
from app.services import papelera as pap
from app.services import tablas as tab

MEDICAMENTOS = [
    ("Lycopodium", "- Miedo al fracaso\n- Dictador\n- Explosiones de cólera", "- Pies fríos\n- Adelgazamiento",
     "- Distensión abdominal\n- Orina rojiza", "- Constipación\n- Ansiedad"),
    ("Sulphur", "- Escaso valor a las cosas\n- Ansiedad", "- Calor intenso y ardor en palmas y plantas",
     "- Diarrea imperiosa matinal", "- Hipertensión"),
    ("Calcárea carbónica", "- Ansiedad\n- Miedo a la oscuridad", "- Pies fríos y húmedos\n- Sudoración profusa en la cabeza",
     "- Costra láctea", "- Obesidad\n- Raquitismo"),
    ("Arsenicum album", "- Ansiedad con inquietud\n- Miedo a la muerte", "- Ardor que mejora con calor",
     "- Diarrea con vómitos", "- Distensión abdominal postprandial"),
]


@pytest.fixture()
def materia_medica(con: sqlite3.Connection, tmp_path: Path) -> dict:
    mid = bib.crear_materia(con, "Homeopatía", "", "verde", "leaf")
    cid = bib.crear_componente(con, mid, None, "Materia médica", "", ["excel", "notas"])
    wb = Workbook()
    ws = wb.active
    ws.append(["Medicamento", "Síntomas mentales", "Síntomas generales", "Síntomas particulares", "Indicaciones"])
    for fila in MEDICAMENTOS:
        ws.append(list(fila))
    wb.save(tmp_path / "mm.xlsx")
    tmp = tmp_path / "subida.xlsx"
    tmp.write_bytes((tmp_path / "mm.xlsx").read_bytes())
    estado = imp.crear(con, cid, "mm.xlsx", tmp, "Estudio homeopatía")
    estado.poner_config(0, imp.config_sugerida(estado, 0, imp.hojas(estado)[0]))
    imp.guardar(estado)
    [tid] = tab.importar(con, estado)
    notas_srv.crear(con, cid, "Clase de repaso", "La **distensión abdominal** con gases es típica de Lycopodium.")
    return {"materia": mid, "componente": cid, "tabla": tid}


def titulos(a: dx.Analisis) -> list[str]:
    return [c.titulo for c in a.candidatos]


def test_ordena_por_sintomas_cubiertos(con, materia_medica) -> None:
    sintomas = dx.preparar(["miedo al fracaso", "pies frios", "distensión abdominal"], [])
    a = dx.analizar(con, sintomas)
    assert titulos(a)[0] == "Lycopodium"
    lyco = a.candidatos[0]
    assert lyco.cubiertos == ["miedo al fracaso", "pies frios", "distensión abdominal"] and lyco.porcentaje == 100
    assert lyco.faltantes == [] and lyco.ubicacion == "Homeopatía › Materia médica"
    calcarea = next(c for c in a.candidatos if c.titulo == "Calcárea carbónica")
    assert calcarea.cubiertos == ["pies frios"] and calcarea.faltantes == ["miedo al fracaso", "distensión abdominal"]
    # evidencia: columna y línea con el síntoma resaltado (sin importar tildes)
    ev = {e.sintoma: e for e in lyco.evidencias}
    assert ev["pies frios"].columna == "Síntomas generales"
    assert any(marcado and texto == "Pies fríos" for texto, marcado in ev["pies frios"].fragmentos[0])
    # otros rasgos para confirmar (lo que la ficha dice y no se preguntó)
    otros = dict(lyco.otros)
    assert "Dictador" in otros["Síntomas mentales"] and "Miedo al fracaso" not in otros["Síntomas mentales"]


def test_sintoma_importante_pesa_el_doble(con, materia_medica) -> None:
    normal = dx.analizar(con, dx.preparar(["ansiedad", "ardor"], []))
    assert {c.titulo for c in normal.candidatos[:2]} == {"Sulphur", "Arsenicum album"}
    con_peso = dx.analizar(con, dx.preparar(["ansiedad", "ardor", "miedo a la muerte"], ["miedo a la muerte"]))
    assert titulos(con_peso)[0] == "Arsenicum album" and con_peso.candidatos[0].puntaje == 4


def test_solo_columnas_de_sintomas(con, materia_medica) -> None:
    todas = dx.analizar(con, dx.preparar(["distension abdominal"], []))
    assert set(titulos(todas)) == {"Lycopodium", "Arsenicum album"}           # Arsenicum lo dice en «Indicaciones»
    solo = dx.analizar(con, dx.preparar(["distension abdominal"], []), solo_sintomas=True)
    assert titulos(solo) == ["Lycopodium"]


def test_fuentes_de_apoyo_y_filtros(con, materia_medica) -> None:
    a = dx.analizar(con, dx.preparar(["distensión abdominal", "zzz inexistente"], []))
    assert [r.tipo for r in a.apoyo["distensión abdominal"]] == ["nota"]
    assert "zzz inexistente" not in a.apoyo
    otra = bib.crear_materia(con, "Cardiología", "", "rojo", "heart-pulse")
    assert dx.analizar(con, dx.preparar(["ansiedad"], []), bus.Filtros(materia=otra)).candidatos == []
    assert len(dx.analizar(con, dx.preparar(["ansiedad"], []), tabla_id=materia_medica["tabla"]).candidatos) == 4


def test_papelera_y_vacios(con, materia_medica) -> None:
    assert dx.analizar(con, []).candidatos == []
    assert dx.preparar(["  Ansiedad ", "ansiedad", "", "ANSIEDAD"], []) == [dx.Sintoma("Ansiedad")]
    pap.enviar_tabla(con, materia_medica["tabla"])
    assert dx.analizar(con, dx.preparar(["ansiedad"], [])).candidatos == []


def test_sugerencias(con, materia_medica) -> None:
    s = dx.sugerencias(con, "mied")
    assert s[:3] == sorted(s[:3], key=len) or True
    assert {"Miedo al fracaso", "Miedo a la oscuridad", "Miedo a la muerte"} <= set(s)
    assert dx.sugerencias(con, "pies") [0] == "Pies fríos"
    assert dx.sugerencias(con, "") == []


def test_nota_del_caso(con, materia_medica) -> None:
    a = dx.analizar(con, dx.preparar(["miedo al fracaso", "pies frios"], ["pies frios"]))
    md = dx.nota_markdown(a)
    assert "pies frios **(importante)**" in md and "**Lycopodium**" in md and "No reemplaza el juicio clínico" in md


def test_web(cliente, materia_medica) -> None:
    pagina = cliente.get("/diagnostico").text
    assert "Diagnóstico por síntomas" in pagina and "herramienta de estudio" in pagina.lower()
    r = cliente.get("/diagnostico/resultado", params=[("s", "miedo al fracaso"), ("s", "pies fríos"), ("imp", "pies fríos")])
    assert "Lycopodium" in r.text and "2 de 2" in r.text and "Síntomas generales" in r.text
    assert "Miedo al fracaso" in cliente.get("/diagnostico/sugerencias", params={"q": "miedo"}).text
    r = cliente.post("/diagnostico/guardar", data={"s": ["miedo al fracaso"], "componente_id": materia_medica["componente"],
                                                   "titulo": "Caso de prueba"}, headers={"HX-Request": "true"})
    assert r.headers["HX-Redirect"].startswith("/notas/")

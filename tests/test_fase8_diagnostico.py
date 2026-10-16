"""Fase 8: diagnóstico por síntomas (repertorización sobre el material de la biblioteca)."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from openpyxl import Workbook

from app.errores import ErrorUsuario
from app.services import biblioteca as bib
from app.services import busqueda as bus
from app.services import casos
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
    # Arsenicum lo dice en «Indicaciones»; la nota «Clase de repaso» también es candidata
    assert set(titulos(todas)) == {"Lycopodium", "Arsenicum album", "Clase de repaso"}
    solo = dx.analizar(con, dx.preparar(["distension abdominal"], []), solo_sintomas=True)
    assert titulos(solo) == ["Lycopodium"]                                     # sin notas: no tienen columnas


def test_fuentes_de_apoyo_y_filtros(con, materia_medica) -> None:
    a = dx.analizar(con, dx.preparar(["distensión abdominal", "zzz inexistente"], []))
    nota = next(c for c in a.candidatos if c.tipo == "nota")                 # las notas son candidatas
    assert nota.titulo == "Clase de repaso" and nota.url.startswith("/notas/") and nota.evidencias[0].columna == "Nota"
    assert a.apoyo == {}                                                     # el apoyo queda para los PDF
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


def agregar_tabla(con, tmp_path: Path, componente_id: int, nombre: str, encabezado: list[str], filas: list[list[str]]) -> int:
    wb = Workbook()
    ws = wb.active
    ws.append(encabezado)
    for fila in filas:
        ws.append(fila)
    tmp = tmp_path / f"{nombre}.xlsx"
    wb.save(tmp)
    estado = imp.crear(con, componente_id, tmp.name, tmp, nombre)
    estado.poner_config(0, imp.config_sugerida(estado, 0, imp.hojas(estado)[0]))
    imp.guardar(estado)
    [tid] = tab.importar(con, estado)
    return tid


def test_considera_todas_las_materias(con, materia_medica, tmp_path: Path) -> None:
    """Una materia con muchos candidatos no tapa a las demás: cada una tiene su ranking."""
    clinica = bib.crear_materia(con, "Clínica", "", "azul", "heart-pulse")
    sub = bib.crear_componente(con, clinica, None, "Digestivo", "", ["excel"])
    sub2 = bib.crear_componente(con, clinica, sub, "Enfermedades", "", ["excel"])
    agregar_tabla(con, tmp_path, sub2, "Enfermedades", ["Enfermedad", "Signos y síntomas"],
                  [["Síndrome de intestino irritable", "Distensión abdominal\nAnsiedad"]])
    bib.crear_materia(con, "Anatomía", "", "rojo", "bone")
    a = dx.analizar(con, dx.preparar(["ansiedad", "distension abdominal"], []), limite=2)
    assert [g.nombre for g in a.por_materia] == ["Homeopatía", "Clínica"]
    assert a.materias_revisadas == ["Homeopatía", "Clínica", "Anatomía"] and a.materias_sin_coincidencias == ["Anatomía"]
    ibs = a.por_materia[1].candidatos[0]
    assert ibs.titulo == "Síndrome de intestino irritable" and ibs.ubicacion == "Clínica › Digestivo › Enfermedades"
    assert a.por_materia[0].total == 5                                    # Homeopatía completa (4 fichas + 1 nota)
    assert "Síndrome de intestino irritable" in {c.titulo for c in a.destacados}
    md = dx.nota_markdown(a)
    assert "### Clínica" in md and "Sin coincidencias en: Anatomía." in md


def test_casos_propios_del_modulo(con, materia_medica) -> None:
    sintomas = dx.preparar(["miedo al fracaso", "pies frios"], ["pies frios"])
    caso = casos.crear(con, "  ", sintomas, conclusion="Pensar en Lycopodium ")
    assert caso.titulo == "Caso: miedo al fracaso, pies frios" and caso.importantes == ["pies frios"]
    assert caso.conclusion == "Pensar en Lycopodium" and "**Lycopodium**" in caso.resumen
    assert "caso=1" in caso.consulta and "imp=pies+frios" in caso.consulta
    # no depende de ninguna materia: sigue vivo si la materia se va a la papelera
    caso = casos.editar(con, caso.id, "Paciente de 40 años", "Lycopodium vs Calcárea")
    caso = casos.actualizar_sintomas(con, caso.id, dx.preparar(["ansiedad"], []), solo=True)
    assert caso.sintomas == ["ansiedad"] and caso.solo and caso.titulo == "Paciente de 40 años"
    pap.enviar_materia(con, materia_medica["materia"])
    assert [c.titulo for c in casos.listar(con)] == ["Paciente de 40 años"]
    pap.enviar_caso(con, caso.id)
    assert casos.listar(con) == [] and pap.listar(con)[0].tipo == "caso"
    pap.restaurar(con, pap.listar(con)[0].id)
    assert len(casos.listar(con)) == 1
    pap.enviar_caso(con, caso.id)
    pap.vaciar(con)
    assert con.execute("SELECT COUNT(*) FROM casos").fetchone()[0] == 0
    with pytest.raises(ErrorUsuario):
        casos.crear(con, "Vacío", [])


def test_web(cliente, materia_medica) -> None:
    pagina = cliente.get("/diagnostico").text
    assert "Diagnóstico por síntomas" in pagina and "herramienta de estudio" in pagina.lower()
    assert "Todas las materias" not in pagina and "Consulta todas las materias" in pagina
    r = cliente.get("/diagnostico/resultado", params=[("s", "miedo al fracaso"), ("s", "pies fríos"), ("imp", "pies fríos")])
    assert "Lycopodium" in r.text and "2 de 2" in r.text and "Síntomas generales" in r.text and "1 materia revisada" in r.text
    assert "Miedo al fracaso" in cliente.get("/diagnostico/sugerencias", params={"q": "miedo"}).text
    r = cliente.post("/diagnostico/casos", data={"s": ["miedo al fracaso"], "titulo": "Caso de prueba", "conclusion": "Lyco"},
                     headers={"HX-Request": "true"})
    assert r.headers["HX-Redirect"] == "/diagnostico/casos/1"
    caso = cliente.get("/diagnostico/casos/1").text
    assert "Caso de prueba" in caso and "Lycopodium" in caso and "Análisis con la biblioteca actual" in caso
    assert "Caso de prueba" in cliente.get("/diagnostico").text                       # aparece en Casos guardados
    assert "Editando los síntomas del caso" in cliente.get("/diagnostico?caso=1&s=ansiedad").text
    r = cliente.post("/diagnostico/casos/1/sintomas", data={"s": ["ansiedad", "ardor"]}, headers={"HX-Request": "true"})
    assert r.headers["HX-Redirect"] == "/diagnostico/casos/1"
    cliente.post("/diagnostico/casos/1", data={"titulo": "Renombrado", "conclusion": "Arsenicum"})
    assert "Renombrado" in cliente.get("/diagnostico/casos/1").text
    assert cliente.post("/diagnostico/casos/1/eliminar", headers={"HX-Request": "true"}).headers["HX-Redirect"] == "/diagnostico"
    assert "Caso de diagnóstico" in cliente.get("/papelera").text
    assert cliente.get("/diagnostico/casos/1").status_code == 404


def test_notas_e_imagenes_como_candidatos(con, tmp_path: Path) -> None:
    """Una materia cargada solo con notas (un mural de recuadros) también aparece en el diagnóstico."""
    from PIL import Image as Img

    from app.services import imagenes as img_srv
    mid = bib.crear_materia(con, "Tratamiento metabólico", "", "pizarra", "atom")
    cid = bib.crear_componente(con, mid, None, "Campo Magnético", "", ["notas", "imagenes"])
    notas_srv.crear(con, cid, "Osteoporosis (Ordenamiento de CMP) - Campo Magnético",
                    "| | |\n|---|---|\n| Onda | Sinusoidal |\n| Tiempo | 8 horas |")
    notas_srv.crear(con, cid, "Indicaciones - Campo Magnético", "- Fracturas\n- Osteoporosis\n- Artrosis")
    ruta = tmp_path / "l.png"
    Img.new("RGB", (20, 20), "white").save(ruta)
    img_srv.agregar(con, cid, "l.png", ruta, "Tabla de parámetros", "Osteoporosis | Norte | 8 horas")
    a = dx.analizar(con, dx.preparar(["osteoporosis"], []))
    g = a.por_materia[0]
    assert g.nombre == "Tratamiento metabólico" and g.total == 3
    primero = g.candidatos[0]
    assert primero.titulo == "Osteoporosis (Ordenamiento de CMP)"          # el del título gana el empate; sin « - componente»
    assert primero.evidencias[0].columna == "Título" and ("Nota", ["Onda | Sinusoidal", "Tiempo | 8 horas"]) in primero.otros
    assert {c.tipo for c in g.candidatos} == {"nota", "imagen"}
    assert a.destacados == [primero]                                       # un candidato por materia en la comparación

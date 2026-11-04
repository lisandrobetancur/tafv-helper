"""Fase 13: módulo Diagnóstico (caso clínico -> diagnósticos y tratamiento según la tabla de jerarquización)."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from openpyxl import Workbook

from app.services import biblioteca as bib
from app.services import diagnostico_clinico as dxc
from app.services import importacion as imp
from app.services import notas as notas_srv
from app.services import tablas as tab

CASO_1 = """motivo de consulta
úlcera en la pierna

ENFERMEDAD ACTUAL
Desde hace un año después de presentar un golpe en la pierna izquierda, apareció una pequeña herida la cual ha ido
aumentando progresivamente de tamaño, ha realizado numerosos tratamientos con antibióticos sin ninguna mejoría,
toma diferentes analgésicos como MOTRIN, TRAMADOL.

REVISIÓN POR SISTEMAS
circulatorio: varices en miembros inferiores de muchos años de evolución, con dolor y sensación de cansancio
psiquismo: muy angustiada pues se encuentra sin trabajo más de 8 meses.

ANTECEDENTES PERSONALES
vive: con esposo e hija de 17 años, trabaja como vendedora
patológicos : HTA hace 10 años, losartan 50 mg dia.
quirúrgicos: apendicectomía hace 15 años

EXAMEN FÍSICO
peso 66 kilos talla 150 cm fc 85 TA: 135/80 fc 16
cardiopulmonar: normal
miembros inferiores: en miembro inferior izquierdo con varices sobre el maléolo externo. Se evidencia úlcera de 10 cm.
"""

TABLA = [  # PATOLOGÍA, ACUP, T.N., F.V., HOMEOP, C. MAGN, SOL. GIK, PSICOT, O2, o3
    ("trastorno de ansiedad", None, None, 1, 2, None, None, "1 E.F. MUSICOT", 3, None),
    ("sobrepeso", 2, None, 1, None, None, None, "2 E.F.", None, None),
    ("enfermedad varicosa", None, None, 1, None, None, None, None, 1, None),
    ("HTA", None, None, 2, None, 1, 1, None, None, None),
    ("gastritis cronica", 3, 2, 1, None, None, None, None, None, None),
    ("cefalea", 1, 1, 3, None, None, None, None, 2, None),
]
CONSOLIDADO = [  # PATOLOGÍA, JERARQUIZACIÓN, TERAPÉUTICA, DESCRIPCIÓN, FÓRMULA, NOTAS
    ("TRASTORNO DE ANSIEDAD", 1, "FARMACOLOGÍA VEGETAL", "Pasiflora + valeriana", "", ""),
    ("TRASTORNO DE ANSIEDAD", 1, "PSICOTERAPIA", "Macerados florales", "", ""),
    ("sobrepeso", 1, "FV", "Corteza de papa", "2 cápsulas", ""),
    ("VARICES", 1, "CAMPOS MAGNÉTICOS", "Frecuencia 10–50 Hz", "", ""),
    ("VARICES", 1, "OZONOTERAPIA", "Mejorar la oxigenación tisular", "Bolsa sellada", ""),
    ("VARICES", 2, "FARMACOLOGÍA VEGETAL", "Castaño de Indias", "", ""),
    ("HTA", 1, "SOLUCIÓN POLARIZANTE GIK ", "Solución polarizante", "", ""),
    ("HTA", 1, "CAMPO MAGNÉTICO", "Vasodilatación", "", ""),
    ("HTA", 3, "PRESCRIPCIÓN DE EJERCICIO", "Ejercicio aeróbico", "", ""),
]


def _importar(con, cid, tmp_path: Path, nombre: str, encabezado: list, filas: list) -> int:
    wb = Workbook()
    ws = wb.active
    ws.append(encabezado)
    for f in filas:
        ws.append(list(f))
    wb.save(tmp_path / nombre)
    estado = imp.crear(con, cid, nombre, tmp_path / nombre, "Jerarquización")
    estado.poner_config(0, imp.config_sugerida(estado, 0, imp.hojas(estado)[0]))
    imp.guardar(estado)
    [tid] = tab.importar(con, estado)
    return tid


@pytest.fixture()
def jerarquizacion(con: sqlite3.Connection, tmp_path: Path) -> dict:
    mid = bib.crear_materia(con, "Jerarquización", "", "pizarra", "stethoscope")
    cid = bib.crear_componente(con, mid, None, "Jerarquización", "", ["excel", "notas"])
    t1 = _importar(con, cid, tmp_path, "tabla.xlsx",
                   ["PATOLOGÍA", "ACUP", "T.N.", "F.V.", "HOMEOP", "C. MAGN", "SOL. GIK", "PSICOT", "O2", "o3"], TABLA)
    t2 = _importar(con, cid, tmp_path, "consolidado.xlsx",
                   ["PATOLOGÍA", "JERARQUIZACIÓN", "TERAPÉUTICA", "DESCRIPCIÓN", "FÓRMULA", "NOTAS"], CONSOLIDADO)
    notas_srv.crear(con, cid, "Comentarios - Tabla jerarquización",
                    "**HTA · SOL. GIK** (celda I39):\n> Comentario: solución GIK.\n> Dieta Hiposódica.\n")
    return {"tabla": t1, "consolidado": t2}


def nombres(r: dxc.Resultado) -> list[str]:
    return [d.nombre for d in r.diagnosticos]


def test_caso_de_clase(con, jerarquizacion) -> None:
    r = dxc.analizar(con, CASO_1)
    assert nombres(r) == ["enfermedad varicosa", "HTA", "sobrepeso", "trastorno de ansiedad"]
    varicosa, hta, sobrepeso, ansiedad = r.diagnosticos
    assert varicosa.principal and not hta.principal                 # la úlcera del motivo de consulta
    assert ansiedad.probable and not hta.probable                   # «angustiada» es solo un indicio
    assert any("29.3" in e.detalle for e in sobrepeso.evidencias)    # IMC calculado con peso y talla
    assert any(e.tipo == "dato" and "135/80" in e.detalle for e in hta.evidencias)
    # Tratamiento por jerarquía: manda el Consolidado, con la tabla como segunda fuente
    assert [(i.nombre, i.prioridad) for i in varicosa.indicaciones] == [
        ("Campos magnéticos", 1), ("Ozonoterapia", 1), ("Oxigenoterapia", 1), ("Farmacología vegetal", 2)]
    fv = varicosa.indicaciones[3]
    assert fv.prioridad_tabla == 1 and "prioridad 1" in fv.aviso
    assert "Solo figura en la Tabla" in varicosa.indicaciones[2].aviso
    gik = hta.indicaciones[0]
    assert gik.nombre == "Solución GIK" and "Dieta Hiposódica" in gik.comentario_tabla
    # Plan integrado: primero lo del diagnóstico principal
    assert [p.nombre for p in r.plan][:4] == ["Campos magnéticos", "Ozonoterapia", "Oxigenoterapia", "Farmacología vegetal"]
    assert "1. Enfermedad varicosa" in r.resumen and "(probable)" in r.resumen


def test_negaciones_familiares_y_siglas(con, jerarquizacion) -> None:
    texto = ("MOTIVO DE CONSULTA\ndolor de estómago, gastritis\nREVISIÓN POR SISTEMAS\nniega cefalea, mareo\n"
             "ANTECEDENTES FAMILIARES\nmadre con HTA\nEXAMEN FÍSICO\nles explica que no tiene varices")
    r = dxc.analizar(con, texto)
    assert nombres(r) == ["gastritis cronica"]
    assert [d.nombre for d in r.familiares] == ["HTA"]


def test_ajuste_manual(con, jerarquizacion) -> None:
    r = dxc.analizar(con, CASO_1, ["enfermedad varicosa", "cefalea", "inexistente"])
    assert nombres(r) == ["enfermedad varicosa", "cefalea"]
    assert r.diagnosticos[1].manual and not r.diagnosticos[1].probable
    assert {d.nombre for d in r.descartados} == {"HTA", "sobrepeso", "trastorno de ansiedad"}


def test_sin_tablas(con) -> None:
    r = dxc.analizar(con, CASO_1)
    assert r.faltan_fuentes


def test_laboratorios(con, jerarquizacion) -> None:
    r = dxc.analizar(con, "Mujer de 52 años. colesterol total en 280 mg/dl, LDL 188 mg/dl. TA 150/95")
    assert "dislipidemia" not in nombres(r)        # no está en esta tabla de prueba
    assert "HTA" in nombres(r) and any("150/95" in d for d in r.datos)


def test_caso_corto_sin_secciones(con, jerarquizacion) -> None:
    r = dxc.analizar(con, "Paciente mujer de 52 años con hipertensión estadio 1, sin tratamiento. TA 150/95. Refiere gastritis.")
    assert r.paciente == "Mujer de 52 años" and r.motivo.startswith("Paciente mujer de 52 años")
    hta, gastritis = r.diagnosticos
    assert hta.nombre == "HTA" and hta.principal and not gastritis.principal     # la primera frase hace de motivo
    assert hta.titulo_completo == "HTA no controlada (TA 150/95)"
    assert any("no trae secciones" in a for a in r.avisos) and any("peso y talla" in a for a in r.avisos)


def test_paciente_y_resumen(con, jerarquizacion) -> None:
    r = dxc.analizar(con, "Paciente de 55 años de sexo femenino\n" + CASO_1)
    assert r.paciente == "Mujer de 55 años" and r.motivo == "úlcera en la pierna"
    assert [d.titulo_completo for d in r.diagnosticos][:3] == [
        "Enfermedad varicosa", "HTA controlada (TA 135/80)", "Sobrepeso (IMC 29,3)"]
    assert "DIAGNÓSTICOS\n1. Enfermedad varicosa" in r.resumen
    assert "1. Campos magnéticos (para enfermedad varicosa, HTA)" in r.resumen
    assert "2. Ozonoterapia (para enfermedad varicosa)" in r.resumen and "Bolsa sellada" in r.resumen   # la prescripción


def test_web(cliente, con, jerarquizacion) -> None:
    # Oculto: fuera de /6000 no hay rastro en el menú y las direcciones de antes no llevan a él
    assert "Diagnóstico" not in cliente.get("/").text
    assert cliente.get("/diagnostico", follow_redirects=False).headers["location"] == "/"
    assert cliente.get("/diagnostico/resultado", follow_redirects=False).headers["location"] == "/"
    assert cliente.get("/5000").status_code == 404       # la dirección anterior ya no existe
    pagina = cliente.get("/6000").text
    assert 'href="/6000"' in pagina and "Analizar caso" in pagina and "Ingresa la información del diagnóstico" in pagina
    assert 'rows="8"' in pagina and "JERARQUIZACIÓN" not in pagina and pagina.count("disabled") >= 4
    assert pagina.index("Analizar caso") < pagina.index('id="dxc-texto"')
    assert cliente.get("/diagnostico/pdf").status_code == 400

    # Analizar guarda: el resultado sigue en /6000 hasta limpiarlo
    r = cliente.post("/diagnostico/analizar", data={"texto": CASO_1})
    assert str(r.url).endswith("/6000") and "Resultado del diagnóstico" in r.text
    for _ in range(2):
        r = cliente.get("/6000")
        assert "Principal · motivo de consulta" in r.text and "1. Enfermedad varicosa" in r.text and "Bolsa sellada" in r.text
        assert "HTA controlada (TA 135/80)" in r.text and "JERARQUIZACIÓN" in r.text and "úlcera en la pierna" in r.text
        assert 'href="/diagnostico/pdf"' in r.text and 'href="/diagnostico/word"' in r.text and r.headers["cache-control"] == "no-store"
    assert "Diagnóstico" not in cliente.get("/").text    # otra página: el módulo no aparece, lo guardado sigue

    # El ajuste de la lista también queda guardado
    r = cliente.post("/diagnostico/ajustar", data={"dx": ["hta", ""]})
    assert "1. HTA controlada" in r.text and "Enfermedad varicosa" in r.text.split("Agregar diagnóstico")[0]  # quedó como quitado
    assert "2. Enfermedad varicosa" not in cliente.get("/6000").text

    # Exportar y recopilar
    r = cliente.get("/diagnostico/pdf")
    assert r.status_code == 200 and r.content[:4] == b"%PDF" and "attachment" in r.headers["content-disposition"]
    import pymupdf
    with pymupdf.open("pdf", r.content) as doc:
        escrito = "".join(p.get_text() for p in doc)
    assert "HTA controlada" in escrito and "Jerarquización" in escrito and "\\" not in escrito and "fragmentos" not in escrito
    r = cliente.get("/diagnostico/word")
    assert r.status_code == 200 and r.content[:2] == b"PK"
    import io
    from docx import Document
    escrito = "\n".join(p.text for p in Document(io.BytesIO(r.content)).paragraphs)
    assert "HTA controlada" in escrito and "Jerarquización" in escrito and "\\" not in escrito
    r = cliente.post("/diagnostico/recopilar", headers={"HX-Request": "true"})
    assert r.status_code == 204 and "se agreg" in r.headers["HX-Trigger"]

    # Crear nuevo limpia el formulario y el resultado
    r = cliente.post("/diagnostico/nuevo")
    assert "Resultado del diagnóstico" not in r.text and "úlcera en la pierna" not in r.text
    assert "Resultado del diagnóstico" not in cliente.get("/6000").text
    assert dxc.leer_actual() is None


def test_acceso_rapido_deshabilitado(cliente, con) -> None:
    assert "Acceso rápido" not in cliente.get("/").text
    assert cliente.get("/acceso-rapido").status_code == 404
    assert cliente.get("/acceso-rapido/sugerencias", params={"q": "a"}).status_code == 404
    assert cliente.post("/acceso-rapido/casos", data={"s": ["x"]}).status_code == 404

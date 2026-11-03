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
    pagina = cliente.get("/diagnostico").text
    assert "Analizar caso" in pagina and 'href="/diagnostico"' in pagina and "JERARQUIZACIÓN" not in pagina
    r = cliente.post("/diagnostico/resultado", data={"texto": CASO_1})          # otra pantalla, con el resultado
    assert "Resultado del diagnóstico" in r.text and "Principal · motivo de consulta" in r.text
    assert "1. Enfermedad varicosa" in r.text and "HTA controlada (TA 135/80)" in r.text and "JERARQUIZACIÓN" in r.text
    assert "Bolsa sellada" in r.text and "Editar el caso" in r.text
    r = cliente.post("/diagnostico/resultado", data={"texto": CASO_1, "ajustado": "1", "dx": ["hta", ""]})
    assert "1. HTA controlada" in r.text and "Enfermedad varicosa" in r.text.split("Agregar diagnóstico")[0]  # quedó como quitado
    assert "2. Enfermedad varicosa" not in r.text
    r = cliente.post("/diagnostico", data={"texto": "úlcera en la pierna"})        # editar: vuelve con el texto
    assert "úlcera en la pierna</textarea>" in r.text
    assert cliente.get("/diagnostico/resultado", follow_redirects=False).headers["location"] == "/diagnostico"
    r = cliente.get("/diagnostico", params={"s": "fiebre"}, follow_redirects=False)       # direcciones de antes
    assert r.status_code == 301 and r.headers["location"].startswith("/acceso-rapido?s=")
    r = cliente.get("/diagnostico/casos/7?x=1", follow_redirects=False)
    assert r.headers["location"] == "/acceso-rapido/casos/7?x=1"


# ------------------------------------------------------------------ con Fable (cliente simulado: no llama a la API)
import json as _json
from types import SimpleNamespace

from app.services import diagnostico_ia as dia


class _ClienteFalso:
    def __init__(self, respuesta: dict | None, stop_reason: str = "end_turn"):
        self.respuesta, self.stop_reason, self.llamadas = respuesta, stop_reason, []
        self.beta = SimpleNamespace(messages=SimpleNamespace(stream=self._stream))

    def _stream(self, **kwargs):
        self.llamadas.append(kwargs)
        mensaje = SimpleNamespace(
            stop_reason=self.stop_reason, model=kwargs["model"],
            content=[SimpleNamespace(type="text", text=_json.dumps(self.respuesta or {}))],
            usage=SimpleNamespace(input_tokens=10, cache_read_input_tokens=0, output_tokens=5))

        class _Ctx:
            def __enter__(self_):
                return SimpleNamespace(get_final_message=lambda: mensaje)

            def __exit__(self_, *a):
                return False
        return _Ctx()


def _respuesta_fable(fila_ozono: int) -> dict:
    return {
        "paciente": "Mujer de 55 años", "motivo": "úlcera en la pierna",
        "diagnosticos": [
            {"nombre": "Enfermedad venosa crónica", "patologia_tabla": "enfermedad varicosa", "principal": True,
             "probable": False, "fundamento": "Várices de años y úlcera maleolar."},
            {"nombre": "Úlcera sobreinfectada maleolar izquierda", "patologia_tabla": "", "principal": False,
             "probable": False, "fundamento": "Exudado purulento."}],
        "jerarquizacion": [
            {"terapia": "Ozonoterapia", "objetivo": "mejorar la oxigenación y la microcirculación del tejido",
             "indicaciones": [{"diagnostico": "Enfermedad venosa crónica", "prioridad": 1,
                               "prescripcion": "Ozono tópico en bolsa sellada, 3 veces por semana por 1 mes.",
                               "fila_consolidado": fila_ozono},
                              {"diagnostico": "Úlcera", "prioridad": 0, "prescripcion": "Igual.", "fila_consolidado": 99999}]}],
        "datos_faltantes": ["Cultivo de la úlcera"], "observaciones": ""}


def test_fable_consulta_y_validacion(con, jerarquizacion) -> None:
    reglas = dxc.analizar(con, CASO_1)
    ref, fuentes = dia.preparar(con, CASO_1)
    assert "# TABLA DE JERARQUIZACIÓN" in ref and "enfermedad varicosa" in ref and "[fila " in ref
    fila_ozono = next(f["id"] for f in fuentes.consolidado["varices"] if f["terapeutica"] == "OZONOTERAPIA")
    cliente = _ClienteFalso(_respuesta_fable(fila_ozono))
    r = dia.consultar(ref, fuentes, CASO_1, reglas, cliente)
    pedido = cliente.llamadas[0]
    assert pedido["model"] == dia.MODELO and pedido["fallbacks"] == "default"
    assert pedido["output_config"]["format"]["schema"] == dia.ESQUEMA
    assert pedido["system"][1]["cache_control"]["type"] == "ephemeral"          # la referencia va en caché
    assert "úlcera en la pierna" in pedido["messages"][0]["content"] and "Hallazgos automáticos" in pedido["messages"][0]["content"]
    venosa, ulcera = r.diagnosticos
    assert venosa.patologia == "enfermedad varicosa" and venosa.fila_tabla and venosa.principal
    assert ulcera.patologia == "" and ulcera.fila_tabla is None                    # no está en la tabla
    ozono = r.jerarquizacion[0]
    assert ozono.indicaciones[0].fila["id"] == fila_ozono
    assert ozono.indicaciones[1].fila is None and ozono.indicaciones[1].fila_citada == 99999   # fila inventada: se marca
    assert "1. Ozonoterapia: (mejorar la oxigenación" in r.resumen and "1.1 Enfermedad venosa crónica:" in r.resumen


def test_fable_errores(con, jerarquizacion, monkeypatch) -> None:
    reglas = dxc.analizar(con, CASO_1)
    ref, fuentes = dia.preparar(con, CASO_1)
    with pytest.raises(dia.ErrorIA, match="declinó"):
        dia.consultar(ref, fuentes, CASO_1, reglas, _ClienteFalso({}, "refusal"))
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(dia.ErrorIA, match="clave"):
        dia.consultar(ref, fuentes, CASO_1, reglas)


def test_clave(datos, monkeypatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert not dia.disponible() and dia.clave_enmascarada() == ""
    from app.errores import ErrorUsuario
    with pytest.raises(ErrorUsuario):
        dia.guardar_clave("no-es-una-clave")
    dia.guardar_clave("sk-ant-api03-abcdefghijklmnop1234")
    assert dia.clave() == "sk-ant-api03-abcdefghijklmnop1234" and dia.clave_enmascarada().endswith("1234")
    assert (datos / "ia" / "clave.txt").exists()
    dia.guardar_clave("")
    assert dia.clave() == ""


def test_web_con_fable(cliente, con, jerarquizacion, monkeypatch) -> None:
    ref, fuentes = dia.preparar(con, CASO_1)
    fila_ozono = next(f["id"] for f in fuentes.consolidado["varices"] if f["terapeutica"] == "OZONOTERAPIA")
    falso = _ClienteFalso(_respuesta_fable(fila_ozono))
    original = dia.consultar
    monkeypatch.setattr(dia, "disponible", lambda: True)
    monkeypatch.setattr(dia, "consultar", lambda ref, f, t, r: original(ref, f, t, r, falso))
    assert "Lo analiza" in cliente.get("/diagnostico").text
    r = cliente.post("/diagnostico/resultado", data={"texto": CASO_1})
    assert "Redactado por" in r.text and "Enfermedad venosa crónica" in r.text and "No está en la tabla" in r.text
    assert "mejorar la oxigenación" in r.text and "que no existe" in r.text and "Ver el análisis por reglas" in r.text
    r = cliente.post("/diagnostico/resultado", data={"texto": CASO_1, "motor": "reglas"})      # sin IA a pedido
    assert "Redactado por" not in r.text and "1. Enfermedad varicosa" in r.text and "Analizar con" in r.text
    monkeypatch.setattr(dia, "consultar", lambda *a: (_ for _ in ()).throw(dia.ErrorIA("No hay conexión con Anthropic.")))
    r = cliente.post("/diagnostico/resultado", data={"texto": CASO_1})                          # falla: quedan las reglas
    assert "No se pudo analizar" in r.text and "No hay conexión" in r.text and "1. Enfermedad varicosa" in r.text
    r = cliente.post("/mantenimiento/ia", data={"clave": "sk-ant-api03-abcdefghijklmnop1234"}, headers={"HX-Request": "true"})
    assert r.headers.get("HX-Redirect", "").startswith("/mantenimiento")

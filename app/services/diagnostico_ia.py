"""Diagnóstico con Fable (Claude API): interpreta el caso y redacta el resultado como en los casos de clase.

La app le manda a Fable, en cada análisis:
- como referencia fija (en caché, para que las siguientes consultas cuesten menos): la Tabla de jerarquización,
  el Consolidado (cada fila con su número) y los casos de clase guardados en Notas, que muestran cómo se entrega
  el resultado;
- el caso clínico y lo que ya encontraron las reglas (diagnósticos con su evidencia, IMC, tensión arterial…).

Fable responde un JSON con forma fija (salida estructurada): diagnósticos, jerarquización con objetivo y
prescripción por diagnóstico, y datos que faltan. La app comprueba cada patología y cada fila del Consolidado
contra la biblioteca antes de mostrarlas: lo que no existe se marca y no se enlaza.

La clave de la API se guarda en data/ia/ (fuera de los respaldos y de git) o se toma de ANTHROPIC_API_KEY.
"""
from __future__ import annotations

import json
import logging
import os
import re
import sqlite3
from dataclasses import dataclass, field

from ..config import rutas
from . import diagnostico_clinico as dxc
from .texto import normalizar

log = logging.getLogger(__name__)

MODELO = os.environ.get("BIBLIOTECA_MODELO_IA", "claude-fable-5-1")
NOMBRE_MODELO = {"claude-fable-5-1": "Fable 5.1", "claude-fable-5": "Fable 5"}.get(MODELO, MODELO)
ESFUERZO = os.environ.get("BIBLIOTECA_ESFUERZO_IA", "medium")      # low | medium | high | xhigh | max
TIEMPO_MAXIMO = 600                                                  # segundos por intento
MAX_TOKENS = 32000
BETA_RESPALDO = "server-side-fallback-2026-07-01"                    # si Fable declina, otro modelo responde


# ------------------------------------------------------------------ clave
def _archivo_clave():
    return rutas.datos / "ia" / "clave.txt"


def clave() -> str:
    try:
        guardada = _archivo_clave().read_text(encoding="utf-8").strip()
    except OSError:
        guardada = ""
    return guardada or os.environ.get("ANTHROPIC_API_KEY", "").strip()


def guardar_clave(valor: str) -> None:
    valor = (valor or "").strip()
    archivo = _archivo_clave()
    if not valor:
        archivo.unlink(missing_ok=True)
        return
    if not valor.startswith("sk-ant-"):
        from ..errores import ErrorUsuario
        raise ErrorUsuario("La clave de Anthropic empieza por «sk-ant-». Revisa que la copiaste completa.")
    archivo.parent.mkdir(parents=True, exist_ok=True)
    archivo.write_text(valor, encoding="utf-8")


def sdk_instalado() -> bool:
    try:
        import anthropic  # noqa: F401
    except ImportError:
        return False
    return True


def disponible() -> bool:
    return sdk_instalado() and bool(clave())


def clave_enmascarada() -> str:
    c = clave()
    return f"{c[:10]}…{c[-4:]}" if len(c) > 16 else ""


# ------------------------------------------------------------------ referencia (va en caché)
def _casos_de_clase(con: sqlite3.Connection, texto_caso: str) -> list[tuple[str, str]]:
    """Los casos de clase guardados en Notas (título, contenido), en orden. Se deja fuera el que coincide con el
    caso que se analiza, para que Fable lo razone y no copie la respuesta del profesor."""
    filas = con.execute(
        """SELECT n.titulo, n.contenido FROM notas n JOIN componentes k ON k.id = n.componente_id
           JOIN materias m ON m.id = k.materia_id
           WHERE m.papelera_id IS NULL AND k.papelera_id IS NULL AND n.papelera_id IS NULL
             AND n.titulo LIKE 'CASO %'""").fetchall()
    caso = normalizar(texto_caso)
    salida = []
    for titulo, contenido in sorted(filas, key=lambda f: [int(x) if x.isdigit() else x for x in re.split(r"(\d+)", f[0])]):
        enunciado = re.split(r"(?im)^#+\s*(diagn|jerarq|tratamiento)", contenido or "")[0]
        lineas = [re.sub(r"[^a-z0-9]", "", normalizar(l))[:50] for l in enunciado.split("\n") if len(l.strip()) > 30]
        compacto = re.sub(r"[^a-z0-9]", "", caso)
        if lineas and sum(l in compacto for l in lineas) >= 0.6 * len(lineas):
            continue
        salida.append((titulo, contenido or ""))
    return salida


def referencia(con: sqlite3.Connection, fuentes: dxc.Fuentes, texto_caso: str) -> str:
    partes = ["# TABLA DE JERARQUIZACIÓN",
              "Prioridad de cada terapia por patología (1 = primera elección). Columnas: "
              + ", ".join(f"{k}={t['nombre']}" for k, t in dxc.TERAPIAS.items()) + ".", ""]
    for p in fuentes.patologias.values():
        celdas = []
        for k, (prioridad, nota, comentario) in p["celdas"].items():
            txt = f"{k}={prioridad if prioridad is not None else '?'}"
            if nota:
                txt += f" ({nota})"
            if comentario:
                txt += f" [comentario: {' '.join(comentario.split())}]"
            celdas.append(txt)
        partes.append(f"- {p['nombre']}: " + ("; ".join(celdas) or "sin terapias"))
    partes += ["", "# CONSOLIDADO",
               "Cada fila: [fila N] PATOLOGÍA · prioridad · TERAPÉUTICA, con DESCRIPCIÓN, FÓRMULA y NOTAS.", ""]
    for nombre, filas in fuentes.consolidado.items():
        for f in filas:
            partes.append(f"[fila {f['id']}] {nombre.upper()} · prioridad {f['prioridad'] if f['prioridad'] is not None else '?'} · {f['terapeutica']}")
            for etiqueta, clave_f in (("DESCRIPCIÓN", "descripcion"), ("FÓRMULA", "formula"), ("NOTAS", "notas")):
                if f[clave_f]:
                    partes.append(f"{etiqueta}: {f[clave_f].strip()}")
            partes.append("")
    casos = _casos_de_clase(con, texto_caso)
    if casos:
        partes += ["# CASOS DE CLASE",
                   "Así se entrega el resultado en clase: el caso y, después, los diagnósticos y la jerarquización.", ""]
        for titulo, contenido in casos:
            partes += [f"## {titulo}", contenido.strip(), ""]
    return "\n".join(partes)


INSTRUCCIONES = """Eres asistente de estudio de una estudiante de Terapias Alternativas y Farmacología Vegetal. Recibes un \
caso clínico, a veces completo (motivo de consulta, enfermedad actual, revisión por sistemas, antecedentes, examen \
físico) y a veces de un solo párrafo, y entregas el resultado como en los casos de clase de la referencia: los \
diagnósticos y la jerarquización del tratamiento, con la prescripción concreta de cada terapia.

Cómo trabajar:
- Diagnósticos: todos los que el caso sostenga, el principal primero (el del motivo de consulta). Para cada uno di si \
corresponde a una patología de la Tabla de jerarquización (escribe su nombre exactamente como está en la tabla) o si \
no está en la tabla. Califícalo como en clase cuando el caso lo permita («HTA controlada», «Sobrepeso IMC 29»). Si \
solo hay indicios, márcalo como probable. No tomes como diagnóstico lo negado ni los antecedentes familiares.
- Jerarquización: ordena las terapias según las prioridades de la tabla y del Consolidado, empezando por el \
diagnóstico principal, y combina las que sirven a varios diagnósticos como en clase. Usa solo terapias que estén en \
la tabla o en el Consolidado para esos diagnósticos; si el caso pide algo que el material no cubre (una úlcera \
infectada, por ejemplo), dilo en observaciones en vez de inventarlo.
- Para cada terapia: el objetivo terapéutico en este paciente (una frase, como «mejorar la oxigenación y la \
microcirculación del tejido») y, por diagnóstico, la prescripción: dosis, vía, frecuencia y duración tomadas del \
Consolidado y adaptadas al caso, con el número de la fila del Consolidado en que te basas (0 si viene solo de la tabla).
- Datos faltantes: lo que falta en el caso para decidir mejor (peso y talla, tensión arterial, paraclínicos…).
- Prioriza los datos del material sobre tu conocimiento general. Escribe en español, claro y sin adornos."""

ESQUEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["paciente", "motivo", "diagnosticos", "jerarquizacion", "datos_faltantes", "observaciones"],
    "properties": {
        "paciente": {"type": "string", "description": "Sexo y edad si el caso los dice, p. ej. «Mujer de 55 años»; vacío si no."},
        "motivo": {"type": "string", "description": "Motivo de consulta en pocas palabras."},
        "diagnosticos": {
            "type": "array",
            "items": {
                "type": "object", "additionalProperties": False,
                "required": ["nombre", "patologia_tabla", "principal", "probable", "fundamento"],
                "properties": {
                    "nombre": {"type": "string", "description": "Como se escribiría en clase, con su calificativo."},
                    "patologia_tabla": {"type": "string", "description": "Nombre exacto en la Tabla de jerarquización, o vacío."},
                    "principal": {"type": "boolean"},
                    "probable": {"type": "boolean"},
                    "fundamento": {"type": "string", "description": "Qué datos del caso lo sostienen (una o dos frases)."},
                },
            },
        },
        "jerarquizacion": {
            "type": "array",
            "items": {
                "type": "object", "additionalProperties": False,
                "required": ["terapia", "objetivo", "indicaciones"],
                "properties": {
                    "terapia": {"type": "string"},
                    "objetivo": {"type": "string"},
                    "indicaciones": {
                        "type": "array",
                        "items": {
                            "type": "object", "additionalProperties": False,
                            "required": ["diagnostico", "prioridad", "prescripcion", "fila_consolidado"],
                            "properties": {
                                "diagnostico": {"type": "string"},
                                "prioridad": {"type": "integer", "description": "Prioridad en la tabla o el Consolidado (0 si no tiene)."},
                                "prescripcion": {"type": "string"},
                                "fila_consolidado": {"type": "integer", "description": "Número de fila del Consolidado, o 0."},
                            },
                        },
                    },
                },
            },
        },
        "datos_faltantes": {"type": "array", "items": {"type": "string"}},
        "observaciones": {"type": "string"},
    },
}


def _pistas(r: dxc.Resultado) -> str:
    """Lo que ya encontraron las reglas, como ayuda (Fable decide)."""
    lineas = ["Hallazgos automáticos de la app (pueden estar incompletos o equivocados):"]
    for d in r.diagnosticos:
        base = "; ".join(f"«{e.linea[e.inicio:e.fin]}» ({e.nombre_seccion or 'caso'}, {e.tipo})" for e in d.evidencias[:5])
        lineas.append(f"- {d.titulo_completo}{' [probable]' if d.probable else ''}{' [principal]' if d.principal else ''}: {base}")
    lineas += [f"- {x}" for x in r.datos]
    return "\n".join(lineas)


# ------------------------------------------------------------------ resultado
@dataclass
class IndicacionIA:
    diagnostico: str
    prioridad: int | None
    prescripcion: str
    fila: dict | None = None          # fila del Consolidado, si existe
    fila_citada: int = 0              # número que dio Fable (para avisar si no existe)


@dataclass
class TerapiaIA:
    terapia: str
    objetivo: str
    indicaciones: list[IndicacionIA] = field(default_factory=list)


@dataclass
class DiagnosticoIA:
    nombre: str
    patologia: str                    # nombre en la tabla ("" si no está)
    fila_tabla: int | None
    principal: bool
    probable: bool
    fundamento: str


@dataclass
class ResultadoIA:
    modelo: str
    paciente: str = ""
    motivo: str = ""
    diagnosticos: list[DiagnosticoIA] = field(default_factory=list)
    jerarquizacion: list[TerapiaIA] = field(default_factory=list)
    datos_faltantes: list[str] = field(default_factory=list)
    observaciones: str = ""
    respaldo: str = ""                # modelo que respondió si Fable declinó

    @property
    def resumen(self) -> str:
        lineas = [x for x in (self.paciente, f"Motivo de consulta: {self.motivo}" if self.motivo else "") if x]
        lineas += (["", "DIAGNÓSTICOS"] if lineas else ["DIAGNÓSTICOS"])
        lineas += [f"{n}. {d.nombre}{' (probable)' if d.probable else ''}" for n, d in enumerate(self.diagnosticos, 1)]
        lineas += ["", "JERARQUIZACIÓN"]
        for n, t in enumerate(self.jerarquizacion, 1):
            lineas.append(f"{n}. {t.terapia}: ({t.objetivo})" if t.objetivo else f"{n}. {t.terapia}")
            for m, i in enumerate(t.indicaciones, 1):
                prefijo = f"{n}.{m} " if len(t.indicaciones) > 1 else ""
                lineas.append(f"{prefijo}{i.diagnostico}: {i.prescripcion}")
            lineas.append("")
        if self.observaciones:
            lineas += ["Observaciones: " + self.observaciones]
        return "\n".join(lineas).strip()


class ErrorIA(Exception):
    """No se pudo obtener el análisis de Fable; el mensaje es para mostrarle a la usuaria."""


def _validar(datos: dict, fuentes: dxc.Fuentes) -> ResultadoIA:
    filas = {f["id"]: f for lista in fuentes.consolidado.values() for f in lista}
    res = ResultadoIA(MODELO, datos.get("paciente", "").strip(), datos.get("motivo", "").strip(),
                      datos_faltantes=[x for x in datos.get("datos_faltantes", []) if x.strip()],
                      observaciones=datos.get("observaciones", "").strip())
    for d in datos.get("diagnosticos", []):
        clave_p = normalizar(d.get("patologia_tabla", ""))
        pat = fuentes.patologias.get(clave_p)
        res.diagnosticos.append(DiagnosticoIA(d.get("nombre", "").strip(), pat["nombre"] if pat else "",
                                              pat["fila"] if pat else None, bool(d.get("principal")),
                                              bool(d.get("probable")), d.get("fundamento", "").strip()))
    for t in datos.get("jerarquizacion", []):
        terapia = TerapiaIA(t.get("terapia", "").strip(), t.get("objetivo", "").strip().strip("()"))
        for i in t.get("indicaciones", []):
            n = int(i.get("fila_consolidado") or 0)
            terapia.indicaciones.append(IndicacionIA(i.get("diagnostico", "").strip(), int(i.get("prioridad") or 0) or None,
                                                     i.get("prescripcion", "").strip(), filas.get(n), n))
        res.jerarquizacion.append(terapia)
    return res


def preparar(con: sqlite3.Connection, texto: str) -> tuple[str, dxc.Fuentes]:
    """Lee la biblioteca (en el hilo de la conexión) y arma la referencia que va en caché."""
    fuentes = dxc.cargar_fuentes(con)
    return referencia(con, fuentes, texto), fuentes


def consultar(ref: str, fuentes: dxc.Fuentes, texto: str, reglas: dxc.Resultado, cliente=None) -> ResultadoIA:
    """Llama a Fable (sin tocar la base: se puede correr en otro hilo). Lanza ErrorIA con un mensaje claro si no
    se puede. `cliente` permite probar sin la API."""
    if cliente is None:
        if not sdk_instalado():
            raise ErrorIA("Falta instalar el paquete «anthropic». Ejecuta de nuevo el instalador.")
        if not clave():
            raise ErrorIA("No hay clave de la API de Anthropic. Agrégala en Mantenimiento › Inteligencia artificial.")
        import anthropic
        cliente = anthropic.Anthropic(api_key=clave(), timeout=TIEMPO_MAXIMO, max_retries=2)
    return _llamar(cliente, ref, texto, reglas, fuentes)


def _llamar(cliente, ref: str, texto: str, reglas: dxc.Resultado, fuentes: dxc.Fuentes) -> ResultadoIA:
    import anthropic
    try:
        with cliente.beta.messages.stream(
            model=MODELO,
            max_tokens=MAX_TOKENS,
            betas=[BETA_RESPALDO],
            fallbacks="default",
            output_config={"effort": ESFUERZO, "format": {"type": "json_schema", "schema": ESQUEMA}},
            system=[{"type": "text", "text": INSTRUCCIONES},
                    {"type": "text", "text": ref, "cache_control": {"type": "ephemeral", "ttl": "1h"}}],
            messages=[{"role": "user", "content": f"CASO CLÍNICO:\n{texto.strip()}\n\n{_pistas(reglas)}"}],
        ) as stream:
            respuesta = stream.get_final_message()
    except anthropic.AuthenticationError as e:
        raise ErrorIA("La clave de la API de Anthropic no es válida. Revísala en Mantenimiento.") from e
    except anthropic.PermissionDeniedError as e:
        raise ErrorIA("La clave no tiene permiso para usar este modelo (o la organización no cumple la retención de "
                      "datos que pide Fable).") from e
    except anthropic.RateLimitError as e:
        raise ErrorIA("Se alcanzó el límite de uso de la API. Espera un momento y vuelve a intentar.") from e
    except anthropic.APITimeoutError as e:
        raise ErrorIA("Fable tardó demasiado en responder. Intenta de nuevo.") from e
    except anthropic.APIConnectionError as e:
        raise ErrorIA("No hay conexión con Anthropic. Revisa el internet del equipo.") from e
    except anthropic.APIStatusError as e:
        log.warning("Error de la API (%s): %s", e.status_code, e.message)
        raise ErrorIA(f"La API respondió con un error ({e.status_code}). Intenta de nuevo más tarde.") from e

    if respuesta.stop_reason == "refusal":
        raise ErrorIA("El modelo declinó analizar este caso.")
    if respuesta.stop_reason == "max_tokens":
        raise ErrorIA("La respuesta quedó incompleta (demasiado larga). Intenta con un caso más corto.")
    texto_json = next((b.text for b in respuesta.content if b.type == "text"), "")
    try:
        datos = json.loads(texto_json)
    except ValueError as e:
        raise ErrorIA("La respuesta del modelo no se pudo leer. Intenta de nuevo.") from e
    resultado = _validar(datos, fuentes)
    if getattr(respuesta, "model", MODELO) != MODELO:
        resultado.respaldo = respuesta.model
    uso = getattr(respuesta, "usage", None)
    if uso is not None:
        log.info("Diagnóstico IA: %s tokens de entrada (%s de caché), %s de salida",
                 getattr(uso, "input_tokens", "?"), getattr(uso, "cache_read_input_tokens", "?"), getattr(uso, "output_tokens", "?"))
    return resultado

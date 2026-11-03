"""Módulo Diagnóstico: de un caso clínico escrito en texto libre a diagnósticos y tratamiento jerarquizado.

1. Lee el caso (motivo de consulta, enfermedad actual, revisión por sistemas, antecedentes, examen físico…)
   y reconoce las patologías de la **Tabla de jerarquización** que aparecen en él. Para cada una guarda la
   evidencia: el renglón del caso donde está, resaltado. Algunas evidencias son directas (el nombre de la
   enfermedad o su sigla) y otras son indicios (un síntoma, un medicamento, un dato del examen como el IMC o
   la tensión arterial); un diagnóstico apoyado solo en indicios se presenta como «probable».
2. Para cada diagnóstico arma el tratamiento ordenado por jerarquía con lo que dice el **Consolidado**
   (prioridad, terapéutica, descripción, fórmula, notas) y la **Tabla de jerarquización** (prioridad e
   indicaciones de cada terapia, más los comentarios de sus celdas). Cuando las dos fuentes no coinciden se
   avisa. La prioridad que manda es la del Consolidado, que es la que trae el tratamiento detallado.
3. Junta todo en un plan integrado: primero las terapias del diagnóstico principal (el del motivo de
   consulta), por su prioridad; luego las demás. Con igual prioridad va antes la que sirve para más
   diagnósticos.

Nada se inventa: el tratamiento sale del material guardado en la biblioteca y siempre se muestra de dónde.
Es una herramienta de estudio; no reemplaza el juicio clínico.
"""
from __future__ import annotations

import json
import re
import sqlite3
import unicodedata
from dataclasses import dataclass, field

from . import biblioteca as bib
from .texto import normalizar

MAX_TEXTO = 20000

# ------------------------------------------------------------------ terapias
# Columnas de la Tabla de jerarquización y nombres con que aparecen en el Consolidado.
TERAPIAS: dict[str, dict] = {
    "acup": {"nombre": "Acupuntura", "columnas": ["acup", "acupuntura"], "alias": [r"acupuntura", r"acup"]},
    "tn": {"nombre": "Terapia neural", "columnas": ["t.n.", "tn", "terapia neural"], "alias": [r"terapia neural", r"tn"]},
    "fv": {"nombre": "Farmacología vegetal", "columnas": ["f.v.", "fv", "farmacologia vegetal"],
           "alias": [r"farmacologia vegetal", r"farmaco vegetal", r"fitoterapia", r"fv"]},
    "homeop": {"nombre": "Homeopatía", "columnas": ["homeop", "homeopatia"], "alias": [r"homeopatia", r"homeop"]},
    "cmagn": {"nombre": "Campos magnéticos", "columnas": ["c. magn", "c.magn", "campos magneticos"],
              "alias": [r"campos? magneticos?", r"c\.? magneticos?", r"c\.? magn", r"cmp"]},
    "gik": {"nombre": "Solución GIK", "columnas": ["sol. gik", "sol gik", "solucion gik"],
            "alias": [r"solucion (polarizante )?gi[nk]k?", r"sol\.? gik", r"gik"]},
    "psicot": {"nombre": "Psicoterapia y esencias florales", "columnas": ["psicot", "psicoterapia"],
               "alias": [r"psicoterapias?", r"\(?esencias florales", r"musicoterapia"]},
    "o2": {"nombre": "Oxigenoterapia", "columnas": ["o2", "oxigenoterapia"],
           "alias": [r"oxigenoterapia", r"oxivenacion", r"oxigeno", r"o2", r"camara hiperbarica"]},
    "o3": {"nombre": "Ozonoterapia", "columnas": ["o3", "ozonoterapia"], "alias": [r"ozonoterapia", r"ozono", r"o3"]},
}
_ALIAS_TERAPIA = [(clave, re.compile(r"^\W*(?:" + "|".join(t["alias"]) + r")(?!\w)")) for clave, t in TERAPIAS.items()]


def terapia_de(nombre: str) -> tuple[str, str]:
    """(clave, nombre para mostrar) de una terapéutica del Consolidado. Las que no son una de las columnas de la
    tabla (ejercicio, dieta…) quedan con su propio nombre."""
    n = normalizar(nombre)
    for clave, patron in _ALIAS_TERAPIA:
        if patron.search(n):
            return clave, TERAPIAS[clave]["nombre"]
    limpio = " ".join(nombre.split()).strip(" ()")
    return "otra:" + normalizar(limpio), limpio[:1].upper() + limpio[1:].lower()


# ------------------------------------------------------------------ reglas de reconocimiento
# Clave: nombre de la patología en la Tabla de jerarquización (normalizado, sin tildes ni mayúsculas).
#   cons      nombres con que aparece en el Consolidado
#   directos  expresiones que nombran la enfermedad
#   indicios  síntomas, medicamentos o hallazgos que la sugieren
#   siglas    siglas que solo cuentan escritas en MAYÚSCULAS ("LES" sí, "les" no)
# Las expresiones son regex sobre el texto normalizado; siempre empiezan al comienzo de una palabra.
REGLAS: dict[str, dict] = {
    "cefalea": {"cons": ["cefalea"], "directos": [r"cefaleas?", r"migranas?", r"jaquecas?"],
                "indicios": [r"dolor(es)? de cabeza", r"cefalalgia"]},
    "artritis reumatoidea": {"cons": ["artritis"], "directos": [r"artritis reumatoidea?"],
                             "indicios": [r"rigidez matutina", r"poliartritis", r"factor reumatoide"]},
    "paralisis facial": {"cons": ["paralisis facial"], "directos": [r"paralisis facial", r"paralisis de bell"],
                         "indicios": [r"desviacion de la comisura", r"no (puede )?cierra?r? el ojo"]},
    "neuralgia del trigemino": {"cons": ["neuralgia del trigemino"],
                                "directos": [r"neuralgia (del )?trigemin\w*", r"tic doloroso"]},
    "obesidad": {"cons": ["obesidad"], "directos": [r"obesidad", r"obes[oa]s?"]},
    "insuficiencia renal": {"cons": ["insuficiencia renal"],
                            "directos": [r"insuficiencia renal", r"enfermedad renal cronica", r"falla renal"],
                            "siglas": ["ERC", "IRC"],
                            "indicios": [r"creatinina (elevada|alta)", r"hemodialisis", r"dialisis", r"nefropatia"]},
    "dermatitis atopica": {"cons": ["dermatitis atopica"], "directos": [r"dermatitis atopica", r"eccema atopico", r"eczema atopico"],
                           "indicios": [r"dermatitis", r"eccemas?", r"eczemas?", r"piel (muy )?seca con prurito"]},
    "trastorno de ansiedad": {"cons": ["trastorno de ansiedad"],
                              "directos": [r"trastorno de ansiedad", r"ansiedad", r"ansios[oa]s?", r"crisis de (angustia|panico)",
                                           r"ataques? de panico", r"trastorno de panico"],
                              "indicios": [r"angusti(a|ad[oa]|os[oa])", r"nervios[oa]", r"preocupad[oa]", r"estres\w*",
                                           r"intranquil\w*", r"inquietud", r"panico"]},
    "cancer": {"cons": ["cancer"],
               "directos": [r"cancer", r"carcinoma", r"adenocarcinoma", r"neoplasia maligna", r"tumor maligno", r"linfoma",
                            r"leucemia", r"ca\.? (de )?(mama|pulmon|prostata|colon|cervix|cuello uterino|estomago|gastrico|ovario|tiroides)"],
               "indicios": [r"metastasis", r"quimioterapia", r"radioterapia", r"mastectomia", r"oncolog\w*"]},
    "hipotiroidismo": {"cons": ["hipotiroidismo"], "directos": [r"hipotiroidismo"],
                       "indicios": [r"levotiroxina", r"eutirox", r"tsh (elevada|alta)"]},
    "trastorno del sueno": {"cons": ["trastorno del sueno"], "directos": [r"insomnio", r"trastornos? del sueno"],
                            "indicios": [r"no (puede )?dorm\w*", r"dificultad para (dormir|conciliar el sueno)", r"duerme (poco|mal)",
                                         r"despierta (varias veces|en la noche|en la madrugada)", r"sueno no reparador",
                                         r"zolpidem", r"mal dormir"]},
    "asma": {"cons": ["asma"], "directos": [r"asma", r"asmatic[oa]"], "indicios": [r"sibilancias", r"broncoespasmo", r"salbutamol"]},
    "osteoporosis": {"cons": ["osteoporosis"], "directos": [r"osteoporosis"],
                     "indicios": [r"osteopenia", r"alendronato", r"densitometria", r"caltrate", r"carbonato de calcio"]},
    "osteoartrosis degenerativa": {"cons": ["osteoartrosis"],
                                   "directos": [r"osteoartrosis", r"artrosis", r"osteoartritis", r"gonartrosis", r"coxartrosis"]},
    "gastritis cronica": {"cons": ["gastritis"], "directos": [r"gastritis"],
                          "indicios": [r"epigastralgia", r"dolor epigastrico", r"dispepsia", r"pirosis", r"acidez",
                                       r"reflujo", r"omeprazol", r"esomeprazol"]},
    "adicciones": {"cons": ["adicciones"],
                   "directos": [r"adiccion(es)?", r"alcoholismo", r"drogadiccion", r"farmacodependencia",
                                r"consumo de (sustancias|drogas|marihuana|cocaina|basuco|heroina)"],
                   "indicios": [r"tabaquismo", r"fumador[a]?", r"consumo de alcohol", r"dependencia (al|a la|de)"]},
    "intestino irritable": {"cons": ["intestino irritable"], "directos": [r"intestino irritable", r"colon irritable"],
                            "siglas": ["SII"],
                            "indicios": [r"distension abdominal", r"alterna\w* (entre )?diarrea y estrenimiento"]},
    "colitis ulcerativa": {"cons": ["colitis"], "directos": [r"colitis ulcer\w*", r"colitis"],
                           "indicios": [r"diarrea con sangre", r"rectorragia", r"mesalazina"]},
    "fracturas de dificil consolidacion": {"cons": ["fracturas"],
                                           "directos": [r"pseudoartrosis", r"retardo (en la|de) consolidacion",
                                                        r"no consolidad[ao]", r"fractura de dificil consolidacion"],
                                           "indicios": [r"fracturas?"]},
    "fibromialgia": {"cons": ["fibromialgia"], "directos": [r"fibromialgia"],
                     "indicios": [r"dolor (generalizado|en todo el cuerpo)", r"puntos dolorosos"]},
    "sd miofascial": {"cons": ["sdmiofascial", "sd miofascial", "sindrome miofascial"],
                      "directos": [r"(sindrome|sd\.?) miofascial", r"dolor miofascial"],
                      "indicios": [r"puntos? gatillo", r"contracturas?( muscular\w*)?", r"nodulos dolorosos"]},
    "vertigo periferico": {"cons": ["vertigo"], "directos": [r"vertigos?"],
                           "indicios": [r"mareos?", r"(todo|el cuarto|la habitacion) (le )?(gira|da vueltas)", r"nistagmo"]},
    "trastorno del animo / depresion": {"cons": ["depresion"],
                                        "directos": [r"depresion", r"depresiv[oa]", r"trastorno del (estado de )?animo", r"distimia"],
                                        "indicios": [r"triste(za)?", r"desanim\w*", r"llanto facil", r"anhedonia", r"desmotiv\w*",
                                                     r"fluoxetina", r"sertralina", r"escitalopram", r"paroxetina",
                                                     r"duelo", r"sin (encontrar )?motivacion", r"labilidad emocional"]},
    "epoc": {"cons": ["epoc"], "siglas": ["EPOC"],
             "directos": [r"enfermedad pulmonar obstructiva", r"enfisema", r"bronquitis cronica"],
             "indicios": [r"oxigeno domiciliario", r"oxigeno \d+ horas", r"bromuro de ipratropio", r"tiotropio", r"roncus",
                          r"disnea progresiva", r"fumador[a]? de \d+", r"fumo un paquete", r"\d+ cigarrillos"]},
    "cloasma facial": {"cons": ["cloasma"], "directos": [r"cloasma", r"melasma"],
                       "indicios": [r"manchas (oscuras )?en (la )?cara", r"hiperpigmentacion facial"]},
    "rosacea": {"cons": ["rosacea"], "directos": [r"rosacea"],
                "indicios": [r"rubor facial", r"eritema facial", r"enrojecimiento (de la |en la )?cara"]},
    "sobrepeso": {"cons": ["sobrepeso"], "directos": [r"sobrepeso"], "indicios": [r"aumento (de peso|ponderal)", r"ganancia de peso"]},
    "les": {"cons": ["les"], "siglas": ["LES"], "directos": [r"lupus"]},
    "discopatia lumbar": {"cons": ["discopatia"], "directos": [r"discopatia", r"hernia(s)? (de )?disc\w*", r"lumbociatica"],
                          "indicios": [r"lumbalgia", r"dolor lumbar", r"ciatica"]},
    "desgarros / esguinces articulares": {"cons": ["desgarros"], "directos": [r"desgarros?", r"esguinces?"],
                                          "indicios": [r"torcedura"]},
    "parkinson": {"cons": ["parkinson"], "directos": [r"parkinson\w*"],
                  "indicios": [r"temblor en reposo", r"levodopa", r"bradicinesia"]},
    "enfermedad bipolar": {"cons": ["bipolar"], "directos": [r"bipolar(idad)?"],
                           "indicios": [r"carbonato de litio", r"episodios? maniac\w*", r"mania"]},
    "infeccion respiratoria a repeticion": {"cons": ["enfermedad respiratoria a repeticion"],
                                            "directos": [r"infecci\w* respiratori\w* (a repeticion|recurrentes?|frecuentes?)",
                                                         r"(bronquitis|gripas?|resfriados?) (a repeticion|recurrentes?|frecuentes?)"],
                                            "indicios": [r"infecci\w* respiratori\w*"]},
    "ivu baja a repeticion": {"cons": ["ivu"], "siglas": ["IVU", "ITU"],
                              "directos": [r"infecci\w* (de vias|del tracto|de las vias) urinari\w*", r"infecci\w* urinari\w*", r"cistitis"],
                              "indicios": [r"disuria", r"ardor al orinar"]},
    "enfermedad hemorroidal": {"cons": ["hemorroides"], "directos": [r"hemorroid\w*", r"almorranas?"]},
    "enfermedad varicosa": {"cons": ["varices"],
                            "directos": [r"varices", r"varic(es|os[ao]s?)", r"variz", r"insuficiencia venosa", r"enfermedad venosa",
                                         r"ulceras? (venosas?|varicosas?)"],
                            "indicios": [r"ulceras?\b[^.;]{0,60}(piernas?|maleol\w*|miembros? inferior\w*|tobillos?|mmii)",
                                         r"telangiectasias?", r"pesadez (de|en) (las )?piernas", r"edema (de|en) miembros inferiores"]},
    "hta": {"cons": ["hta"], "siglas": ["HTA"], "directos": [r"hipertension( arterial)?", r"hipertens[oa]s?"],
            "indicios": [r"losartan", r"enalapril", r"captopril", r"amlodipin[oa]", r"valsartan", r"irbesartan", r"telmisartan",
                         r"hidroclorotiazida", r"nifedipin[oa]", r"metoprolol", r"carvedilol"]},
    "secuelas acv isquemico": {"cons": ["acv"], "siglas": ["ACV", "ECV"],
                               "directos": [r"accidente cerebro ?vascular", r"evento cerebro ?vascular", r"infarto cerebral", r"ictus"],
                               "indicios": [r"hemiparesia", r"hemiplejia"]},
    "afasia": {"cons": ["afasia"], "directos": [r"afasi\w*"],
               "indicios": [r"dificultad para hablar", r"no puede hablar", r"disartria"]},
    "diabetes tipo 2": {"cons": ["diabetes"], "siglas": ["DM", "DM2"], "directos": [r"diabetes( mellitus)?", r"diabetic[oa]s?"],
                        "indicios": [r"metformina", r"glibenclamida", r"hiperglucemia", r"glucemia (elevada|alta)", r"hba1c"]},
    "dismenorrea": {"cons": ["dismenorrea"], "directos": [r"dismenorrea"],
                    "indicios": [r"colicos menstruales", r"dolor menstrual", r"dolor (con|durante) (la )?menstruacion"]},
    "sd climaterico": {"cons": ["climaterio"],
                       "directos": [r"climateri\w*", r"menopausia", r"perimenopausia", r"(sindrome|sd\.?) climaterico"],
                       "indicios": [r"bochornos", r"sofocos", r"oleadas de calor"]},
    "urolitiasis": {"cons": ["urolitiasis"],
                    "directos": [r"urolitiasis", r"nefrolitiasis", r"litiasis (renal|urinaria)", r"calculos? (renal\w*|urinari\w*)"],
                    "indicios": [r"colico renal"]},
    "gota": {"cons": ["gota"], "directos": [r"(?<!\d )(?<!una )gota(?!s)", r"artritis gotosa", r"podagra"],
             "indicios": [r"hiperuricemia", r"acido urico (elevado|alto)", r"alopurinol", r"colchicina"]},
    "sd sjogren": {"cons": ["sjogren"], "directos": [r"sjogren"], "indicios": [r"xerostomia", r"xeroftalmia", r"boca seca"]},
    "autismo": {"cons": ["autismo"], "siglas": ["TEA"], "directos": [r"autismo", r"autista", r"espectro autista"]},
    "disfuncion erectil": {"cons": ["disfuncion erectil"], "directos": [r"disfuncion erectil", r"impotencia sexual"],
                           "indicios": [r"sildenafil", r"tadalafil", r"(problemas|dificultad) (de|para la|con la) ereccion"]},
    "rinitis/rinosinusitis": {"cons": ["rinitis"], "directos": [r"rinitis", r"sinusitis", r"rinosinusitis"],
                              "indicios": [r"congestion nasal", r"obstruccion nasal", r"rinorrea", r"estornudos"]},
    "amigdalitis cronica": {"cons": ["amigdalitis"], "directos": [r"amigdalitis", r"faringoamigdalitis", r"tonsilitis"],
                            "indicios": [r"amigdalas (hipertrofic\w*|grandes|aumentadas)"]},
    "toc": {"cons": ["toc"], "siglas": ["TOC"], "directos": [r"trastorno obsesivo", r"obsesivo[- ]compulsivo", r"obsesiv[oa]"],
            "indicios": [r"compulsi\w*", r"meticulos[oa]", r"perfeccionista"]},
    "dislipidemia": {"cons": ["dislipidemia"],
                     "directos": [r"dislipidemia", r"hipercolesterolemia", r"hipertrigliceridemia", r"colesterol (alto|elevado)",
                                  r"trigliceridos (altos|elevados)"],
                     "indicios": [r"atorvastatina", r"rosuvastatina", r"lovastatina", r"simvastatina", r"gemfibrozilo"]},
    "estrenimiento": {"cons": [], "directos": [r"estrenimiento", r"estrenid[oa]", r"constipacion"],
                      "indicios": [r"deposiciones? (cada \d+ dias|duras|escasas)", r"no (hace|realiza) deposicion"]},
    "temblor esencial": {"cons": [], "directos": [r"temblor esencial"], "indicios": [r"temblor\w*"]},
    "cervicalgia": {"cons": [], "directos": [r"cervicalgia", r"cervicodorsalgia", r"dolor cervical",
                                             r"dolor (en|de) (la )?region cervic\w*([ -]dorsal)?"],
                    "indicios": [r"dolor (de|en el) cuello", r"rigidez (de|en el) cuello"]},
}

# Palabras que niegan lo que sigue en la misma frase («niega cefalea», «sin várices»)
_NEGACION = re.compile(r"(?<![a-z])(no|niega|negativ[oa]|sin|ausencia de|descarta)(?![a-z])")
_NEGACION_FALSA = re.compile(r"sin embargo|sin ninguna mejoria|sin mejoria|no mejora")
# Encabezados de las secciones de una historia clínica
SECCIONES = {
    "motivo": r"motivo de (la )?consulta",
    "actual": r"enfermedad actual",
    "sistemas": r"revision por sistemas",
    "personales": r"antecedentes( personales)?",
    "familiares": r"antecedentes familiares",
    "examen": r"examen fisico",
    "paraclinicos": r"paraclinicos|laboratorios?",
    "diagnosticos": r"diagnosticos?|impresion diagnostica",
}
NOMBRE_SECCION = {"motivo": "Motivo de consulta", "actual": "Enfermedad actual", "sistemas": "Revisión por sistemas",
                  "personales": "Antecedentes", "familiares": "Antecedentes familiares", "examen": "Examen físico",
                  "paraclinicos": "Paraclínicos", "diagnosticos": "Diagnósticos", "": ""}
SECCIONES_PRINCIPALES = {"motivo", "actual"}


# ------------------------------------------------------------------ resultado
@dataclass
class Evidencia:
    linea: str                    # renglón del caso, tal cual
    inicio: int
    fin: int
    seccion: str = ""
    tipo: str = "directo"         # directo | indicio | dato
    detalle: str = ""             # explicación de un dato calculado (IMC, TA)
    valor: str = ""               # el dato en corto, para el nombre del diagnóstico («IMC 29,3», «TA 135/80»)

    @property
    def partes(self) -> list[tuple[str, bool]]:
        return [(self.linea[:self.inicio], False), (self.linea[self.inicio:self.fin], True), (self.linea[self.fin:], False)]

    @property
    def nombre_seccion(self) -> str:
        return NOMBRE_SECCION.get(self.seccion, "")


@dataclass
class Indicacion:
    """Una terapia para un diagnóstico, con lo que dicen las dos fuentes."""
    clave: str
    nombre: str
    prioridad: int | None = None              # la que manda (Consolidado; si no está ahí, la Tabla)
    prioridad_consolidado: int | None = None
    prioridad_tabla: int | None = None
    nota_tabla: str = ""                      # texto de la celda de la tabla además del número
    comentario_tabla: str = ""                # comentario de la celda
    filas: list[dict] = field(default_factory=list)   # filas del Consolidado: id, terapeutica, descripcion, formula, notas

    @property
    def aviso(self) -> str:
        c, t = self.prioridad_consolidado, self.prioridad_tabla
        en_c, en_t = bool(self.filas), self.prioridad_tabla is not None or bool(self.nota_tabla)
        if en_c and en_t and c is not None and t is not None and c != t:
            return f"La Tabla de jerarquización le da prioridad {t}."
        if en_c and not en_t:
            return "No figura en la Tabla de jerarquización."
        if en_t and not en_c:
            return "Solo figura en la Tabla de jerarquización (sin detalle en el Consolidado)."
        return ""


@dataclass
class Diagnostico:
    clave: str                    # nombre normalizado en la Tabla
    nombre: str                   # tal como está en la Tabla
    fila_tabla: int | None = None
    evidencias: list[Evidencia] = field(default_factory=list)
    indicaciones: list[Indicacion] = field(default_factory=list)
    manual: bool = False          # agregado a mano por la usuaria

    @property
    def titulo(self) -> str:
        return self.nombre[:1].upper() + self.nombre[1:]

    @property
    def calificativo(self) -> str:
        """Lo que el caso dice del diagnóstico, como en clase: «controlada (TA 135/80)», «IMC 29,3»."""
        valores = list(dict.fromkeys(e.valor for e in self.evidencias if e.valor))
        if self.clave == "hta":
            ta = [e for e in self.evidencias if e.valor.startswith("TA")]
            if any(e.tipo == "dato" for e in ta):
                return "controlada (" + ", ".join(e.valor for e in ta) + ")"
            if ta and any(e.tipo == "directo" for e in self.evidencias):
                return "no controlada (" + ", ".join(e.valor for e in ta) + ")"
        return ", ".join(valores)

    @property
    def titulo_completo(self) -> str:
        return self.titulo + (f" {self.calificativo}" if self.calificativo.startswith(("controlada", "no controlada"))
                              else f" ({self.calificativo})" if self.calificativo else "")

    @property
    def base(self) -> list[str]:
        """Palabras del caso en que se apoya (para el resumen)."""
        return list(dict.fromkeys(e.linea[e.inicio:e.fin].strip() for e in self.evidencias if e.tipo != "dato"))

    @property
    def principal(self) -> bool:
        return any(e.seccion in SECCIONES_PRINCIPALES and e.tipo != "dato" for e in self.evidencias)

    @property
    def probable(self) -> bool:
        """Solo hay indicios (ninguna evidencia nombra la enfermedad)."""
        return not self.manual and not any(e.tipo == "directo" for e in self.evidencias)

    @property
    def peso(self) -> int:
        return sum(2 if e.tipo == "directo" else 1 for e in self.evidencias if e.tipo != "dato")


@dataclass
class PasoPlan:
    """Una terapia del plan integrado y los diagnósticos que atiende."""
    clave: str
    nombre: str
    usos: list[tuple[Diagnostico, Indicacion]] = field(default_factory=list)

    @property
    def prioridad(self) -> int | None:
        valores = [i.prioridad for _, i in self.usos if i.prioridad is not None]
        return min(valores) if valores else None


@dataclass
class Resultado:
    texto: str
    diagnosticos: list[Diagnostico] = field(default_factory=list)
    descartados: list[Diagnostico] = field(default_factory=list)      # reconocidos pero quitados por la usuaria
    familiares: list[Diagnostico] = field(default_factory=list)       # solo en antecedentes familiares
    plan: list[PasoPlan] = field(default_factory=list)
    datos: list[str] = field(default_factory=list)                    # IMC, TA… calculados del examen
    patologias: list[tuple[str, str]] = field(default_factory=list)   # (clave, nombre) para agregar a mano
    fuentes: dict[str, int | None] = field(default_factory=dict)      # id de las tablas usadas
    faltan_fuentes: bool = False
    paciente: str = ""                                                # «Mujer de 55 años»
    motivo: str = ""                                                  # motivo de consulta tal como viene
    avisos: list[str] = field(default_factory=list)                   # lo que le falta al caso

    @property
    def resumen(self) -> str:
        """Texto para copiar, con la forma de los casos de clase: diagnósticos y jerarquización con su prescripción."""
        lineas = []
        if self.paciente:
            lineas.append(self.paciente)
        if self.motivo:
            lineas.append(f"Motivo de consulta: {self.motivo}")
        lineas += ["", "DIAGNÓSTICOS"] if lineas else ["DIAGNÓSTICOS"]
        lineas += [f"{n}. {d.titulo_completo}{' (probable)' if d.probable else ''}" for n, d in enumerate(self.diagnosticos, 1)]
        lineas += ["", "JERARQUIZACIÓN"]
        for n, p in enumerate(self.plan, 1):
            lineas.append(f"{n}. {p.nombre} (para {', '.join(d.nombre for d, _ in p.usos)})")
            for m, (d, i) in enumerate(p.usos, 1):
                prefijo = f"{n}.{m} " if len(p.usos) > 1 else ""
                lineas.append(f"{prefijo}{d.titulo} — prioridad {i.prioridad if i.prioridad is not None else 's/p'}")
                for f in i.filas:
                    texto = f["formula"] or f["descripcion"]
                    if texto:
                        lineas.append(texto.strip())
                if i.nota_tabla:
                    lineas.append(f"Tabla: {i.nota_tabla}")
                if i.comentario_tabla:
                    lineas.append(f"Comentario de la tabla: {i.comentario_tabla}")
            lineas.append("")
        return "\n".join(lineas).strip()


# ------------------------------------------------------------------ texto
def _plano(texto: str) -> str:
    """Minúsculas y sin tildes, letra por letra: conserva las posiciones para resaltar sobre el original."""
    salida = []
    for c in texto:
        d = "".join(x for x in unicodedata.normalize("NFKD", c) if not unicodedata.combining(x)).lower()
        salida.append(d[:1] if d else " ")
    return "".join(salida)


def _seccion_de_encabezado(plano: str) -> tuple[str | None, int]:
    """Si el renglón empieza con el nombre de una sección, devuelve (sección, fin del encabezado)."""
    limpio = plano.lstrip(" #*-•>").rstrip()
    corrimiento = len(plano) - len(plano.lstrip(" #*-•>"))
    # «antecedentes familiares» antes que «antecedentes»
    for clave in ("familiares", "motivo", "actual", "sistemas", "personales", "examen", "paraclinicos", "diagnosticos"):
        m = re.match(r"(?:" + SECCIONES[clave] + r")\s*[:.\-*]*\s*", limpio)
        if m:
            return clave, corrimiento + m.end()
    if re.match(r"familiares?\s*:", limpio):
        return "familiares", corrimiento
    return None, 0


def renglones(texto: str) -> list[tuple[str, str, str, int]]:
    """(renglón original, renglón plano, sección, desde dónde buscar) de cada renglón con contenido."""
    salida, seccion = [], ""
    for linea in (texto or "")[:MAX_TEXTO].replace("\r", "").split("\n"):
        if not linea.strip():
            continue
        plano = _plano(linea)
        nueva, desde = _seccion_de_encabezado(plano)
        if nueva:
            seccion_linea = nueva
            # «Familiares: madre con HTA» es solo ese renglón; un encabezado solo cambia la sección
            if not plano[desde:].strip() or nueva != "familiares" or re.match(r"\W*antecedentes", plano):
                seccion = nueva
            if not plano[desde:].strip():
                continue
        else:
            seccion_linea, desde = seccion, 0
        salida.append((linea, plano, seccion_linea, desde))
    if salida and not any(r[2] for r in salida):
        # Caso sin secciones («Paciente de 52 años con hipertensión…»): la primera frase hace de motivo de consulta
        linea, plano, _, _ = salida[0]
        m = re.search(r"[.;]\s", plano)
        corte = m.end() if m else len(plano)
        salida[0:1] = [(linea[:corte], plano[:corte], "motivo", 0)] + (
            [(linea[corte:], plano[corte:], "", 0)] if plano[corte:].strip() else [])
    return salida


def tiene_secciones(texto: str) -> bool:
    return any(_seccion_de_encabezado(_plano(l))[0] for l in (texto or "").split("\n"))


def datos_paciente(texto: str) -> tuple[str, str]:
    """(«Mujer de 55 años», motivo de consulta) cuando el caso los dice."""
    plano = _plano((texto or "")[:3000])
    sexo = ""
    if re.search(r"(?<![a-z])(femenin[oa]|mujer|senora|paciente femenina)(?![a-z])", plano):
        sexo = "Mujer"
    elif re.search(r"(?<![a-z])(masculino|hombre|varon|senor)(?![a-z])", plano):
        sexo = "Hombre"
    edad = re.search(r"(?<![a-z])(?:paciente|edad|mujer|hombre|varon|femenin[oa]|masculin[oa])[^.\n\d]{0,25}?(\d{1,3})\s*anos", plano) \
        or re.search(r"^\W*(\d{1,3})\s*anos", plano)
    edad_txt = f"{edad.group(1)} años" if edad else ""
    paciente = " de ".join(x for x in (sexo, edad_txt) if x) if sexo else (f"Paciente de {edad_txt}" if edad_txt else "")
    motivo = " ".join(l.strip() for l, _, sec, _ in renglones(texto) if sec == "motivo")
    return paciente, motivo[:300]


def _negado(plano: str, inicio: int) -> bool:
    antes = re.split(r"[.;:]", plano[:inicio])[-1][-45:]
    antes = _NEGACION_FALSA.sub(" ", antes)
    return bool(_NEGACION.search(antes))


def _compilar(regla: dict, nombre: str) -> list[tuple[re.Pattern, str, bool]]:
    patrones = [(r"(?<![a-z0-9])(?:" + p + r")(?![a-z0-9])", "directo", False) for p in regla.get("directos", [])]
    patrones += [(r"(?<![a-z0-9])(?:" + p + r")(?![a-z0-9])", "indicio", False) for p in regla.get("indicios", [])]
    patrones += [(r"(?<![A-Za-z0-9])" + re.escape(s) + r"(?![A-Za-z0-9])", "directo", True) for s in regla.get("siglas", [])]
    if not regla.get("directos") and not regla.get("siglas") and nombre:      # patología nueva en la tabla: su nombre
        patrones.append((r"(?<![a-z0-9])" + re.escape(nombre) + r"(?![a-z0-9])", "directo", False))
    return [(re.compile(p), t, sigla) for p, t, sigla in patrones]


def _buscar(texto: str, clave: str, nombre: str) -> list[Evidencia]:
    regla = REGLAS.get(clave, {})
    patrones = _compilar(regla, clave)
    evidencias: list[Evidencia] = []
    usados: list[tuple[int, int, int]] = []          # (renglón, inicio, fin) ya tomados: sin evidencias superpuestas
    for n, (linea, plano, seccion, desde) in enumerate(renglones(texto)):
        for patron, tipo, sigla in patrones:
            for m in patron.finditer(linea if sigla else plano, desde):
                if _negado(plano, m.start()):
                    continue
                if any(r == n and m.start() < f and m.end() > i for r, i, f in usados):
                    continue
                usados.append((n, m.start(), m.end()))
                evidencias.append(Evidencia(linea, m.start(), m.end(), seccion, tipo))
    return evidencias


# ------------------------------------------------------------------ datos del examen físico
_NUM = r"(\d+(?:[.,]\d+)?)"


def _numero(s: str) -> float:
    return float(s.replace(",", "."))


# (patología, expresión con el valor al final, umbral, nombre, tipo de evidencia)
LABORATORIOS = [
    ("dislipidemia", r"colesterol( total)?\s*(:|de|en|=)?\s*" + _NUM, 200, "Colesterol total", "directo"),
    ("dislipidemia", r"(?<![a-z])(ldl|c-ldl|colesterol ldl)\s*(:|de|en|=)?\s*" + _NUM, 130, "Colesterol LDL", "directo"),
    ("dislipidemia", r"trigliceridos\s*(:|de|en|=)?\s*" + _NUM, 150, "Triglicéridos", "directo"),
    ("hipotiroidismo", r"(?<![a-z])tsh\s*(:|de|en|=)?\s*" + _NUM, 4.5, "TSH", "indicio"),
    ("diabetes tipo 2", r"glucemia( en ayunas| basal)?\s*(:|de|en|=)?\s*" + _NUM, 126, "Glucemia", "indicio"),
    ("diabetes tipo 2", r"(hba1c|hemoglobina glicosilada|hemoglobina glucosilada)\s*(:|de|en|=)?\s*" + _NUM, 6.5, "HbA1c", "directo"),
    ("gota", r"acido urico\s*(:|de|en|=)?\s*" + _NUM, 7, "Ácido úrico", "indicio"),
]


def datos_examen(texto: str) -> tuple[dict[str, list[Evidencia]], list[str]]:
    """IMC (dado o calculado con peso y talla) y tensión arterial. Devuelve evidencias por patología y un resumen."""
    por_clave: dict[str, list[Evidencia]] = {}
    resumen: list[str] = []
    peso = talla = imc = None
    linea_peso = linea_imc = None
    for linea, plano, seccion, _ in renglones(texto):
        if seccion == "familiares":
            continue
        if (m := re.search(r"(?<![a-z])peso\s*:?\s*(de\s*)?" + _NUM + r"\s*(kg|kilos?|kilogramos?)?", plano)) and peso is None:
            peso, linea_peso = _numero(m.group(2)), (linea, m.start(), m.end(), seccion)
        if (m := re.search(r"(?<![a-z])(talla|estatura)\s*:?\s*(de\s*)?" + _NUM + r"\s*(cm|mts?|m)?(?![a-z])", plano)) and talla is None:
            v = _numero(m.group(3))
            talla = v / 100 if v > 3 else v
            if linea_peso and linea_peso[0] == linea:
                linea_peso = (linea, min(linea_peso[1], m.start()), max(linea_peso[2], m.end()), seccion)
        if (m := re.search(r"(?<![a-z])imc\s*:?\s*(de\s*)?" + _NUM, plano)) and imc is None:
            imc, linea_imc = _numero(m.group(2)), (linea, m.start(), m.end(), seccion)
        if m := re.search(r"(?<![a-z])(ta|pa|t\.a\.?|p\.a\.?|tension arterial|presion arterial)\s*:?\s*(de\s*)?(\d{2,3})\s*/\s*(\d{2,3})", plano):
            sis, dia = int(m.group(3)), int(m.group(4))
            if sis >= 140 or dia >= 90:
                txt = f"Tensión arterial {sis}/{dia} mmHg: elevada (≥ 140/90)."
                por_clave.setdefault("hta", []).append(Evidencia(linea, m.start(), m.end(), seccion, "indicio", txt, f"TA {sis}/{dia}"))
            else:
                txt = f"Tensión arterial {sis}/{dia} mmHg: por debajo de 140/90 (si es hipertensa, está controlada)."
                por_clave.setdefault("hta", []).append(Evidencia(linea, m.start(), m.end(), seccion, "dato", txt, f"TA {sis}/{dia}"))
            resumen.append(txt)
        for clave, patron, umbral, nombre_lab, tipo in LABORATORIOS:
            if (m := re.search(patron, plano)) and _numero(m.group(m.lastindex)) >= umbral:
                valor = _numero(m.group(m.lastindex))
                txt = f"{nombre_lab} {valor:g}: por encima de {umbral:g}."
                por_clave.setdefault(clave, []).append(
                    Evidencia(linea, m.start(), m.end(), seccion, tipo, txt, f"{nombre_lab} {valor:g}".replace(".", ",")))
                resumen.append(txt)
    origen = linea_imc
    if imc is None and peso and talla and 0.5 < talla < 2.5:
        imc, origen = round(peso / (talla * talla), 1), linea_peso
        resumen.insert(0, f"IMC calculado: {peso:g} kg / ({talla:.2f} m)² = {imc:.1f} kg/m².")
    elif imc is not None:
        resumen.insert(0, f"IMC indicado en el caso: {imc:g} kg/m².")
    if imc is not None and origen:
        clave = "obesidad" if imc >= 30 else "sobrepeso" if imc >= 25 else None
        if clave:
            categoria = "obesidad (≥ 30)" if clave == "obesidad" else "sobrepeso (25 a 29,9)"
            txt = f"IMC {imc:.1f}: {categoria}."
            resumen[0] += f" Corresponde a {categoria}."
            linea, i, f, seccion = origen
            por_clave.setdefault(clave, []).append(Evidencia(linea, i, f, seccion, "directo", txt, f"IMC {imc:.1f}".replace(".", ",")))
        else:
            resumen[0] += " Sin sobrepeso." if imc >= 18.5 else " Bajo peso."
    return por_clave, resumen


# ------------------------------------------------------------------ fuentes en la biblioteca
def _columnas(columnas_json: str) -> dict[str, str]:
    return {normalizar(c["nombre"]): c["clave"] for c in json.loads(columnas_json)}


def _fuentes(con: sqlite3.Connection) -> tuple[tuple | None, tuple | None, int | None]:
    """Busca, en las materias que no están en la papelera, la Tabla de jerarquización (columnas PATOLOGÍA y ACUP…)
    y el Consolidado (PATOLOGÍA, JERARQUIZACIÓN y TERAPÉUTICA). Devuelve (tabla, consolidado, componente de la tabla)."""
    tabla = consolidado = None
    componente = None
    filas = con.execute(
        f"""SELECT t.id, t.columnas, t.componente_id FROM tablas t JOIN componentes k ON k.id = t.componente_id
            JOIN materias m ON m.id = k.materia_id
            WHERE t.papelera_id IS NULL AND k.papelera_id IS NULL AND m.papelera_id IS NULL
              AND m.id NOT IN ({bib.SQL_OCULTAS_SIN_BUSQUEDA})
            ORDER BY t.id""").fetchall()
    for tid, columnas_json, cid in filas:
        cols = _columnas(columnas_json)
        pat = cols.get("patologia")
        if not pat:
            continue
        if consolidado is None and "jerarquizacion" in cols and "terapeutica" in cols:
            consolidado = (tid, cols)
        elif tabla is None and any(n in cols for t in TERAPIAS.values() for n in t["columnas"]):
            tabla, componente = (tid, cols), cid
    return tabla, consolidado, componente


def _prioridad(valor: str) -> tuple[int | None, str]:
    """«1 E.F. MUSICOT» -> (1, "E.F. MUSICOT"); «opción de cazar el viento» -> (None, texto)."""
    valor = " ".join((valor or "").split())
    m = re.match(r"^(\d+)\s*[.)\-:]?\s*(.*)$", valor)
    if m:
        return int(m.group(1)), m.group(2).strip()
    return None, valor


def _comentarios(con: sqlite3.Connection, componente_id: int | None) -> dict[tuple[str, str], str]:
    """Comentarios de las celdas de la tabla, guardados en la nota «Comentarios - …» del mismo componente:
    **patología · COLUMNA** (celda X) seguido de las líneas «> Comentario: …»."""
    if componente_id is None:
        return {}
    salida: dict[tuple[str, str], str] = {}
    for (contenido,) in con.execute("SELECT contenido FROM notas WHERE componente_id = ? AND papelera_id IS NULL "
                                    "AND titulo LIKE 'Comentarios%'", (componente_id,)):
        for m in re.finditer(r"\*\*(.+?) · (.+?)\*\*[^\n]*\n((?:>[^\n]*\n?)+)", contenido or ""):
            texto = "\n".join(l.lstrip("> ").strip() for l in m.group(3).strip().split("\n"))
            texto = re.sub(r"^Comentario( de [^:]+)?:\s*", "", texto).strip()
            texto = re.sub(r"^[A-Z]+:\s*$", "", texto).strip()
            if texto:
                salida[(normalizar(m.group(1)), normalizar(m.group(2)))] = texto
    return salida


@dataclass
class Fuentes:
    tabla_id: int | None
    consolidado_id: int | None
    patologias: dict[str, dict]       # clave normalizada -> {"nombre", "fila", "celdas": {terapia: (prioridad, nota, comentario)}}
    consolidado: dict[str, list[dict]]  # nombre normalizado de la patología -> filas


def cargar_fuentes(con: sqlite3.Connection) -> Fuentes:
    tabla, consolidado, componente = _fuentes(con)
    patologias: dict[str, dict] = {}
    if tabla:
        tid, cols = tabla
        comentarios = _comentarios(con, componente)
        nombres_col = {v: k for k, v in cols.items()}
        terapia_col = {}
        for clave_t, t in TERAPIAS.items():
            for n in t["columnas"]:
                if n in cols:
                    terapia_col[clave_t] = cols[n]
                    break
        for fid, valores in con.execute("SELECT id, valores FROM filas WHERE tabla_id = ? AND huerfana = 0 ORDER BY posicion", (tid,)):
            v = json.loads(valores)
            nombre = " ".join((v.get(cols["patologia"]) or "").split())
            if not nombre:
                continue
            clave = normalizar(nombre)
            celdas = {}
            for clave_t, col in terapia_col.items():
                crudo = (v.get(col) or "").strip()
                comentario = comentarios.get((clave, nombres_col[col]), "")
                if crudo or comentario:
                    prioridad, nota = _prioridad(crudo)
                    celdas[clave_t] = (prioridad, nota, comentario)
            patologias[clave] = {"nombre": nombre, "fila": fid, "celdas": celdas}
    filas_cons: dict[str, list[dict]] = {}
    if consolidado:
        cid, cols = consolidado
        g = lambda v, n: (v.get(cols.get(n, ""), "") or "").strip()  # noqa: E731
        for fid, valores in con.execute("SELECT id, valores FROM filas WHERE tabla_id = ? AND huerfana = 0 ORDER BY posicion", (cid,)):
            v = json.loads(valores)
            nombre = normalizar(g(v, "patologia"))
            if not nombre:
                continue
            prioridad, _ = _prioridad(g(v, "jerarquizacion"))
            filas_cons.setdefault(nombre, []).append({
                "id": fid, "prioridad": prioridad, "terapeutica": " ".join(g(v, "terapeutica").split()),
                "descripcion": g(v, "descripcion"), "formula": g(v, "formula"), "notas": g(v, "notas")})
    return Fuentes(tabla[0] if tabla else None, consolidado[0] if consolidado else None, patologias, filas_cons)


def _nombres_consolidado(clave: str, fuentes: Fuentes) -> list[str]:
    regla = REGLAS.get(clave)
    if regla is not None:
        return [n for n in regla["cons"] if n in fuentes.consolidado]
    # patología nueva: el Consolidado la llama igual o con las primeras palabras de su nombre
    return [n for n in fuentes.consolidado if clave == n or clave.startswith(n + " ")]


def indicaciones(clave: str, fuentes: Fuentes) -> list[Indicacion]:
    """Tratamiento de una patología, ordenado por jerarquía, juntando el Consolidado y la Tabla."""
    por_terapia: dict[str, Indicacion] = {}
    orden: list[str] = []
    for nombre in _nombres_consolidado(clave, fuentes):
        for fila in fuentes.consolidado[nombre]:
            k, mostrar = terapia_de(fila["terapeutica"])
            ind = por_terapia.get(k)
            if ind is None:
                ind = por_terapia[k] = Indicacion(k, mostrar)
                orden.append(k)
            ind.filas.append(fila)
            if fila["prioridad"] is not None and (ind.prioridad_consolidado is None or fila["prioridad"] < ind.prioridad_consolidado):
                ind.prioridad_consolidado = fila["prioridad"]
    pat = fuentes.patologias.get(clave)
    if pat:
        for k, (prioridad, nota, comentario) in pat["celdas"].items():
            ind = por_terapia.get(k)
            if ind is None:
                ind = por_terapia[k] = Indicacion(k, TERAPIAS[k]["nombre"])
                orden.append(k)
            ind.prioridad_tabla, ind.nota_tabla, ind.comentario_tabla = prioridad, nota, comentario
    for ind in por_terapia.values():
        ind.prioridad = ind.prioridad_consolidado if ind.prioridad_consolidado is not None else ind.prioridad_tabla
    # Con igual prioridad, primero lo que trae tratamiento detallado en el Consolidado
    return sorted(por_terapia.values(),
                  key=lambda i: (i.prioridad if i.prioridad is not None else 99, not i.filas, orden.index(i.clave)))


# ------------------------------------------------------------------ análisis
def analizar(con: sqlite3.Connection, texto: str, elegidos: list[str] | None = None) -> Resultado:
    """Reconoce los diagnósticos del caso y arma el tratamiento. Con `elegidos` (claves de la tabla), la usuaria
    ya ajustó la lista: se usan esos (con su evidencia, si la hay) y los demás reconocidos quedan como descartados."""
    texto = (texto or "")[:MAX_TEXTO]
    fuentes = cargar_fuentes(con)
    resultado = Resultado(texto=texto, fuentes={"tabla": fuentes.tabla_id, "consolidado": fuentes.consolidado_id})
    resultado.faltan_fuentes = fuentes.tabla_id is None and fuentes.consolidado_id is None
    claves = list(fuentes.patologias) or list(REGLAS)
    nombres = {k: fuentes.patologias[k]["nombre"] if k in fuentes.patologias else k for k in claves}
    resultado.patologias = sorted(((k, nombres[k]) for k in claves), key=lambda x: normalizar(x[1]))
    datos, resultado.datos = datos_examen(texto)
    resultado.paciente, resultado.motivo = datos_paciente(texto)
    if texto.strip():
        if not tiene_secciones(texto):
            resultado.avisos.append("El caso no trae secciones (motivo de consulta, enfermedad actual, examen físico…): "
                                    "se tomó la primera frase como motivo de consulta.")
        if not any("IMC" in d for d in resultado.datos):
            resultado.avisos.append("No hay peso y talla (ni IMC): no se pudo valorar sobrepeso u obesidad.")
        if not any("Tensión arterial" in d for d in resultado.datos):
            resultado.avisos.append("No hay tensión arterial.")

    reconocidos: list[Diagnostico] = []
    for clave in claves:
        evidencias = _buscar(texto, clave, nombres[clave]) + datos.get(clave, [])
        propias = [e for e in evidencias if e.seccion != "familiares" and e.tipo != "dato"]
        d = Diagnostico(clave, nombres[clave], fuentes.patologias.get(clave, {}).get("fila"),
                        [e for e in evidencias if e.seccion != "familiares"])
        if propias:
            reconocidos.append(d)
        elif any(e.seccion == "familiares" for e in evidencias):
            d.evidencias = [e for e in evidencias if e.seccion == "familiares"]
            resultado.familiares.append(d)

    if elegidos is not None:
        elegidos_set = [k for k in dict.fromkeys(elegidos) if k in nombres]
        por_clave = {d.clave: d for d in reconocidos}
        resultado.descartados = [d for d in reconocidos if d.clave not in elegidos_set]
        lista = []
        for k in elegidos_set:
            d = por_clave.get(k)
            if d is None:
                d = Diagnostico(k, nombres[k], fuentes.patologias.get(k, {}).get("fila"),
                                [e for e in datos.get(k, []) if e.tipo == "dato"], manual=True)
            lista.append(d)
        reconocidos = lista

    # Un indicio compartido no basta para dos diagnósticos: «temblor» con Parkinson ya reconocido
    if any(d.clave == "parkinson" for d in reconocidos):
        reconocidos = [d for d in reconocidos if not (d.clave == "temblor esencial" and d.probable)]

    for d in reconocidos:
        d.indicaciones = indicaciones(d.clave, fuentes)
    reconocidos.sort(key=lambda d: (not d.principal, d.probable and not d.manual, -d.peso))
    resultado.diagnosticos = reconocidos
    resultado.plan = plan_integrado(reconocidos)
    return resultado


def plan_integrado(diagnosticos: list[Diagnostico]) -> list[PasoPlan]:
    pasos: dict[str, PasoPlan] = {}
    for d in diagnosticos:
        for i in d.indicaciones:
            paso = pasos.setdefault(i.clave, PasoPlan(i.clave, i.nombre))
            paso.usos.append((d, i))
    hay_principal = any(d.principal for d in diagnosticos)

    def orden(p: PasoPlan):
        # (prioridad, sin detalle en el Consolidado) del mejor uso: en el diagnóstico principal y en general
        usos = [(i.prioridad if i.prioridad is not None else 99, not i.filas, d.principal) for d, i in p.usos]
        principal = min((u[:2] for u in usos if u[2]), default=(99, True) if hay_principal else (0, False))
        return (principal, min(u[:2] for u in usos), -len(p.usos), p.nombre)

    for p in pasos.values():
        p.usos.sort(key=lambda u: (u[1].prioridad if u[1].prioridad is not None else 99))
    return sorted(pasos.values(), key=orden)

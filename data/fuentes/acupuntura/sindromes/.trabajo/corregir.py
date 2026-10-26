"""Copia hojas/Sindromes.xlsx a tablas/Síndromes.xlsx con ortografía corregida y actualiza plan.json."""
import json
import re
import sys
from pathlib import Path

import openpyxl

BASE = Path(sys.argv[1])

# Cambios de letras / palabras pegadas / restos técnicos (se declaran). Frases primero.
LETRAS = {
    "+F52menstruales": "menstruales",
    "tos co catarro": "tos con catarro",
    "aveces son sangre": "a veces con sangre",
    "aveces": "a veces",
    "co saburra": "con saburra",
    "por l a tarde": "por la tarde",
    "enfermedad el estomago": "enfermedad del estómago",
    "haces blandas": "heces blandas",
    "sed ee liquidos": "sed de líquidos",
    "enl os": "en los",
    "dolorp recordial": "dolor precordial",
    "vesicular biliar": "vesícula biliar",
    "estomaago": "estómago", "Qii": "Qi", "Triplerecalentador": "Triple recalentador",
    "Triplerecalenttador": "Triple recalentador", "exposion": "exposición", "palisda": "pálida",
    "expectoraion": "expectoración", "pocahidratacion": "poca hidratación", "esalofrio": "escalofrío",
    "tranpiracion": "transpiración", "ceaflea": "cefalea", "Dolro": "Dolor", "dolro": "dolor",
    "invacion": "invasión", "Invacion": "Invasión", "friebre": "fiebre", "piczon": "picazón",
    "acomulacion": "acumulación", "neuseas": "náuseas", "flam": "flema", "bronquitits": "bronquitis",
    "pagajosa": "pegajosa", "Door": "Dolor", "moc": "moco", "abadominal": "abdominal",
    "gastroenteritits": "gastroenteritis", "colitits": "colitis", "Filiforma": "Filiforme",
    "filiforma": "filiforme", "grudos": "crudos", "apetitio": "apetito", "adelgazaiento": "adelgazamiento",
    "lengia": "lengua", "alcoghol": "alcohol", "sangreso": "sangrado", "aliemntos": "alimentos",
    "aliva": "alivia", "borgborismo": "borborigmo", "enmiembros": "en miembros", "gastritits": "gastritis",
    "distencion": "distensión", "eruptos": "eructos", "imnombio": "insomnio", "adema": "edema",
    "volund": "voluntad", "posrprandial": "posprandial", "veetigos": "vértigos",
    "descendenteen": "descendente en", "orgamos": "órganos", "espitiru": "espíritu",
    "hematuras": "hematurias", "ematemesis": "hematemesis", "gaas": "ganas", "prenitud": "plenitud",
    "cornaria": "coronaria", "angnas": "anginas", "Escondidao": "Escondido", "sudiracion": "sudoración",
    "irradiadohacia": "irradiado hacia", "crnes": "carnes", "codimentos": "condimentos",
    "confusio": "confusión", "maniacoy": "maníaco y", "imsomnio": "insomnio", "pfrecuencia": "frecuencia",
    "abdomina": "abdominal", "planitud": "plenitud", "pegajosaen": "pegajosa en", "saburraen": "saburra en",
    "entros": "centros", "sudoracio": "sudoración", "pulmoar": "pulmonar", "sexal": "sexual",
    "dema": "edema", "mieso": "miedo", "hereditria": "hereditaria", "subnutricio": "subnutrición",
    "enfermedads": "enfermedades", "dlor": "dolor", "roj": "roja", "flama": "flema", "banca": "blanca",
    "mnos": "manos", "estremidades": "extremidades", "diatea": "dieta", "nica": "nuca", "deprende": "depende",
}

# Solo tildes (no se declaran)
TILDES = dict(x.split(":") for x in """acida:ácida acufenos:acúfenos afonia:afonía agitacion:agitación
ambicion:ambición apatia:apatía apice:ápice apoplejia:apoplejía asmatica:asmática audicion:audición
aversion:aversión azucar:azúcar azucares:azúcares calido:cálido calculo:cálculo cancer:cáncer
cardiogenico:cardiogénico cardiopatia:cardiopatía climaterico:climatérico coagulos:coágulos colico:cólico
confusion:confusión constipacion:constipación constitucion:constitución contraccion:contracción
corazon:corazón cronica:crónica cronicas:crónicas cronico:crónico debil:débil debiles:débiles
depresion:depresión desordenes:desórdenes desviacion:desviación despues:después difusion:difusión
distension:distensión encias:encías energia:energía enfasis:énfasis epigastrica:epigástrica
esclerotica:esclerótica escalofrio:escalofrío espiritu:espíritu espontanea:espontánea
espontaneo:espontáneo estomago:estómago estres:estrés evacuacion:evacuación exposicion:exposición
expectoracion:expectoración eyaculacion:eyaculación facilmente:fácilmente febricula:febrícula
fetida:fétida fisica:física fisico:físico flacida:flácida fria:fría frias:frías frio:frío frios:fríos
frustracion:frustración hemorragicas:hemorrágicas hepatica:hepática higado:hígado
hipertension:hipertensión humeda:húmeda humedo:húmedo humedos:húmedos impetigo:impétigo
indeterminacion:indeterminación infeccion:infección invasion:invasión lacteos:lácteos liquido:líquido
liquidos:líquidos manias:manías mas:más menstruacion:menstruación multiples:múltiples nauseas:náuseas
neumonia:neumonía neurologicas:neurológicas nodulos:nódulos obnubilacion:obnubilación
obstruccion:obstrucción opresion:opresión oseas:óseas palida:pálida palido:pálido palidos:pálidos
paralisis:parálisis patron:patrón peptica:péptica perdida:pérdida perdidas:pérdidas posicion:posición
preocupacion:preocupación presion:presión produccion:producción profundizacion:profundización
proteinas:proteínas psiquico:psíquico pulmon:pulmón pulsatil:pulsátil purpura:púrpura
purpuras:púrpuras raiz:raíz rapido:rápido region:región regurgitacion:regurgitación
respiracion:respiración retencion:retención riñon:riñón secrecion:secreción sensacion:sensación
sindrome:síndrome sindromes:síndromes sintomas:síntomas subito:súbito sudoracion:sudoración
tension:tensión testiculos:testículos toracica:torácica torax:tórax torticolis:tortícolis
ulcera:úlcera ulceras:úlceras utero:útero vacio:vacío vertigo:vértigo vertigos:vértigos vision:visión
vomito:vómito vomitos:vómitos vividos:vívidos violacea:violácea agitacion:agitación caida:caída traqueitis:traqueítis""".split())

L = r"A-Za-zÁÉÍÓÚáéíóúñÑü"


def sub_palabra(texto, a, b, ignorar_mayus):
    def rep(m):
        s = m.group(0)
        return b[0].upper() + b[1:] if s[0].isupper() and ignorar_mayus else b
    flags = re.IGNORECASE if ignorar_mayus else 0
    pat = (rf"(?<![{L}]){re.escape(a)}(?![{L}])") if a[0] != "+" else re.escape(a)
    return re.sub(pat, rep, texto, flags=flags)


usadas = {}
wb = openpyxl.load_workbook(BASE / "hojas/Sindromes.xlsx")
ws = wb.active
for fila in ws.iter_rows():
    for c in fila:
        if not isinstance(c.value, str):
            continue
        t = c.value
        for a, b in LETRAS.items():  # sensibles a mayúsculas (claves exactas)
            n = sub_palabra(t, a, b, False)
            if n != t:
                usadas[a] = b
                t = n
        for a, b in TILDES.items():
            t = sub_palabra(t, a, b, True)
        c.value = t
wb.save(BASE / "tablas/Síndromes.xlsx")

plan = json.loads((BASE / "plan.json").read_text(encoding="utf-8"))
plan["correcciones"] = usadas
plan["tablas"] = [{"archivo": "tablas/Síndromes.xlsx", "nombre": "Síndromes", "columna_titulo": "Síndromes",
                   "celdas": ["A1:F54"]}]
(BASE / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(len(usadas), "correcciones;", "sin usar:", sorted(set(LETRAS) - set(usadas)))

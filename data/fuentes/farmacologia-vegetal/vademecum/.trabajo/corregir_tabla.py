"""Corrige ortografía en la copia tablas/Farmacología vegetal.xlsx (re-extraída de la hoja)."""
import json, re, sys
from pathlib import Path
import openpyxl
D = Path(sys.argv[1])
ruta = D / "tablas/Farmacología vegetal.xlsx"
LETRAS = [  # (original, corregido) literales; se declaran en correcciones
    ("Solucio oral", "Solución oral"), ("obstrucciónbiliar", "obstrucción biliar"), ("lss secreciones", "las secreciones"),
    ("Eucalytus", "Eucalyptus"), ("Antiinflamtorio", "Antiinflamatorio"), ("antiinflamtoria", "antiinflamatoria"),
    ("Antiinflamtoria", "Antiinflamatoria"), ("Antinflamatorio", "Antiinflamatorio"), ("esecnial", "esencial"),
    ("anticuagulantes", "anticoagulantes"), ("anticuagualentes", "anticoagulantes"), ("mucuosa", "mucosa"),
    ("escencial", "esencial"), ("antivital", "antiviral"), ("Antivital", "Antiviral"), ("Antiflactulento", "Antiflatulento"),
    ("Ezimatico", "Enzimático"), ("Rubibarbo", "Ruibarbo"), ("veces la dia", "veces al día"), ("Cassi pulchra", "Cassia pulchra"),
    ("excecer", "exceder"), ("Sacharomyces", "Saccharomyces"), ("Acanthaceace", "Acanthaceae"), ("estra al", "estar al"),
    ("traquilizante", "tranquilizante"), ("mollisima", "mollissima"), ("inductoe", "inductor"), ("estereoides", "esteroides"),
    ("Apium graveolen", "Apium graveolens"), ("comunis", "communis"), ("Cavendshia", "Cavendishia"),
    ("americanun", "americanum"), ("apolecia", "Alopecia"), ("Cordondicillo", "Cordoncillo"),
    ("ene l tratamiento", "en el tratamiento"), ("bursistis", "bursitis"), ("esgunces", "esguinces"),
    ("desgarroos", "desgarros"), ("distenciones", "distensiones"), ("linaool", "linalool"),
    ("Antireumatico", "Antirreumático"), ("antireumatico", "antirreumático"), ("Soanum", "Solanum"),
    ("Paulinia yoco", "Paullinia yoco"), ("Cinnamomun", "Cinnamomum"), ("pancraticas", "pancreáticas"),
    ("Intercciones", "Interacciones"), ("Hipogliciamientes", "Hipoglicemiantes"), ("Decocion", "Decocción"),
    ("insufiencia", "insuficiencia"),
]
TILDES = dict(x.split(":") for x in """dia:día dias:días solucion:solución capsula:cápsula capsulas:cápsulas
mucolitico:mucolítico hepatica:hepática coagulacion:coagulación via:vía vias:vías inflamacion:inflamación
duracion:duración infeccion:infección cronica:crónica cronico:crónico expulsion:expulsión tambien:también
entraria:entraría sindrome:síndrome camara:cámara fenolicos:fenólicos triterpenicas:triterpénicas
triterpenicos:triterpénicos comun:común antitusigeno:antitusígeno llanten:llantén oregano:orégano acidos:ácidos
acido:ácido prevencion:prevención antialergico:antialérgico vaporizacion:vaporización toxico:tóxico
interaccion:interacción congestion:congestión sintomas:síntomas funcion:función antiseptico:antiséptico
bucofaringeo:bucofaríngeo topico:tópico antibiotico:antibiótico antibiotica:antibiótica estreptococica:estreptocócica
formacion:formación cóstras:costras cumarico:cumárico gastrica:gástrica calendula:caléndula volatiles:volátiles
musculo:músculo anis:anís benzaldehido:benzaldehído estrogeno:estrógeno despues:después procinetico:procinético
proquinetico:proquinético coleretico:colerético latex:látex uricosurico:uricosúrico diabeticos:diabéticos
decoccion:decocción proteinas:proteínas peptidos:péptidos aminoacidos:aminoácidos lipidos:lípidos alegria:alegría
ansiolitico:ansiolítico cidron:cidrón galico:gálico accion:acción arrayan:arrayán irritacion:irritación
guarana:guaraná hipertension:hipertensión psiquiatricos:psiquiátricos infusion:infusión raiz:raíz
ginsenosidos:ginsenósidos polisacaridos:polisacáridos suspension:suspensión preparacion:preparación
cutaneo:cutáneo cutanea:cutánea acne:acné locion:loción boton:botón alergicas:alérgicas lineas:líneas
expresion:expresión diuretico:diurético diureticos:diuréticos jabon:jabón flebotrofica:flebotrófica ulceras:úlceras
flebotropico:flebotrópico analgesico:analgésico opiaceos:opiáceos administracion:administración cancer:cáncer
antineoplasico:antineoplásico nucleo:núcleo poligalico:poligálico metabolico:metabólico cascara:cáscara
perdida:pérdida formula:fórmula inhibicion:inhibición absorcion:absorción celulas:células estres:estrés
leon:león aereas:aéreas precaucion:precaución prostata:próstata activacion:activación liquido:líquido
presentacion:presentación cientifico:científico sabila:sábila anamu:anamú""".split())
def caso(orig, nuevo):
    if orig.isupper() and len(orig) > 1: return nuevo.upper()
    if orig[0].isupper(): return nuevo[0].upper() + nuevo[1:]
    return nuevo
patron = re.compile(r"\b(" + "|".join(sorted(map(re.escape, TILDES), key=len, reverse=True)) + r")\b", re.I)
wb = openpyxl.load_workbook(ruta); ws = wb.active
usadas, cambios = set(), 0
for fila in ws.iter_rows(min_row=3):
    for c in fila:
        if not isinstance(c.value, str): continue
        v = c.value
        for a, b in LETRAS:
            if a in v: v = v.replace(a, b); usadas.add(a)
        if c.column_letter != "D" or c.row == 3:   # nombres científicos en latín: sin tildes
            v = patron.sub(lambda m: caso(m.group(0), TILDES[m.group(0).lower()]), v)
        if v != c.value: cambios += 1; c.value = v
wb.save(ruta)
print("celdas cambiadas", cambios, "| sin usar:", [a for a, _ in LETRAS if a not in usadas])
json.dump({a: b for a, b in LETRAS}, open(D/".trabajo/letras.json", "w"), ensure_ascii=False, indent=1)

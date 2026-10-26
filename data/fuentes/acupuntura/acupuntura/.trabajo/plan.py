"""Escribe plan.json del componente Acupuntura."""
import json
import sys
from pathlib import Path

BASE = Path(sys.argv[1])

notas = [
    ("TÉCNICA ZANG-FU - Acupuntura", ["B136:R159", "H140", "K141", "O142", "P143", "Q144"]),
    ("LUO - Acupuntura", ["C161:F183"]),
    ("YUAN - Acupuntura", ["G161:J168"]),
    ("MU - Acupuntura", ["P162:Q173"]),
    ("TÉCNICA DE PLANOS - Acupuntura", ["B186", "B188:O201", "H191:I191"]),
    ("HUI - Acupuntura", ["B222:C235"]),
    ("XI - Acupuntura", ["B236:C251"]),
    ("HE - Acupuntura", ["D222:E249"]),
    ("8 técnicas BA FENG - Acupuntura", ["F222:I231"]),
    ("Dolor de vísceras - Acupuntura", ["F232:I239"]),
    ("Dolor de órganos - Acupuntura", ["F240:I245"]),
    ("Enfermedad interna - Acupuntura", ["F246:I255"]),
    ("Técnica de LUO - Acupuntura", ["F256:I261"]),
] + [(t, ["J222"] + [r] if i == 0 else [r]) for i, (t, r) in enumerate(json.loads((BASE / ".trabajo/patogenos.json").read_text()))]

imagenes = [
    ("Acupuntura - A1.jpg", "A1", "Ciclo generación - Acupuntura", """Ciclo generación.
Fuego
Corazón / Intestino Delgado
Pericardio / Triple recalentador
(Mano)
Tierra
Bazo / Estómago
(Pie)
Metal
Pulmón / IG
(Mano)
Agua
Riñón / Vejiga
(Pie)
Madera
Hígado
VB
(Pie)
Madera → Fuego → Tierra → Metal → Agua → Madera

Ciclo de generación
Madera genera Fuego
Fuego genera Tierra
Tierra genera Metal
Metal genera Agua
Agua genera Madera.

Ciclo Dominancia
Fuego Domina Metal
Tierra Domina Agua
Agua Domina Fuego
Madera Domina Tierra
Metal Domina Madera

Contradominancia
Madera contradomina Metal
Metal contradomina Fuego
Fuego evapora Agua
Agua Inunda Tierra
Tierra pudre Madera."""),
    ("Acupuntura - G2.jpg", "G2", "4 niveles energéticos - Acupuntura", """4 niveles energéticos.
Wi - Energía de defensa, protege contra factores patógenos externos.
Qi - Energía funcional, mantiene las actividades fisiológicas.
Jing - Esencia base de la constitución y desarrollo
Xue - Sangre, nutre y mantiene tejidos

Externa
Wei | - Meridiano tendinomuscular (12 meridianos clásicos)
- Luo longitudinal (Drenar excesos)
- Meridianos diferentes
Interna
Qi | Tai yang (Posterior) Térmico | ID Show (Mano) | V Zu (Pie) | ↓ 1 ID cabeza ↓ V 67
  | Shao yang (Medial) Dinámico | TR Show (Mano) | VB Zu (Pie) | ↓ 1 TR cabeza ↓ VB 44
  | Yang Ming (Anterior) Hídrico | IG Show (Mano) | E Zu (Pie) | ↓ 1 IG cabeza ↓ E 45
Jing | Tai yin (anterior) | P Show (Mano) | B Zu (Pie) | ↑ 11 P tórax B1
  | Jue yin (Medial) | PC Show (Mano) | H Zu (Pie) | ↑ 9 PC tórax H1
  | Shao yin (posterior) | C Show (Mano) | R Zu (Pie) | ↑ 9 C tórax R1
Xue | Línea Blanca, Línea Roja, Plaquetas } Homeostasis, Nutrición de los tejidos.

Nota: Útil para manejo en síndrome Bi"""),
    ("Acupuntura - A48.jpg", "A48", "Puntos llave/Apertura - Acupuntura", """Puntos llave/Apertura.
Puntos | Meridiano extra | Indicaciones |
B4 | Chong | Sangre - Meridianos | Genitourinario (Ginecología)
PC6 | Yin wei | MD (emociones - neuralgias) | Meridianos Diferentes
P7 | Ren Mai (VC) | órganos (H-C-B-R-P) | Lumbalgia (interna)
R6 | Yin qiao | Frío - oscuridad | Insomnio
ID3 | Du Mai (VG) | vísceras (VB-ID-E-IG, V) |
V62 | Yang qiao | calor - luz | sueño y debilidad
VB41 | Dai Mai | Equilibrio yang/yin |
TR5 | Yang wei | MTM. |

Mujeres: Abro por la derecha, cierro por la izquierda
Hombres: Abro por la izquierda, cierro por la derecha.

Puntos:
Vejiga 40 - Punto Diclofenaco Región lumbar.
Intestino Delgado 3 - Punto Diclofenaco Región cervical."""),
    ("Acupuntura - H48.jpg", "H48", "Técnicas - Acupuntura", """Técnicas

Enfermedad interna
Órganos Zang/Fu
1 Punto emperador (ID3/P7)
2 Técnica Shu/MU
3 Técnica MU/Zi
4 Técnica Yuan/Luo
5 Roe (Reunión)
6 Técnica de planos
7 Tierra del acoplado
8 Cierre (V62/R6)

Enfermedad interna
Técnica de planos
1 Punto acelerador (fuego) Meridiano que inicia.
2 Punto arrastre (pozo) del Meridiano con el que termina
3 Nudos yang V1-VB2-E7 (Emocionales)
yin VC12-VC17-VC23 (Emocionales)
4 Nudos de nudos yang ExH9-VB8-E8
(donde se concentra la energía)
5 Gran nudo VG20 (Crisis HTA, ojos rojos, de resto no) manejo de mucho exceso.
6 Puntos Ashi (Puntos dolorosos)

Técnica MU/Zi
Madre - Hijo
- En deficiencia tonifico a la madre y en exceso sedo al hijo.

Técnica Shu/MU
Shu (Deficiencia de órgano)
MU (uso en exceso de yin vísceras)

Técnica Yuan/Luo
Equilibrar energía y manejo de meridiano afectado y acoplador por relación. Interior/Exterior.

Puntos Zi o Xi
se utilizan en caso de bloqueo de energía."""),
    ("Acupuntura - B87.jpg", "B87", "Puntos de los 12 meridianos - Acupuntura", """yin | P | P5, P6, P7, P8, P9, P10, P11 | Final Mano
yang | IG | IG11, IG10, IG9, IG8, IG7, IG6, IG5, IG4, IG3, IG2, IG1 | Inicio Mano
yang | E | E18 (Gran Luo E), E34, E35, E36, E37, E38, E39, E40, E41, E42, E43, E44, E45 | Final Pie
yin | B | B10, B9, B8, B7, B6, B5, B4, B3, B2, B1 | Inicio Pie
yin | C | C3, C4, C5, C6, C7, C8, C9 | Final Mano
yang | ID | ID8, ID7, ID6, ID5, ID4, ID3, ID2, ID1 | Inicio Mano
yang | V | V40, V41, V42, V43, V44, V45, V46, V47, V48, V49, V50, V51, V52, V53, V54, V55, V56, V57, V58, V59, V60, V61, V62, V63, V64, V65, V66, V67 | Final Pie
yin | R | R10, R9, R8, R7, R6, R5, R4, R3, R2, R1 | Inicio Pie
yin | PC | PC3, PC4, PC5, PC6, PC7, PC8, PC9 | Final Mano
yang | TR | TR10, TR9, TR8, TR7, TR6, TR5, TR4, TR3, TR2, TR1 | Inicio Mano
yang | VB | VB34, VB35, VB36, VB37, VB38, VB39, VB40, VB41, VB42, VB43, VB44 | Final Pie
yin | H | H8, H7, H6, H5, H4, H3, H2, H1 | Inicio Pie

Madera
Fuego
Tierra
Agua
Metal
Zi
Luo
Tonifica
Sedo
Yuan
(-) embarazo
Emocional"""),
    ("Acupuntura - B269.png", "B269", "Meridianos anteriores, posteriores y mediales - Acupuntura", """ANTERIORES
Yang Ming
I.Grueso
Estómago
ulmón
Bazo

POSTERIORES
TaiYang
I.Delgado
Vejiga
Shaoyin
corazón
Riñón

MEDIALES
ShaoYang
Triple recalentador
Vesícula Biliar
Jueyin
pericardio
Hígado"""),
    ("Acupuntura - A286.jpg", "A286", "Puntos MU (yin) - Acupuntura", """Puntos MU (yin)
P1 | MU de Pulmón → Dispersa calor
VC17 | MU de Pericardio → Regula Qi, todas las emociones que entran
VC14 | MU de corazón → Manías, Agitación, Insomnio, Baja el Fuego
H14 | MU de Hígado → Hace articular Qi de Hígado
H13 | MU de Bazo → Armoniza Hígado - Bazo
VB25 | MU de Riñón → Dispersa calor-Húmedo
VC12 | MU de Estómago → Tonifica estómago
VB24 | MU de Vesícula Biliar → Dispersa calor-Húmedo
VC3 | MU de Vejiga → Cistitis - vejiga
E25 | MU Intestino Grueso → ↓ Diarrea
VC5 | MU de TR → Circulación Quemador inferior, ITU, leucorreas
VC4 | MU de Intestino Delgado. → Aporta yin, absorbe Agua, Puerta del Brillo
Qi original."""),
    ("Acupuntura - H291.jpg", "H291", "Shu de espalda - Acupuntura", """Shu de espalda.
Rama externa V | Rama interna V | Zang Fu | Apófisis espinosa | VG | Función
V42 | V13 | Pulmón | T3 | VG12 | Asma, Tos, Sinusitis
V44 | V15 | Corazón | T5 | VG11 | Problemas lengua, Pulso - vasos
V46 | V17 | Diafragma | T7 | VG9 |
V47 | V18 | Hígado | T9 | VG8 | Patología Hígado, ojo, tendón, articulación
V48 | V19 | VB | T10 | VG7 |
V49 | V20 | Bazo | T11 | VG6 | Problemas boca y músculos
V50 | V21 | Estómago | T12 | | Estreñimiento y vómitos
V52 | V23 | Riñón | L2 | VG4 | Dificultad micción. oído, Tinnitus, Hueso.

Nota: Escojo MU por excesos y acompaña Shu por deficiencia y
* Bilateral + yang en enfermedad crónica
* Shu transporte de energía a los órganos.
* Excesos igual a dolor
* Dolor con cambios de color o textura desequilibrio órganos relacionados
* Vacío = Alivio del dolor a la palpación."""),
]

plan = {
    "materia": "Acupuntura",
    "componente": "Acupuntura",
    "fuentes": ["hojas/Acupuntura.xlsx"],
    "correcciones": {
        "DEFICIENCIE TONIFICAR": "DEFICIENCIA TONIFICAR",
        "Cistitis aguada": "Cistitis aguda",
        "è": "→",
    },
    "omitidos": [
        {"celda": "Acupuntura!M46", "motivo": "celda con espacios, sin texto"},
    ],
    "notas": [{"titulo": t, "archivo": f"notas/{t}.md", "celdas": c} for t, c in notas],
    "tablas": [],
    "imagenes": [{"archivo": f"imagenes/{a}", "titulo": t, "celda": c, "descripcion": d} for a, c, t, d in imagenes],
    "pdfs": [],
}
(BASE / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("plan.json escrito")

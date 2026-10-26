import json
from pathlib import Path
base = Path(__file__).resolve().parents[1]
C = " - Campo Magnético"
def nota(t, celdas): return {"titulo": t + C, "archivo": f"notas/{t}{C}.md", "celdas": celdas}
img_l32 = """Tabla de Parámetros CMP – Magnetoterapia
Centro / Corpas
Condición | Tipo de onda | Tiempo total | Tiempo mínimo exposición | Días
Postquirúrgicos ortopédicos | Norte o alterna | Segun Criterio Medico | Segun Criterio Medico | Segun Criterio Medico
Osteoartrosis degenerativa | Norte, sur o alterna | 100 horas | 1 hora | —
IAM post-etapa aguda | Sur o alterna | 40 horas | 1 hora | —
Insuficiencia cardíaca | Alterna | 30 horas | 1 hora | —
Artritis reumatoide | Norte o alterna | 30 horas | 1 hora | 30 días
Osteoporosis | Sur o alterna | 150 horas | 1 hora | 150 días
Fracturas | Sur o alterna | 20 horas | 2 horas | —
Necrosis fémur-tibia | Sur o alterna | 150 horas | 1 hora | —
Colagenosis | Norte o alterna | 70 horas | 1 hora | —
Dolores articulares | Norte o alterna | Segun Criterio Medico | Segun Criterio Medico | Segun Criterio Medico
Fibromialgia | Norte o alterna | 20 horas | 2 horas | 10 dias
Cáncer | Siempre norte | Segun Criterio Medico | Segun Criterio Medico | Segun Criterio Medico
Parálisis facial | Norte→Sur/Alterna | 150 horas | 3 horas | 50 días
Hipertensión | Alterna | 30 horas | 1 hora | —"""
img_w23 = """• Formulación de campos magnéticos
- TIPO de campo.
- Número de sesiones. (180 h de exposición a el campo antes de ver algún cambio) - tiene un efecto acumulativo ( siempre sesiones de 2 h - 1 a 3 veces por semana)
- Polaridad: casi todas se usan alternos
  • Positivos : Antiinflamatorio
  • Negativa: Estimulante
- Intensidad: Se usa unidad de medida Gauss
  • 100 a 200 gauss Maximo ( mas de 200 es iatrogenia)
- Frecuencia : Se usa en Hz
  • No es claro para que patología a que tipo de frecuencia
  • Van de 1 a 100 / ese utiliza 50 Hz, pero cuando hay mucho dolor, usamos menos Hz para control del dolor ( 10 a 30 Hz)"""
img_a132 = """Categoría | Patología | Mecanismo del campo magnético | Efecto terapéutico
Traumatología y ortopedia | Fracturas | Estimulación osteoblástica | Acelera formación de callo óseo
Traumatología y ortopedia | Pseudoartrosis | Aumento síntesis de colágeno y ADN | Favorece consolidación ósea
Traumatología y ortopedia | Retardo de consolidación | Activación metabólica celular | Disminuye tiempo de recuperación
Enfermedades óseas | Osteoporosis | Estimulación osteoblástica y calcio | Mejora densidad ósea
Enfermedades óseas | Enfermedad de Sudeck | Modulación vascular y celular | Disminuye dolor e inflamación
Musculoesquelético | Artrosis | Aumento colágeno y microcirculación | Mejora función articular
Musculoesquelético | Tendinitis | Estimulación reparación tisular | Disminuye dolor y acelera recuperación
Musculoesquelético | Lesión muscular | Activación fibroblastos | Favorece regeneración muscular
Tejido conectivo | Artritis reumatoide | Modulación inflamatoria | Disminuye inflamación
Tejido conectivo | Esclerodermia | Estimulación colágeno | Mejora elasticidad tisular
Vascular | Raynaud | Aumento microcirculación | Mejora perfusión
Vascular | Insuficiencia vascular periférica | Mejora flujo sanguíneo | Disminuye isquemia
Inflamatorio | Inflamación aguda | Modulación capilar | Disminuye edema
Inflamatorio | Inflamación crónica | Regulación celular | Reduce inflamación persistente
Cicatrización | Heridas | Estimulación fibroblastos | Acelera cicatrización
Cicatrización | Úlceras | Aumento oxigenación tisular | Mejora reparación
Sistema nervioso | Dolor crónico | Modulación neuronal | Efecto analgésico
Sistema nervioso | Neuralgias | Regulación impulso nervioso | Disminuye dolor
Metabólico | Hipoxia tisular | Aumento pO2 y metabolismo | Mejora función celular
Metabólico | Enfermedades crónicas | Aumento ATP | Optimiza metabolismo"""
plan = {
  "materia": "Tratamiento metabólico",
  "componente": "Campo Magnético",
  "fuentes": ["hojas/Campo Magnetico.xlsx"],
  "correcciones": {
    "Polariazante": "Polarizante",
    "para general proteinas": "para generar proteínas",
    "dexosirribonucleasa": "desoxirribonucleasa",
    "los acido nucleicos": "los ácidos nucleicos",
    "desoxirribunucleasa": "desoxirribonucleasa",
    "mebrana": "membrana",
    "condroblastros": "condroblastos",
    "Osteositos": "Osteocitos",
    "osteoclastros": "osteoclastos",
    "oxgeno": "oxígeno",
    "eslasticidad": "elasticidad",
    "excergonica": "exergónica",
    "Gibs": "Gibbs",
    "Qie": "Que",
    "al rededor": "alrededor",
    "Convalencia": "Convalecencia",
    "Ordenamiento der CMP": "Ordenamiento de CMP",
    "Manual(Aplicación": "Manual (Aplicación",
    "1Tesla": "1 Tesla",
    "Gaus": "Gauss",
    "intesnsidad": "intensidad",
    "Herz": "Hertz",
    "Sinosoidal": "Sinusoidal",
    "Enmermedades": "Enfermedades",
    "agrvaciónn": "agravación",
    "convalenciente": "convaleciente",
    "Mageneticos": "Magnéticos",
    "Macrogafos": "Macrófagos",
    "falicita": "facilita",
    "interluquinas": "interleuquinas",
    "periartitis": "periartritis",
    "Aumeta": "Aumenta",
    "sinstesis": "síntesis",
    "Seccion: diaria": "Sesión: diaria",
    "sonovial": "sinovial",
    "estiromilisima": "estromelisina",
    "Nevioso": "Nervioso"
  },
  "omitidos": [],
  "notas": [
    nota("Acciones del Campo Magnético Polarizante", ["A1:J59"]),
    nota("Indicaciones de los Campos Magnéticos Polarizantes", ["L1:R16"]),
    nota("Polaridad de los Campos Magnéticos", ["L18:R30"]),
    nota("Ordenamiento de CMP según Etiología", ["T1:U73"]),
    nota("Cómo formular campos magnéticos", ["W1:Y21"]),
    nota("Tips de Tratamiento Metabólico-Campos Magnéticos", ["L53:R136"]),
    nota("Tratamiento Metabólico", ["A61:J130"]),
  ],
  "tablas": [],
  "imagenes": [
    {"archivo": "imagenes/Campo Magnetico - L32.png", "titulo": "Tabla de Parámetros CMP – Magnetoterapia" + C, "celda": "L32", "descripcion": img_l32},
    {"archivo": "imagenes/Campo Magnetico - W23.jpg", "titulo": "Formulación de campos magnéticos" + C, "celda": "W23", "descripcion": img_w23},
    {"archivo": "imagenes/Campo Magnetico - A132.png", "titulo": "Categoría, patología, mecanismo del campo magnético y efecto terapéutico" + C, "celda": "A132", "descripcion": img_a132},
  ],
  "pdfs": [],
}
for n in plan["notas"]:
    assert (base / n["archivo"]).exists(), n["archivo"]
(base / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("ok")

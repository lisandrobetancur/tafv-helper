"""Genera notas/*.md y plan.json de «Solución GIK-Dieta Metabólica»."""
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
COMP = "Solución GIK-Dieta Metabólica"

# (encabezado, celdas, contenido markdown)
NOTAS = [
    # --- Bloque A1:J70 (Solucion Polarizante)
    ("Finalidad de la Solución Polarizante (GIK)", ["A2:J5"],
     "Aumentar la energía libre celular y corregir entropía celular.\n"
     "Cuando la célula se halla despolarizada durante el reposo celular, produciendo la polarización durante el reposo, corrigiendo la lesión."),
    ("La composición clásica de la solución re-polarizante incluye", ["A6:J8"],
     "DAD al 10% 500 ml\n\n1 ampolla de 20mEq de potasio\n\nInsulina cristalina 5 unidades"),
    ("La composición Corpas de la solución re-polarizante incluye", ["A9:J11"],
     "DAD al 5% 250 ml\n\n1 ampolla de 10mEq de potasio\n\nInsulina cristalina 2.5 unidades"),
    ("Aplicación de la Solución Polarizante (GIK)", ["A12:J17"],
     "Se pasa por vena periférica a una velocidad de goteo de 30 gotas por minuto, pero si el paciente siente dolor en el área de canalización al paso de la solución, este se debe al potasio y hay que disminuir la velocidad de goteo a 20 gotas por minuto."),
    ("Recomendación durante la aplicación de la Solución Polarizante (GIK)", ["A18:J22"],
     "La solución debe mezclarse cada 10 a 20 minutos, debido a que la insulina tiene mayor peso molecular y tiende a decantarse en el fondo del frasco, con el riesgo que pase primero al paciente, pudiendo producir cuadro de hipoglicemia"),
    ("Efectos de la Insulina en la Solución Polarizante (GIK)", ["A23:J29"],
     "(organiza la célula, aumenta su energía (ATP) y restaura su polaridad)\n\n"
     "1. Aumento de ATP (más energía disponible)\n\n"
     "2. Restauración del orden metabólico (↓ entropía)\n\n"
     "3. Activación de la bomba sodio–potasio (Na⁺/K⁺ ATPasa)\n\n"
     "4. Efecto eléctrico (antiarrítmico y estabilizador)\n\n"
     "5. Cambio del metabolismo hacia glucosa (más eficiente)\n\n"
     "6. Efecto citoprotector celular\n\n"
     "Disminuye el consumo de ácidos grasos (menos tóxicos para el miocardio isquémico)."),
    ("Efectos del Potasio en la Solución Polarizante (GIK)", ["A30:J37"],
     "El potasio “repolariza” la célula:\n"
     "devuelve estabilidad eléctrica, orden iónico y permite que la energía (ATP) se utilice correctamente.\n\n"
     "Mantenimiento de la osmolaridad celular y su interacción con la síntesis de energía libre por parte de la célula\n\n"
     "Aumenta el ATP\n\n"
     "Activa el primer paso del ciclo de Krebs\n\n"
     "Aumenta la síntesis y el depósito de glucógeno\n\n"
     "El potasio se requiere, para la completa oxidación de la glucosa\n\n"
     "Regula la respiración celular o cadena de transporte de electrones\n\n"
     "Interfiere en la agresión metabólica de las catecolaminas"),
    ("Dextrosa", ["A38:J43"],
     "La dextrosa “alimenta” la célula:\n"
     "aporta la energía (ATP) que permite recuperar la polaridad, el orden y la función celular.\n\n"
     "1. Fuente directa de energía celular (ATP)\n\n"
     "2. Aumento de la energía libre de Gibbs\n\n"
     "3. Favorece un metabolismo más eficiente (especialmente en hipoxia)\n\n"
     "4. Disminuye el metabolismo lipídico nocivo\n\n"
     "5. Sustrato para almacenamiento energético (glucógeno)\n\n"
     "6. Facilita la acción de la insulina y del potasio"),
    ("Acción general de la Solución GIK", ["A44:J54"],
     "“La solución polarizante convierte la célula enferma (desordenada y despolarizada) en una célula organizada, energizada y funcional.”\n\n"
     "1. Aumenta el potasio intracelular\n\n"
     "2. Incrementa la síntesis de glucógeno\n\n"
     "3. Incrementa la glicólisis anaeróbica\n\n"
     "4. Aumenta glicerol fosfato por esterificación de los ácidos grasos\n\n"
     "5. Disminuye los ácidos grasos libres\n\n"
     "6. Tiene efecto diurético por efecto hiperosmolar\n\n"
     "7. Aumenta el metabolismo oxidativo de la glucosa\n\n"
     "8. Disminuye la actividad lisosómica\n\n"
     "9. Incrementa la síntesis proteica\n\n"
     "10. Coadyuva a la replicación celular, acelerando los procesos de curación de heridas"),
    ("Indicaciones de la Solución Polarizante", ["A55:J61"],
     "(ayuda en dislipidemia)\n\n"
     "Enfermedad Coronaria o IAM\n\n"
     "ICC\n\n"
     "Apoyo en convalecencia y recuperación de pacientes debilitados\n\n"
     "Mejora la cicatrización y el callo de fractura\n\n"
     "Osteoporosis\n\n"
     "Estímulo de la inmunidad\n\n"
     "Cáncer"),
    ("Efectos Secundarios", ["A62:J66"],
     "Flebitis\n\nRubor\n\nEdema\n\nEquimosis\n\nInfección Local"),
    ("Contraindicaciones", ["A67:J70"],
     "Hiperkalemia\n\nHiperglucemia no controlada\n\nInsuficiencia renal severa\n\n"
     "Estados donde no se pueda manejar el equilibrio hidroelectrolítico"),
    # --- Bloque L1:R111 (Dieta Metabolica)
    ("Dieta de regulación metabólica", ["L2:R2"], "Baja en sodio y rica en potasio"),
    ("Recomendación de la dieta", ["L3:R5"],
     "Esta dieta elimina todos los alimentos que tienen 100 mg de sodio o más por gramo de alimento."),
    ("Cantidad de sodio en el día", ["L6:R6"], "1 gramo día (360 mg)"),
    ("Cantidad de potasio en el día", ["L7:R7"], "3600 a 4000 mg (3 a 4 gr)"),
    ("Efecto dieta en metabolismo celular", ["L8:R11"],
     "Estimula bomba sodio–potasio (Na⁺/K⁺ ATPasa)\n\nAumento de la producción de ATP\n\nAumenta el glucógeno\n\nHidrólisis de ATP"),
    ("Efectos termodinámicos", ["L12:R17"],
     "Eleva la Kalemia\n\nEstimula la Bomba de Na y K\n\nFavorece la Hidrólisis del ATP\n\nAumenta la Energía libre de G.\n\n"
     "Favorece a través de la E la síntesis de Macromoléculas y la estructuración del agua."),
    ("Leche y su derivados", ["L18:R24"],
     "2 vasos (240mL c/u) al día\n"
     "Puede cambiar 1 vaso de 240mL de leche por:\n"
     "½ vaso (120mL) de yogurt de fruta casero\n"
     "½ vaso (120mL) de kumis casero\n"
     "1 onza (30grs) de cuajada"),
    ("Evitar consumo de (leche y derivados)", ["L25:R30"],
     "Mayor cantidad de leche de la indicada\n"
     "Productos comerciales preparados con leche\n"
     "Chocolate. Leche condensada. Helados. Malteadas. Batidos de leche. Leche instantánea. Sorbetes. Queso salado. Queso para untar. Yogurt crema."),
    ("Carnes y Huevos", ["L31:R44"],
     "Está permitido el consumo de 4 onzas (120grs) de carne de res magra.\n"
     "Puede cambiar 120grs de carne de res por:\n"
     "120grs de pollo (1/2 pechuga)\n"
     "120grs de ternera\n"
     "120grs de lengua.\n"
     "120grs de pescado fresco ( pargo, trucha, róbalo, bagre, salmón, atún, lenguado, merluza)\n"
     "120grs de carne de cerdo magra\n"
     "Puede incluir 1 huevo diariamente o cambiarlo por dos yemas de huevo, sin clara."),
    ("Evite el consumo de (carnes y huevos)", ["L45:R52"],
     "Carnes gordas\nCarnes procesadas o de salsamentarias\nSesos\nRiñones\nHígado.\nCarne salada\n"
     "Concentrados de carne o gallina\nMariscos."),
    ("Leguminosas", ["L53:R55"],
     "Leguminosas enlatadas\n\nManí de Sal\n\nMantequilla de maní"),
    ("Frutas", ["L56:R56"], "5 porciones de frutas"),
    ("Evitar el consumo de (frutas)", ["L57:R62"],
     "Frutas enlatadas\nJugos en cajas\nMermelada comercial\nFrutas cristalizadas\nUvas pasas."),
    ("Hortalizas y Verduras", ["L63:R71"],
     "Evite el consumo de:\nHortalizas o verduras ensaladas\nEncurtidos\nSopas de verduras en sobre o instantánea\n"
     "Apio\nEspinaca\nRemolacha\nAceitunas\nAlcaparras."),
    ("Tubérculos y Plátanos", ["L72:R77"],
     "Evite el consumo de:\nPapas fritas de paquete\nPatacones y demás productos de paquete\n"
     "Papas precocidas o listas para freír\nPuré instantáneo de papa."),
    ("Evite el consumo de (cereales)", ["L78:R86"],
     "Cereales procesados e instantáneos\nCereales precocidos\nCereales para el desayuno\n"
     "Todos los productos de panadería\nBizcochería\nPastelería\nGalletería."),
    ("Grasas", ["L87:R92"],
     "Evite consumo de:\nMargarina vegetal con sal\nMantequilla\nGrasa animal, Tocino\nCrema de leche."),
    ("Condimentos", ["L93:R102"],
     "Ajo, Albahaca, Anís, Azafrán, Cardamomo, Cebolla, Cilantro, Clavo, Comino, Enebro, Eneldo, Cilantro, Clavo, Comino, Enebro, Eneldo, Limón, Naranja, Hinojo, Jengibre, Jugo de ajo, Laurel, Mejorana, Menta, Nuez moscada, Orégano\n"
     "Páprika, Pimentón, Perejil, Romero, Tomillo, Ají\n"
     "Vainilla, Vinagre."),
    ("Verduras con mayor contenido de sodio", ["L103:R104"],
     "Apio, Remolacha, Acelga, Espinaca, Zanahoria (moderado)"),
    ("Frutas y verduras ricas en potasio", ["L105:R111"],
     "✔️ Banano (plátano) ✔️ Aguacate ✔️ Papaya\n"
     "✔️ Melón ✔️ Naranja ✔️ Mango\n"
     "✔️ Lentejas ✔️ Frijoles ✔️ Garbanzos\n"
     "✔️ Almendras ✔️ Semillas\n"
     "Papa, Tomate, ✔️ Espinaca\n"
     "✔️ Acelga ✔️ Brócoli"),
    # --- Bloque T1:Y13
    ("Indicaciones más importantes de la dieta", ["T1:Y13"],
     "HTA y DM\n\nIAM\n\nCardiopatía Coronaria\n\nICC\n\nEnfermedades Cardiovasculares en General\n\n"
     "En patologías que se busca preservar función celular adecuada\n\nTrastornos del ritmo cardiaco\n\n"
     "Enfermedad Renal\n\nProcesos inflamatorios y degenerativos\n\nEstados de hipoxia o sufrimiento celular\n\n"
     "“El tratamiento metabólico está indicado en cualquier padecimiento donde exista desorden celular.”"),
]

notas_dir = BASE / "notas"
notas_dir.mkdir(exist_ok=True)
for viejo in notas_dir.glob("*.md"):
    viejo.unlink()
plan_notas = []
titulos = set()
for enc, celdas, md in NOTAS:
    col = celdas[0][0]
    general = {"A": " (Solución Polarizante)", "L": " (Dieta Metabólica)"}.get(col, "")
    if general and general.strip(" ()") in enc:   # el encabezado ya lo nombra (y el título no pasa de 120)
        general = ""
    titulo = f"{enc}{general} - {COMP}"
    assert titulo not in titulos, titulo
    titulos.add(titulo)
    assert len(titulo) <= 120, titulo
    archivo = f"notas/{titulo}.md"
    (BASE / archivo).write_text(md.strip() + "\n", encoding="utf-8")
    plan_notas.append({"titulo": titulo, "archivo": archivo, "celdas": celdas})

plan = {
    "materia": "Tratamiento metabólico",
    "componente": COMP,
    "fuentes": ["hojas/Solucion GIK-Dieta Metabolica.xlsx"],
    "correcciones": {
        "se haya despolarizada": "se halla despolarizada",
        "composición corpas": "composición Corpas",
        "osmoralidad": "osmolaridad",
        "interraccion": "interacción",
        "sinstesis": "síntesis",
        "cayo de fractura": "callo de fractura",
        "postasio": "potasio",
        "Sorbertes": "Sorbetes",
        "Aguacate✔️ Papaya": "Aguacate ✔️ Papaya",
        "Frijoles✔️ Garbanzos": "Frijoles ✔️ Garbanzos",
        "Almendras✔️ Semillas": "Almendras ✔️ Semillas",
        "Acelga✔️ Brócoli": "Acelga ✔️ Brócoli",
    },
    "omitidos": [],
    "notas": plan_notas,
    "tablas": [],
    "imagenes": [],
    "pdfs": [],
}
(BASE / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(len(plan_notas), "notas")

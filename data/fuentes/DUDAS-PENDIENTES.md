# Dudas pendientes de la carga (2026-10-16)

Lo que no se cambió por no ser seguro, y algunas correcciones para que confirmes. Cada sección viene del preguntas.md de su componente.

---

## acupuntura/acupuntura


## Estructura
1. **Bloque B136:R159 (TABLA PEQUEÑA, 22 registros) → tabla Markdown en la nota «TÉCNICA ZANG-FU - Acupuntura»,
   no tabla de Excel.** Motivo, según las reglas: no es una base de registros como el vademécum. Es una matriz
   de consulta (función × meridiano) dividida en secciones (1 Extraordinarios/Emperador, Shu antiguos/Ministros,
   2 Mu Zi, 3 Shu post/Mu, 4 Yuan/Luo, 5 Xi/Hui). Tiene dos filas de encabezados (BRAZO/PIERNA en la 136;
   FUNCIÓN, C, PC, P… en la 137), una fila de encabezados repetida a mitad (146: Yin, C, PC…, Yang, IG…),
   celdas combinadas horizontales (F159:K159, M159:R159) y ninguna columna nombra cada fila como un registro.
   Además es un recuadro más del mural, junto a LUO, YUAN, MU y Técnica de planos.
   Detalles de cómo quedó:
   - La columna B («TECNICA ZANG-FU», escrita en vertical sobre toda la tabla) es el encabezado: va en el título
     de la nota, no como columna.
   - La fila 136 es el encabezado Markdown y la 137 la primera fila de la tabla.
   - Las celdas sueltas H140 (P7), K141 (R6), O142 (ID3), P143 (V62) y Q144 (VB41), que el inspector separó como
     bloques aparte, quedaron en su fila y su columna dentro de la tabla.
   - Las celdas combinadas en vertical (C138:C145, C146:C151, C152:C153…) tienen el texto solo en la primera
     fila; no se rellenaron.
   - C138 «1 / EXTRAORDINARIOS / EMPERADOR», C146 «SHU ANTIG / MINISTROS» y C152 «2 / MU ZI» tienen saltos de
     línea; una celda de tabla Markdown no los admite, así que se unieron con un espacio
     («1 EXTRAORDINARIOS EMPERADOR»). ¿Está bien así?
2. «TÉCNICA DE PLANOS» (B186 + B188:O201) es otra matriz del mismo tipo: va también como tabla Markdown en su
   nota. B186 es el título; las celdas H191:I191 (VC17, VC23) quedaron en la fila 3 «nudo».
3. «LUO» (C161:F183): las celdas combinadas en vertical (p. ej. IG / P7 / «Palmas y muñecas calientes» en las
   filas 163–164) tienen el texto solo en la primera fila; no se repitió en la segunda. ¿Se rellenan?
4. «YUAN», «MU», «HUI», «XI» y «HE» no tienen fila de encabezados en la hoja: van como tablas de dos columnas con
   el encabezado vacío (como en Oxigenoterapia). En «YUAN», la frase combinada G162 va como párrafo encima.
   «XI» (B236:C251) es un recuadro aparte debajo de «HUI» (tiene su propio encabezado de color).
5. Columna F (F222:I261): «8 tecnicas BA FENG» y, debajo, cuatro recuadros con su propio color y encabezado
   («Dolor de vísceras», «Dolor de órganos», «Enfermedad interna», «Técnica de LUO») → una nota cada uno.
   - En «8 técnicas BA FENG», F224 «Purificación calor: IG4-IG11- VG14» no tiene número: quedó como renglón
     dentro del punto 1. Los renglones de F231 quedaron dentro del punto 8.
   - En «Enfermedad interna», F247 «Técnica para órganos Zang-fu» quedó como primer renglón (no como subtítulo).
6. «PATOGENOS EXTERNOS» (J222:M278), por decisión de la usuaria: una nota por recuadro (grupo de color), con
   «(Patógenos externos)» en el título. Los grupos sin encabezado propio toman su primer renglón como título
   (p. ej. «Frío ataca el Tai Yang:La capa Yin le da e. para liberar el frío (Patógenos externos)»); se quitó
   solo el «:» final. «FRIO», «VIENTO», «HUMEDAD» y «FLEMA» se escribieron «Frío», «Viento», «Humedad» y
   «Flema». FLEMA (J255) está dentro del grupo de color de HUMEDAD, pero es un encabezado del mismo estilo:
   quedó como nota propia («Flema (Patógenos externos)», J255:M257). ¿O va dentro de «Humedad»?
7. La parte de arriba de la hoja (filas 1–135) no tiene texto en celdas: solo las imágenes A1, G2, A48, H48 y
   B87. M46 tiene solo espacios: va en `omitidos`.

## Textos de la hoja que se dejaron como están
- F231, J235, J274, J276: el carácter «è» (flecha de la fuente Wingdings perdida) se cambió por «→»
  (declarado en `correcciones`).
- J223 «Frío ataca el Tai Yang:La capa Yin le da e. para liberar el frío»: «le da e.» parece cortado.
- J224 «P7 Luo-», J225 «IG4 Yuan-», J241 «B10: mar de la sangre XI de bazo-» y B245 «Dolor, palpitaciones,»
  terminan en guion o coma; puede que les falte texto.
- J250 «1.VG16+ VB20+ V12» y J251 «1.V10-Tr17- VB31»: los dos tienen el número 1 en la hoja.
- M159 «.VC12 HUI DE VISCERAS» (punto inicial), B248 «sangrado genital .cistitis», F243 «por que es
  plenitud», F226 «Vomificación», E228 «lumbar-aX dermatológica», «Roe»: tal cual.

## Ortografía
- Correcciones con cambio de letras: «DEFICIENCIE TONIFICAR» → «DEFICIENCIA TONIFICAR» (D152) y «Cistitis
  aguada» → «Cistitis aguda» (B243), y «è» → «→».
- Solo tildes: ORGANOS, VISCERAS, FRIO/frio, rio, TECNICA, tecnicas, PATOGENOS, Inflamacion, Vertigo, Sincope,
  medulas, SEPARACION, REUNION, TELURICA, ACELERACION, CIRCULACION, TORACICA, ENERGIAS; J247 «Sí frio» → «Si
  frío».

## Imágenes (dudas de lectura: se dejó lo transcrito, sin adivinar)
- **«IG»**: en A1, G2, A48 y B87 la sigla IG está escrita de forma que parece «16». Se transcribió «IG» (en A1
  «Pulmón / IG», en el ciclo del metal). ¿Correcto?
- **Ciclo generación (A1)**: el título de la tercera lista parece escrito «Contadominancia»; se transcribió
  «Contradominancia». Del dibujo se transcribieron las flechas del círculo exterior (Madera → Fuego → Tierra →
  Metal → Agua → Madera); las flechas de la estrella azul y las rayadas rosadas del centro no se describieron
  (coinciden con las listas «Ciclo Dominancia» y «Contradominancia» de abajo). ¿Está bien así?
- **4 niveles energéticos (G2)**: el primer renglón se lee «Wi - Energía de defensa…» y el rótulo lateral de la
  tabla, «Wei»; se transcribió cada uno como se ve. «Show (Mano)» y «Zu (Pie)» están tal cual (¿«Shou»?). La
  columna derecha (el recorrido del meridiano) se transcribió como «↓ 1 ID cabeza ↓ V 67», «↑ 11 P tórax B1»,
  etc. Los rótulos «Qi» y «Jing» abarcan tres filas cada uno; se escribieron solo en la primera, sin rellenar.
- **Técnicas (H48)**: punto 4 «Nudos de nudos yang ExH9-VB8-E8»: no se lee con seguridad si dice «ExH9» o
  «ExHN9» (en la hoja, Técnica de planos dice «EXHN9»). Punto 5 «(Crisis HTA, ojos rojos, de resto no)» es la
  lectura más probable; confirme. En «MU (uso en exceso de yin vísceras)», el «de» podría ser «da».
- **Puntos de los 12 meridianos (B87)**: la imagen no tiene título; se le puso uno descriptivo. Se transcribió
  todo su texto: yin/yang, la sigla de cada meridiano, los puntos de arriba abajo, «Inicio/Final Mano/Pie» y la
  leyenda (Madera, Fuego, Tierra, Agua, Metal, Zi, Luo, Tonifica, Sedo, Yuan, (-) embarazo, Emocional). Los
  rótulos pequeños de V41–V66 se leen con dificultad, pero siguen la secuencia. Junto a E18 dice «Gran Luo E»
  (lectura probable). **Los símbolos de cada punto** (figura del elemento, Zi, Luo, tonifica, seda, yuan,
  embarazo, emocional) son dibujos, no texto, y no se describen (decisión de la usuaria).
- **Meridianos anteriores, posteriores y mediales (B269)**: el rótulo azul de la figura de la izquierda está
  cortado por el borde y solo se ve «ulmón» (¿Pulmón?); se transcribió «ulmón». En «ANTERIORES» no aparece el
  rótulo Tai yin. El sello de abajo a la derecha tiene un texto pequeño ilegible («… AÑOS»): no se transcribió.
- **Puntos MU (yin) (A286)**: H14 se lee «Hace articular Qi de Hígado» (¿«circular»?): se dejó «articular». En
  VC4, «Puerta del Brillo» no se lee con seguridad.
- **Shu de espalda (H291)**: la última palabra de «Nota: Escojo MU por excesos y acompaña Shu por deficiencia
  y …» no se lee con seguridad (¿«visceral»?, ¿«vísceras»?): no se transcribió. ¿Qué dice? En la tabla, la
  casilla VG de V50 y la «Función» de V46 y V48 están vacías en la imagen.
- Las tablas de A48, A286 y H291 quedan solo en la descripción de su imagen (sin tabla de Excel, decisión
  de la usuaria).

---

## acupuntura/sindromes


## Estructura
1. La hoja entera (A1:F54) es una base de registros: una fila de encabezados (Sindromes, Causa, Pulso, Lengua,
   Sintomas, Claves) y 53 síndromes, uno por fila. Por decisión de la usuaria se carga una copia con la
   ortografía corregida, `tablas/Síndromes.xlsx` (la hoja de `hojas/` no se tocó), como tabla de Excel
   «Síndromes», con la columna «Síndromes» como título. No tiene comentarios ni imágenes.
2. Filas 44 y 45 («Triplerecalentador superior» / «Triplerecalenttador medio»): en la columna Pulso dicen
   «gravedad moderada» y «enfermedad peligrosa», y Lengua y Claves están vacías. ¿Están bien así o el texto está
   en otra columna? Se dejaron como están.
3. F48 termina en «desordenes +F52menstruales y complicaciones postparto»: «+F52» parece un resto de fórmula
   pegado por error: se quitó (declarado en `correcciones`: «+F52menstruales» → «menstruales»).
4. C34 (Pulso de «Calor lleno en intestino delgado») dice «rebosante, palido». Se dejó tal cual.
5. Celdas vacías (no se rellenaron): F4 (Claves de «Sequedad de pulmon») y D44, F44, D45, F45.

## Ortografía (corregida en la copia)
- Se agregaron tildes (pulmón, estómago, corazón, hígado, riñón, débil, crónica, rápido…, también en los
  encabezados «Síndromes» y «Síntomas»).
- 99 cambios de letras, palabras pegadas o restos técnicos, declarados en `correcciones` del plan (p. ej.
  «estomaago» → «estómago», «Triplerecalentador» → «Triple recalentador», «vesicular biliar» → «vesícula
  biliar», «ceaflea» → «cefalea», «aveces» → «a veces», «maniacoy» → «maníaco y», «+F52menstruales» →
  «menstruales», «estremidades» → «extremidades»).
- Lecturas que conviene confirmar: «imnombio» (E17) → «insomnio»; «sangreso de las encias» (E15) → «sangrado
  de las encías»; «volund de quedarse acostado» (E19) → «voluntad»; «o roj en los laterales» (D47) → «roja»;
  «mieso» (B41) → «miedo»; «nica» (E53) → «nuca»; «flama» (B48) y «flam» (F8) → «flema».
- No se cambiaron (no se sabe con seguridad qué dicen o no son ortografía): C9 «Respiso, suave o
  resbaladizo»; E50 «epicondrio» (¿hipocondrio? ¿epigastrio?); E41 «audicion disminuido» (concordancia);
  E43 «fiebre alto»; «crohn» en minúscula; B8 termina en «baja de» (¿cortado?).

---

## farmacologia-vegetal/vademecum


## Tabla «Farmacología vegetal» (A2:K114)
1. La tabla se extrajo a `tablas/Farmacología vegetal.xlsx` (A1:K114, mismas coordenadas que la hoja) en vez de
   cargar la hoja completa: debajo de la base (filas 121–208) hay recuadros que, con la hoja completa, habrían
   entrado como registros. Encabezados en la fila 3; 111 plantas; columna título «Nombre».
2. La fila 2 («FITOTERAPEUTICOS FARMACOLOGIA VEGETAL», A2:J2) es un título sobre los encabezados: va en
   `omitidos` (decidido).
3. La columna K no tiene encabezado y solo tiene K9 (fila de Malva): queda como «Columna K» (decidido).
4. Se corrigió la ortografía en la copia de la tabla (la hoja de `hojas/` no se tocó): tildes en todas las columnas
   salvo los nombres científicos en latín (columna D), y los cambios de letras declarados en `correcciones`.
   En la columna D solo se corrigieron letras claras: Eucalytus → Eucalyptus, Sacharomyces → Saccharomyces,
   Cassi pulchra → Cassia pulchra, Acanthaceace → Acanthaceae, mollisima → mollissima, Apium graveolen →
   graveolens, comunis → communis, Cavendshia → Cavendishia, americanun → americanum, Soanum → Solanum,
   Paulinia yoco → Paullinia yoco, Cinnamomun → Cinnamomum.
5. Las celdas combinadas hacia abajo («Sistema», y «Formula Magistral» en J4:J5, J9:J11, J112:J114…) la app
   las repite en cada fila del rango. Las celdas vacías quedan vacías.

## Dudas de la tabla que NO se corrigieron (no son solo ortografía)
6. D36 (Nombre científico de Mejorana) dice «Piel»: en el original era una fórmula y ese es su valor visible.
   Parece un error de la fórmula. ¿Cuál es el nombre científico?
7. D76 «Urticaria urens» (Ortiga blanca): ¿es «Urtica urens»? D65 «Myrciantes leucoxila» (Arrayán): ¿«Myrcianthes
   leucoxyla»?
8. F16 «Expectotal y mucolitico»: ¿«Expectorante»? · F91 «Inmunolador»: ¿«Inmunomodulador»? · F71 «Dermatitis
   atipica»: ¿«atípica» o «atópica»? (se dejó «atipica») · F13 «espasmolítico bronquia»: ¿«bronquial»? ·
   J85 «artritos»: ¿«artritis»?
9. Palabras repetidas o sueltas: J19 «de la la orofaringe», H45 «1 cuchara en en vaso de agua», E99 «semilla d
   persea» y «1 capsula 12 veces al dia (am)», H105 «30 gotas veces al dia» (falta el número). Se dejaron tal cual.

## Comentarios de celda
10. Los 21 comentarios están dentro de la tabla y van en «Comentarios - Farmacología vegetal», en el orden de la
    hoja: «**<Nombre> · <columna>** (celda X):» y debajo «> Comentario de <Autor>: …» (cada renglón con «>»).
    Los nombres de planta y columna son los ya corregidos de la tabla (Alegría del Campo, Arrayán, Guaraná,
    Acción…). Los comentarios de la celda «Sistema» llevan el nombre de la planta de esa fila (decidido).
11. A105 y F107 tienen como autor «Objetivos terapéuticos» e «Indicaciones»: se escribieron tal cual.
12. Se unieron con un espacio los saltos de línea que solo cortaban una frase (C46, A51, C66, E66, F109).

## Recuadros
13. Los seis recuadros bajo «Otros medicamentos en homeopatia» (A146) son seis notas con el encabezado general
    entre paréntesis, p. ej. «Tos seca (Otros medicamentos en homeopatía) - Vademecum».
14. «Dosis general» (C135:D138): la tercera columna («antes de cada comida») no tiene encabezado; queda vacío.
15. Sin cambiar (decidido): «Trumex» (A150), «Antimonio Tartaricum» (A180), «Ácido Maleico» (B208).

---

## homeopatia/vademecum-homeopatia


## Tabla «Estudio homeopatia» (copia corregida `tablas/Estudio homeopatia.xlsx`, A1:R44, 43 registros, columna título «Medicamento»)

Ya decidido: ortografía corregida en la copia (cada cambio de letras está en `correcciones`), R33 «#REF!» vacía
(en `omitidos`), Q32 tal cual, columnas Q y R con el nombre de la app. Como R33 queda vacía y era el único
dato de la columna R, la app ya no muestra «Columna R»; queda «Columna Q».

Correcciones que conviene que revises (son las menos obvias):
1. N2 (Sulfur): «filoso arapiento» → «filósofo harapiento».
2. N19 (Aurum): «fracas» → «fracaso»; «induracin» → «induración».
3. N20 (Hepar sulfur): «supuracion rapida y doloros» → «supuración rápida y dolorosa»; «queso viajo» → «queso viejo».
4. N34 (Carbo vegetabilis): «necesidad de ire» → «necesidad de aire».
5. N38 (Cantharis): «tenesmo vesicual imperioroy» → «tenesmo vesical imperioso y»; «a la plicaciones frial» → «a las aplicaciones frías».
6. P29 (Arnica): «Arnicadolor» → «Arnica dolor».
7. M27 (Graphites): «lilamento de moco» → «filamento de moco».
8. A6, A13, B36 (nombres latinos): «Calcium fluorathum» → «fluoratum», «Chamomilia» → «Chamomilla», «Berberis vulgares» → «vulgaris».
9. C40 / G40 (Bryonia): «curcubitacinos/Curcubitacinas» → «cucurbitacinos/Cucurbitacinas» (solo se ordenaron las letras; «cucurbitacinos» se dejó con su terminación).
10. N44 (Cannabis sativa): «risa totna» → «risa tonta».

No se corrigieron, porque no está claro qué decían (¿cómo deben quedar?):
11. N18 (Pulsatilla): «retraso i supresión de la menstruación» (¿«y» u «o»?).
12. N19 (Aurum): «hipervalia (perfección)»; «afecciones sifilicas» (¿«sifilíticas»?).
13. N23 (Syphilinum): «dolores osteopepticos» (¿«osteócopos»?).
14. N24 (Tuberculinum): «alterciones de afecciones respiratorias con problemas cutáneos» (¿«alternancia»?).
15. N29 (Arnica): «mejora al aestirara o cambias de postura».
16. N43 (Cannabis indica): «hilaridad incontrolable y sisa convulsiva (risa)».
17. K39 (Sarsaparrilla): «ruido en los oídos como panas» (¿«campanas»?) y «poliguria» (¿«poliuria»?).
18. H31 «varioleciformes», O31 «violeciformes», L31 «varioliformis» (Antimonium tart): tres formas distintas.
19. P31: «la lengua el limpia»; N15 (Natrium muriaticum): «debilidad debilidad» (palabra repetida).
20. Paréntesis sin cerrar: K2 (Sulfur) «…salir de la cama)» tiene un paréntesis de cierre sin apertura.

Otros avisos:
21. Q32 (Spongia) repite el texto de Q33 (Antimonium crudum) porque en el original Q32 es la fórmula `=Q33`; se cargó así, como decidiste.
22. F2 y F3 están guardadas como fechas con formato d-m; la app muestra «6-7» y «4-7», como en Excel.
23. P38 está dentro de la tabla: es el «Artículo» de la fila 38 (Cantharis Vesicante).
24. Saltos de línea que solo cortaban una frase (p. ej. H22, H35, I35, J35, K35, L35, I28, K44) se unieron con un espacio; los renglones propios se mantienen.

## Hoja «Formulación» (dos recuadros → dos notas con tabla Markdown)

25. Recuadro «Formulación» (B2:D8): la primera fila «Dilución | Potencia | Escala» no está en negrita; se cargó como fila de datos con encabezado vacío. La fila «Observaciones pronósticas de Kent» no tiene nada a la derecha.
26. Recuadro «Potencia» (B12:E15): «Depende de la agravación homeopática» (E12) está en la fila de encabezados, sin negrita y sin datos debajo; se dejó como cuarta columna del encabezado.

---

## oxigenoterapia/hbo


## Estructura
1. «Pasos en Camara Monoplaza» (D2:E6) es un recuadro aparte, junto a la tabla de «HBO PROTOCOLO CORPAS» (cuyo
   encabezado A1:C1 solo cubre las columnas A–C). Siguiendo «una nota por recuadro», se separó en la nota
   «Pasos en Cámara Monoplaza - HBO». ¿Está bien, o va como sección dentro de «HBO PROTOCOLO CORPAS - HBO»?
2. En «Otras Indicaciones», la celda G32 («Doxorrubicina (Adriamicina) 50 mg / Cisplatino 50 mg / Bleomicina
   Mafenida (Sulfamylon)») se cargó como un renglón más de la lista (con sus saltos de línea), justo después
   de «Cáncer (No durante quimioterapia)». No se interpretó su relación con ese renglón.
3. «Contraindicaciones» solo tiene el subencabezado «Absolutas»; no hay «Relativas» en la hoja.

## Ortografía
- G30 «sulfato de hidrigeno»: se corrigió «hidrigeno» → «hidrógeno», pero se dejó «sulfato» tal cual.

## Imágenes
- «Barotrauma de oído» (AB1): el rótulo inferior del primer dibujo está cortado por el borde; solo se ve
  «Trompa» (a medias). Se transcribió «Trompa». ¿Se completa?
- «Barotrauma pulmonar» (AB26) y «Barotrauma de senos paranasales» (AB53): tienen un reflejo espejado del
  dibujo/radiografía debajo; no se transcribió el texto invertido del reflejo («Pneumothorax / Mediastinal
  Emphysema» repetidos). En la radiografía de AB53 hay una inscripción manuscrita (parece una fecha, «2?-7-98»)
  que no se lee con seguridad: no se transcribió.
- «Toxicidad sobre el Sistema Nervioso Central (Paul Bert)» (AK1): del recuadro «Tiempo de latencia» salen dos
  flechas (una al recuadro de síntomas y otra hacia abajo, que termina cerca de «Convulsiones tónico clónicas
  generalizadas», sin tocarlo); además hay una flecha ↓ de síntomas a convulsiones. Se transcribió como
  «→ Náuseas… / ↓ / → Convulsiones…». ¿Está bien así?

---

## oxigenoterapia/oxivenacion


Sin preguntas.

---

## oxigenoterapia/ozonoterapia


1. **Títulos repetidos, distinguidos con un paréntesis.** Cinco encabezados aparecen en dos recuadros. Para que no se confundan les agregué entre paréntesis lo que contiene cada recuadro:
   - «Insuflación Rectal»: L49 (técnica + indicaciones) → «(indicaciones)»; Q14 (tabla de sesiones) → «(técnica)».
   - «Insuflación Vaginal»: L82 (técnica + indicaciones) → «(indicaciones)»; Q31 (solo técnica) → «(técnica)».
   - «Autohemoterapia menor»: L97 (técnica + indicaciones) → «(indicaciones)»; U1 (tabla de sesiones) → «(técnica)».
   - «Aplicación en Bolsa»: L132 (lista de indicaciones) → «(indicaciones)»; Q40 (exposición, frecuencia, concentraciones) → «(técnica)».
   - «Inyección subcutánea»: L149 (indicaciones) → «(indicaciones)»; Q47 (concentración, volumen, tabla) → «(técnica)».
   ¿Te sirven esos nombres? Las tablas de sesiones (Q14 y U1) podrían llamarse de otra forma, p. ej. «(tabla)».
2. **«Ozono intrarrectal en niños» (Q22:S29):** no tiene fila de encabezados. La puse como tabla Markdown cuya primera fila es «Concentración | 10μg/mL-35 μg/mL», seguida de «Volumen» con su celda vacía y las edades. ¿Te sirve así?
3. **Autor de los comentarios:** en el Excel figura «Luis fernando Lenis»; lo escribí «Luis Fernando Lenis», como pediste.

---

## psicoterapia/macerados-florales


## Estructura
1. La base de registros va de A3 (encabezados) a F46 (43 flores). No se cargó la hoja entera como tabla porque
   debajo (filas 47–112) hay recuadros que se habrían convertido en filas de la tabla: se extrajo A3:F46 a
   `tablas/Macerados Florales.xlsx` (columna título «Flor de Bach», etiqueta «Flores de Bach»).
2. Filas 1–2 (encima de los encabezados): A1:D2 «Flores de Bach» (título) y E1 con el enlace
   https://somapsiconatur.com/flores-de-bach/. Como la tabla no tiene dónde guardar un título ni un enlace, se
   cargaron como la nota «Flores de Bach - Macerados Florales» (contenido: el enlace). ¿Está bien, o prefieres
   omitirlas (el título ya es la etiqueta de la tabla)?
3. Filas 47–55, dentro del bloque de la tabla pero sin forma de registro: «FÓRMULA DE EXAMEN» (A47:B47) y el
   recuadro A48:D55 van como notas. El recuadro A48 no tiene celda de encabezado aparte; se usó su primer renglón
   («¿Qué es el «Rescue Remedy» (Remedio de Rescate)?») como título de la nota.
4. Grupo «Rescue Remedy» (filas 42–46): las celdas C42:D42 … C46:D46 están combinadas, así que la app repite el
   texto en «Nombre común» y en «Indicacion»; E42:E46 y F42:F46 están combinadas hacia abajo y la app repite su
   texto en las 5 filas (igual que el «Grupo emocional»). Es el comportamiento normal de la app con celdas
   combinadas; no se tocó la fuente.
5. Comentarios: los 7 comentarios están en los recuadros de «Esencias para el Duelo» (A61–A80), ninguno dentro
   de la tabla; por eso no hay nota «Comentarios - Macerados Florales». Van en la nota del Duelo, debajo de cada
   esencia.
6. D28 (Vine): «Dominio y autoritarismo. ¨Para las personas excesivamente entusiastas que intentan imponer sus
   ideales» repite la frase de Vervain (D27) y empieza con «¨». Se dejó tal cual: ¿es un error de copiado?
7. A25 (Psicorigidez): la frase del grupo «Cuando la mente se vuelve rígida, el cuerpo también se contrae.”»
   no tiene comilla de apertura. A42 (Rescue Remedy): el paréntesis «(estrés agudo (un accidente, …).» no se
   cierra. Se dejaron como están.

## Ortografía en la tabla
Se corrigió en la copia `tablas/Macerados Florales.xlsx` (A3:F46 extraído con `extraer_rango.py` y corregido
con `.trabajo/corregir_tabla.py`): tildes (incluidos los encabezados «Indicación» y «Característico»), letras
cambiadas («facilamente», «aprece», «Par las», «persons»), palabras pegadas («pánicoTerror», «rumbo.Para»,
«pasado.Nostalgico», «frecuente.En», «trauma.Hay», «otros.Idealista», «desánimo.Para», «anticipado.Para»),
«Por que / por que» → «Porque / porque» (D7, D10), dobles espacios y espacios al inicio o al final de las
celdas (incluidos los espacios iniciales de F34 y el salto de línea inicial de Vervain «Tipo de Persona»).
Cada cambio de letras está en `correcciones`.

Dudas que se dejaron tal cual:
- F5 (Aspen) «experiencias orínicas intensas»: ¿«oníricas»?
- D12 (Wild Oat) «Para las personas desaminadas»: ¿«desanimadas»?
- C34 (Hornbeam) «Hojarazo»: ¿«Hojarasco»/«Carpe»? No se cambió el nombre común.
- D28 (Vine): ver la pregunta 6 (frase repetida de Vervain y «¨»).
- Comillas y paréntesis sin cerrar: ver la pregunta 7.
- E16 (White Chestnut) «Insomnio por pensamientos Dificultad para concentrarse»: falta una coma (puntuación,
  no se tocó).

## PDF
- «MATERIAL MACERADOS FLORALES.pdf» se carga tal cual con el título de su primera página: «Material de Estudio:
  Esencias Florales de Bach».

---

## tratamiento-metabolico/campo-magnetico


## Estructura (aplicadas las decisiones de la usuaria)
1. **Una nota por recuadro con el encabezado general entre paréntesis.** Las 14 fichas de T1:U73 son 14 notas
   «<ficha> (Ordenamiento de CMP según Etiología) - Campo Magnético», cada una con su tabla Markdown de 2
   columnas sin fila de encabezados. También se separaron los rótulos con recuadro de color propio: los 13
   numerales de «Acciones del Campo Magnético Polarizante», los 8 rótulos de «Cómo formular campos magnéticos»,
   los 27 rótulos de «Tips de Tratamiento Metabólico-Campos Magnéticos» y los 4 numerales más «Sistema
   Celular» e «Inmunidad Humoral» de «Tratamiento Metabólico». En total 70 notas. En los títulos se quitaron
   los dos puntos finales de los rótulos («5. Frecuencia:» → «5. Frecuencia»).
   Dentro de «4. Acciones sobre el crecimiento», Piel / Hueso / Articular / Sistema Nervioso / Sistema
   Circulatorio están dentro del mismo recuadro (la celda A91:D130 los abarca), así que quedan como `###`.
2. **Subencabezado A2 «Acciones Biologicas del Campo Magnetico»** (banda bajo A1 que cubre los 13 numerales):
   en el título de esas notas va entre paréntesis el encabezado general A1 «Acciones del Campo Magnético
   Polarizante». No caben los dos (límite de 120 caracteres en el título), así que A2 quedó en `omitidos`.
   ¿Lo pongo en lugar de A1, o como primera línea de cada una de esas 13 notas?
3. «Indicaciones de los Campos Magnéticos Polarizantes» y «Polaridad de los Campos Magnéticos» son tablas
   (un solo recuadro cada una) y quedan como una nota con tabla Markdown. Los rótulos combinados hacia abajo
   (Categoría, Polo, y en «Onda Alterna» las celdas de Acciones y Efectos que abarcan 4 filas) van solo en la
   primera fila del grupo; las demás quedan vacías (no se rellenó). En las celdas de tabla con salto de línea
   se usó « / » (como hace la app al pegar desde Excel), salvo «Polo + (Norte)» y «Polo - (Sur)», donde se unió
   con un espacio.
4. **Comentarios de la tabla de Polaridad:** van debajo de la tabla con su fila: «> Comentario de Luis Fernando
   Lenis (fila «Polo + (Norte)»): …» (celda L20) y «(fila «Onda Alterna»)» (celda L27).
5. Los comentarios de W13 («5. Frecuencia») y L58 («Frecuencia de CMP») están en la celda del rótulo, así que
   van al inicio de su nota.
6. Paramagnéticas / Diamagnéticas / Ferromagnéticas: el rótulo tiene dos renglones; el primero es el título y el
   paréntesis con la lista de sustancias es el primer párrafo de la nota. En L95 el salto entre «oxigeno» y
   «ferritina» (sin coma) se unió con un espacio.
7. «¿?»: los rótulos «Que hace el CMP», «Cual es el efecto de CMP en el oxigeno» y «En que enfermedades no CMP»
   no tienen ningún signo de interrogación; solo se les pusieron tildes (no se agregaron «¿?»).

## Textos incompletos o dudosos (se dejaron como están)
- A54/E54 «Se hidroliza ATP + H2=2 = Forma ADP…»: «H2=2» parece «H2O», pero no se cambió.
- X13 «… Baja Intensidad: 1 a 0h»: no se entiende «1 a 0h»; quedó tal cual.
- Paréntesis sin cerrar: E41 «Disminuye el potencial mitotico (Funcionan alterando … (apoptosis)»;
  E89 «Procesos virales anti-inflamatorios (Hepatitis, glomerulonefrosis aguda, EPI Cronica».
  Paréntesis de cierre sobrante: E117 «Isquemia (ACV) infarto, Herida quirurgica)»; X2 «… trastornos metabólicos.)».
- E79 «Disminucion de las fases mitosicas»: se dejó «mitósicas» (¿«mitóticas»?).
- A41 «Acción antineoplásica coayudante» se dejó así (en E41 dice «COADYUVANTE»).

## Ortografía (declaradas en `correcciones`)
- Se corrigieron «Gaus» → «Gauss» y «Herz/herz» → «Hertz» (también en el comentario de W13: «200 gaus, 60 hertz»).
  (Confirmado por la usuaria.)
- Cambios menos obvios: «para general proteinas» → «para generar proteínas»; «Seccion: diaria» → «Sesión:
  diaria»; «interluquinas» → «interleuquinas»; «estiromilisima» → «estromelisina»; «los acido nucleicos» →
  «los ácidos nucleicos». Revisa si alguno no corresponde.
- Se dejaron «Antinflamatorio» (variante válida), «Negativo/ Sur», «Frecuencias alta», «Evento fisiopatológicos»,
  «Deficiencia de mecanismo locales», «1 horas» (redacción/concordancia, no ortografía).

## Imágenes
- «Tabla de Parámetros CMP – Magnetoterapia» (L32) y «Categoría, patología, mecanismo del campo magnético y
  efecto terapéutico» (A132) son tablas; por decisión de la usuaria quedan solo como imágenes, sin Excel. (A132 no tiene título
  propio: el título de la imagen se tomó de sus encabezados de columna.)
- La tabla L32 repite casi todas las fichas de T1:U73, pero con diferencias (p. ej. Cáncer «Siempre norte» y
  «Segun Criterio Medico» frente a «Norte / 180 horas» en la ficha; «Post Operatorio Ortopedico» tiene tiempos
  «Segun Criterio Medico»). Se cargaron las dos tal cual.
- En la imagen W23 se lee «Van de 1 a 100 / ese utiliza 50 Hz» (¿«se utiliza»?): se transcribió «ese» como se ve.
- Las transcripciones de las imágenes son literales (sin tildes agregadas: «Segun Criterio Medico», «10 dias», «Maximo»).

---

## tratamiento-metabolico/solucion-gik-dieta-metabolica


1. **Encabezado general que ya está en el título.** Seis encabezados del bloque «Solucion Polarizante» ya contienen «Solución Polarizante» (Finalidad…, Aplicación…, Recomendación durante la aplicación…, Efectos de la Insulina…, Efectos del Potasio…, Indicaciones de la Solución Polarizante). A esos no les agregué «(Solución Polarizante)»: sería repetirlo, y en «Recomendación durante la aplicación…» el título pasaba de 120 caracteres y la app lo cortaba. ¿Te parece bien?
2. **Espacio tras paréntesis:** «( pargo, trucha, …» en Carnes y Huevos (O31) quedó como en la fuente.
3. **Cifras de la dieta:** «1 gramo dia (360 mg)» de sodio (O6) se dejó tal cual; revisa si el dato es correcto en tu material.

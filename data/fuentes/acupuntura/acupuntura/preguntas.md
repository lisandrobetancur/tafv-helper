# Preguntas — Acupuntura › Acupuntura

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

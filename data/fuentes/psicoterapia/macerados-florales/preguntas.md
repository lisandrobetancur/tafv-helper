# Preguntas — Psicoterapia › Macerados Florales

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

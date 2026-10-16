# Reglas de contenido para cargar material

Estas reglas salen de lo que pidió la usuaria («no se debe perder información ni se debe tratar de
interpretar información»). Ante la duda, pregunta; no decidas por ella.

## Fidelidad
1. **Texto literal.** Lo que se carga es el texto de la celda, del comentario o de la imagen, con el mismo
   orden, las mismas viñetas, números y saltos de línea.
2. **Solo se corrige ortografía:** tildes, letras cambiadas («Cuagulopatias» → «Coagulopatías»), palabras
   pegadas por error («mLde» → «mL de», «Streptococcushaemolyticus» → «Streptococcus haemolyticus»), y
   mayúscula inicial. Cada corrección que cambie letras (no solo tildes) va en `correcciones` del plan.
   No se corrige: redacción, puntuación que cambie el sentido, unidades, abreviaturas, ni paréntesis sin
   cerrar (se dejan como están y se avisan en `preguntas.md`).
3. **No se agrega nada** que no esté en la fuente: ni referencias («ver imagen…»), ni títulos inventados,
   ni resúmenes, ni traducciones, ni etiquetas como «Síntomas:» o «Manejo:» si la fuente no las tiene.
4. **No se une ni se divide:** un renglón con comas («Asma, EPOC, SDRA») sigue siendo un renglón; dos
   renglones iguales en secciones distintas quedan en las dos. No se reagrupan condiciones por similitud.
5. **No se rellena:** una celda vacía queda vacía. Si una tabla (de Excel o de una imagen) agrupa filas con un
   rótulo escrito solo en la primera, repetirlo en las demás es una interpretación: pregunta antes.
6. **Comentarios de celda:** van en la nota del bloque donde está la celda, justo debajo del texto que
   comentan, así: `> Comentario de <Autor>: <texto>` (el autor y el texto tal cual; sin ID ni fecha).
7. **Nada se omite en silencio.** Lo que no se cargue (celda de relleno, imagen duplicada, imagen que la
   usuaria pidió convertir en notas) va en `omitidos` con su motivo.

## Qué forma toma cada cosa
- **Tabla de Excel** (se carga como tabla en la app): **solo cuando la fuente ya es una base de registros**,
  como el vademécum de Farmacología vegetal (`data/archivos/farmacologia-vegetal/vademecum/excel/`): una fila
  de encabezados (Sistema, Grupo, Nombre, Nombre científico, Acción, Dosis, Contraindicaciones…) y debajo
  decenas de filas, **cada fila un registro** (una planta, un medicamento) con sus atributos en columnas; es el
  contenido principal de la hoja. Rótulos de grupo combinados hacia abajo (como «Sistema») son normales.
  Así son también «Estudio homeopatia» y «Macerados Florales». `inspeccionar.py` lo marca **TABLA**.
  Si toda la hoja es la tabla, se carga el archivo de la hoja tal cual; la columna título es la que nombra el
  registro (Nombre, Medicamento…).
- **Nunca se fabrica una tabla de Excel** a partir de recuadros, listas o viñetas. Ejemplo de lo que NO se hace:
  convertir los recuadros «I Grupo / II Grupo / Indicaciones Corpas» de Oxivenación en una tabla
  «Condición | Grupo». Eso es reinterpretar el material: va en notas, como está.
- **Tabla pequeña dentro de un mural** (p. ej. «Sección | Presión | Tiempo» o una tabla de dosis junto a otros
  recuadros; `inspeccionar.py` la marca **TABLA PEQUEÑA**): va como tabla Markdown dentro de la nota de su
  encabezado, no como Excel. Si dudas entre tabla de Excel y nota, pregunta.
- **Notas** (recuadros sueltos, como un mural de diapositivas): **una nota por encabezado** (celda de color o
  en negrita que titula un recuadro), con todo lo que tiene debajo hasta el siguiente encabezado del mismo
  nivel, en el orden de la hoja (de arriba abajo, columna por columna de izquierda a derecha).
  - Título de la nota: el texto del encabezado + « - <Componente>» (p. ej. «Contraindicaciones - HBO»).
  - Subencabezados dentro del recuadro → `###`; listas con viñetas o números → listas Markdown;
    texto corrido → párrafos con sus saltos de línea.
  - Una tabla pequeña dentro de un recuadro (con o sin fila de encabezados) → tabla Markdown en la nota.
- **Imágenes**: todas se cargan, con
  - título descriptivo tomado de su propio encabezado o tema (+ « - <Componente>» si ayuda a distinguirla);
  - descripción = **transcripción literal de todo su texto** (incluidos rótulos de dibujos, fuentes y notas al
    pie), con saltos de línea; las tablas de la imagen como renglones «col | col | col» con su encabezado;
    las flechas de un esquema como «→»;
  - si algún texto no se puede leer con seguridad, **no se adivina**: la imagen va a `preguntas.md` y se le
    pregunta a la usuaria si se mejora o se convierte en notas.
  - Si una imagen contiene una tabla que la usuaria querría consultar como tabla, pregunta si también se crea
    un Excel con ella (con las mismas reglas: sin rellenar ni interpretar).
- **PDF**: se cargan tal cual con un título descriptivo; la app extrae su texto (y hace OCR de las páginas
  escaneadas).
- **Varias hojas en un archivo**: cada hoja va a su propio archivo (lo hace `preparar_fuentes.py`) y se
  carga en el componente que corresponda.

## Seguridad de los datos
- Siempre: respaldo antes de cargar (lo hace `cargar.py`), prueba en una copia (`--prueba`) y auditoría.
- Nunca edites ni borres elementos que la usuaria creó o modificó; si hay que reemplazar algo suyo, pregunta.
- Nunca modifiques los archivos de `data/fuentes/`: son la referencia de la auditoría.

"""SQL del índice de búsqueda global (FTS5), generado a partir de una tabla de definiciones.

Cada tipo de elemento tiene una vista `doc_<tipo>` que arma su documento (título + contenido +
datos para filtrar y enlazar) y triggers que mantienen el índice sincronizado al crear, editar
o borrar, venga el cambio de donde venga (también del OCR en segundo plano). Los elementos en
la papelera siguen en el índice y se excluyen al consultar.

`rowid` del índice = código del tipo × 10^12 + id del origen, para borrar sin buscar.
"""
from __future__ import annotations

BASE = 1_000_000_000_000

# Etiquetas de un elemento, separadas por espacios
_ETQ = """(SELECT group_concat(e.nombre, ' ') FROM etiquetas e JOIN etiquetas_elemento x ON x.etiqueta_id = e.id
           WHERE x.tipo = '{tipo}' AND x.ref_id = {alias}.id)"""

# tipo: (código, tabla origen, columnas que al cambiar reindexan, SELECT del documento con alias "o")
TIPOS: dict[str, tuple[int, str, str, str]] = {
    "materia": (1, "materias", "nombre, descripcion", """
        SELECT o.id AS fuente, o.nombre AS titulo, o.descripcion AS contenido,
               o.id AS ref, NULL AS sub, NULL AS padre, NULL AS componente, o.id AS materia
        FROM materias o"""),
    "componente": (2, "componentes", "nombre, descripcion", """
        SELECT o.id, o.nombre, o.descripcion, o.id, NULL, NULL, o.id, o.materia_id
        FROM componentes o"""),
    "tabla": (3, "tablas", "nombre", f"""
        SELECT o.id, o.nombre, COALESCE({_ETQ.format(tipo='tabla', alias='o')}, ''), o.id, NULL, o.id, o.componente_id, c.materia_id
        FROM tablas o JOIN componentes c ON c.id = o.componente_id"""),
    "fila": (4, "filas", "titulo, valores", f"""
        SELECT o.id, o.titulo, (SELECT group_concat(value, ' · ') FROM json_each(o.valores))
               || ' ' || COALESCE({_ETQ.format(tipo='fila', alias='o')}, ''),
               o.id, NULL, o.tabla_id, t.componente_id, c.materia_id
        FROM filas o JOIN tablas t ON t.id = o.tabla_id JOIN componentes c ON c.id = t.componente_id"""),
    "pdf": (5, "pdfs", "titulo", f"""
        SELECT o.id, o.titulo, COALESCE({_ETQ.format(tipo='pdf', alias='o')}, ''), o.id, NULL, o.id, o.componente_id, c.materia_id
        FROM pdfs o JOIN componentes c ON c.id = o.componente_id"""),
    "pagina": (6, "pdf_paginas", "texto", """
        SELECT o.id, d.titulo, o.texto, d.id, o.numero, d.id, d.componente_id, c.materia_id
        FROM pdf_paginas o JOIN pdfs d ON d.id = o.pdf_id JOIN componentes c ON c.id = d.componente_id"""),
    "imagen": (7, "imagenes", "titulo, descripcion, texto_ocr", f"""
        SELECT o.id, o.titulo, o.descripcion || ' ' || o.texto_ocr || ' ' || COALESCE({_ETQ.format(tipo='imagen', alias='o')}, ''),
               o.id, NULL, NULL, o.componente_id, c.materia_id
        FROM imagenes o JOIN componentes c ON c.id = o.componente_id"""),
    "nota": (8, "notas", "titulo, contenido", f"""
        SELECT o.id, o.titulo, o.contenido || ' ' || COALESCE({_ETQ.format(tipo='nota', alias='o')}, ''),
               o.id, NULL, NULL, o.componente_id, c.materia_id
        FROM notas o JOIN componentes c ON c.id = o.componente_id"""),
    "imagen_fila": (9, "imagenes_fila", "titulo, pie", """
        SELECT o.id, o.titulo, o.pie, o.id, o.fila_id, f.tabla_id, t.componente_id, c.materia_id
        FROM imagenes_fila o JOIN filas f ON f.id = o.fila_id JOIN tablas t ON t.id = f.tabla_id
        JOIN componentes c ON c.id = t.componente_id"""),
}

COLUMNAS = "fuente, titulo, contenido, ref, sub, padre, componente, materia"

# Tipos cuyas etiquetas forman parte del documento indexado
CON_ETIQUETAS = ("imagen", "nota", "fila", "pdf", "tabla")


def _insertar(tipo: str, codigo: int, condicion: str) -> str:
    return (f"INSERT INTO busqueda (rowid, titulo, contenido, tipo, ref, sub, padre, componente, materia) "
            f"SELECT {codigo} * {BASE} + fuente, titulo, COALESCE(contenido, ''), '{tipo}', ref, sub, padre, componente, materia "
            f"FROM doc_{tipo} {condicion};")


def migracion() -> str:
    partes = ["""
    CREATE VIRTUAL TABLE busqueda USING fts5(
        titulo, contenido,
        tipo UNINDEXED, ref UNINDEXED, sub UNINDEXED, padre UNINDEXED, componente UNINDEXED, materia UNINDEXED,
        tokenize = 'unicode61 remove_diacritics 2', prefix = '2 3'
    );"""]
    for tipo, (codigo, tabla, vigiladas, select) in TIPOS.items():
        partes.append(f"CREATE VIEW doc_{tipo} ({COLUMNAS}) AS {select};")
        partes.append(f"""
    CREATE TRIGGER busqueda_{tipo}_alta AFTER INSERT ON {tabla} BEGIN
        {_insertar(tipo, codigo, "WHERE fuente = NEW.id")}
    END;
    CREATE TRIGGER busqueda_{tipo}_baja AFTER DELETE ON {tabla} BEGIN
        DELETE FROM busqueda WHERE rowid = {codigo} * {BASE} + OLD.id;
    END;
    CREATE TRIGGER busqueda_{tipo}_cambio AFTER UPDATE OF {vigiladas} ON {tabla} BEGIN
        DELETE FROM busqueda WHERE rowid = {codigo} * {BASE} + OLD.id;
        {_insertar(tipo, codigo, "WHERE fuente = NEW.id")}
    END;""")
    # Al cambiar las etiquetas de un elemento se rehace su documento
    for tipo in CON_ETIQUETAS:
        codigo = TIPOS[tipo][0]
        for evento, fila in (("INSERT", "NEW"), ("DELETE", "OLD")):
            partes.append(f"""
    CREATE TRIGGER busqueda_etiquetas_{tipo}_{evento.lower()} AFTER {evento} ON etiquetas_elemento
    WHEN {fila}.tipo = '{tipo}' BEGIN
        DELETE FROM busqueda WHERE rowid = {codigo} * {BASE} + {fila}.ref_id;
        {_insertar(tipo, codigo, f"WHERE fuente = {fila}.ref_id")}
    END;""")
    partes.append(reconstruir())
    return "\n".join(partes)


def recrear() -> str:
    """Borra el índice, sus vistas y triggers y los vuelve a crear con las definiciones actuales
    (para migraciones que cambian qué se indexa)."""
    borrar = ["DROP TABLE IF EXISTS busqueda;"]
    for tipo in TIPOS:
        borrar.append(f"DROP VIEW IF EXISTS doc_{tipo};")
        for evento in ("alta", "baja", "cambio"):
            borrar.append(f"DROP TRIGGER IF EXISTS busqueda_{tipo}_{evento};")
    for tipo in CON_ETIQUETAS:
        for evento in ("insert", "delete"):
            borrar.append(f"DROP TRIGGER IF EXISTS busqueda_etiquetas_{tipo}_{evento};")
    return "\n".join(borrar) + "\n" + migracion()


def reconstruir() -> str:
    """Vacía y vuelve a llenar el índice desde cero (mantenimiento)."""
    return "DELETE FROM busqueda;\n" + "\n".join(_insertar(t, c, "") for t, (c, *_r) in TIPOS.items())

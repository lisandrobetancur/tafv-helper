"""Configuración y rutas de la biblioteca.

Todas las rutas se calculan a partir de la carpeta del proyecto, nunca se
guardan rutas absolutas: así la carpeta completa se puede copiar entre Mac
y Windows sin reconfigurar nada.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT: Path = Path(__file__).resolve().parent.parent
APP_DIR: Path = ROOT / "app"
STATIC_DIR: Path = APP_DIR / "static"
TEMPLATES_DIR: Path = APP_DIR / "templates"

NOMBRE_APP = "Biblioteca de Estudio"
INSTITUCION = "Fundación Universitaria Juan N. Corpas"
PUERTO_POR_DEFECTO = int(os.environ.get("BIBLIOTECA_PUERTO", "8765"))
PROFUNDIDAD_MAXIMA = 4  # niveles de componentes bajo una materia (componente › subcomponente › …)


@dataclass
class Rutas:
    """Carpetas de datos. Se puede reapuntar (p. ej. en pruebas) con `usar_datos`."""

    datos: Path

    @property
    def db(self) -> Path:
        return self.datos / "biblioteca.db"

    @property
    def archivos(self) -> Path:
        return self.datos / "archivos"

    @property
    def cache(self) -> Path:
        return self.datos / "cache"

    @property
    def miniaturas(self) -> Path:
        return self.cache / "miniaturas"

    @property
    def respaldos(self) -> Path:
        return self.datos / "respaldos"

    @property
    def papelera(self) -> Path:
        return self.datos / "papelera"

    @property
    def logs(self) -> Path:
        return self.datos / "logs"

    @property
    def bloqueo(self) -> Path:
        return self.datos / ".en_uso"

    def crear_carpetas(self) -> None:
        for carpeta in (self.datos, self.archivos, self.miniaturas, self.respaldos, self.papelera, self.logs):
            carpeta.mkdir(parents=True, exist_ok=True)

    def relativa(self, ruta: Path) -> str:
        """Ruta relativa a `data/` con separador "/" (la única forma en que se guardan en la BD)."""
        return ruta.resolve().relative_to(self.datos.resolve()).as_posix()

    def absoluta(self, relativa: str) -> Path:
        """Convierte una ruta guardada en la BD a una ruta del sistema, impidiendo salir de `data/`."""
        ruta = (self.datos / Path(*relativa.split("/"))).resolve()
        if not ruta.is_relative_to(self.datos.resolve()):
            raise ValueError("Ruta fuera de la carpeta de datos")
        return ruta


rutas = Rutas(Path(os.environ.get("BIBLIOTECA_DATOS", ROOT / "data")))


def usar_datos(carpeta: Path) -> None:
    """Reapunta la carpeta de datos (usado por las pruebas y la demostración)."""
    rutas.datos = Path(carpeta)


# Tipos de contenido que puede aceptar un componente
TIPOS_CONTENIDO: dict[str, dict[str, str]] = {
    "excel": {"nombre": "Excel / CSV", "icono": "file-spreadsheet"},
    "pdf": {"nombre": "PDF", "icono": "file-text"},
    "imagenes": {"nombre": "Imágenes", "icono": "images"},
    "notas": {"nombre": "Notas", "icono": "sticky-note"},
}

COLORES_MATERIA: list[dict[str, str]] = [
    {"id": "rojo", "nombre": "Rojo", "hex": "#c0392b"},
    {"id": "ambar", "nombre": "Ámbar", "hex": "#d68910"},
    {"id": "oro", "nombre": "Oro", "hex": "#b7950b"},
    {"id": "verde", "nombre": "Verde", "hex": "#229954"},
    {"id": "turquesa", "nombre": "Turquesa", "hex": "#16a085"},
    {"id": "azul", "nombre": "Azul", "hex": "#2e86c1"},
    {"id": "indigo", "nombre": "Índigo", "hex": "#4f46b8"},
    {"id": "violeta", "nombre": "Violeta", "hex": "#8e44ad"},
    {"id": "rosa", "nombre": "Rosa", "hex": "#c2185b"},
    {"id": "pizarra", "nombre": "Pizarra", "hex": "#5d6d7e"},
]
COLOR_POR_ID = {c["id"]: c for c in COLORES_MATERIA}

ICONOS_MATERIA: list[dict[str, str]] = [
    {"id": "book-open", "nombre": "Libro"},
    {"id": "heart-pulse", "nombre": "Cardiología"},
    {"id": "brain", "nombre": "Neurología"},
    {"id": "bone", "nombre": "Huesos"},
    {"id": "pill", "nombre": "Farmacología"},
    {"id": "flask-conical", "nombre": "Laboratorio"},
    {"id": "microscope", "nombre": "Microscopio"},
    {"id": "stethoscope", "nombre": "Clínica"},
    {"id": "dna", "nombre": "Genética"},
    {"id": "eye", "nombre": "Oftalmología"},
    {"id": "baby", "nombre": "Pediatría"},
    {"id": "activity", "nombre": "Fisiología"},
    {"id": "syringe", "nombre": "Procedimientos"},
    {"id": "bug", "nombre": "Microbiología"},
    {"id": "droplet", "nombre": "Hematología"},
    {"id": "wind", "nombre": "Neumología"},
    {"id": "shield-plus", "nombre": "Inmunología"},
    {"id": "apple", "nombre": "Nutrición"},
    {"id": "globe", "nombre": "Salud pública"},
    {"id": "leaf", "nombre": "Hoja"},
    {"id": "atom", "nombre": "Bioquímica"},
    {"id": "test-tube", "nombre": "Análisis"},
    {"id": "thermometer", "nombre": "Semiología"},
    {"id": "ear", "nombre": "Otorrino"},
    {"id": "hand", "nombre": "Anatomía"},
    {"id": "scale", "nombre": "Ética"},
    {"id": "users", "nombre": "Comunidad"},
    {"id": "ribbon", "nombre": "Oncología"},
    {"id": "venus", "nombre": "Ginecología"},
    {"id": "graduation-cap", "nombre": "General"},
    # Medicinas alternativas y terapias
    {"id": "sprout", "nombre": "Farmacología vegetal"},
    {"id": "flower-2", "nombre": "Plantas medicinales"},
    {"id": "pipette", "nombre": "Homeopatía"},
    {"id": "droplets", "nombre": "Diluciones"},
    {"id": "cylinder", "nombre": "Oxigenoterapia"},
    {"id": "brain-circuit", "nombre": "Terapia neural"},
    {"id": "zap", "nombre": "Impulso nervioso"},
    {"id": "flame", "nombre": "Metabolismo"},
    {"id": "orbit", "nombre": "Bioenergética"},
    {"id": "waypoints", "nombre": "Acupuntura"},
    {"id": "message-circle-heart", "nombre": "Psicoterapia"},
    {"id": "hand-heart", "nombre": "Terapias manuales"},
]
ICONOS_VALIDOS = {i["id"] for i in ICONOS_MATERIA}

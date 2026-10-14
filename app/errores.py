"""Errores pensados para mostrarse tal cual a la usuaria (nunca trazas técnicas)."""


class ErrorUsuario(Exception):
    """Algo que la usuaria puede corregir; el mensaje se muestra tal cual."""

    def __init__(self, mensaje: str, estado: int = 400):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.estado = estado


class NoEncontrado(ErrorUsuario):
    def __init__(self, que: str = "El elemento"):
        super().__init__(f"{que} no existe o fue enviado a la papelera.", 404)

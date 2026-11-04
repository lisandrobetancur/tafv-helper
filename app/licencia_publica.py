"""Clave pública para comprobar licencias (Ed25519, 32 bytes en base64url).

La escribe `python tools/licencias/crear_claves.py`, que guarda la clave privada fuera del proyecto.
Esta clave puede ir en el código y en git: solo sirve para comprobar licencias, no para crearlas.
Vacía, ninguna licencia es válida y el programa no se abre.
"""
CLAVE_PUBLICA = ""

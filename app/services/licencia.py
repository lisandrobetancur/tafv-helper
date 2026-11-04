"""Licencia por equipo, sin internet.

- Cada computador tiene un **código de equipo** (p. ej. «7K3M-QWXD-2RPA-F4TB») que sale del identificador del sistema
  operativo: siempre el mismo en ese equipo y distinto en otro.
- La licencia es ese código (más el nombre de la persona) **firmado** con la clave privada de quien distribuye el
  programa (Ed25519). La app solo tiene la clave pública: puede comprobar una licencia, pero no fabricarla.
- No vence y no hay límite de equipos: cada equipo recibe su propia licencia.
- La licencia se guarda en la carpeta de datos; si esa carpeta se copia a otro equipo, allí no vale y se pide otra.

Formato de la licencia: «TAFV1.<datos en base64url>.<firma en base64url>».
Herramientas para crear las claves y emitir licencias: tools/licencias/.
"""
from __future__ import annotations

import base64
import functools
import hashlib
import json
import os
import platform
import re
import subprocess
import uuid
from dataclasses import dataclass
from datetime import date

from ..config import rutas
from ..licencia_publica import CLAVE_PUBLICA

PREFIJO = "TAFV1"


# ------------------------------------------------------------------ código de equipo
def _identificador_sistema() -> str:
    """Identificador estable del equipo según el sistema operativo."""
    sistema = platform.system()
    try:
        if sistema == "Windows":
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography", 0,
                                winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as k:
                return "win:" + winreg.QueryValueEx(k, "MachineGuid")[0]
        if sistema == "Darwin":
            salida = subprocess.run(["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"], capture_output=True,
                                    text=True, timeout=10).stdout
            m = re.search(r'"IOPlatformUUID"\s*=\s*"([^"]+)"', salida)
            if m:
                return "mac:" + m.group(1)
        for ruta in ("/etc/machine-id", "/var/lib/dbus/machine-id"):
            if os.path.exists(ruta):
                with open(ruta, encoding="utf-8") as f:
                    valor = f.read().strip()
                if valor:
                    return "linux:" + valor
    except Exception:  # noqa: BLE001 - si el sistema no responde, se usa la tarjeta de red
        pass
    return "mac-red:" + format(uuid.getnode(), "x")


def formatear_codigo(crudo: str) -> str:
    resumen = hashlib.sha256(("biblioteca-estudio|" + crudo).encode()).digest()
    letras = base64.b32encode(resumen).decode()[:16]
    return "-".join(letras[i:i + 4] for i in range(0, 16, 4))


@functools.lru_cache(maxsize=1)
def codigo_equipo() -> str:
    return formatear_codigo(_identificador_sistema())


def normalizar_codigo(codigo: str) -> str:
    # Confusiones típicas al copiar a mano: 0→O, 1→I, 8→B (el código no usa esos números)
    limpio = re.sub(r"[^A-Z2-7]", "", (codigo or "").upper().translate(str.maketrans("018", "OIB")))
    return "-".join(limpio[i:i + 4] for i in range(0, len(limpio), 4))


# ------------------------------------------------------------------ firma
def _b64(datos: bytes) -> str:
    return base64.urlsafe_b64encode(datos).decode().rstrip("=")


def _de_b64(texto: str) -> bytes:
    return base64.urlsafe_b64decode(texto + "=" * (-len(texto) % 4))


def emitir(clave_privada, codigo: str, nombre: str = "", fecha: str | None = None) -> str:
    """Crea una licencia (lo usa la herramienta de quien distribuye; la app nunca tiene la clave privada)."""
    datos = {"e": normalizar_codigo(codigo), "n": " ".join((nombre or "").split())[:80],
             "f": fecha or date.today().isoformat()}
    cuerpo = json.dumps(datos, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()
    return f"{PREFIJO}.{_b64(cuerpo)}.{_b64(clave_privada.sign(cuerpo))}"


@dataclass
class Estado:
    valida: bool
    mensaje: str = ""
    nombre: str = ""
    fecha: str = ""


def verificar(licencia: str, codigo: str | None = None, clave_publica: str | None = None) -> Estado:
    """Comprueba la firma y que la licencia sea de este equipo."""
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

    publica = CLAVE_PUBLICA if clave_publica is None else clave_publica
    if not publica:
        return Estado(False, "Esta copia del programa no tiene configurada la clave para comprobar licencias.")
    texto = re.sub(r"\s+", "", licencia or "")
    partes = texto.split(".")
    if len(partes) != 3 or partes[0] != PREFIJO:
        return Estado(False, "La licencia no tiene el formato correcto. Cópiala completa, tal como la recibiste.")
    try:
        cuerpo, firma = _de_b64(partes[1]), _de_b64(partes[2])
        Ed25519PublicKey.from_public_bytes(_de_b64(publica)).verify(firma, cuerpo)
        datos = json.loads(cuerpo)
    except (InvalidSignature, ValueError):
        return Estado(False, "La licencia no es válida. Revisa que la copiaste completa.")
    if normalizar_codigo(datos.get("e", "")) != (codigo or codigo_equipo()):
        return Estado(False, "Esta licencia es de otro equipo. Pide una para el código que aparece aquí.")
    return Estado(True, nombre=datos.get("n", ""), fecha=datos.get("f", ""))


# ------------------------------------------------------------------ licencia guardada
def _archivo():
    return rutas.datos / "licencia.txt"


def guardada() -> str:
    try:
        return _archivo().read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def estado_actual() -> Estado:
    licencia = guardada()
    if not licencia:
        return Estado(False, "")
    return verificar(licencia)


def activar(licencia: str) -> Estado:
    estado = verificar(licencia)
    if estado.valida:
        _archivo().parent.mkdir(parents=True, exist_ok=True)
        _archivo().write_text(re.sub(r"\s+", "", licencia), encoding="utf-8")
    return estado

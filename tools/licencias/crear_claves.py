"""Crea el par de claves de las licencias (se hace UNA sola vez).

    python tools/licencias/crear_claves.py [--carpeta RUTA]

- La clave privada se guarda FUERA del proyecto (por defecto en ~/LicenciasBiblioteca/clave_privada.pem).
  Con ella se emiten las licencias: guárdala con cuidado y haz una copia (USB, nube personal). Si se pierde,
  no se pueden emitir más licencias que valgan para los programas ya repartidos.
- La clave pública se escribe en app/licencia_publica.py (va en el programa y en git).

No sobrescribe una clave privada existente.
"""
from __future__ import annotations

import argparse
import base64
import re
import sys
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

RAIZ = Path(__file__).resolve().parents[2]
ARCHIVO_PUBLICA = RAIZ / "app" / "licencia_publica.py"
CARPETA = Path.home() / "LicenciasBiblioteca"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--carpeta", type=Path, default=CARPETA, help="dónde guardar la clave privada")
    args = parser.parse_args()
    privada_pem = args.carpeta / "clave_privada.pem"
    if privada_pem.exists():
        sys.exit(f"Ya existe {privada_pem}. No se sobrescribe: si la reemplazas, las licencias emitidas dejan de valer.")
    if args.carpeta.resolve().is_relative_to(RAIZ):
        sys.exit("La clave privada no puede quedar dentro del proyecto (terminaría en git o en el instalador).")

    clave = Ed25519PrivateKey.generate()
    args.carpeta.mkdir(parents=True, exist_ok=True)
    privada_pem.write_bytes(clave.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                                serialization.NoEncryption()))
    try:
        privada_pem.chmod(0o600)
    except OSError:
        pass
    publica = base64.urlsafe_b64encode(clave.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw)).decode().rstrip("=")
    texto = ARCHIVO_PUBLICA.read_text(encoding="utf-8")
    ARCHIVO_PUBLICA.write_text(re.sub(r'CLAVE_PUBLICA = ".*"', f'CLAVE_PUBLICA = "{publica}"', texto), encoding="utf-8")
    print(f"Clave privada guardada en: {privada_pem}")
    print("  -> Haz una copia de seguridad de ese archivo y no lo compartas con nadie.")
    print(f"Clave pública escrita en: {ARCHIVO_PUBLICA}")
    print("  -> Haz commit de ese archivo para que los instaladores la incluyan.")


if __name__ == "__main__":
    main()

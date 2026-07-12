"""
Cifrado en reposo para secretos de los tenants (PLAN §10): los tokens de las
conexiones contables no se guardan en claro en la base de datos.

La llave se deriva de DJANGO_SECRET_KEY: si esa clave cambia, los tokens
guardados dejan de poder descifrarse y cada empresa debe reconectar su
software contable (mejor eso que tokens legibles en un respaldo filtrado).
"""
import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.db import models


def _llave():
    material = hashlib.sha256(
        ("cifrado-conexiones:" + settings.SECRET_KEY).encode()).digest()
    return base64.urlsafe_b64encode(material)


def cifrar(texto):
    return Fernet(_llave()).encrypt(texto.encode()).decode()


def descifrar(valor):
    try:
        return Fernet(_llave()).decrypt(valor.encode()).decode()
    except (InvalidToken, ValueError):
        # Valor heredado en claro (previo al cifrado) o llave cambiada:
        # se devuelve tal cual; al siguiente guardado queda cifrado.
        return valor


class CampoCifrado(models.TextField):
    """TextField que cifra al guardar y descifra al leer, transparente
    para el resto del código."""

    def get_prep_value(self, value):
        if value in (None, ""):
            return value
        return cifrar(str(value))

    def from_db_value(self, value, expression, connection):
        if value in (None, ""):
            return value
        return descifrar(value)

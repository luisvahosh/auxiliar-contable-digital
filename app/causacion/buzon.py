"""
Lectura de facturas desde el buzón de correo del cliente (PLAN §4).

Se conecta por IMAP-SSL, lee los correos no vistos, extrae los adjuntos XML
(directos o dentro de un ZIP, como los envía la DIAN/proveedores) y los pasa
por el MISMO motor procesar_xml de todos los canales de ingesta. Los correos
procesados se marcan como leídos; nunca se borra nada.

Aislado con try/except por correo y por adjunto: un mensaje corrupto no frena
el resto. Lo no procesable se cuenta y se reporta, nunca se pierde.
"""
import email
import imaplib
import io
import zipfile
from dataclasses import dataclass, field

from django.utils import timezone

from .servicios import procesar_xml

TIEMPO_MAXIMO = 30  # segundos de espera del servidor IMAP


class BuzonError(Exception):
    """Fallo al conectar o leer el buzón. Mensaje apto para el usuario."""


@dataclass
class ResumenBuzon:
    correos: int = 0
    creados: int = 0
    duplicados: int = 0
    errores: int = 0
    detalle: list = field(default_factory=list)


def _xmls_del_mensaje(mensaje):
    """Todos los XML del correo: adjuntos .xml directos y los que vengan
    dentro de un .zip. → lista de (nombre, bytes)."""
    encontrados = []
    for parte in mensaje.walk():
        nombre = parte.get_filename() or ""
        contenido = parte.get_payload(decode=True)
        if not contenido:
            continue
        bajo = nombre.lower()
        if bajo.endswith(".xml"):
            encontrados.append((nombre, contenido))
        elif bajo.endswith(".zip"):
            try:
                with zipfile.ZipFile(io.BytesIO(contenido)) as z:
                    for interno in z.namelist():
                        if interno.lower().endswith(".xml"):
                            encontrados.append((interno, z.read(interno)))
            except zipfile.BadZipFile:
                continue
    return encontrados


def revisar_buzon(buzon, marcar_leidos=True):
    """Lee los correos no vistos del buzón y procesa sus facturas.
    → ResumenBuzon. Levanta BuzonError si no se pudo conectar."""
    resumen = ResumenBuzon()
    try:
        conexion = imaplib.IMAP4_SSL(buzon.servidor, buzon.puerto,
                                     timeout=TIEMPO_MAXIMO)
    except (OSError, imaplib.IMAP4.error):
        raise BuzonError("no se pudo conectar al servidor de correo "
                         "(revisa servidor y puerto).")
    try:
        try:
            conexion.login(buzon.usuario, buzon.clave)
        except imaplib.IMAP4.error:
            raise BuzonError("el correo o la contraseña no fueron aceptados "
                             "(con 2FA usa una contraseña de aplicación).")
        if conexion.select(buzon.carpeta)[0] != "OK":
            raise BuzonError(f"no se encontró la carpeta «{buzon.carpeta}».")

        tipo, datos = conexion.search(None, "UNSEEN")
        if tipo != "OK":
            raise BuzonError("no se pudieron listar los correos.")
        ids = datos[0].split()
        resumen.correos = len(ids)

        for correo_id in ids:
            try:
                tipo, cuerpo = conexion.fetch(correo_id, "(RFC822)")
                if tipo != "OK":
                    continue
                mensaje = email.message_from_bytes(cuerpo[0][1])
                for nombre, xml in _xmls_del_mensaje(mensaje):
                    resultado = procesar_xml(buzon.empresa, xml)
                    if resultado.estado == "creado":
                        resumen.creados += 1
                    elif resultado.estado == "duplicado":
                        resumen.duplicados += 1
                    else:
                        resumen.errores += 1
                    resumen.detalle.append(f"{nombre}: {resultado.mensaje}")
                if marcar_leidos:
                    conexion.store(correo_id, "+FLAGS", "\\Seen")
            except Exception as error:  # un correo malo no frena el resto
                resumen.errores += 1
                resumen.detalle.append(f"Correo {correo_id.decode()}: {error}")
    finally:
        try:
            conexion.logout()
        except Exception:
            pass

    buzon.ultima_revision = timezone.now()
    buzon.save(update_fields=["ultima_revision"])
    return resumen

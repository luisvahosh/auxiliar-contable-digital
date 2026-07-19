"""
Extrae el XML UBL de la factura desde los formatos en que la recibe el auxiliar.

En Colombia la DIAN y los proveedores entregan la MISMA factura de varias formas
y el auxiliar rara vez tiene a mano el .xml "pelado":

- **.xml** suelto — a veces envuelto en un `AttachedDocument` de la DIAN, que
  lleva el `Invoice`/`CreditNote` real dentro de un CDATA (o en base64).
- **.zip** con el .xml adentro (como lo baja el portal DIAN).
- **.pdf** (representación gráfica) con el XML embebido como ADJUNTO del PDF
  (la DIAN exige adjuntarlo; casi todos los proveedores lo hacen).
- **.html** con el XML embebido (data URI base64 o el propio XML en el cuerpo).

Este módulo solo DESEMPAQUETA: siempre devuelve los bytes del XML UBL para que
`procesar_xml` los valide con defusedxml (XXE, CUFE, totales, tenant). Si el
archivo no trae XML dentro (p. ej. un PDF escaneado), levanta `SinXml` con un
mensaje que guía al usuario a la ruta de foto (P1.10).
"""
import base64
import io
import re
import zipfile
from xml.etree.ElementTree import ParseError

from defusedxml import ElementTree as ET
from defusedxml.common import DefusedXmlException

EXTENSIONES = (".xml", ".zip", ".pdf", ".html", ".htm")

_TAG_ATTACHED = ("{urn:oasis:names:specification:ubl:schema:xsd:"
                 "AttachedDocument-2}AttachedDocument")
_TAG_DESCRIPTION = ("{urn:oasis:names:specification:ubl:schema:xsd:"
                    "CommonBasicComponents-2}Description")


class SinXml(Exception):
    """No se pudo extraer un XML UBL del archivo. Mensaje apto para el usuario."""


def _parece_ubl(datos):
    """¿Estos bytes contienen un documento UBL (Invoice/CreditNote/AttachedDocument)?"""
    return any(marca in datos for marca in
               (b"<Invoice", b"<CreditNote", b"<AttachedDocument",
                b"<ApplicationResponse", b":Invoice", b":CreditNote"))


def desenvolver_attached_document(contenido):
    """Si el XML es un `AttachedDocument` de la DIAN, devuelve el Invoice/CreditNote
    embebido (CDATA o base64); si no, devuelve el mismo contenido tal cual."""
    try:
        raiz = ET.fromstring(contenido)
    except (DefusedXmlException, ParseError, ValueError):
        return contenido  # que procesar_xml dé el error de XML formal
    if raiz.tag != _TAG_ATTACHED:
        return contenido
    for desc in raiz.iter(_TAG_DESCRIPTION):
        texto = (desc.text or "").strip()
        if not texto:
            continue
        if texto.startswith("<") and ("Invoice" in texto or "CreditNote" in texto):
            return texto.encode("utf-8")
        # Algunos proveedores embeben el documento en base64 dentro del Description
        try:
            crudo = base64.b64decode(texto, validate=True)
        except (ValueError, base64.binascii.Error):
            continue
        if _parece_ubl(crudo):
            return crudo
    return contenido


def _xml_de_zip(contenido):
    try:
        with zipfile.ZipFile(io.BytesIO(contenido)) as z:
            for interno in z.namelist():
                if interno.lower().endswith(".xml"):
                    return z.read(interno)
    except zipfile.BadZipFile:
        raise SinXml("el archivo no es un ZIP válido o está dañado.")
    return None


def _xml_de_pdf(contenido):
    """El XML adjunto dentro del PDF de la representación gráfica (pypdf)."""
    from pypdf import PdfReader
    from pypdf.errors import PdfReadError
    try:
        lector = PdfReader(io.BytesIO(contenido))
        adjuntos = lector.attachments  # nombre -> lista de versiones (bytes)
    except (PdfReadError, ValueError, OSError):
        raise SinXml("no se pudo leer el PDF (¿dañado o protegido con clave?).")
    # Primero los adjuntos con nombre .xml; si no, cualquiera que parezca UBL.
    candidatos = sorted(adjuntos.items(),
                        key=lambda kv: not kv[0].lower().endswith(".xml"))
    for _nombre, versiones in candidatos:
        for datos in versiones:
            if _parece_ubl(datos):
                return datos
    return None


def _xml_de_html(contenido):
    """El XML embebido en el HTML: data URI en base64 o el XML en el cuerpo."""
    texto = contenido.decode("utf-8", errors="replace")
    # 1) Enlace/atributo data:...;base64,<...> con el XML dentro
    for bloque in re.findall(
            r"data:(?:application|text)/xml[^,]*base64,([A-Za-z0-9+/=\s]+)", texto):
        try:
            datos = base64.b64decode(re.sub(r"\s", "", bloque), validate=True)
        except (ValueError, base64.binascii.Error):
            continue
        if _parece_ubl(datos):
            return datos
    # 2) XML incrustado tal cual en el cuerpo (AttachedDocument/Invoice/CreditNote)
    marca = re.search(r"<(?:\w+:)?(?:AttachedDocument|Invoice|CreditNote)\b", texto)
    if marca:
        recorte = texto[marca.start():]
        cierre = re.search(r"</(?:\w+:)?(?:AttachedDocument|Invoice|CreditNote)>",
                           recorte)
        if cierre:
            return recorte[:cierre.end()].encode("utf-8")
    return None


def extraer_xml(nombre, contenido):
    """Bytes de un archivo subido (por su nombre) → bytes del XML UBL para
    `procesar_xml`. Levanta `SinXml` (mensaje mostrable) si no lo trae dentro."""
    bajo = (nombre or "").lower()
    if bajo.endswith(".xml"):
        return desenvolver_attached_document(contenido)
    if bajo.endswith(".zip"):
        xml = _xml_de_zip(contenido)
        if xml is None:
            raise SinXml("el ZIP no contiene ningún archivo .xml de factura.")
        return desenvolver_attached_document(xml)
    if bajo.endswith(".pdf"):
        xml = _xml_de_pdf(contenido)
        if xml is None:
            raise SinXml(
                "este PDF no trae el XML de la factura adentro (es solo la "
                "representación gráfica). Si es una factura de papel o escaneada, "
                "usa «Causar desde una foto»; si la bajaste de la DIAN, sube el "
                "XML o el ZIP.")
        return desenvolver_attached_document(xml)
    if bajo.endswith((".html", ".htm")):
        xml = _xml_de_html(contenido)
        if xml is None:
            raise SinXml(
                "este HTML no trae el XML de la factura adentro. Sube el XML o el "
                "ZIP de la factura, o usa «Causar desde una foto».")
        return desenvolver_attached_document(xml)
    raise SinXml("formato no soportado; sube el XML, ZIP, PDF o HTML de la factura.")

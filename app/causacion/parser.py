"""
Parseo de facturas electrónicas DIAN (UBL 2.1, documento Invoice).

Seguridad (CLAUDE.md §4): el XML descargado de la DIAN o recibido por correo
es entrada externa — el vector de ataque principal del producto. Se parsea
SIEMPRE con defusedxml (bloquea XXE y bombas de entidades); nunca con
xml.etree directo. Los mensajes de FacturaInvalida son aptos para el usuario.
"""
import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
# Solo la CLASE de excepción viene de xml.etree (es inofensiva);
# el parseo en sí siempre pasa por defusedxml.
from xml.etree.ElementTree import ParseError

from defusedxml import ElementTree as ET
from defusedxml.common import DefusedXmlException

NS = {
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
}
_RAIZ_FACTURA = "{urn:oasis:names:specification:ubl:schema:xsd:Invoice-2}Invoice"
_RAIZ_NOTA_CREDITO = "{urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2}CreditNote"
_RUTA_FISCAL = "cac:Party/cac:PartyTaxScheme/"


class FacturaInvalida(Exception):
    """XML rechazado: no es una factura UBL utilizable. Mensaje mostrable al usuario."""


@dataclass
class Linea:
    descripcion: str
    cantidad: Decimal
    valor: Decimal


@dataclass
class FacturaParseada:
    cufe: str
    numero: str
    fecha_emision: date
    nota: str
    nit_emisor: str
    nombre_emisor: str
    tipo_persona_emisor: str      # AdditionalAccountID DIAN: "1" jurídica, "2" natural
    responsabilidad_emisor: str   # TaxLevelCode del RUT: O-13/O-15/O-23/O-47/R-99-PN
    nit_adquiriente: str
    nombre_adquiriente: str
    subtotal: Decimal
    iva: Decimal
    total: Decimal
    lineas: list
    tipo_documento: str           # "factura" | "nota_credito"
    retefuente_practicada: Decimal  # WithholdingTaxTotal esquema 06 (ventas)
    referencia_numero: str        # BillingReference (notas crédito)
    referencia_cufe: str

    @property
    def texto_clasificable(self):
        """Nota + descripciones de línea: el insumo del motor de clasificación."""
        partes = [self.nota] + [linea.descripcion for linea in self.lineas]
        return " ".join(parte for parte in partes if parte).lower()


def _texto(nodo, ruta, campo):
    hijo = nodo.find(ruta, NS)
    if hijo is None or not (hijo.text or "").strip():
        raise FacturaInvalida(
            f"El XML no contiene {campo} — ¿es una factura electrónica UBL de la DIAN?"
        )
    return hijo.text.strip()


def _texto_opcional(nodo, ruta):
    hijo = nodo.find(ruta, NS)
    return (hijo.text or "").strip() if hijo is not None else ""


def _decimal(texto, campo):
    try:
        return Decimal(texto)
    except InvalidOperation:
        raise FacturaInvalida(f"{campo} no es un número válido: «{texto}».")


def parsear_factura(contenido):
    """Convierte los bytes de un XML en FacturaParseada, o levanta FacturaInvalida."""
    try:
        raiz = ET.fromstring(contenido)
    except DefusedXmlException:
        raise FacturaInvalida(
            "el archivo contiene construcciones XML peligrosas (DOCTYPE/entidades "
            "externas) y fue rechazado por seguridad."
        )
    except (ParseError, ValueError):
        raise FacturaInvalida("el archivo no es un XML bien formado (¿truncado o corrupto?).")

    if raiz.tag == _RAIZ_FACTURA:
        tipo_documento = "factura"
        etiqueta_linea = "cac:InvoiceLine"
        etiqueta_cantidad = "cbc:InvoicedQuantity"
    elif raiz.tag == _RAIZ_NOTA_CREDITO:
        tipo_documento = "nota_credito"
        etiqueta_linea = "cac:CreditNoteLine"
        etiqueta_cantidad = "cbc:CreditedQuantity"
    else:
        raise FacturaInvalida(
            "el XML no es un documento UBL DIAN (se esperaba <Invoice> o <CreditNote>)."
        )

    cufe = _texto(raiz, "cbc:UUID", "el CUFE (cbc:UUID)")
    if not re.fullmatch(r"[0-9a-fA-F]{40,100}", cufe):
        raise FacturaInvalida("el CUFE no tiene el formato esperado (hexadecimal DIAN).")

    fecha_texto = _texto(raiz, "cbc:IssueDate", "la fecha de emisión")
    try:
        fecha_emision = date.fromisoformat(fecha_texto)
    except ValueError:
        raise FacturaInvalida(f"la fecha de emisión no es válida: «{fecha_texto}».")

    emisor = raiz.find("cac:AccountingSupplierParty", NS)
    adquiriente = raiz.find("cac:AccountingCustomerParty", NS)
    if emisor is None or adquiriente is None:
        raise FacturaInvalida("el XML no identifica emisor y adquiriente.")

    lineas = []
    for nodo in raiz.findall(etiqueta_linea, NS):
        lineas.append(Linea(
            descripcion=_texto(nodo, "cac:Item/cbc:Description", "la descripción de una línea"),
            cantidad=_decimal(_texto(nodo, etiqueta_cantidad, "la cantidad de una línea"),
                              "La cantidad de una línea"),
            valor=_decimal(_texto(nodo, "cbc:LineExtensionAmount", "el valor de una línea"),
                           "El valor de una línea"),
        ))
    if not lineas:
        raise FacturaInvalida("el documento no tiene líneas de detalle.")

    subtotal = _decimal(_texto(raiz, "cac:LegalMonetaryTotal/cbc:LineExtensionAmount",
                               "el subtotal"), "El subtotal")
    total = _decimal(_texto(raiz, "cac:LegalMonetaryTotal/cbc:PayableAmount",
                            "el total a pagar"), "El total")
    iva_texto = _texto_opcional(raiz, "cac:TaxTotal/cbc:TaxAmount")
    iva = _decimal(iva_texto, "El IVA") if iva_texto else Decimal("0")

    # Controles del auxiliar (guía P1 paso 2): los cálculos del XML deben cuadrar.
    if subtotal + iva != total:
        raise FacturaInvalida(
            f"los totales no cuadran: subtotal {subtotal} + IVA {iva} ≠ total {total}."
        )
    suma_lineas = sum(linea.valor for linea in lineas)
    if suma_lineas != subtotal:
        raise FacturaInvalida(
            f"la suma de las líneas ({suma_lineas}) no coincide con el subtotal ({subtotal})."
        )

    # Retefuente que el adquiriente practica (viene sugerida en ventas):
    # WithholdingTaxTotal con esquema 06 (renta). 05=reteIVA y 07=reteICA
    # se ignoran por ahora.
    retefuente_practicada = Decimal("0")
    for nodo in raiz.findall("cac:WithholdingTaxTotal", NS):
        esquema = _texto_opcional(nodo, "cac:TaxSubtotal/cac:TaxCategory/cac:TaxScheme/cbc:ID")
        if esquema == "06":
            retefuente_practicada += _decimal(
                _texto(nodo, "cbc:TaxAmount", "la retención practicada"),
                "La retención practicada")

    # Notas crédito: referencia a la factura original.
    referencia = raiz.find("cac:BillingReference/cac:InvoiceDocumentReference", NS)
    referencia_numero = _texto_opcional(referencia, "cbc:ID") if referencia is not None else ""
    referencia_cufe = _texto_opcional(referencia, "cbc:UUID") if referencia is not None else ""
    if tipo_documento == "nota_credito" and not (referencia_numero or referencia_cufe):
        raise FacturaInvalida(
            "la nota crédito no referencia la factura original (BillingReference)."
        )

    return FacturaParseada(
        cufe=cufe,
        numero=_texto(raiz, "cbc:ID", "el número de documento"),
        fecha_emision=fecha_emision,
        nota=_texto_opcional(raiz, "cbc:Note"),
        nit_emisor=_texto(emisor, _RUTA_FISCAL + "cbc:CompanyID", "el NIT del emisor"),
        nombre_emisor=_texto(emisor, _RUTA_FISCAL + "cbc:RegistrationName", "el nombre del emisor"),
        tipo_persona_emisor=_texto(emisor, "cbc:AdditionalAccountID", "el tipo de persona del emisor"),
        responsabilidad_emisor=_texto_opcional(emisor, _RUTA_FISCAL + "cbc:TaxLevelCode"),
        nit_adquiriente=_texto(adquiriente, _RUTA_FISCAL + "cbc:CompanyID", "el NIT del adquiriente"),
        nombre_adquiriente=_texto(adquiriente, _RUTA_FISCAL + "cbc:RegistrationName",
                                  "el nombre del adquiriente"),
        subtotal=subtotal,
        iva=iva,
        total=total,
        lineas=lineas,
        tipo_documento=tipo_documento,
        retefuente_practicada=retefuente_practicada,
        referencia_numero=referencia_numero,
        referencia_cufe=referencia_cufe,
    )

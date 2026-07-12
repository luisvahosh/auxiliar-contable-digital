"""
Motor de conciliación bancaria (guía P4).

Cruza cada movimiento del extracto contra los registros contables:
- Abonos: pagos de clientes (cruce exacto por el neto de cartera, o parcial
  si el nombre del cliente aparece en la descripción — P4.4). Lo que no
  cruza va a excepciones con el cliente más probable (P4.3).
- Cargos: pagos a proveedores (neto) y gastos bancarios conocidos
  (comisiones, GMF — P4.2), con su asiento propuesto.

Como todo en la app: cada sugerencia lleva su porqué y nada se concilia
sin el clic del humano.
"""
import csv
import io
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from pypdf import PdfReader

CUENTA_BANCOS = ("111005", "Bancos — moneda nacional")
CUENTA_CLIENTES = ("1305", "Clientes nacionales")

# Gastos bancarios reconocibles por la descripción del extracto (P4.2).
GASTOS_BANCARIOS = [
    (re.compile(r"gmf|4\s*x\s*1000|gravamen", re.IGNORECASE),
     "531595", "Gravamen a los movimientos financieros (GMF)"),
    (re.compile(r"cuota|comisi[oó]n|manejo|chequera|portal|iva\s+serv", re.IGNORECASE),
     "530505", "Gastos bancarios — comisiones"),
]

ENCABEZADO_ESPERADO = ["fecha", "descripcion", "valor"]


class ExtractoInvalido(Exception):
    """CSV rechazado. Mensaje apto para mostrar al usuario."""


def _parsear_fecha(texto):
    for formato in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(texto.strip(), formato).date()
        except ValueError:
            continue
    raise ExtractoInvalido(
        f"Fecha inválida en el extracto: «{texto}» (se acepta AAAA-MM-DD o DD/MM/AAAA)."
    )


def _parsear_valor(texto):
    limpio = texto.strip().replace("$", "").replace(" ", "")
    limpio = limpio.replace(".", "").replace(",", ".")  # formato colombiano
    try:
        return Decimal(limpio)
    except InvalidOperation:
        raise ExtractoInvalido(f"Valor inválido en el extracto: «{texto}».")


def parsear_extracto(contenido):
    """Bytes del CSV (fecha;descripcion;valor) → lista de movimientos crudos."""
    try:
        texto = contenido.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ExtractoInvalido("El archivo no es texto UTF-8 (¿es realmente un CSV?).")

    filas = list(csv.reader(io.StringIO(texto), delimiter=";"))
    filas = [f for f in filas if any(celda.strip() for celda in f)]
    if not filas:
        raise ExtractoInvalido("El archivo está vacío.")
    encabezado = [c.strip().lower().replace("ó", "o") for c in filas[0]]
    if encabezado[:3] != ENCABEZADO_ESPERADO:
        raise ExtractoInvalido(
            "El CSV debe empezar con el encabezado «fecha;descripcion;valor» "
            f"(se encontró: {';'.join(filas[0][:3])})."
        )
    movimientos = []
    for numero_fila, fila in enumerate(filas[1:], start=2):
        if len(fila) < 3:
            raise ExtractoInvalido(f"La fila {numero_fila} no tiene las 3 columnas.")
        movimientos.append({
            "fecha": _parsear_fecha(fila[0]),
            "descripcion": fila[1].strip()[:200],
            "valor": _parsear_valor(fila[2]),
        })
    if not movimientos:
        raise ExtractoInvalido("El extracto no tiene movimientos.")
    return movimientos


# Renglón de movimiento en el texto de un PDF bancario:
# fecha  descripción  valor (con signo, formato colombiano)
PATRON_MOVIMIENTO_PDF = re.compile(
    r"^(\d{2}/\d{2}/\d{4}|\d{4}-\d{2}-\d{2})\s+(.+?)\s+(-?\$?[\d.,]+)$")


def parsear_extracto_pdf(contenido):
    """Extrae los movimientos del texto de un extracto en PDF (P4.5).

    Funciona con PDF de texto (el que descarga el portal del banco); un
    escaneo/imagen no tiene texto y se rechaza con instrucción clara.
    """
    try:
        lector = PdfReader(io.BytesIO(contenido))
        texto = "\n".join((pagina.extract_text() or "") for pagina in lector.pages)
    except Exception:
        raise ExtractoInvalido("el archivo no es un PDF legible.")

    movimientos = []
    for linea in texto.splitlines():
        encontrado = PATRON_MOVIMIENTO_PDF.match(linea.strip())
        if not encontrado:
            continue  # encabezados, saldos, pies de página
        try:
            movimientos.append({
                "fecha": _parsear_fecha(encontrado.group(1)),
                "descripcion": encontrado.group(2).strip()[:200],
                "valor": _parsear_valor(encontrado.group(3)),
            })
        except ExtractoInvalido:
            continue  # línea con pinta de movimiento pero valores raros: se ignora
    if not movimientos:
        raise ExtractoInvalido(
            "no se encontraron movimientos en el PDF. Si es un escaneo (imagen), "
            "por ahora usa el CSV del banco; la lectura de imágenes llegará después."
        )
    return movimientos


def parsear_extracto_archivo(nombre, contenido):
    """Un solo punto de entrada: decide por la extensión (CSV o PDF)."""
    if nombre.lower().endswith(".pdf"):
        return parsear_extracto_pdf(contenido)
    return parsear_extracto(contenido)


def _renglon(cuenta, nombre, debito=Decimal("0"), credito=Decimal("0")):
    return {"cuenta": cuenta, "nombre": nombre,
            "debito": str(debito), "credito": str(credito)}


def _tokens_nombre(nombre):
    """Palabras significativas (≥4 letras) del nombre del cliente, sin genéricas."""
    genericas = {"sas", "ltda", "sociedad", "centro", "grupo", "colombia", "nacional"}
    return {t for t in re.findall(r"[a-záéíóúñ]{4,}", nombre.lower()) if t not in genericas}


def _nombre_en_descripcion(nombre, descripcion):
    return bool(_tokens_nombre(nombre) & _tokens_nombre(descripcion))


def sugerir(movimiento, ventas, compras, ventas_usadas, compras_usadas):
    """Sugerencia de cruce para un movimiento. Devuelve un dict con
    sugerencia, facturas vinculadas, asiento propuesto y explicación."""
    valor = movimiento["valor"]
    descripcion = movimiento["descripcion"]

    if valor > 0:  # abono
        # Cruce exacto por el neto de cartera (total - retefuente practicada)
        for venta in ventas:
            neto = venta.total - venta.retencion_practicada
            if venta.pk not in ventas_usadas and neto == valor:
                ventas_usadas.add(venta.pk)
                return {
                    "sugerencia": "pago_cliente",
                    "factura_venta": venta,
                    "asiento": [_renglon(*CUENTA_BANCOS, debito=valor),
                                _renglon(*CUENTA_CLIENTES, credito=valor)],
                    "explicacion": f"Cruza exacto con la factura {venta.numero} de "
                                   f"{venta.nombre_cliente} (neto de cartera ${neto:,.0f}).",
                }
        # Pago parcial: el nombre del cliente aparece y el valor es menor (P4.4)
        for venta in ventas:
            neto = venta.total - venta.retencion_practicada
            if valor < neto and _nombre_en_descripcion(venta.nombre_cliente, descripcion):
                return {
                    "sugerencia": "pago_cliente_parcial",
                    "factura_venta": venta,
                    "asiento": [_renglon(*CUENTA_BANCOS, debito=valor),
                                _renglon(*CUENTA_CLIENTES, credito=valor)],
                    "explicacion": f"Pago parcial de la factura {venta.numero} de "
                                   f"{venta.nombre_cliente}: ${valor:,.0f} de un neto de "
                                   f"${neto:,.0f}. No se fuerza el cruce total; el saldo "
                                   "queda en cartera.",
                }
        # Sin identificar: sugerir el cliente más probable por cercanía de valor (P4.3)
        candidata = min(
            ventas,
            key=lambda v: abs((v.total - v.retencion_practicada) - valor),
            default=None,
        )
        pista = ""
        if candidata is not None:
            neto = candidata.total - candidata.retencion_practicada
            pista = (f" Cliente más probable por valor: {candidata.nombre_cliente} "
                     f"(factura {candidata.numero}, neto ${neto:,.0f}).")
        return {
            "sugerencia": "sin_identificar",
            "explicacion": "Consignación sin identificar: no cruza con ninguna "
                           f"factura registrada.{pista}",
        }

    # cargo
    magnitud = -valor
    for patron, cuenta, nombre in GASTOS_BANCARIOS:
        if patron.search(descripcion):
            return {
                "sugerencia": "gasto_bancario",
                "asiento": [_renglon(cuenta, nombre, debito=magnitud),
                            _renglon(*CUENTA_BANCOS, credito=magnitud)],
                "explicacion": f"Gasto bancario no registrado en libros ({nombre.lower()}): "
                               f"se propone el asiento por ${magnitud:,.0f}.",
            }
    for compra in compras:
        neto = compra.total - compra.retencion
        if compra.pk not in compras_usadas and neto == magnitud:
            compras_usadas.add(compra.pk)
            # La contrapartida del pago es la misma cuenta por pagar del asiento original
            por_pagar = next(
                (r for r in compra.asiento
                 if Decimal(r["credito"]) > 0 and r["cuenta"].startswith("2")
                 and not r["cuenta"].startswith("2365")),
                None,
            )
            cuenta_pago = (por_pagar["cuenta"], por_pagar["nombre"]) if por_pagar \
                else ("2335", "Costos y gastos por pagar")
            return {
                "sugerencia": "pago_proveedor",
                "factura_compra": compra,
                "asiento": [_renglon(*cuenta_pago, debito=magnitud),
                            _renglon(*CUENTA_BANCOS, credito=magnitud)],
                "explicacion": f"Cruza exacto con el pago de la factura {compra.numero} de "
                               f"{compra.nombre_emisor} (neto ${neto:,.0f}).",
            }
    return {
        "sugerencia": "sin_identificar",
        "explicacion": "Cargo sin identificar: no es un gasto bancario conocido ni "
                       "cruza con ninguna factura de compra aprobada.",
    }

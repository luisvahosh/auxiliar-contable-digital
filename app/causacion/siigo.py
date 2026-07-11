"""
Export del asiento aprobado en CSV importable en Siigo.

Siigo (plan sin API) se alimenta por la plantilla de importación de
comprobantes contables. Columnas separadas por ';' (Excel colombiano) y
codificación utf-8-sig para que Excel abra bien las tildes.
OJO: validar contra la plantilla oficial en la primera importación real a
Siigo (criterio P1.9: "el CSV importa sin errores"); ajustar aquí lo que pida.
"""
import csv
import io

ENCABEZADOS = [
    "TIPO COMPROBANTE", "NUMERO COMPROBANTE", "FECHA",
    "CODIGO CUENTA", "DESCRIPCION", "NIT TERCERO", "NOMBRE TERCERO",
    "DEBITO", "CREDITO",
]


def generar_csv_siigo(factura):
    """CSV del asiento de una factura aprobada, un renglón por movimiento."""
    salida = io.StringIO()
    escritor = csv.writer(salida, delimiter=";", lineterminator="\r\n")
    escritor.writerow(ENCABEZADOS)
    fecha = factura.fecha_emision.strftime("%d/%m/%Y")
    descripcion = f"Causación factura {factura.numero} — {factura.nombre_emisor}"
    for renglon in factura.asiento:
        escritor.writerow([
            "CC",                      # comprobante de causación/contable
            factura.numero,
            fecha,
            renglon["cuenta"],
            descripcion,
            factura.nit_emisor,
            factura.nombre_emisor,
            renglon["debito"],
            renglon["credito"],
        ])
    return salida.getvalue()

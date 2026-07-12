"""
Cierre mensual (guía P7): la lista de chequeo que un auxiliar repasa antes
de entregarle el mes al contador.

- Todo el mes causado o en bandeja con motivo (P7.1).
- Conciliación bancaria sin movimientos pendientes (las excepciones quedan
  documentadas como partidas conciliatorias, no bloquean).
- Retenciones cuadradas (P7.2): la suma del campo retención de las facturas
  aprobadas debe coincidir con los créditos a las cuentas 2365 de sus
  asientos — esa cifra es la base del formulario 350.

No hay modelos: el cierre es una lectura transversal de lo ya registrado,
siempre filtrada por empresa (P7.3).
"""
from decimal import Decimal

from causacion.models import FacturaCompra, FacturaVenta
from conciliacion.models import MovimientoBancario


def periodos_disponibles(empresa):
    """Meses (date al día 1º) con documentos registrados, el más reciente primero."""
    meses = set(FacturaCompra.objects.de_empresa(empresa)
                .dates("fecha_emision", "month"))
    meses |= set(FacturaVenta.objects.de_empresa(empresa)
                 .dates("fecha_emision", "month"))
    return sorted(meses, reverse=True)


def resumen_cierre(empresa, anio, mes):
    compras = FacturaCompra.objects.de_empresa(empresa).filter(
        fecha_emision__year=anio, fecha_emision__month=mes)
    ventas = FacturaVenta.objects.de_empresa(empresa).filter(
        fecha_emision__year=anio, fecha_emision__month=mes)

    pendientes = ([("compra", f) for f in compras.filter(estado="pendiente")] +
                  [("venta", v) for v in ventas.filter(estado="pendiente")])
    compras_aprobadas = list(compras.filter(estado="aprobada"))
    ventas_aprobadas = list(ventas.filter(estado="aprobada"))

    # P7.2 — cuadre de retenciones (base del formulario 350)
    retenciones_por_cuenta = {}
    total_en_asientos = Decimal("0")
    for factura in compras_aprobadas:
        for renglon in factura.asiento:
            credito = Decimal(renglon["credito"])
            if renglon["cuenta"].startswith("2365") and credito > 0:
                clave = (renglon["cuenta"], renglon["nombre"])
                retenciones_por_cuenta[clave] = (
                    retenciones_por_cuenta.get(clave, Decimal("0")) + credito)
                total_en_asientos += credito
    total_en_facturas = sum((f.retencion for f in compras_aprobadas), Decimal("0"))
    retenciones_cuadran = total_en_asientos == total_en_facturas

    # Conciliación: lo pendiente bloquea; las excepciones quedan documentadas
    movimientos = MovimientoBancario.objects.de_empresa(empresa)
    movimientos_pendientes = list(movimientos.filter(estado="pendiente"))
    excepciones = list(movimientos.filter(estado="excepcion"))

    listo = (not pendientes and not movimientos_pendientes and retenciones_cuadran)

    return {
        "anio": anio,
        "mes": mes,
        "compras": list(compras),
        "ventas": list(ventas),
        "compras_aprobadas": compras_aprobadas,
        "ventas_aprobadas": ventas_aprobadas,
        "aprobadas_total": len(compras_aprobadas) + len(ventas_aprobadas),
        "pendientes": pendientes,
        "rechazadas": (compras.filter(estado="rechazada").count() +
                       ventas.filter(estado="rechazada").count()),
        "retenciones_por_cuenta": [
            {"cuenta": cuenta, "nombre": nombre, "valor": valor}
            for (cuenta, nombre), valor in sorted(retenciones_por_cuenta.items())
        ],
        "total_retenciones_asientos": total_en_asientos,
        "total_retenciones_facturas": total_en_facturas,
        "retenciones_cuadran": retenciones_cuadran,
        "movimientos_pendientes": movimientos_pendientes,
        "excepciones": excepciones,
        "listo": listo,
    }

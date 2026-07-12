"""
Cartera y edades de las cuentas por cobrar (guía P5.1).

El saldo de cada factura de venta aprobada es su neto de cartera (total menos
la retefuente que practicó el cliente) menos los pagos conciliados en bancos
(P4) y las notas crédito aprobadas. Lo pagado por completo sale solo del
reporte — la base del "no acosar" de P5.3.

Si la factura no trae fecha de vencimiento (PaymentDueDate del XML), se asume
el plazo comercial común de 30 días y el reporte lo aclara.
"""
from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Sum

from conciliacion.models import MovimientoBancario

from .models import FacturaVenta

PLAZO_PREDETERMINADO = timedelta(days=30)

RANGOS = [
    ("corriente", "Corriente"),
    ("hasta_30", "1–30 días"),
    ("hasta_60", "31–60 días"),
    ("hasta_90", "61–90 días"),
    ("mas_90", "Más de 90 días"),
]


def _rango(dias_vencida):
    if dias_vencida <= 0:
        return "corriente"
    if dias_vencida <= 30:
        return "hasta_30"
    if dias_vencida <= 60:
        return "hasta_60"
    if dias_vencida <= 90:
        return "hasta_90"
    return "mas_90"


def edades_de_cartera(empresa, hoy=None):
    """Aging de cartera: (partidas ordenadas por vencimiento, totales por rango)."""
    hoy = hoy or date.today()
    etiquetas = dict(RANGOS)
    partidas = []
    totales = {clave: Decimal("0") for clave, _ in RANGOS}

    ventas = FacturaVenta.objects.de_empresa(empresa).filter(
        tipo="venta", estado="aprobada")
    for venta in ventas:
        neto = venta.total - venta.retencion_practicada
        pagos = (MovimientoBancario.objects.de_empresa(empresa)
                 .filter(factura_venta=venta, estado="conciliado")
                 .aggregate(suma=Sum("valor"))["suma"]) or Decimal("0")
        notas = (venta.notas_credito.filter(estado="aprobada")
                 .aggregate(suma=Sum("total"))["suma"]) or Decimal("0")
        saldo = neto - pagos - notas
        if saldo <= 0:
            continue  # pagada o anulada: fuera del aging (y de los recordatorios)

        vencimiento = venta.fecha_vencimiento or (venta.fecha_emision + PLAZO_PREDETERMINADO)
        dias_vencida = (hoy - vencimiento).days
        clave = _rango(dias_vencida)
        totales[clave] += saldo
        partidas.append({
            "venta": venta,
            "neto": neto,
            "abonos": pagos + notas,
            "saldo": saldo,
            "vencimiento": vencimiento,
            "vencimiento_asumido": venta.fecha_vencimiento is None,
            "dias_vencida": dias_vencida,
            "rango": clave,
            "etiqueta": etiquetas[clave],
        })

    partidas.sort(key=lambda partida: partida["vencimiento"])
    return partidas, totales

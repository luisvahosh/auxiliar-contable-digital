"""
Avisa por correo, el mismo día, las facturas emitidas que la DIAN rechazó (P6.3).

Correr a diario (Programador de tareas de Windows por ahora; Celery beat
cuando llegue): python manage.py alertar_rechazos_dian
El estado de rechazo lo pone el ApplicationResponse de la DIAN que el auxiliar
sube o llega por el buzón (la app NO consulta la DIAN). Cada rechazo se avisa
una sola vez (rechazo_notificado).
"""
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.utils import timezone

from causacion.models import FacturaVenta
from core.models import Empresa


class Command(BaseCommand):
    help = "Avisa por correo las facturas rechazadas por la DIAN aún no notificadas."

    def handle(self, *args, **opciones):
        avisadas = 0
        for empresa in Empresa.objects.exclude(correo_alertas=""):
            rechazadas = list(FacturaVenta.objects.de_empresa(empresa).filter(
                tipo="venta", estado_dian="rechazada", rechazo_notificado__isnull=True))
            if not rechazadas:
                continue
            lineas = [
                f"- Factura {v.numero} a {v.nombre_cliente} "
                f"(${v.total:,.0f}): {v.motivo_dian or 'sin detalle'}".rstrip()
                for v in rechazadas
            ]
            send_mail(
                subject=(f"[Auxiliar Contable] {len(rechazadas)} factura(s) "
                         "RECHAZADA(S) por la DIAN"),
                message=(f"La DIAN rechazó estas facturas de {empresa.razon_social} "
                         f"(NIT {empresa.nit}):\n\n" + "\n".join(lineas) +
                         "\n\nCorrígelas y reemítelas en tu software de facturación. "
                         "Detalle en la app: Facturación → Monitoreo DIAN."),
                from_email=None,  # DEFAULT_FROM_EMAIL
                recipient_list=[empresa.correo_alertas],
            )
            ahora = timezone.now()
            for v in rechazadas:
                v.rechazo_notificado = ahora
                v.save(update_fields=["rechazo_notificado", "actualizada"])
            avisadas += len(rechazadas)
        self.stdout.write(f"Rechazos DIAN avisados: {avisadas}.")

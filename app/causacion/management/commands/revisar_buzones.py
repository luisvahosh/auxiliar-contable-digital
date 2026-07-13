"""
Revisa los buzones de correo activos y causa las facturas que lleguen
(PLAN §4). Programar a diario/por horas junto a las demás tareas:
python manage.py revisar_buzones
"""
from django.core.management.base import BaseCommand

from causacion.buzon import BuzonError, revisar_buzon
from causacion.models import BuzonCorreo


class Command(BaseCommand):
    help = "Lee las facturas de los buzones de correo activos y las causa."

    def handle(self, *args, **opciones):
        buzones = BuzonCorreo.objects.filter(activo=True).select_related("empresa")
        if not buzones:
            self.stdout.write("No hay buzones activos.")
            return
        for buzon in buzones:
            try:
                resumen = revisar_buzon(buzon)
            except BuzonError as error:
                self.stdout.write(self.style.WARNING(
                    f"{buzon.empresa.razon_social}: {error}"))
                continue
            self.stdout.write(
                f"{buzon.empresa.razon_social}: {resumen.correos} correo(s), "
                f"{resumen.creados} nueva(s), {resumen.duplicados} duplicada(s), "
                f"{resumen.errores} error(es).")
        self.stdout.write("Las facturas quedan PENDIENTES de aprobación en las bandejas.")

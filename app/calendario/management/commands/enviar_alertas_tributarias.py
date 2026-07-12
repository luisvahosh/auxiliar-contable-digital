"""
Envía por correo las alertas del calendario tributario (guía P6.2).

Correr a diario (Programador de tareas de Windows por ahora; Celery beat
cuando llegue): python manage.py enviar_alertas_tributarias
El backend de correo se configura por .env (en desarrollo: consola).
"""
from django.core.mail import send_mail
from django.core.management.base import BaseCommand

from calendario.logica import alertas_de
from core.models import Empresa


class Command(BaseCommand):
    help = "Envía por correo las alertas tributarias próximas de cada empresa."

    def handle(self, *args, **opciones):
        enviadas = 0
        for empresa in Empresa.objects.exclude(correo_alertas=""):
            alertas = alertas_de(empresa)
            if not alertas:
                continue
            lineas = []
            for item in alertas:
                v = item["vencimiento"]
                cuando = "HOY" if item["dias"] == 0 else f"en {item['dias']} día(s)"
                lineas.append(f"- {v.obligacion} ({v.periodo}): vence {cuando}, "
                              f"el {v.fecha:%d/%m/%Y}. {v.nota}".rstrip())
            send_mail(
                subject=f"[Auxiliar Contable] {len(alertas)} vencimiento(s) tributario(s) próximo(s)",
                message=(f"Vencimientos próximos para {empresa.razon_social} "
                         f"(NIT {empresa.nit}):\n\n" + "\n".join(lineas) +
                         "\n\nConfigura la anticipación de estas alertas en la app."),
                from_email=None,  # DEFAULT_FROM_EMAIL
                recipient_list=[empresa.correo_alertas],
            )
            enviadas += 1
        self.stdout.write(f"Alertas enviadas a {enviadas} empresa(s).")

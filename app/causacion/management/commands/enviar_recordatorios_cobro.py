"""
Recordatorios de cobro a clientes morosos (guía P5.2), un estado de cuenta
por cliente con todas sus facturas vencidas.

Regla "no acosar" (P5.3): la cartera descuenta sola los pagos conciliados y
las notas crédito — el cliente que ya pagó no aparece en el aging y por lo
tanto no recibe correo. Solo corre para las empresas que lo activaron
(opt-in en Empresa.enviar_recordatorios_cobro).

Correr a diario junto con las alertas tributarias:
python manage.py enviar_recordatorios_cobro
"""
from collections import defaultdict

from django.core.mail import send_mail
from django.core.management.base import BaseCommand

from causacion.cartera import edades_de_cartera
from core.models import Empresa


class Command(BaseCommand):
    help = "Envía el estado de cuenta a los clientes con facturas vencidas."

    def handle(self, *args, **opciones):
        enviados = 0
        sin_correo = 0
        for empresa in Empresa.objects.filter(enviar_recordatorios_cobro=True):
            partidas, _ = edades_de_cartera(empresa)
            por_cliente = defaultdict(list)
            for partida in partidas:
                if partida["dias_vencida"] < 1:
                    continue  # aún corriente: no se molesta al cliente
                if not partida["venta"].correo_cliente:
                    sin_correo += 1
                    continue
                clave = (partida["venta"].correo_cliente, partida["venta"].nombre_cliente)
                por_cliente[clave].append(partida)

            for (correo, nombre), vencidas in por_cliente.items():
                lineas = [
                    f"- Factura {p['venta'].numero} del {p['venta'].fecha_emision:%d/%m/%Y}: "
                    f"vencida hace {p['dias_vencida']} día(s), saldo ${p['saldo']:,.0f}"
                    for p in vencidas
                ]
                total = sum(p["saldo"] for p in vencidas)
                send_mail(
                    subject=f"Estado de cuenta — {empresa.razon_social}",
                    message=(f"Estimado cliente {nombre}:\n\n"
                             f"A la fecha presenta saldo pendiente con "
                             f"{empresa.razon_social} (NIT {empresa.nit}):\n\n"
                             + "\n".join(lineas) +
                             f"\n\nTotal pendiente: ${total:,.0f}\n\n"
                             "Si ya realizó el pago, por favor omita este mensaje: "
                             "se aplicará en la próxima conciliación."),
                    from_email=None,  # DEFAULT_FROM_EMAIL
                    recipient_list=[correo],
                )
                enviados += 1

        self.stdout.write(f"Recordatorios enviados: {enviados}. "
                          f"Facturas vencidas sin correo del cliente: {sin_correo}.")

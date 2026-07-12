"""
Pruebas del calendario tributario (casos P6.1 y P6.2).
"""
from datetime import date

from django.core import mail
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from core.models import Empresa
from core.pruebas import CasoConEmpresa

from .logica import alertas_de, digito_del_nit, vencimientos_de
from .models import VencimientoTributario

HOY = date(2026, 7, 11)


class PruebasCalendarioPorNit(CasoConEmpresa):
    def setUp(self):
        super().setUp()
        # La beta cero (NIT …7) más otro tenant con dígito distinto
        self.empresa_7 = self.empresa
        self.empresa_3 = Empresa.objects.create(nit="800111223", razon_social="OTRA SAS")
        VencimientoTributario.objects.all().delete()  # sin la semilla, control total
        VencimientoTributario.objects.create(
            obligacion="Retención en la fuente", periodo="junio 2026",
            ultimo_digito="7", fecha=date(2026, 7, 16))
        VencimientoTributario.objects.create(
            obligacion="Retención en la fuente", periodo="junio 2026",
            ultimo_digito="3", fecha=date(2026, 7, 20))
        VencimientoTributario.objects.create(
            obligacion="Renovación matrícula mercantil", periodo="2026",
            ultimo_digito="", fecha=date(2026, 7, 31))  # aplica a todos

    def test_p61_cada_tenant_ve_sus_fechas_y_no_las_del_otro(self):
        fechas_7 = [i["vencimiento"].fecha for i in vencimientos_de(self.empresa_7, HOY)]
        fechas_3 = [i["vencimiento"].fecha for i in vencimientos_de(self.empresa_3, HOY)]
        self.assertIn(date(2026, 7, 16), fechas_7)
        self.assertNotIn(date(2026, 7, 20), fechas_7)
        self.assertIn(date(2026, 7, 20), fechas_3)
        self.assertNotIn(date(2026, 7, 16), fechas_3)
        # Las obligaciones de todos los NIT aparecen en ambos
        self.assertIn(date(2026, 7, 31), fechas_7)
        self.assertIn(date(2026, 7, 31), fechas_3)

    def test_digito_del_nit(self):
        self.assertEqual(digito_del_nit("901234567"), "7")
        self.assertEqual(digito_del_nit(" 800111223 "), "3")

    def test_la_pagina_renderiza_con_alertas(self):
        respuesta = self.client.get(reverse("calendario:calendario"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Calendario tributario")


class PruebasAlertas(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.get(nit="901234567")
        VencimientoTributario.objects.all().delete()
        VencimientoTributario.objects.create(
            obligacion="Retención en la fuente", periodo="junio 2026",
            ultimo_digito="7", fecha=date(2026, 7, 16))  # en 5 días desde HOY

    def test_p62_alerta_con_la_anticipacion_configurada(self):
        self.empresa.dias_anticipacion_alertas = 5
        self.empresa.save()
        self.assertEqual(len(alertas_de(self.empresa, HOY)), 1)
        # Con menos anticipación, aún no alerta (configurable por empresa)
        self.empresa.dias_anticipacion_alertas = 3
        self.empresa.save()
        self.assertEqual(len(alertas_de(self.empresa, HOY)), 0)

    def test_p62_el_correo_incluye_obligacion_y_destinatario(self):
        from datetime import timedelta
        VencimientoTributario.objects.create(
            obligacion="IVA bimestral", periodo="prueba",
            ultimo_digito="7", fecha=date.today() + timedelta(days=2))
        self.empresa.correo_alertas = "contadora@learnway.example.com"
        self.empresa.dias_anticipacion_alertas = 5
        self.empresa.save()
        call_command("enviar_alertas_tributarias")
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("contadora@learnway.example.com", mail.outbox[0].to)
        self.assertIn("IVA bimestral", mail.outbox[0].body)

    def test_sin_correo_configurado_no_se_envia_nada(self):
        call_command("enviar_alertas_tributarias")
        self.assertEqual(len(mail.outbox), 0)


class PruebasSemilla(TestCase):
    def test_la_semilla_2026_cubre_los_diez_digitos(self):
        digitos = set(VencimientoTributario.objects
                      .filter(obligacion="Retención en la fuente")
                      .values_list("ultimo_digito", flat=True))
        self.assertEqual(digitos, set("0123456789"))
        # Todas las fechas estimadas caen en día hábil
        for vencimiento in VencimientoTributario.objects.exclude(ultimo_digito=""):
            self.assertLess(vencimiento.fecha.weekday(), 5)

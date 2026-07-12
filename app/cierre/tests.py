"""
Pruebas del cierre mensual (casos P7 de PROCESO-AUXILIAR-CONTABLE.md).
"""
import io
import zipfile
from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from causacion.models import FacturaCompra, FacturaVenta
from core.models import Empresa

from .logica import resumen_cierre
from .paquete import construir_paquete


def compra(empresa, numero, estado="aprobada", retencion="200000"):
    return FacturaCompra.objects.create(
        empresa=empresa, cufe=numero.lower() * 12, numero=numero,
        fecha_emision=date(2026, 6, 15), nit_emisor="79456123",
        nombre_emisor="CARLOS PÉREZ", tipo_persona_emisor="2",
        subtotal=2000000, iva=380000, total=2380000, retencion=retencion,
        cuenta_puc="5110", nombre_cuenta_puc="Honorarios",
        estado=estado, explicacion="motivo de prueba", xml_crudo="<Invoice/>",
        asiento=[
            {"cuenta": "5110", "nombre": "Honorarios", "debito": "2000000", "credito": "0"},
            {"cuenta": "240802", "nombre": "IVA descontable", "debito": "380000", "credito": "0"},
            {"cuenta": "236515", "nombre": "Retefuente honorarios", "debito": "0", "credito": str(retencion)},
            {"cuenta": "2335", "nombre": "Costos y gastos por pagar", "debito": "0",
             "credito": str(2380000 - int(retencion))},
        ])


def venta(empresa, numero, estado="aprobada"):
    return FacturaVenta.objects.create(
        empresa=empresa, tipo="venta", cufe=numero.lower() * 12, numero=numero,
        fecha_emision=date(2026, 6, 20), nit_cliente="860222333",
        nombre_cliente="COMERCIALIZADORA ANDINA", subtotal=3000000, iva=570000,
        total=3570000, estado=estado, explicacion="motivo venta", xml_crudo="<Invoice/>",
        asiento=[
            {"cuenta": "1305", "nombre": "Clientes", "debito": "3570000", "credito": "0"},
            {"cuenta": "4135", "nombre": "Ingresos", "debito": "0", "credito": "3000000"},
            {"cuenta": "240801", "nombre": "IVA generado", "debito": "0", "credito": "570000"},
        ])


class PruebasResumen(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.get(nit="901234567")

    def test_p71_pendientes_bloquean_y_aparecen_con_motivo(self):
        compra(self.empresa, "AA-1")
        compra(self.empresa, "BB-2", estado="pendiente")
        resumen = resumen_cierre(self.empresa, 2026, 6)
        self.assertFalse(resumen["listo"])
        self.assertEqual(len(resumen["pendientes"]), 1)
        respuesta = self.client.get(reverse("cierre:cierre") + "?periodo=2026-06")
        self.assertContains(respuesta, "Con pendientes")
        self.assertContains(respuesta, "BB-2")
        self.assertContains(respuesta, "motivo de prueba")

    def test_p71_sin_pendientes_queda_listo(self):
        compra(self.empresa, "AA-1")
        venta(self.empresa, "FE-104")
        resumen = resumen_cierre(self.empresa, 2026, 6)
        self.assertTrue(resumen["listo"])
        respuesta = self.client.get(reverse("cierre:cierre") + "?periodo=2026-06")
        self.assertContains(respuesta, "Listo para entrega")

    def test_p72_retenciones_cuadran_contra_asientos(self):
        compra(self.empresa, "AA-1")
        compra(self.empresa, "CC-3")
        resumen = resumen_cierre(self.empresa, 2026, 6)
        self.assertEqual(resumen["total_retenciones_asientos"], Decimal("400000"))
        self.assertEqual(resumen["total_retenciones_facturas"], Decimal("400000"))
        self.assertTrue(resumen["retenciones_cuadran"])
        self.assertEqual(resumen["retenciones_por_cuenta"][0]["cuenta"], "236515")

    def test_p72_descuadre_se_detecta(self):
        factura = compra(self.empresa, "AA-1")
        factura.retencion = Decimal("999")  # dato corrupto a propósito
        factura.save()
        resumen = resumen_cierre(self.empresa, 2026, 6)
        self.assertFalse(resumen["retenciones_cuadran"])
        self.assertFalse(resumen["listo"])

    def test_solo_cuenta_el_mes_pedido(self):
        factura = compra(self.empresa, "AA-1")
        factura.fecha_emision = date(2026, 5, 30)
        factura.save()
        resumen = resumen_cierre(self.empresa, 2026, 6)
        self.assertEqual(len(resumen["compras"]), 0)


class PruebasPaquete(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.get(nit="901234567")
        compra(self.empresa, "AA-1")
        venta(self.empresa, "FE-104")

    def zip_del_paquete(self):
        _, contenido = construir_paquete(self.empresa, 2026, 6)
        return zipfile.ZipFile(io.BytesIO(contenido))

    def test_p71_el_paquete_trae_resumen_auxiliares_y_soportes(self):
        paquete = self.zip_del_paquete()
        nombres = paquete.namelist()
        self.assertIn("resumen-cierre-2026-06.txt", nombres)
        self.assertIn("auxiliar-por-cuenta-2026-06.csv", nombres)
        self.assertIn("auxiliar-por-tercero-2026-06.csv", nombres)
        self.assertIn("siigo-consolidado-2026-06.csv", nombres)
        self.assertIn("soportes/AA-1.xml", nombres)
        self.assertIn("soportes/FE-104.xml", nombres)
        auxiliar = paquete.read("auxiliar-por-cuenta-2026-06.csv").decode("utf-8-sig")
        self.assertIn("5110", auxiliar)
        self.assertIn("1305", auxiliar)
        resumen = paquete.read("resumen-cierre-2026-06.txt").decode("utf-8-sig")
        self.assertIn("LISTO PARA ENTREGA", resumen)
        self.assertIn("236515", resumen)

    def test_la_descarga_web_responde_zip(self):
        respuesta = self.client.get(reverse("cierre:paquete") + "?periodo=2026-06")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta["Content-Type"], "application/zip")
        self.assertIn("paquete-cierre-901234567-2026-06.zip",
                      respuesta["Content-Disposition"])

    def test_p73_el_paquete_no_mezcla_tenants(self):
        otra = Empresa.objects.create(nit="800111222", razon_social="OTRA SAS")
        compra(otra, "ZZ-99")
        paquete = self.zip_del_paquete()
        self.assertNotIn("soportes/ZZ-99.xml", paquete.namelist())
        auxiliar = paquete.read("auxiliar-por-cuenta-2026-06.csv").decode("utf-8-sig")
        self.assertNotIn("ZZ-99", auxiliar)

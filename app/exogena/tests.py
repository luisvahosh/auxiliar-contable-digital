"""
Pruebas del pre-armado de exógena (casos P12).
"""
from datetime import date
from decimal import Decimal

from django.urls import reverse

from causacion.models import FacturaCompra, FacturaVenta
from core.pruebas import CasoConEmpresa
from nomina.models import LiquidacionNomina

from .logica import formato_1001, formato_1007, formato_2276


def compra(empresa, numero, nit, concepto, base, retencion="0", anio=2026,
           estado="aprobada", tipo="compra", original=None):
    base, retencion = Decimal(base), Decimal(retencion)
    return FacturaCompra.objects.create(
        empresa=empresa, tipo=tipo, factura_original=original,
        cufe=(numero + "z" * 30)[:40], numero=numero,
        fecha_emision=date(anio, 6, 15), nit_emisor=nit,
        nombre_emisor=f"Proveedor {nit}", tipo_persona_emisor="1",
        subtotal=base, iva=0, total=base, retencion=retencion,
        cuenta_puc="5110", nombre_cuenta_puc="x", concepto_retencion=concepto,
        estado=estado, explicacion="x", asiento=[], xml_crudo="<x/>")


def venta(empresa, numero, nit, base, anio=2026, estado="aprobada",
          tipo="venta", original=None):
    base = Decimal(base)
    return FacturaVenta.objects.create(
        empresa=empresa, tipo=tipo, factura_original=original,
        cufe=(numero + "y" * 30)[:40], numero=numero,
        fecha_emision=date(anio, 6, 20), nit_cliente=nit,
        nombre_cliente=f"Cliente {nit}", subtotal=base, iva=0, total=base,
        estado=estado, explicacion="x", asiento=[], xml_crudo="<x/>")


class PruebasFormato1001(CasoConEmpresa):
    def test_p121_pagos_y_retenciones_por_tercero_con_concepto(self):
        compra(self.empresa, "F-1", "901111111", "honorarios", "2000000", "200000")
        compra(self.empresa, "F-2", "901111111", "honorarios", "1000000", "100000")
        compra(self.empresa, "F-3", "800222222", "servicios", "500000", "20000")
        datos = formato_1001(self.empresa, 2026)
        por_nit = {f["nit"]: f for f in datos["filas"]}
        self.assertEqual(por_nit["901111111"]["base"], Decimal("3000000"))
        self.assertEqual(por_nit["901111111"]["retencion"], Decimal("300000"))
        self.assertEqual(por_nit["901111111"]["concepto"], "5001")  # honorarios
        self.assertEqual(por_nit["800222222"]["concepto"], "5004")  # servicios

    def test_p123_solo_aprobadas_y_del_anio(self):
        compra(self.empresa, "F-1", "901111111", "honorarios", "2000000")
        compra(self.empresa, "F-2", "901111111", "honorarios", "9000000", estado="pendiente")
        compra(self.empresa, "F-3", "901111111", "honorarios", "5000000", anio=2025)
        datos = formato_1001(self.empresa, 2026)
        self.assertEqual(datos["total_base"], Decimal("2000000"))

    def test_p126_nota_credito_descuenta(self):
        orig = compra(self.empresa, "F-1", "901111111", "honorarios", "2000000", "200000")
        compra(self.empresa, "NC-1", "901111111", "honorarios", "500000",
               tipo="nota_credito", original=orig)
        datos = formato_1001(self.empresa, 2026)
        self.assertEqual(datos["filas"][0]["base"], Decimal("1500000"))


class PruebasFormato1007(CasoConEmpresa):
    def test_p122_ingresos_por_cliente(self):
        venta(self.empresa, "FE-1", "860111111", "3000000")
        venta(self.empresa, "FE-2", "860111111", "2000000")
        venta(self.empresa, "FE-3", "890222222", "1000000")
        datos = formato_1007(self.empresa, 2026)
        por_nit = {f["nit"]: f for f in datos["filas"]}
        self.assertEqual(por_nit["860111111"]["ingreso"], Decimal("5000000"))
        self.assertEqual(por_nit["860111111"]["concepto"], "4001")
        self.assertEqual(datos["total"], Decimal("6000000"))

    def test_p126_nota_credito_venta_descuenta(self):
        original = venta(self.empresa, "FE-1", "860111111", "3000000")
        venta(self.empresa, "NC-1", "860111111", "500000",
              tipo="nota_credito", original=original)
        datos = formato_1007(self.empresa, 2026)
        self.assertEqual(datos["filas"][0]["ingreso"], Decimal("2500000"))


def liquidacion(empresa, mes, empleados, anio=2026, estado="aprobada"):
    """empleados = [(cedula, nombre, devengado, salud, pension), ...]"""
    detalle = [{"cedula": c, "empleado": n, "devengado": str(d),
                "salud_empleado": str(s), "pension_empleado": str(p)}
               for c, n, d, s, p in empleados]
    return LiquidacionNomina.objects.create(
        empresa=empresa, anio=anio, mes=mes, estado=estado, detalle=detalle,
        total_devengado=0, total_deducciones=0, total_neto=0,
        total_aportes_empleador=0, total_provisiones=0, asiento=[], explicacion="x")


class PruebasFormato2276(CasoConEmpresa):
    def test_p12_rentas_de_trabajo_suma_los_meses_por_empleado(self):
        liquidacion(self.empresa, 6, [("100", "Ana", "1800000", "64940", "64940")])
        liquidacion(self.empresa, 7, [("100", "Ana", "1800000", "64940", "64940"),
                                      ("200", "Beto", "3000000", "120000", "120000")])
        datos = formato_2276(self.empresa, 2026)
        por_ced = {f["nit"]: f for f in datos["filas"]}
        self.assertEqual(por_ced["100"]["pagos"], Decimal("3600000"))  # 2 meses
        self.assertEqual(por_ced["100"]["salud"], Decimal("129880"))
        self.assertEqual(por_ced["100"]["tipo_doc"], "13")  # cédula
        self.assertEqual(datos["totales"]["pagos"], Decimal("6600000"))

    def test_solo_aprobadas_y_del_anio(self):
        liquidacion(self.empresa, 6, [("100", "Ana", "1800000", "64940", "64940")])
        liquidacion(self.empresa, 7, [("100", "Ana", "9000000", "0", "0")],
                    estado="pendiente")
        liquidacion(self.empresa, 6, [("100", "Ana", "5000000", "0", "0")], anio=2025)
        datos = formato_2276(self.empresa, 2026)
        self.assertEqual(datos["totales"]["pagos"], Decimal("1800000"))

    def test_export_2276_csv(self):
        liquidacion(self.empresa, 6, [("100", "Ana Prueba", "1800000", "64940", "64940")])
        respuesta = self.client.get(reverse("exogena:exportar_2276") + "?anio=2026")
        self.assertEqual(respuesta.status_code, 200)
        cuerpo = respuesta.content.decode("utf-8-sig")
        self.assertIn("Ana Prueba", cuerpo)
        self.assertIn("1800000", cuerpo)
        self.assertIn("RETENCION EN LA FUENTE", cuerpo)  # casilla que completa el operador


class PruebasExportYCuadre(CasoConEmpresa):
    def test_p124_cuadra_con_libros(self):
        compra(self.empresa, "F-1", "901111111", "honorarios", "2000000", "200000")
        compra(self.empresa, "F-2", "800222222", "servicios", "1000000", "40000")
        venta(self.empresa, "FE-1", "860111111", "5000000")
        # 1001 total = compras del año; 1007 total = ventas del año
        self.assertEqual(formato_1001(self.empresa, 2026)["total_base"],
                         Decimal("3000000"))
        self.assertEqual(formato_1007(self.empresa, 2026)["total"],
                         Decimal("5000000"))

    def test_p125_export_csv(self):
        compra(self.empresa, "F-1", "901111111", "honorarios", "2000000", "200000")
        respuesta = self.client.get(reverse("exogena:exportar_1001") + "?anio=2026")
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn("text/csv", respuesta["Content-Type"])
        cuerpo = respuesta.content.decode("utf-8-sig")
        self.assertIn("901111111", cuerpo)
        self.assertIn("5001", cuerpo)
        self.assertIn("2000000", cuerpo)

    def test_el_panel_renderiza(self):
        respuesta = self.client.get(reverse("exogena:panel"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Formato 1001")
        self.assertContains(respuesta, "Formato 2276")
        self.assertContains(respuesta, "prevalidador")

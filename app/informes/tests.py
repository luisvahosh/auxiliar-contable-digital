"""
Pruebas de informes contables (casos P13).
"""
from datetime import date
from decimal import Decimal

from django.urls import reverse

from core.models import Empresa
from core.pruebas import CasoConEmpresa

from .logica import balance_comprobacion, estado_resultados, libro_mayor


def compra(empresa, numero, anio=2026, mes=6, estado="aprobada"):
    from causacion.models import FacturaCompra
    return FacturaCompra.objects.create(
        empresa=empresa, cufe=(numero + "z" * 30)[:40], numero=numero,
        fecha_emision=date(anio, mes, 15), nit_emisor="79456123",
        nombre_emisor="Proveedor", tipo_persona_emisor="2",
        subtotal=2000000, iva=380000, total=2380000, retencion=200000,
        cuenta_puc="5110", nombre_cuenta_puc="Honorarios", estado=estado,
        explicacion="x", xml_crudo="<x/>",
        asiento=[
            {"cuenta": "511005", "nombre": "Honorarios", "debito": "2000000", "credito": "0"},
            {"cuenta": "240802", "nombre": "IVA descontable", "debito": "380000", "credito": "0"},
            {"cuenta": "236515", "nombre": "Retefuente", "debito": "0", "credito": "200000"},
            {"cuenta": "233595", "nombre": "Costos y gastos por pagar", "debito": "0", "credito": "2180000"},
        ])


def venta(empresa, numero, anio=2026, mes=6, estado="aprobada"):
    from causacion.models import FacturaVenta
    return FacturaVenta.objects.create(
        empresa=empresa, tipo="venta", cufe=(numero + "y" * 30)[:40], numero=numero,
        fecha_emision=date(anio, mes, 20), nit_cliente="860222333",
        nombre_cliente="Cliente", subtotal=5000000, iva=950000, total=5950000,
        estado=estado, explicacion="x", xml_crudo="<x/>",
        asiento=[
            {"cuenta": "130505", "nombre": "Clientes", "debito": "5950000", "credito": "0"},
            {"cuenta": "413505", "nombre": "Ingresos", "debito": "0", "credito": "5000000"},
            {"cuenta": "240801", "nombre": "IVA generado", "debito": "0", "credito": "950000"},
        ])


class PruebasBalance(CasoConEmpresa):
    def test_p131_balance_cuadra(self):
        compra(self.empresa, "F-1")
        venta(self.empresa, "FE-1")
        bal = balance_comprobacion(self.empresa, 2026)
        self.assertTrue(bal["cuadra"])
        self.assertEqual(bal["total_debito"], bal["total_credito"])
        # 2.380.000 (compra) + 5.950.000 (venta) = 8.330.000
        self.assertEqual(bal["total_debito"], Decimal("8330000"))

    def test_p132_solo_aprobados_y_del_periodo(self):
        compra(self.empresa, "F-1")
        compra(self.empresa, "F-2", estado="pendiente")
        compra(self.empresa, "F-3", anio=2025)
        bal = balance_comprobacion(self.empresa, 2026)
        # Solo la aprobada de 2026: 2.380.000
        self.assertEqual(bal["total_debito"], Decimal("2380000"))

    def test_filtra_por_mes(self):
        compra(self.empresa, "F-1", mes=6)
        compra(self.empresa, "F-2", mes=7)
        self.assertEqual(balance_comprobacion(self.empresa, 2026, 6)["total_debito"],
                         Decimal("2380000"))
        self.assertEqual(balance_comprobacion(self.empresa, 2026)["total_debito"],
                         Decimal("4760000"))


class PruebasEstadoResultados(CasoConEmpresa):
    def test_p133_ingresos_menos_gastos(self):
        compra(self.empresa, "F-1")   # gasto 511005 = 2.000.000
        venta(self.empresa, "FE-1")   # ingreso 413505 = 5.000.000
        er = estado_resultados(self.empresa, 2026)
        self.assertEqual(er["ingresos"], Decimal("5000000"))
        self.assertEqual(er["gastos"], Decimal("2000000"))
        self.assertEqual(er["utilidad"], Decimal("3000000"))


class PruebasConsolidaModulos(CasoConEmpresa):
    def test_p135_incluye_nomina_activos_caja(self):
        from activos.models import DepreciacionMensual
        from cajamenor.models import CajaMenor, ReembolsoCajaMenor
        from nomina.models import LiquidacionNomina
        LiquidacionNomina.objects.create(
            empresa=self.empresa, anio=2026, mes=6, estado="aprobada",
            total_devengado=1000000, total_deducciones=80000, total_neto=920000,
            total_aportes_empleador=0, total_provisiones=0, explicacion="x",
            asiento=[{"cuenta": "510506", "nombre": "Sueldos", "debito": "1000000", "credito": "0"},
                     {"cuenta": "250505", "nombre": "Salarios x pagar", "debito": "0", "credito": "1000000"}])
        DepreciacionMensual.objects.create(
            empresa=self.empresa, anio=2026, mes=6, estado="aprobada", total=100000,
            explicacion="x",
            asiento=[{"cuenta": "516020", "nombre": "Gasto dep", "debito": "100000", "credito": "0"},
                     {"cuenta": "159220", "nombre": "Dep acum", "debito": "0", "credito": "100000"}])
        caja = CajaMenor.objects.create(empresa=self.empresa, nombre="CM",
                                        monto_fijo=500000)
        ReembolsoCajaMenor.objects.create(
            empresa=self.empresa, caja=caja, estado="aprobado", total=50000,
            explicacion="x",
            asiento=[{"cuenta": "519530", "nombre": "Papelería", "debito": "50000", "credito": "0"},
                     {"cuenta": "111005", "nombre": "Bancos", "debito": "0", "credito": "50000"}])
        bal = balance_comprobacion(self.empresa, 2026)
        cuentas = {f["cuenta"] for f in bal["filas"]}
        self.assertIn("510506", cuentas)  # nómina
        self.assertIn("516020", cuentas)  # depreciación
        self.assertIn("519530", cuentas)  # caja menor
        self.assertTrue(bal["cuadra"])


class PruebasLibroMayorYExport(CasoConEmpresa):
    def test_p134_libro_mayor_por_cuenta(self):
        compra(self.empresa, "F-1")
        compra(self.empresa, "F-2")
        filas = libro_mayor(self.empresa, "511005", 2026)
        self.assertEqual(len(filas), 2)
        self.assertEqual(filas[-1]["saldo"], Decimal("4000000"))  # saldo corriente
        origenes = " ".join(f["origen"] for f in filas)
        self.assertIn("F-1", origenes)
        self.assertIn("F-2", origenes)

    def test_p136_export_csv(self):
        compra(self.empresa, "F-1")
        respuesta = self.client.get(reverse("informes:exportar_balance") + "?anio=2026")
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn("text/csv", respuesta["Content-Type"])
        cuerpo = respuesta.content.decode("utf-8-sig")
        self.assertIn("511005", cuerpo)
        self.assertIn("TOTALES", cuerpo)

    def test_la_vista_balance_renderiza(self):
        compra(self.empresa, "F-1")
        respuesta = self.client.get(reverse("informes:balance") + "?anio=2026")
        self.assertContains(respuesta, "Balance de comprobación")
        self.assertContains(respuesta, "Cuadra")

    def test_aislado_por_tenant(self):
        otra = Empresa.objects.create(nit="800111222", razon_social="OTRA SAS")
        compra(otra, "AJENA-1")
        self.assertEqual(balance_comprobacion(self.empresa, 2026)["filas"], [])

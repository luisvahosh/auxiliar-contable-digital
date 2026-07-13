"""
Pruebas de activos fijos y depreciación (casos P10).
"""
from datetime import date
from decimal import Decimal

from django.urls import reverse

from core.models import Empresa
from core.pruebas import CasoConEmpresa

from .calculo import depreciar_mes
from .models import ActivoFijo, DepreciacionMensual


def activo_de(empresa, nombre="Portátil", categoria="equipo_computo",
              costo="6000000", residual="0", fecha="2025-01-10", acumulada="0"):
    return ActivoFijo.objects.create(
        empresa=empresa, nombre=nombre, categoria=categoria,
        fecha_adquisicion=date.fromisoformat(fecha), costo=Decimal(costo),
        valor_residual=Decimal(residual), depreciacion_acumulada=Decimal(acumulada))


class PruebasCalculoDepreciacion(CasoConEmpresa):
    def test_p101_linea_recta_cuota_y_asiento(self):
        activo_de(self.empresa)  # 6.000.000 / 60 meses = 100.000
        resultado = depreciar_mes(
            self.empresa, list(ActivoFijo.objects.de_empresa(self.empresa)), 2026, 7)
        self.assertEqual(resultado["total"], Decimal("100000"))
        cuentas = {r["cuenta"] for r in resultado["asiento"]}
        self.assertIn("516020", cuentas)   # gasto depreciación cómputo
        self.assertIn("159220", cuentas)   # depreciación acumulada cómputo
        debitos = sum(Decimal(r["debito"]) for r in resultado["asiento"])
        creditos = sum(Decimal(r["credito"]) for r in resultado["asiento"])
        self.assertEqual(debitos, creditos)

    def test_p102_no_pasa_del_valor_depreciable(self):
        # Ya lleva 5.950.000 de 6.000.000: la última cuota es solo 50.000
        activo_de(self.empresa, acumulada="5950000")
        resultado = depreciar_mes(
            self.empresa, list(ActivoFijo.objects.de_empresa(self.empresa)), 2026, 7)
        self.assertEqual(resultado["total"], Decimal("50000"))

    def test_p102_totalmente_depreciado_no_genera(self):
        activo_de(self.empresa, acumulada="6000000")
        resultado = depreciar_mes(
            self.empresa, list(ActivoFijo.objects.de_empresa(self.empresa)), 2026, 7)
        self.assertEqual(resultado["detalle"], [])

    def test_p104_valor_residual_reduce_la_base(self):
        # (6.000.000 - 600.000) / 60 = 90.000
        activo_de(self.empresa, residual="600000")
        resultado = depreciar_mes(
            self.empresa, list(ActivoFijo.objects.de_empresa(self.empresa)), 2026, 7)
        self.assertEqual(resultado["total"], Decimal("90000"))

    def test_p105_no_deprecia_antes_de_adquirir(self):
        activo_de(self.empresa, fecha="2026-08-15")  # comprado en agosto
        resultado = depreciar_mes(
            self.empresa, list(ActivoFijo.objects.de_empresa(self.empresa)), 2026, 7)
        self.assertEqual(resultado["detalle"], [])  # julio: aún no existía


class PruebasFlujoDepreciacion(CasoConEmpresa):
    def setUp(self):
        super().setUp()
        activo_de(self.empresa)

    def depreciar(self, periodo="2026-07"):
        return self.client.post(reverse("activos:depreciar"),
                                {"periodo": periodo}, follow=True)

    def test_aprobar_actualiza_el_valor_en_libros(self):
        self.depreciar()
        dep = DepreciacionMensual.objects.de_empresa(self.empresa).get()
        self.assertEqual(dep.estado, "pendiente")
        self.client.post(reverse("activos:decidir", args=[dep.pk, "aprobada"]))
        activo = ActivoFijo.objects.de_empresa(self.empresa).get()
        self.assertEqual(activo.depreciacion_acumulada, Decimal("100000"))
        self.assertEqual(activo.valor_en_libros, Decimal("5900000"))

    def test_p103_un_mes_una_depreciacion(self):
        self.depreciar()
        respuesta = self.depreciar()
        self.assertContains(respuesta, "ya existe")
        self.assertEqual(DepreciacionMensual.objects.de_empresa(self.empresa).count(), 1)

    def test_rechazar_no_afecta_libros(self):
        self.depreciar()
        dep = DepreciacionMensual.objects.de_empresa(self.empresa).get()
        self.client.post(reverse("activos:decidir", args=[dep.pk, "rechazada"]))
        activo = ActivoFijo.objects.de_empresa(self.empresa).get()
        self.assertEqual(activo.depreciacion_acumulada, Decimal("0"))

    def test_dos_meses_seguidos_acumulan(self):
        self.depreciar("2026-07")
        dep1 = DepreciacionMensual.objects.de_empresa(self.empresa).get(mes=7)
        self.client.post(reverse("activos:decidir", args=[dep1.pk, "aprobada"]))
        self.depreciar("2026-08")
        dep2 = DepreciacionMensual.objects.de_empresa(self.empresa).get(mes=8)
        self.client.post(reverse("activos:decidir", args=[dep2.pk, "aprobada"]))
        activo = ActivoFijo.objects.de_empresa(self.empresa).get()
        self.assertEqual(activo.depreciacion_acumulada, Decimal("200000"))

    def test_activos_aislados_por_tenant(self):
        otra = Empresa.objects.create(nit="800111222", razon_social="OTRA SAS")
        self.assertEqual(ActivoFijo.objects.de_empresa(otra).count(), 0)
        self.assertEqual(ActivoFijo.objects.de_empresa(self.empresa).count(), 1)

    def test_crear_activo_por_la_vista(self):
        respuesta = self.client.post(reverse("activos:activo_nuevo"), {
            "nombre": "Camioneta", "categoria": "vehiculos",
            "fecha_adquisicion": "2026-01-01", "costo": "80000000",
            "valor_residual": "0", "activo": "on"}, follow=True)
        self.assertContains(respuesta, "Camioneta")
        self.assertEqual(ActivoFijo.objects.de_empresa(self.empresa).count(), 2)

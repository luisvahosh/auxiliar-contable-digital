"""
Pruebas de caja menor (casos P11).
"""
from datetime import date
from decimal import Decimal

from django.urls import reverse

from core.models import Empresa
from core.pruebas import CasoConEmpresa

from .models import CajaMenor, GastoCajaMenor, ReembolsoCajaMenor


class BaseCajaMenor(CasoConEmpresa):
    def setUp(self):
        super().setUp()
        self.caja = CajaMenor.objects.create(
            empresa=self.empresa, nombre="Caja principal",
            responsable="Ana", monto_fijo=Decimal("500000"))

    def vale(self, base, iva="0", categoria="cm_papeleria", concepto="Papel"):
        base, iva = Decimal(base), Decimal(iva)
        return GastoCajaMenor.objects.create(
            empresa=self.empresa, caja=self.caja, fecha=date(2026, 7, 10),
            categoria=categoria, concepto=concepto, base=base, iva=iva,
            total=base + iva)


class PruebasCajaMenor(BaseCajaMenor):
    def test_p111_constitucion_asiento(self):
        from causacion.plan_cuentas import plan_de_empresa
        from .logica import asiento_constitucion
        asiento = asiento_constitucion(self.caja, plan_de_empresa(self.empresa))
        cuentas = {r["cuenta"] for r in asiento}
        self.assertIn("110505", cuentas)  # caja menor
        self.assertIn("111005", cuentas)  # bancos
        self.assertEqual(Decimal(asiento[0]["debito"]), Decimal("500000"))

    def test_p112_vale_baja_el_efectivo(self):
        self.vale("50000", iva="9500")
        self.caja.refresh_from_db()
        self.assertEqual(self.caja.efectivo_disponible, Decimal("440500"))
        self.assertEqual(self.caja.total_vales_pendientes, Decimal("59500"))

    def test_p113_arqueo_cuadra(self):
        self.vale("100000")
        self.vale("50000", iva="9500")
        # efectivo + vales pendientes = monto fijo
        self.assertEqual(self.caja.efectivo_disponible + self.caja.total_vales_pendientes,
                         self.caja.monto_fijo)

    def test_p114_reembolso_legaliza_y_cuadra(self):
        self.vale("100000", categoria="cm_papeleria")
        self.vale("60000", iva="11400", categoria="cm_transporte")
        respuesta = self.client.post(reverse("cajamenor:reembolsar",
                                             args=[self.caja.pk]), follow=True)
        reembolso = ReembolsoCajaMenor.objects.de_empresa(self.empresa).get()
        self.assertEqual(reembolso.total, Decimal("171400"))
        cuentas = {r["cuenta"] for r in reembolso.asiento}
        self.assertIn("519530", cuentas)  # papelería
        self.assertIn("519525", cuentas)  # transporte
        self.assertIn("240802", cuentas)  # IVA descontable
        self.assertIn("111005", cuentas)  # bancos
        debitos = sum(Decimal(r["debito"]) for r in reembolso.asiento)
        creditos = sum(Decimal(r["credito"]) for r in reembolso.asiento)
        self.assertEqual(debitos, creditos)
        # Los vales quedan vinculados: el fondo vuelve a su monto
        self.caja.refresh_from_db()
        self.assertEqual(self.caja.efectivo_disponible, self.caja.monto_fijo)

    def test_p115_no_exceder_el_fondo(self):
        respuesta = self.client.post(reverse("cajamenor:detalle", args=[self.caja.pk]), {
            "fecha": "2026-07-10", "categoria": "cm_otros",
            "concepto": "Muy caro", "base": "600000", "iva": "0"}, follow=True)
        self.assertContains(respuesta, "supera el efectivo disponible")
        self.assertEqual(GastoCajaMenor.objects.de_empresa(self.empresa).count(), 0)

    def test_p116_reembolso_requiere_aprobacion(self):
        self.vale("100000")
        self.client.post(reverse("cajamenor:reembolsar", args=[self.caja.pk]))
        reembolso = ReembolsoCajaMenor.objects.de_empresa(self.empresa).get()
        self.assertEqual(reembolso.estado, "pendiente")
        self.client.post(reverse("cajamenor:decidir",
                                 args=[reembolso.pk, "aprobado"]))
        reembolso.refresh_from_db()
        self.assertEqual(reembolso.estado, "aprobado")

    def test_rechazar_devuelve_los_vales_a_pendientes(self):
        self.vale("100000")
        self.client.post(reverse("cajamenor:reembolsar", args=[self.caja.pk]))
        reembolso = ReembolsoCajaMenor.objects.de_empresa(self.empresa).get()
        self.client.post(reverse("cajamenor:decidir",
                                 args=[reembolso.pk, "rechazado"]))
        self.caja.refresh_from_db()
        # El vale vuelve a pendiente: el efectivo baja de nuevo
        self.assertEqual(self.caja.total_vales_pendientes, Decimal("100000"))

    def test_registrar_vale_por_la_vista(self):
        respuesta = self.client.post(reverse("cajamenor:detalle", args=[self.caja.pk]), {
            "fecha": "2026-07-10", "categoria": "cm_cafeteria",
            "concepto": "Café", "base": "30000", "iva": "0"}, follow=True)
        self.assertContains(respuesta, "registrado")
        self.assertEqual(GastoCajaMenor.objects.de_empresa(self.empresa).count(), 1)

    def test_aislada_por_tenant(self):
        otra = Empresa.objects.create(nit="800111222", razon_social="OTRA SAS")
        self.assertEqual(CajaMenor.objects.de_empresa(otra).count(), 0)
        self.assertEqual(CajaMenor.objects.de_empresa(self.empresa).count(), 1)

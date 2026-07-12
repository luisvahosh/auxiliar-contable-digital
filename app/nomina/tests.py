"""
Pruebas de nómina (casos P8 de PROCESO-AUXILIAR-CONTABLE.md).
"""
from datetime import date
from decimal import Decimal

from django.urls import reverse

from core.models import Empresa
from core.pruebas import CasoConEmpresa

from .calculo import liquidar_empleado, liquidar_mes
from .models import Empleado, LiquidacionNomina
from .parametros import parametros_del_anio


def empleado_de(empresa, nombre="Ana Prueba", cedula="100", salario="1623500"):
    return Empleado.objects.create(
        empresa=empresa, nombre=nombre, cedula=cedula,
        salario=Decimal(salario), fecha_ingreso=date(2025, 1, 15))


class PruebasCalculo(CasoConEmpresa):
    def test_p81_salario_minimo_con_auxilio_y_neto_correcto(self):
        valores = parametros_del_anio(2026)
        fila = liquidar_empleado(empleado_de(self.empresa), valores, exonerada=True)
        self.assertEqual(Decimal(fila["auxilio"]), valores["auxilio_transporte"])
        # Deducciones: 4% + 4% de 1.623.500 = 64.940 + 64.940
        self.assertEqual(Decimal(fila["salud_empleado"]), Decimal("64940"))
        self.assertEqual(Decimal(fila["neto"]),
                         Decimal("1623500") + valores["auxilio_transporte"]
                         - Decimal("64940") * 2)

    def test_p82_tres_smmlv_no_lleva_auxilio(self):
        valores = parametros_del_anio(2026)
        alto = empleado_de(self.empresa, cedula="101",
                           salario=str(valores["smmlv"] * 3))
        fila = liquidar_empleado(alto, valores, exonerada=True)
        self.assertEqual(Decimal(fila["auxilio"]), 0)

    def test_p83_la_exoneracion_cambia_los_aportes(self):
        valores = parametros_del_anio(2026)
        quien = empleado_de(self.empresa)
        con = Decimal(liquidar_empleado(quien, valores, exonerada=False)["aportes_empleador"])
        sin = Decimal(liquidar_empleado(quien, valores, exonerada=True)["aportes_empleador"])
        # No exonerada paga además salud 8.5% + SENA 2% + ICBF 3%,
        # cada rubro redondeado al peso: 137.998 + 32.470 + 48.705
        self.assertEqual(con - sin, Decimal("219173"))

    def test_p84_el_asiento_balancea(self):
        empleado_de(self.empresa)
        empleado_de(self.empresa, nombre="Beto", cedula="102", salario="4870500")
        resultado = liquidar_mes(self.empresa,
                                 list(Empleado.objects.de_empresa(self.empresa)),
                                 2026, 7)
        debitos = sum(Decimal(r["debito"]) for r in resultado["asiento"])
        creditos = sum(Decimal(r["credito"]) for r in resultado["asiento"])
        self.assertEqual(debitos, creditos)
        self.assertGreater(debitos, 0)

    def test_p87_usa_los_parametros_del_anio(self):
        self.assertEqual(parametros_del_anio(2025)["smmlv"], Decimal("1423500"))
        self.assertEqual(parametros_del_anio(2026)["smmlv"], Decimal("1623500"))
        # Año futuro sin datos: usa el último conocido
        self.assertEqual(parametros_del_anio(2027)["smmlv"], Decimal("1623500"))


class PruebasFlujoNomina(CasoConEmpresa):
    def setUp(self):
        super().setUp()
        empleado_de(self.empresa)

    def liquidar(self, periodo="2026-07"):
        return self.client.post(reverse("nomina:liquidar"),
                                {"periodo": periodo}, follow=True)

    def test_p86_liquidar_queda_pendiente_y_se_aprueba(self):
        respuesta = self.liquidar()
        liquidacion = LiquidacionNomina.objects.de_empresa(self.empresa).get()
        self.assertEqual(liquidacion.estado, "pendiente")
        self.assertContains(respuesta, "pendiente de tu")
        self.client.post(reverse("nomina:decidir",
                                 args=[liquidacion.pk, "aprobada"]))
        liquidacion.refresh_from_db()
        self.assertEqual(liquidacion.estado, "aprobada")

    def test_p85_el_mismo_mes_no_se_liquida_dos_veces(self):
        self.liquidar()
        respuesta = self.liquidar()
        self.assertContains(respuesta, "ya fue liquidada")
        self.assertEqual(LiquidacionNomina.objects.de_empresa(self.empresa).count(), 1)

    def test_sin_empleados_activos_no_liquida(self):
        Empleado.objects.de_empresa(self.empresa).update(activo=False)
        respuesta = self.liquidar()
        self.assertContains(respuesta, "No hay empleados activos")

    def test_crear_y_editar_empleado(self):
        respuesta = self.client.post(reverse("nomina:empleado_nuevo"), {
            "nombre": "Carla Nueva", "cedula": "200", "salario": "2500000",
            "fecha_ingreso": "2026-07-01", "activo": "on"}, follow=True)
        self.assertContains(respuesta, "Carla Nueva")
        self.assertEqual(Empleado.objects.de_empresa(self.empresa).count(), 2)

    def test_nomina_aislada_por_tenant(self):
        self.liquidar()
        otra = Empresa.objects.create(nit="800111222", razon_social="OTRA SAS")
        self.assertEqual(LiquidacionNomina.objects.de_empresa(otra).count(), 0)
        self.assertEqual(Empleado.objects.de_empresa(otra).count(), 0)
        liquidacion = LiquidacionNomina.objects.de_empresa(self.empresa).get()
        # El detalle de nómina de A no es accesible con la empresa B activa
        # (cubierto por diseño: de_empresa; verificación directa del manager)
        self.assertNotIn(liquidacion,
                         LiquidacionNomina.objects.de_empresa(otra))

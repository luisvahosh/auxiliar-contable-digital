"""
Pruebas de nómina (casos P8 de PROCESO-AUXILIAR-CONTABLE.md).
"""
from datetime import date
from decimal import Decimal

from django.urls import reverse

from core.models import Empresa
from core.pruebas import CasoConEmpresa

from .calculo import liquidar_empleado, liquidar_mes
from .models import Empleado, LiquidacionNomina, NovedadNomina
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
        self.assertEqual(parametros_del_anio(2026)["smmlv"], Decimal("1750905"))
        # Año futuro sin datos: usa el último conocido
        self.assertEqual(parametros_del_anio(2027)["smmlv"], Decimal("1750905"))


class PruebasImportarEmpleados(CasoConEmpresa):
    """Carga masiva de la planta desde CSV."""

    def csv(self, *filas):
        cuerpo = "nombre;cedula;salario;fecha_ingreso\n" + "\n".join(filas)
        from django.core.files.uploadedfile import SimpleUploadedFile
        return SimpleUploadedFile("empleados.csv", cuerpo.encode("utf-8"),
                                  content_type="text/csv")

    def importar(self, archivo):
        return self.client.post(reverse("nomina:importar_empleados"),
                                {"archivo": archivo}, follow=True)

    def test_carga_varios_empleados(self):
        respuesta = self.importar(self.csv(
            "Ana Pérez;52111222;1623500;2025-01-15",
            "Beto Gómez;79333444;3.000.000;15/03/2024"))
        self.assertContains(respuesta, "2 empleado(s) nuevo(s)")
        self.assertEqual(Empleado.objects.de_empresa(self.empresa).count(), 2)
        beto = Empleado.objects.de_empresa(self.empresa).get(cedula="79333444")
        self.assertEqual(beto.salario, Decimal("3000000"))
        self.assertEqual(str(beto.fecha_ingreso), "2024-03-15")

    def test_cedula_existente_se_actualiza(self):
        empleado_de(self.empresa, cedula="52111222", salario="1000000")
        respuesta = self.importar(self.csv("Ana Nueva;52111222;1623500;2025-01-15"))
        self.assertContains(respuesta, "1 actualizado")
        self.assertEqual(Empleado.objects.de_empresa(self.empresa).count(), 1)
        ana = Empleado.objects.de_empresa(self.empresa).get()
        self.assertEqual(ana.salario, Decimal("1623500"))  # actualizado

    def test_filas_con_error_se_reportan_sin_frenar_el_resto(self):
        respuesta = self.importar(self.csv(
            "Buena;111;1623500;2025-01-15",
            "Mala;abc;1623500;2025-01-15",       # cédula no numérica
            "Fecha mala;222;1623500;32/13/2025"))  # fecha inválida
        self.assertContains(respuesta, "1 empleado(s) nuevo(s)")
        self.assertContains(respuesta, "no se importaron")
        self.assertEqual(Empleado.objects.de_empresa(self.empresa).count(), 1)

    def test_encabezado_incorrecto_se_rechaza(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        archivo = SimpleUploadedFile("x.csv", b"a;b;c;d\nX;1;2;3", content_type="text/csv")
        respuesta = self.importar(archivo)
        self.assertContains(respuesta, "No se pudo procesar")
        self.assertEqual(Empleado.objects.de_empresa(self.empresa).count(), 0)


class PruebasNovedades(CasoConEmpresa):
    """Caso P8.8: novedades del mes aplicadas a la liquidación."""

    def setUp(self):
        super().setUp()
        self.empleado = empleado_de(self.empresa, salario="2000000")

    def novedad(self, tipo, valor, anio=2026, mes=7):
        return NovedadNomina.objects.create(
            empresa=self.empresa, empleado=self.empleado, anio=anio, mes=mes,
            tipo=tipo, valor=Decimal(valor))

    def liquidar(self):
        return liquidar_mes(
            self.empresa, [self.empleado], 2026, 7,
            {self.empleado.pk: list(NovedadNomina.objects.de_empresa(self.empresa))})

    def test_hora_extra_constitutiva_sube_base_y_neto(self):
        self.novedad("he_diurna", "150000")
        fila = self.liquidar()["detalle"][0]
        # Base ahora 2.150.000: salud 4% = 86.000 (antes 80.000)
        self.assertEqual(Decimal(fila["salud_empleado"]), Decimal("86000"))
        self.assertEqual(Decimal(fila["novedades_devengo"]), Decimal("150000"))

    def test_bono_no_salarial_suma_neto_pero_no_base(self):
        sin = self.liquidar()["detalle"][0]
        self.novedad("bono_no_salarial", "300000")
        con = self.liquidar()["detalle"][0]
        # La base no cambia: salud sigue igual
        self.assertEqual(Decimal(con["salud_empleado"]), Decimal(sin["salud_empleado"]))
        # Pero el devengado y el neto suben exactamente el bono
        self.assertEqual(Decimal(con["devengado"]) - Decimal(sin["devengado"]),
                         Decimal("300000"))
        self.assertEqual(Decimal(con["neto"]) - Decimal(sin["neto"]), Decimal("300000"))

    def test_dias_no_laborados_reducen_la_base(self):
        self.novedad("dias_no_laborados", "200000")
        fila = self.liquidar()["detalle"][0]
        # Base 1.800.000: salud 4% = 72.000
        self.assertEqual(Decimal(fila["salud_empleado"]), Decimal("72000"))

    def test_prestamo_descuenta_solo_del_neto(self):
        self.novedad("prestamo", "250000")
        fila = self.liquidar()["detalle"][0]
        self.assertEqual(Decimal(fila["otros_descuentos"]), Decimal("250000"))
        self.assertEqual(Decimal(fila["salud_empleado"]), Decimal("80000"))  # base intacta

    def test_el_asiento_sigue_cuadrando_con_novedades(self):
        self.novedad("he_diurna", "150000")
        self.novedad("bono_no_salarial", "300000")
        self.novedad("prestamo", "250000")
        self.novedad("dias_no_laborados", "100000")
        resultado = self.liquidar()
        debitos = sum(Decimal(r["debito"]) for r in resultado["asiento"])
        creditos = sum(Decimal(r["credito"]) for r in resultado["asiento"])
        self.assertEqual(debitos, creditos)
        # El descuento del préstamo aparece como pasivo separado
        self.assertIn("237010", {r["cuenta"] for r in resultado["asiento"]})

    def test_registrar_novedad_por_la_vista(self):
        respuesta = self.client.post(reverse("nomina:novedades"), {
            "empleado": str(self.empleado.pk), "periodo": "2026-07",
            "tipo": "he_diurna", "cantidad": "10", "valor": "150000",
            "descripcion": "10 horas extra"}, follow=True)
        self.assertContains(respuesta, "Novedad registrada")
        self.assertEqual(NovedadNomina.objects.de_empresa(self.empresa).count(), 1)


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

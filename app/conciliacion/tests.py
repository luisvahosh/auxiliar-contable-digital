"""
Pruebas de la conciliación bancaria (casos P4 de PROCESO-AUXILIAR-CONTABLE.md).
"""
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from causacion.models import FacturaCompra, FacturaVenta
from core.models import Empresa
from core.pruebas import CasoConEmpresa

from .models import ExtractoBancario, MovimientoBancario
from .motor import (ExtractoInvalido, parsear_extracto, parsear_extracto_pdf)


def csv_bytes(*filas):
    return ("fecha;descripcion;valor\n" + "\n".join(filas)).encode("utf-8")


class BaseConciliacion(CasoConEmpresa):
    def setUp(self):
        super().setUp()
        self.venta = FacturaVenta.objects.create(
            empresa=self.empresa, tipo="venta", cufe="a1" * 30, numero="FE-104",
            fecha_emision="2026-06-15", nit_cliente="860222333",
            nombre_cliente="COMERCIALIZADORA ANDINA SAS",
            subtotal=3000000, iva=570000, total=3570000,
            estado="aprobada", explicacion="x", asiento=[], xml_crudo="<x/>")
        self.venta_retenida = FacturaVenta.objects.create(
            empresa=self.empresa, tipo="venta", cufe="b2" * 30, numero="FE-106",
            fecha_emision="2026-06-28", nit_cliente="890900555",
            nombre_cliente="GRANDES SUPERFICIES DEL CENTRO SA",
            subtotal=8000000, iva=1520000, total=9520000,
            retencion_practicada=320000,
            estado="aprobada", explicacion="x", asiento=[], xml_crudo="<x/>")
        self.compra = FacturaCompra.objects.create(
            empresa=self.empresa, cufe="c3" * 30, numero="FVS-847",
            fecha_emision="2026-06-30", nit_emisor="79456123",
            nombre_emisor="CARLOS ANDRÉS PÉREZ GÓMEZ", tipo_persona_emisor="2",
            subtotal=2000000, iva=380000, total=2380000, retencion=200000,
            cuenta_puc="5110", nombre_cuenta_puc="Honorarios",
            estado="aprobada", explicacion="x", xml_crudo="<x/>",
            asiento=[
                {"cuenta": "5110", "nombre": "Honorarios", "debito": "2000000", "credito": "0"},
                {"cuenta": "240802", "nombre": "IVA descontable", "debito": "380000", "credito": "0"},
                {"cuenta": "236515", "nombre": "Retefuente honorarios", "debito": "0", "credito": "200000"},
                {"cuenta": "2335", "nombre": "Costos y gastos por pagar", "debito": "0", "credito": "2180000"},
            ])

    def subir(self, contenido, nombre="extracto.csv"):
        archivo = SimpleUploadedFile(nombre, contenido, content_type="text/csv")
        return self.client.post(reverse("conciliacion:bancos"),
                                {"archivo": archivo}, follow=True)

    def movimientos(self):
        return list(MovimientoBancario.objects.de_empresa(self.empresa))


class PruebasParserExtracto(TestCase):
    def test_rechaza_encabezado_incorrecto(self):
        with self.assertRaises(ExtractoInvalido):
            parsear_extracto(b"dia;detalle;monto\n2026-07-01;X;100")

    def test_acepta_formatos_colombianos(self):
        movimientos = parsear_extracto(
            csv_bytes("02/07/2026;ABONO;3.570.000", "2026-07-08;GMF;-14.900,50"))
        self.assertEqual(movimientos[0]["valor"], Decimal("3570000"))
        self.assertEqual(movimientos[1]["valor"], Decimal("-14900.50"))

    def test_fecha_invalida_da_error_claro(self):
        with self.assertRaises(ExtractoInvalido) as ctx:
            parsear_extracto(csv_bytes("hoy;X;100"))
        self.assertIn("Fecha inválida", str(ctx.exception))


class PruebasExtractoPdf(BaseConciliacion):
    """Caso P4.5: el mismo extracto en PDF produce los mismos movimientos."""

    @staticmethod
    def datos_prueba(nombre):
        from pathlib import Path
        from django.conf import settings
        return (Path(settings.BASE_DIR).parent / "datos-prueba" / nombre).read_bytes()

    def test_p45_pdf_y_csv_producen_los_mismos_movimientos(self):
        del_csv = parsear_extracto(self.datos_prueba("P4-extracto-junio.csv"))
        del_pdf = parsear_extracto_pdf(self.datos_prueba("P4-extracto-junio.pdf"))
        self.assertEqual(del_csv, del_pdf)
        self.assertEqual(len(del_pdf), 6)

    def test_pdf_sin_movimientos_da_instruccion_clara(self):
        # Un PDF válido pero sin renglones de movimientos (p. ej. un escaneo)
        pdf_vacio = self.datos_prueba("P4-extracto-junio.pdf").replace(b"/2026", b"/x026")
        with self.assertRaises(ExtractoInvalido) as ctx:
            parsear_extracto_pdf(pdf_vacio)
        self.assertIn("escaneo", str(ctx.exception))

    def test_subida_web_del_pdf(self):
        respuesta = self.subir(self.datos_prueba("P4-extracto-junio.pdf"),
                               nombre="extracto.pdf")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(
            MovimientoBancario.objects.de_empresa(self.empresa).count(), 6)
        # El cruce funciona igual que con CSV: la FE-104 cruza exacta
        exacto = MovimientoBancario.objects.de_empresa(self.empresa).get(
            sugerencia="pago_cliente")
        self.assertEqual(exacto.factura_venta, self.venta)


class PruebasConciliacion(BaseConciliacion):
    def test_p41_mes_limpio_concilia_todo_y_cuadra(self):
        self.subir(csv_bytes(
            "2026-07-02;TRANSFERENCIA COMERCIALIZADORA ANDINA;3570000",
            "2026-07-05;PAGO PSE CARLOS PEREZ;-2180000",
        ))
        movimientos = self.movimientos()
        self.assertEqual([m.sugerencia for m in movimientos],
                         ["pago_cliente", "pago_proveedor"])
        for movimiento in movimientos:
            self.client.post(reverse("conciliacion:conciliar", args=[movimiento.pk]))
        extracto = ExtractoBancario.objects.de_empresa(self.empresa).get()
        respuesta = self.client.get(reverse("conciliacion:extracto", args=[extracto.pk]))
        self.assertContains(respuesta, "Conciliación cuadrada")

    def test_p42_comisiones_y_gmf_proponen_asiento_de_gasto(self):
        self.subir(csv_bytes(
            "2026-07-08;CUOTA DE MANEJO;-14900",
            "2026-07-08;GMF 4X1000;-35000",
        ))
        cuota, gmf = self.movimientos()
        self.assertEqual(cuota.sugerencia, "gasto_bancario")
        self.assertEqual(cuota.asiento[0]["cuenta"], "530505")
        self.assertEqual(gmf.asiento[0]["cuenta"], "531595")
        # Todo asiento propuesto acredita el banco por la misma magnitud
        self.assertEqual(gmf.asiento[1]["cuenta"], "111005")
        self.assertEqual(Decimal(gmf.asiento[1]["credito"]), Decimal("35000"))

    def test_p43_consignacion_sin_identificar_sugiere_cliente_probable(self):
        self.subir(csv_bytes("2026-07-09;CONSIGNACION EFECTIVO;1100000"))
        movimiento = self.movimientos()[0]
        self.assertEqual(movimiento.sugerencia, "sin_identificar")
        self.assertEqual(movimiento.estado, "pendiente")
        # El más cercano por valor a $1.100.000 es FE-104 ($3.570.000)
        self.assertIn("COMERCIALIZADORA ANDINA", movimiento.explicacion)
        # No se puede conciliar a la fuerza
        respuesta = self.client.post(
            reverse("conciliacion:conciliar", args=[movimiento.pk]), follow=True)
        self.assertContains(respuesta, "no se puede conciliar")

    def test_p44_pago_parcial_no_fuerza_el_cruce_total(self):
        self.subir(csv_bytes("2026-07-03;ABONO GRANDES SUPERFICIES;4600000"))
        movimiento = self.movimientos()[0]
        self.assertEqual(movimiento.sugerencia, "pago_cliente_parcial")
        self.assertEqual(movimiento.factura_venta, self.venta_retenida)
        self.assertIn("parcial", movimiento.explicacion)
        self.assertIn("saldo queda en cartera", movimiento.explicacion)
        # El asiento va por el valor pagado, no por el total de la factura
        self.assertEqual(Decimal(movimiento.asiento[0]["debito"]), Decimal("4600000"))

    def test_p46_la_diferencia_es_lo_no_conciliado(self):
        self.subir(csv_bytes(
            "2026-07-02;TRANSFERENCIA COMERCIALIZADORA ANDINA;3570000",
            "2026-07-09;CONSIGNACION EFECTIVO;1100000",
        ))
        exacto, suelto = self.movimientos()
        self.client.post(reverse("conciliacion:conciliar", args=[exacto.pk]))
        extracto = ExtractoBancario.objects.de_empresa(self.empresa).get()
        respuesta = self.client.get(reverse("conciliacion:extracto", args=[extracto.pk]))
        self.assertContains(respuesta, "Diferencia por explicar")
        self.assertNotContains(respuesta, "Conciliación cuadrada")

    def test_extracto_invalido_no_deja_nada_a_medias(self):
        respuesta = self.subir(b"esto no es un csv de extracto")
        self.assertContains(respuesta, "No se pudo procesar el extracto")
        self.assertEqual(ExtractoBancario.objects.de_empresa(self.empresa).count(), 0)

    def test_extractos_aislados_por_tenant(self):
        otra = Empresa.objects.create(nit="800111222", razon_social="OTRA SAS")
        ajeno = ExtractoBancario.objects.create(empresa=otra, nombre="ajeno.csv")
        respuesta = self.client.get(reverse("conciliacion:extracto", args=[ajeno.pk]))
        self.assertEqual(respuesta.status_code, 404)

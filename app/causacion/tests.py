"""
Pruebas del vertical de causación contra los XML reales-simulados de
datos-prueba/ — casos P1 de PROCESO-AUXILIAR-CONTABLE.md.
"""
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from core.models import Empresa

from .clasificacion import calcular_retencion, clasificar, construir_asiento
from .models import FacturaCompra, MapeoCuentaAlegra
from .parser import FacturaInvalida, parsear_factura

DATOS_PRUEBA = Path(settings.BASE_DIR).parent / "datos-prueba"


def contenido(nombre):
    return (DATOS_PRUEBA / nombre).read_bytes()


def procesar(nombre):
    """Parsear + clasificar + retención + asiento, como lo hace la vista."""
    factura = parsear_factura(contenido(nombre))
    propuesta = clasificar(factura)
    retencion = calcular_retencion(factura, propuesta.concepto)
    renglones = construir_asiento(factura, propuesta, retencion)
    return factura, propuesta, retencion, renglones


class PruebasParser(TestCase):
    def test_p11_extrae_los_datos_de_la_factura(self):
        factura = parsear_factura(contenido("P1.1-factura-honorarios.xml"))
        self.assertEqual(factura.numero, "FVS-847")
        self.assertEqual(factura.nit_emisor, "79456123")
        self.assertEqual(factura.tipo_persona_emisor, "2")  # persona natural
        self.assertEqual(factura.nit_adquiriente, "901234567")
        self.assertEqual(factura.subtotal, Decimal("2000000.00"))
        self.assertEqual(factura.iva, Decimal("380000.00"))
        self.assertEqual(factura.total, Decimal("2380000.00"))
        self.assertEqual(len(factura.cufe), 96)

    def test_p16a_xml_malformado_da_error_claro(self):
        with self.assertRaises(FacturaInvalida) as ctx:
            parsear_factura(contenido("P1.6a-xml-malformado.xml"))
        self.assertIn("bien formado", str(ctx.exception))

    def test_p16b_xxe_es_bloqueado(self):
        with self.assertRaises(FacturaInvalida) as ctx:
            parsear_factura(contenido("P1.6b-xml-xxe.xml"))
        self.assertIn("seguridad", str(ctx.exception))

    def test_totales_que_no_cuadran_se_rechazan(self):
        xml = contenido("P1.1-factura-honorarios.xml").replace(
            b'<cbc:PayableAmount currencyID="COP">2380000.00</cbc:PayableAmount>',
            b'<cbc:PayableAmount currencyID="COP">2999999.00</cbc:PayableAmount>',
        )
        with self.assertRaises(FacturaInvalida) as ctx:
            parsear_factura(xml)
        self.assertIn("no cuadran", str(ctx.exception))


class PruebasClasificacionYRetencion(TestCase):
    def test_p11_honorarios_5110_con_retefuente_10(self):
        factura, propuesta, retencion, renglones = procesar("P1.1-factura-honorarios.xml")
        self.assertEqual(propuesta.cuenta, "5110")
        self.assertEqual(propuesta.nivel, "automatica")
        self.assertEqual(retencion.valor, Decimal("200000"))  # 10% de 2.000.000
        cuentas = {r["cuenta"] for r in renglones}
        self.assertIn("236515", cuentas)   # retefuente honorarios
        self.assertIn("240802", cuentas)   # IVA descontable

    def test_p12_inventario_va_a_1435_con_retefuente_compras(self):
        factura, propuesta, retencion, renglones = procesar("P1.2-factura-inventario.xml")
        self.assertEqual(propuesta.cuenta, "1435")  # inventario, no gasto
        self.assertEqual(propuesta.nivel, "automatica")
        self.assertEqual(retencion.valor, Decimal("140000"))  # 2.5% de 5.600.000
        # La contrapartida de mercancías es proveedores (2205)
        self.assertIn("2205", {r["cuenta"] for r in renglones})

    def test_p13_regimen_simple_no_lleva_retefuente(self):
        factura, propuesta, retencion, renglones = procesar("P1.3-factura-regimen-simple.xml")
        self.assertEqual(retencion.valor, Decimal("0"))
        self.assertIn("Régimen Simple", retencion.porque)
        self.assertFalse({r["cuenta"] for r in renglones} & {"236515", "236525", "236540"})

    def test_p14_bajo_base_minima_no_calcula_retencion(self):
        factura, propuesta, retencion, renglones = procesar("P1.4-factura-bajo-base-minima.xml")
        self.assertEqual(propuesta.cuenta, "5145")
        self.assertEqual(retencion.valor, Decimal("0"))
        self.assertIn("base mínima", retencion.porque)

    def test_p17_concepto_ambiguo_queda_sugerida(self):
        factura, propuesta, retencion, renglones = procesar("P1.7-factura-concepto-ambiguo.xml")
        self.assertEqual(propuesta.nivel, "sugerida")
        self.assertGreaterEqual(len(propuesta.candidatas), 2)
        self.assertIn("ambiguo", propuesta.explicacion)

    def test_todos_los_asientos_balancean(self):
        validas = ["P1.1-factura-honorarios.xml", "P1.2-factura-inventario.xml",
                   "P1.3-factura-regimen-simple.xml", "P1.4-factura-bajo-base-minima.xml",
                   "P1.7-factura-concepto-ambiguo.xml"]
        for nombre in validas:
            with self.subTest(xml=nombre):
                _, _, _, renglones = procesar(nombre)
                debitos = sum(Decimal(r["debito"]) for r in renglones)
                creditos = sum(Decimal(r["credito"]) for r in renglones)
                self.assertEqual(debitos, creditos)


class PruebasFlujoWeb(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.get(nit="901234567")

    def subir(self, nombre, archivo_nombre=None):
        archivo = SimpleUploadedFile(archivo_nombre or nombre, contenido(nombre),
                                     content_type="text/xml")
        return self.client.post(reverse("causacion:subir"), {"archivo": archivo},
                                follow=True)

    def test_flujo_completo_subir_y_aprobar(self):
        respuesta = self.subir("P1.1-factura-honorarios.xml")
        self.assertEqual(respuesta.status_code, 200)
        factura = FacturaCompra.objects.de_empresa(self.empresa).get()
        self.assertEqual(factura.estado, "pendiente")  # humano en el circuito
        self.assertContains(respuesta, "Asiento propuesto")
        respuesta = self.client.post(reverse("causacion:aprobar", args=[factura.pk]),
                                     follow=True)
        factura.refresh_from_db()
        self.assertEqual(factura.estado, "aprobada")

    def test_p15_cufe_duplicado_no_crea_asiento_doble(self):
        self.subir("P1.1-factura-honorarios.xml")
        respuesta = self.subir("P1.5-factura-duplicada-mismo-cufe.xml")
        self.assertContains(respuesta, "ya fue causada")
        self.assertEqual(FacturaCompra.objects.de_empresa(self.empresa).count(), 1)

    def test_p16a_malformado_error_claro_sin_crash_ni_asiento(self):
        respuesta = self.subir("P1.6a-xml-malformado.xml")
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "No se pudo procesar")
        self.assertEqual(FacturaCompra.objects.de_empresa(self.empresa).count(), 0)

    def test_p16b_xxe_bloqueado_sin_filtrar_contenido_local(self):
        respuesta = self.subir("P1.6b-xml-xxe.xml")
        self.assertContains(respuesta, "seguridad")
        # El contenido del archivo local atacado jamás aparece en la respuesta.
        self.assertNotContains(respuesta, "win.ini")
        self.assertNotContains(respuesta, "[fonts]")
        self.assertEqual(FacturaCompra.objects.de_empresa(self.empresa).count(), 0)

    def test_factura_dirigida_a_otro_nit_se_rechaza(self):
        xml = contenido("P1.1-factura-honorarios.xml").replace(
            b'schemeID="3" schemeName="31">901234567<', b'schemeID="3" schemeName="31">899999999<')
        archivo = SimpleUploadedFile("otra.xml", xml, content_type="text/xml")
        respuesta = self.client.post(reverse("causacion:subir"), {"archivo": archivo},
                                     follow=True)
        self.assertContains(respuesta, "no es el de")
        self.assertEqual(FacturaCompra.objects.de_empresa(self.empresa).count(), 0)


class PruebasExportSiigoYAlegra(TestCase):
    """P1.9: el asiento aprobado llega al software contable."""

    def setUp(self):
        self.empresa = Empresa.objects.get(nit="901234567")
        archivo = SimpleUploadedFile("P1.1.xml", contenido("P1.1-factura-honorarios.xml"),
                                     content_type="text/xml")
        self.client.post(reverse("causacion:subir"), {"archivo": archivo})
        self.factura = FacturaCompra.objects.de_empresa(self.empresa).get()

    def aprobar(self):
        self.client.post(reverse("causacion:aprobar", args=[self.factura.pk]))
        self.factura.refresh_from_db()

    def test_csv_siigo_solo_para_aprobadas(self):
        url = reverse("causacion:exportar_siigo", args=[self.factura.pk])
        self.assertEqual(self.client.get(url).status_code, 404)  # aún pendiente
        self.aprobar()
        respuesta = self.client.get(url)
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn("text/csv", respuesta["Content-Type"])
        cuerpo = respuesta.content.decode("utf-8-sig")
        self.assertIn("CODIGO CUENTA", cuerpo)
        self.assertIn("5110", cuerpo)
        self.assertIn("236515", cuerpo)
        self.assertIn("79456123", cuerpo)  # NIT del tercero en cada renglón
        # encabezado + 4 renglones del asiento
        self.assertEqual(len([l for l in cuerpo.splitlines() if l.strip()]), 5)

    def test_alegra_sin_configurar_avisa_sin_romperse(self):
        self.aprobar()
        with patch.dict("os.environ", {"ALEGRA_EMAIL": "", "ALEGRA_TOKEN": ""}):
            respuesta = self.client.post(
                reverse("causacion:enviar_alegra", args=[self.factura.pk]), follow=True)
        self.assertContains(respuesta, "Alegra no está configurado")
        self.factura.refresh_from_db()
        self.assertEqual(self.factura.id_alegra, "")

    def test_alegra_exige_mapeo_de_cuentas(self):
        self.aprobar()
        entorno = {"ALEGRA_EMAIL": "x@y.co", "ALEGRA_TOKEN": "tok"}
        with patch.dict("os.environ", entorno):
            respuesta = self.client.post(
                reverse("causacion:enviar_alegra", args=[self.factura.pk]), follow=True)
        self.assertContains(respuesta, "Faltan cuentas por mapear")
        self.assertContains(respuesta, "5110")

    def test_alegra_envia_el_asiento_mapeado(self):
        self.aprobar()
        for i, cuenta in enumerate(["5110", "240802", "236515", "2335"], start=1):
            MapeoCuentaAlegra.objects.create(empresa=self.empresa,
                                             cuenta_puc=cuenta, id_alegra=i)
        entorno = {"ALEGRA_EMAIL": "x@y.co", "ALEGRA_TOKEN": "tok"}
        with patch.dict("os.environ", entorno), \
             patch("causacion.alegra.requests.post") as envio:
            envio.return_value.ok = True
            envio.return_value.status_code = 200
            envio.return_value.json.return_value = {"id": 777}
            respuesta = self.client.post(
                reverse("causacion:enviar_alegra", args=[self.factura.pk]), follow=True)

        self.assertContains(respuesta, "#777")
        self.factura.refresh_from_db()
        self.assertEqual(self.factura.id_alegra, "777")
        self.assertIsNotNone(self.factura.enviada_alegra)
        # Lo enviado a Alegra balancea y trae las 4 cuentas mapeadas
        cuerpo = envio.call_args.kwargs["json"]
        self.assertEqual(len(cuerpo["entries"]), 4)
        self.assertEqual(sum(e["debit"] for e in cuerpo["entries"]),
                         sum(e["credit"] for e in cuerpo["entries"]))
        # Reenviar no duplica: la app avisa que ya está en Alegra
        respuesta = self.client.post(
            reverse("causacion:enviar_alegra", args=[self.factura.pk]), follow=True)
        self.assertContains(respuesta, "ya está en Alegra")


class PruebasMultiTenant(TestCase):
    """Test de acceso cruzado entre tenants — obligatorio en CI (CLAUDE.md §2)."""

    def setUp(self):
        self.empresa_a = Empresa.objects.get(nit="901234567")
        self.empresa_b = Empresa.objects.create(nit="800111222", razon_social="OTRA SAS")
        self.factura_b = FacturaCompra.objects.create(
            empresa=self.empresa_b, cufe="ab" * 30, numero="X-1",
            fecha_emision="2026-06-01", nit_emisor="1", nombre_emisor="Emisor B",
            tipo_persona_emisor="1", subtotal=100, iva=19, total=119,
            cuenta_puc="5195", nombre_cuenta_puc="Diversos",
            explicacion="prueba", asiento=[], xml_crudo="<x/>",
        )

    def test_el_manager_aisla_por_empresa(self):
        self.assertNotIn(self.factura_b,
                         FacturaCompra.objects.de_empresa(self.empresa_a))
        self.assertIn(self.factura_b,
                      FacturaCompra.objects.de_empresa(self.empresa_b))

    def test_no_se_accede_a_facturas_de_otro_tenant_por_url(self):
        # La empresa activa es A (la primera creada); la factura es de B.
        respuesta = self.client.get(reverse("causacion:detalle",
                                            args=[self.factura_b.pk]))
        self.assertEqual(respuesta.status_code, 404)

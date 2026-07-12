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
from .models import FacturaCompra, FacturaVenta, MapeoCuentaAlegra, Tercero
from .parser import FacturaInvalida, parsear_factura
from .ventas import consecutivos_faltantes

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

    def test_factura_de_terceros_ajenos_se_rechaza(self):
        xml = contenido("P1.1-factura-honorarios.xml").replace(
            b'schemeID="3" schemeName="31">901234567<', b'schemeID="3" schemeName="31">899999999<')
        archivo = SimpleUploadedFile("otra.xml", xml, content_type="text/xml")
        respuesta = self.client.post(reverse("causacion:subir"), {"archivo": archivo},
                                     follow=True)
        self.assertContains(respuesta, "no menciona a")
        self.assertEqual(FacturaCompra.objects.de_empresa(self.empresa).count(), 0)


class PruebasFacturaFisica(TestCase):
    """Caso P1.10: causación desde foto de factura de papel."""

    def setUp(self):
        self.empresa = Empresa.objects.get(nit="901234567")

    def subir_foto(self):
        foto = SimpleUploadedFile("factura.png", b"\x89PNG-fake-bytes",
                                  content_type="image/png")
        with patch.dict("os.environ", {"NVIDIA_API_KEY": ""}):
            return self.client.post(reverse("causacion:foto"), {"foto": foto},
                                    follow=True)

    def nombre_foto_de(self, respuesta):
        import re as _re
        return _re.search(r'name="nombre_foto" value="([^"]+)"',
                          respuesta.content.decode()).group(1)

    def campos_base(self, nombre_foto, **cambios):
        campos = {
            "nombre_foto": nombre_foto,
            "nit_emisor": "79456123",
            "nombre_emisor": "CARLOS ANDRÉS PÉREZ GÓMEZ",
            "tipo_persona": "2",
            "numero": "CC-2026-07",
            "fecha": "2026-07-05",
            "subtotal": "2000000",
            "iva": "0",
            "total": "2000000",
            "concepto": "Honorarios asesoría contable julio",
        }
        campos.update(cambios)
        return campos

    def test_sin_ia_permite_digitacion_manual_y_causa_como_sugerida(self):
        respuesta = self.subir_foto()
        self.assertContains(respuesta, "no está configurada")   # aviso claro
        self.assertContains(respuesta, "nombre_foto")           # formulario listo
        nombre = self.nombre_foto_de(respuesta)
        respuesta = self.client.post(reverse("causacion:foto_causar"),
                                     self.campos_base(nombre), follow=True)
        factura = FacturaCompra.objects.de_empresa(self.empresa).get()
        self.assertEqual(factura.origen, "foto")
        self.assertEqual(factura.nivel, "sugerida")  # NUNCA automática desde foto
        self.assertEqual(factura.cuenta_puc, "5110")
        self.assertEqual(factura.retencion, Decimal("200000"))  # 10% honorarios PN
        self.assertTrue(factura.imagen.name.startswith("facturas_fisicas/"))
        # El proveedor entró a la matriz de terceros
        self.assertTrue(Tercero.objects.de_empresa(self.empresa)
                        .filter(nit="79456123").exists())

    def test_antiduplicado_por_nit_numero_fecha(self):
        nombre = self.nombre_foto_de(self.subir_foto())
        self.client.post(reverse("causacion:foto_causar"), self.campos_base(nombre))
        nombre2 = self.nombre_foto_de(self.subir_foto())
        respuesta = self.client.post(reverse("causacion:foto_causar"),
                                     self.campos_base(nombre2), follow=True)
        self.assertContains(respuesta, "ya fue causada")
        self.assertEqual(FacturaCompra.objects.de_empresa(self.empresa).count(), 1)

    def test_totales_que_no_cuadran_no_se_causan(self):
        nombre = self.nombre_foto_de(self.subir_foto())
        respuesta = self.client.post(
            reverse("causacion:foto_causar"),
            self.campos_base(nombre, total="9999999"), follow=True)
        self.assertContains(respuesta, "no cuadran")
        self.assertEqual(FacturaCompra.objects.de_empresa(self.empresa).count(), 0)

    def test_nombre_de_foto_malicioso_se_rechaza(self):
        respuesta = self.client.post(
            reverse("causacion:foto_causar"),
            self.campos_base("..\\..\\config\\settings.py"), follow=True)
        self.assertContains(respuesta, "Referencia de foto inválida")
        self.assertEqual(FacturaCompra.objects.de_empresa(self.empresa).count(), 0)

    def test_con_ia_prellenado_desde_la_vision(self):
        foto = SimpleUploadedFile("factura.jpg", b"bytes", content_type="image/jpeg")
        campos_ia = {"nit_emisor": "900.123.456", "nombre_emisor": "PAPELERIA EL LAPIZ SAS",
                     "numero": "PL-88", "fecha": "2026-07-01", "subtotal": 250000,
                     "iva": 47500, "total": 297500, "concepto": "Papelería oficina",
                     "confianza": 92}
        with patch.dict("os.environ", {"NVIDIA_API_KEY": "nvapi-prueba"}), \
             patch("causacion.views.vision.extraer_campos", return_value=campos_ia):
            respuesta = self.client.post(reverse("causacion:foto"), {"foto": foto},
                                         follow=True)
        self.assertContains(respuesta, "PAPELERIA EL LAPIZ SAS")
        self.assertContains(respuesta, "900123456")  # NIT normalizado a dígitos
        self.assertContains(respuesta, "92/100")     # confianza visible
        self.assertContains(respuesta, "UNO POR UNO")


class PruebasMatrizDeTerceros(TestCase):
    """Casos P3: la calidad tributaria real del proveedor manda sobre el XML."""

    def setUp(self):
        self.empresa = Empresa.objects.get(nit="901234567")

    def subir(self, nombre):
        archivo = SimpleUploadedFile(nombre, contenido(nombre), content_type="text/xml")
        return self.client.post(reverse("causacion:subir"), {"archivo": archivo},
                                follow=True)

    def test_p31_usa_la_uvt_del_anio_fiscal_correcto(self):
        # $205.000 está entre la base mínima de 4 UVT de 2025 ($199.196)
        # y la de 2026 ($209.496): retiene en 2025, no en 2026.
        base = parsear_factura(contenido("P1.4-factura-bajo-base-minima.xml"))
        base.subtotal = Decimal("205000")
        base.fecha_emision = base.fecha_emision.replace(year=2025)
        con_2025 = calcular_retencion(base, "servicios")
        self.assertGreater(con_2025.valor, 0)
        base.fecha_emision = base.fecha_emision.replace(year=2026)
        con_2026 = calcular_retencion(base, "servicios")
        self.assertEqual(con_2026.valor, Decimal("0"))
        self.assertIn("2026", con_2026.porque)

    def test_p32_autorretenedor_no_lleva_retefuente(self):
        self.subir("P3.2-factura-autorretenedor.xml")
        factura = FacturaCompra.objects.de_empresa(self.empresa).get(numero="CEA-501")
        self.assertEqual(factura.retencion, Decimal("0"))
        self.assertIn("autorretenedor", factura.explicacion)
        self.assertFalse({r["cuenta"] for r in factura.asiento} &
                         {"236515", "236525", "236540"})

    def test_el_tercero_se_crea_con_la_primera_factura(self):
        self.subir("P3.2-factura-autorretenedor.xml")
        tercero = Tercero.objects.de_empresa(self.empresa).get(nit="830444999")
        self.assertTrue(tercero.autorretenedor)   # tomado del TaxLevelCode O-15
        self.assertFalse(tercero.verificado)      # pendiente de cotejar con el RUT
        self.assertIn("pendiente de verificar",
                      FacturaCompra.objects.de_empresa(self.empresa).get().explicacion)

    def test_la_matriz_manda_sobre_el_xml(self):
        # El XML de P1.1 no trae calidad especial, pero el auxiliar registró
        # al proveedor como autorretenedor tras revisar su RUT.
        datos = parsear_factura(contenido("P1.1-factura-honorarios.xml"))
        Tercero.objects.create(
            empresa=self.empresa, nit=datos.nit_emisor, razon_social=datos.nombre_emisor,
            tipo_persona="2", autorretenedor=True, verificado=True)
        self.subir("P1.1-factura-honorarios.xml")
        factura = FacturaCompra.objects.de_empresa(self.empresa).get()
        self.assertEqual(factura.retencion, Decimal("0"))
        self.assertIn("autorretenedor", factura.explicacion)

    def test_no_declarante_usa_tarifa_mas_alta(self):
        datos = parsear_factura(contenido("P1.4-factura-bajo-base-minima.xml"))
        datos.subtotal = Decimal("1000000")  # sobre la base mínima
        tercero = Tercero(empresa=self.empresa, nit=datos.nit_emisor,
                          razon_social="X", tipo_persona="2",
                          declarante=False, verificado=True)
        retencion = calcular_retencion(datos, "servicios", tercero)
        self.assertEqual(retencion.tarifa, Decimal("6"))  # 6% no declarante vs 4%
        self.assertEqual(retencion.valor, Decimal("60000"))
        self.assertIn("no declarante", retencion.porque)

    def test_editar_tercero_cambia_la_proxima_causacion(self):
        self.subir("P1.1-factura-honorarios.xml")
        tercero = Tercero.objects.de_empresa(self.empresa).get(nit="79456123")
        respuesta = self.client.post(
            reverse("causacion:editar_tercero", args=[tercero.pk]),
            {"razon_social": tercero.razon_social, "tipo_persona": "2",
             "regimen_simple": "on", "verificado": "on"},
            follow=True)
        self.assertContains(respuesta, "actualizado")
        tercero.refresh_from_db()
        self.assertTrue(tercero.regimen_simple)
        # La siguiente factura del mismo proveedor ya no lleva retención
        datos = parsear_factura(contenido("P1.1-factura-honorarios.xml"))
        retencion = calcular_retencion(datos, "honorarios", tercero)
        self.assertEqual(retencion.valor, Decimal("0"))

    def test_terceros_aislados_por_tenant(self):
        otra = Empresa.objects.create(nit="800111222", razon_social="OTRA SAS")
        Tercero.objects.create(empresa=otra, nit="1", razon_social="Ajeno")
        self.assertEqual(Tercero.objects.de_empresa(self.empresa).count(), 0)
        ajeno = Tercero.objects.de_empresa(otra).get()
        respuesta = self.client.get(
            reverse("causacion:editar_tercero", args=[ajeno.pk]))
        self.assertEqual(respuesta.status_code, 404)


class PruebasVentas(TestCase):
    """Casos P2: registro de facturas emitidas, retenciones a favor,
    consecutivo y notas crédito."""

    def setUp(self):
        self.empresa = Empresa.objects.get(nit="901234567")

    def subir(self, nombre):
        archivo = SimpleUploadedFile(nombre, contenido(nombre), content_type="text/xml")
        return self.client.post(reverse("causacion:subir"), {"archivo": archivo},
                                follow=True)

    def test_p21_venta_estandar_registra_ingreso(self):
        respuesta = self.subir("P2.1-venta-estandar.xml")
        self.assertEqual(respuesta.status_code, 200)
        venta = FacturaVenta.objects.de_empresa(self.empresa).get()
        self.assertEqual(venta.tipo, "venta")
        self.assertEqual(venta.estado, "pendiente")  # humano en el circuito
        por_cuenta = {r["cuenta"]: r for r in venta.asiento}
        self.assertEqual(Decimal(por_cuenta["1305"]["debito"]), Decimal("3570000.00"))
        self.assertEqual(Decimal(por_cuenta["4135"]["credito"]), Decimal("3000000.00"))
        self.assertEqual(Decimal(por_cuenta["240801"]["credito"]), Decimal("570000.00"))

    def test_p22_retencion_del_cliente_queda_en_1355(self):
        self.subir("P2.2-venta-cliente-retiene.xml")
        venta = FacturaVenta.objects.de_empresa(self.empresa).get(numero="FE-106")
        self.assertEqual(venta.retencion_practicada, Decimal("320000.00"))
        por_cuenta = {r["cuenta"]: r for r in venta.asiento}
        self.assertEqual(Decimal(por_cuenta["135515"]["debito"]), Decimal("320000.00"))
        # Cartera por el neto
        self.assertEqual(Decimal(por_cuenta["1305"]["debito"]), Decimal("9200000.00"))
        debitos = sum(Decimal(r["debito"]) for r in venta.asiento)
        creditos = sum(Decimal(r["credito"]) for r in venta.asiento)
        self.assertEqual(debitos, creditos)

    def test_p23_alerta_hueco_en_consecutivo(self):
        self.subir("P2.1-venta-estandar.xml")   # FE-104
        respuesta = self.subir("P2.2-venta-cliente-retiene.xml")  # FE-106
        self.assertContains(respuesta, "falta FE-105")
        self.assertEqual(consecutivos_faltantes(["FE-104", "FE-106"]), ["FE-105"])
        # La bandeja de ventas también lo muestra
        respuesta = self.client.get(reverse("causacion:bandeja_ventas"))
        self.assertContains(respuesta, "FE-105")

    def test_p24_nota_credito_sin_original_se_rechaza(self):
        respuesta = self.subir("P2.4-nota-credito.xml")
        self.assertContains(respuesta, "no está registrada")
        self.assertEqual(FacturaVenta.objects.de_empresa(self.empresa).count(), 0)

    def test_p24_nota_credito_reversa_vinculada(self):
        self.subir("P2.1-venta-estandar.xml")
        respuesta = self.subir("P2.4-nota-credito.xml")
        self.assertEqual(respuesta.status_code, 200)
        nota = FacturaVenta.objects.de_empresa(self.empresa).get(tipo="nota_credito")
        self.assertEqual(nota.factura_original.numero, "FE-104")
        por_cuenta = {r["cuenta"]: r for r in nota.asiento}
        self.assertEqual(Decimal(por_cuenta["4135"]["debito"]), Decimal("500000.00"))
        self.assertEqual(Decimal(por_cuenta["240801"]["debito"]), Decimal("95000.00"))
        self.assertEqual(Decimal(por_cuenta["1305"]["credito"]), Decimal("595000.00"))
        self.assertIn("parcial", nota.explicacion)

    def test_el_mismo_upload_distingue_compra_de_venta(self):
        self.subir("P1.1-factura-honorarios.xml")   # LEARNWAY es adquiriente → compra
        self.subir("P2.1-venta-estandar.xml")       # LEARNWAY es emisor → venta
        self.assertEqual(FacturaCompra.objects.de_empresa(self.empresa).count(), 1)
        self.assertEqual(FacturaVenta.objects.de_empresa(self.empresa).count(), 1)


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
        # Lo enviado a Alegra balancea, trae las 4 cuentas mapeadas y cada
        # movimiento lleva solo débito o crédito (regla del endpoint /journals)
        cuerpo = envio.call_args.kwargs["json"]
        self.assertEqual(len(cuerpo["entries"]), 4)
        for movimiento in cuerpo["entries"]:
            self.assertTrue(("debit" in movimiento) != ("credit" in movimiento))
        self.assertEqual(sum(e.get("debit", 0) for e in cuerpo["entries"]),
                         sum(e.get("credit", 0) for e in cuerpo["entries"]))
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

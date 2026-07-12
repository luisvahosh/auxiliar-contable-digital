"""
Pruebas de acceso e identidad (PLAN.md §12): sin registro abierto, tokens de
un solo uso, errores que no revelan nada e invisibilidad entre empresas.
"""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from causacion.models import FacturaCompra

from .models import Empresa, Invitacion, Membresia
from .pruebas import CasoConEmpresa

Usuario = get_user_model()


class PruebasAccesoCerrado(TestCase):
    def test_nada_visible_sin_sesion(self):
        for ruta in ["/", "/causacion/", "/causacion/subir/", "/bancos/",
                     "/calendario/", "/cierre/", "/causacion/cartera/"]:
            with self.subTest(ruta=ruta):
                respuesta = self.client.get(ruta)
                self.assertEqual(respuesta.status_code, 302)
                self.assertTrue(respuesta.url.startswith("/login/"))

    def test_el_error_de_login_no_revela_que_fallo(self):
        Usuario.objects.create_user(username="existe@x.co", password="clave-larga-123")
        for correo in ["existe@x.co", "noexiste@x.co"]:
            respuesta = self.client.post(reverse("core:login"),
                                         {"username": correo, "password": "mala"})
            self.assertContains(respuesta, "Correo o contraseña incorrectos")
            self.assertNotContains(respuesta, "no existe")

    def test_usuario_sin_membresia_no_ve_datos(self):
        usuario = Usuario.objects.create_user(username="huerfano@x.co",
                                              password="clave-larga-123")
        self.client.force_login(usuario)
        respuesta = self.client.get("/causacion/", follow=True)
        self.assertContains(respuesta, "no está vinculada a ninguna empresa")


class PruebasRegistroPorToken(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.get(nit="901234567")

    def test_flujo_completo_de_matricula(self):
        invitacion, token = Invitacion.crear(self.empresa, "nueva@x.co", "operador")
        # El token no se guarda en claro
        self.assertNotEqual(invitacion.token_hash, token)

        respuesta = self.client.get(f"/registro/{token}/")
        self.assertContains(respuesta, "nueva@x.co")

        respuesta = self.client.post(f"/registro/{token}/", {
            "nombre": "Nueva Auxiliar",
            "contrasena": "una-clave-larga-y-rara-77",
            "confirmacion": "una-clave-larga-y-rara-77",
        }, follow=True)
        self.assertEqual(respuesta.status_code, 200)
        usuario = Usuario.objects.get(username="nueva@x.co")
        membresia = usuario.membresias.get()
        self.assertEqual(membresia.empresa, self.empresa)
        self.assertEqual(membresia.rol, "operador")
        # El token muere al usarse
        self.assertEqual(self.client.get(f"/registro/{token}/").status_code, 410)

    def test_token_vencido_o_inventado_no_dan_pistas(self):
        invitacion, token = Invitacion.crear(self.empresa, "tarde@x.co")
        invitacion.expira = timezone.now() - timedelta(hours=1)
        invitacion.save()
        for probado in [token, "token-inventado"]:
            respuesta = self.client.get(f"/registro/{probado}/")
            self.assertEqual(respuesta.status_code, 410)
            self.assertContains(respuesta, "no es válido", status_code=410)

    def test_contrasena_debil_se_rechaza(self):
        _, token = Invitacion.crear(self.empresa, "debil@x.co")
        respuesta = self.client.post(f"/registro/{token}/", {
            "nombre": "X", "contrasena": "12345678", "confirmacion": "12345678"})
        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(Usuario.objects.filter(username="debil@x.co").exists())


class PruebasRecuperacionContrasena(TestCase):
    """§12: recuperación por enlace de un solo uso, sin revelar si el correo existe."""

    def setUp(self):
        self.usuaria = Usuario.objects.create_user(
            username="ana@x.co", email="ana@x.co", password="clave-vieja-larga-1")

    def test_respuesta_identica_exista_o_no_el_correo(self):
        from django.core import mail
        for correo in ["ana@x.co", "nadie@x.co"]:
            respuesta = self.client.post("/recuperar/", {"email": correo}, follow=True)
            self.assertContains(respuesta, "Revisa tu correo")
        self.assertEqual(len(mail.outbox), 1)  # solo al que existe, sin decirlo

    def test_flujo_completo_y_enlace_de_un_solo_uso(self):
        import re as _re
        from django.core import mail
        self.client.post("/recuperar/", {"email": "ana@x.co"})
        enlace = _re.search(r"/recuperar/[^\s]+/[^\s]+/", mail.outbox[0].body).group(0)
        # Django redirige a una URL de sesión para no dejar el token en el historial
        respuesta = self.client.get(enlace, follow=True)
        self.assertContains(respuesta, "Define tu nueva contraseña")
        url_formulario = respuesta.request["PATH_INFO"]
        respuesta = self.client.post(url_formulario, {
            "new_password1": "clave-nueva-larga-2026",
            "new_password2": "clave-nueva-larga-2026"}, follow=True)
        self.assertContains(respuesta, "Contraseña actualizada")
        self.usuaria.refresh_from_db()
        self.assertTrue(self.usuaria.check_password("clave-nueva-larga-2026"))
        # El enlace original ya no sirve
        respuesta = self.client.get(enlace, follow=True)
        self.assertContains(respuesta, "no es válido")


class PruebasMultiEmpresa(CasoConEmpresa):
    def setUp(self):
        super().setUp()
        self.otra = Empresa.objects.create(nit="800111222", razon_social="OTRA SAS")

    def test_el_selector_solo_lista_mis_empresas(self):
        respuesta = self.client.get(reverse("core:empresas"))
        self.assertContains(respuesta, "LEARNWAY")
        self.assertNotContains(respuesta, "OTRA SAS")  # invisibilidad §12

    def test_no_puedo_cambiarme_a_una_empresa_ajena(self):
        respuesta = self.client.post(reverse("core:cambiar_empresa"),
                                     {"empresa": str(self.otra.pk)}, follow=True)
        self.assertContains(respuesta, "No perteneces a esa empresa")

    def test_cambiar_de_empresa_cambia_lo_que_veo(self):
        Membresia.objects.create(usuario=self.usuario, empresa=self.otra, rol="lectura")
        FacturaCompra.objects.create(
            empresa=self.otra, cufe="zz" * 30, numero="AJENA-1",
            fecha_emision="2026-06-01", nit_emisor="1", nombre_emisor="Emisor B",
            tipo_persona_emisor="1", subtotal=100, iva=0, total=100,
            cuenta_puc="5195", nombre_cuenta_puc="Diversos",
            explicacion="x", asiento=[], xml_crudo="<x/>")
        # Con LEARNWAY activa no la veo
        self.assertNotContains(self.client.get("/causacion/"), "AJENA-1")
        # Cambio de empresa y la veo
        self.client.post(reverse("core:cambiar_empresa"),
                         {"empresa": str(self.otra.pk)})
        self.assertContains(self.client.get("/causacion/"), "AJENA-1")

    def test_solo_el_admin_invita_y_solo_a_su_empresa(self):
        respuesta = self.client.post(reverse("core:invitar"),
                                     {"correo": "colega@x.co", "rol": "operador"})
        invitacion = Invitacion.objects.get()
        self.assertEqual(invitacion.empresa, self.empresa)  # la activa, no otra
        self.assertContains(respuesta, "/registro/")

    def test_un_operador_no_puede_invitar(self):
        operador = Usuario.objects.create_user(username="op@x.co",
                                               password="clave-larga-123")
        Membresia.objects.create(usuario=operador, empresa=self.empresa, rol="operador")
        self.client.force_login(operador)
        respuesta = self.client.get(reverse("core:invitar"), follow=True)
        self.assertContains(respuesta, "Solo el administrador")
        self.assertEqual(Invitacion.objects.count(), 0)

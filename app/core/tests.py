"""
Pruebas de acceso e identidad (PLAN.md §12): sin registro abierto, tokens de
un solo uso, errores que no revelan nada e invisibilidad entre empresas.
"""
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
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


class PruebasPanelInicio(CasoConEmpresa):
    """El inicio es el panel del día: pendientes, cartera, conciliación, alertas."""

    def test_muestra_los_indicadores_del_dia(self):
        from datetime import date, timedelta
        from calendario.models import VencimientoTributario

        FacturaCompra.objects.create(
            empresa=self.empresa, cufe="aa" * 30, numero="PEND-1",
            fecha_emision=date.today(), nit_emisor="1", nombre_emisor="X",
            tipo_persona_emisor="1", subtotal=100, iva=0, total=100,
            cuenta_puc="5195", nombre_cuenta_puc="Diversos",
            explicacion="x", asiento=[], xml_crudo="<x/>")
        VencimientoTributario.objects.create(
            obligacion="Retención en la fuente", periodo="prueba",
            ultimo_digito="7", fecha=date.today() + timedelta(days=2))

        respuesta = self.client.get("/")
        self.assertContains(respuesta, "Por aprobar")
        self.assertContains(respuesta, "Cartera vencida")
        self.assertContains(respuesta, "Sin conciliar")
        self.assertContains(respuesta, "Vence pronto")
        self.assertContains(respuesta, "Retención en la fuente")
        self.assertContains(respuesta, "Cierre")  # hay un período con documentos

    def test_sin_datos_no_se_rompe(self):
        respuesta = self.client.get("/")
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Causar una factura")


@override_settings(EXIGIR_2FA=True)  # independiente del .env local (DJANGO_EXIGIR_2FA)
class Pruebas2FA(CasoConEmpresa):
    """§12: segundo factor TOTP — activación con QR y validación por sesión."""

    def token_de(self, dispositivo, corrimiento=0):
        # corrimiento=1 → código de la SIGUIENTE ventana de 30 s (el TOTP
        # rechaza reusar un código ya consumido — protección anti-repetición)
        from django_otp.oath import totp
        return f"{totp(dispositivo.bin_key, step=dispositivo.step, digits=dispositivo.digits, drift=corrimiento):06d}"

    def activar(self):
        from django_otp.plugins.otp_totp.models import TOTPDevice
        self.client.get("/seguridad/2fa/")  # crea el dispositivo sin confirmar
        dispositivo = TOTPDevice.objects.get(user=self.usuario)
        self.client.post("/seguridad/2fa/", {"token": self.token_de(dispositivo)})
        dispositivo.refresh_from_db()
        return dispositivo

    def test_el_admin_ve_el_aviso_hasta_activarlo(self):
        self.assertContains(self.client.get("/"), "segundo factor")

    def test_activacion_con_codigo_correcto(self):
        dispositivo = self.activar()
        self.assertTrue(dispositivo.confirmed)
        # Ya activo: el aviso desaparece y la sesión queda verificada
        respuesta = self.client.get("/")
        self.assertEqual(respuesta.status_code, 200)
        self.assertNotContains(respuesta, "aún no tienes segundo factor")

    def test_codigo_malo_no_activa(self):
        from django_otp.plugins.otp_totp.models import TOTPDevice
        self.client.get("/seguridad/2fa/")
        respuesta = self.client.post("/seguridad/2fa/", {"token": "000000"})
        self.assertContains(respuesta, "Código incorrecto")
        self.assertFalse(TOTPDevice.objects.get(user=self.usuario).confirmed)

    def test_sesion_nueva_exige_el_codigo(self):
        dispositivo = self.activar()
        # Sesión nueva: contraseña sí, código todavía no
        self.client.logout()
        self.client.force_login(self.usuario)
        respuesta = self.client.get("/")
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn("/verificar/", respuesta.url)
        # Código malo: sigue afuera
        respuesta = self.client.post("/verificar/", {"token": "000000"})
        self.assertContains(respuesta, "incorrecto")
        # El intento fallido activa el freno anti fuerza bruta (~1 s):
        # en la vida real se espera; en el test se resetea.
        dispositivo.refresh_from_db()
        dispositivo.throttle_reset()
        # Código bueno (de la ventana siguiente, el anterior ya se consumió): entra
        self.client.post("/verificar/", {"token": self.token_de(dispositivo, corrimiento=1)})
        self.assertEqual(self.client.get("/").status_code, 200)

    def test_sin_2fa_activo_no_se_exige_codigo(self):
        self.assertEqual(self.client.get("/").status_code, 200)

    def test_desactivado_por_config_no_exige_codigo_ni_avisa(self):
        from django.test import override_settings
        # Aunque el usuario tenga 2FA activo, con DJANGO_EXIGIR_2FA=0 no se pide
        self.activar()
        self.client.logout()
        self.client.force_login(self.usuario)
        with override_settings(EXIGIR_2FA=False):
            respuesta = self.client.get("/")
            self.assertEqual(respuesta.status_code, 200)  # no redirige a /verificar/

    def test_desactivado_no_avisa_a_los_admins(self):
        from django.test import override_settings
        with override_settings(EXIGIR_2FA=False):
            self.assertNotContains(self.client.get("/"), "segundo factor")


class PruebasCifradoEnReposo(CasoConEmpresa):
    """PLAN §10: los tokens de conexiones no viven en claro en la base."""

    def test_el_token_queda_cifrado_en_la_base_y_legible_en_el_modelo(self):
        from django.db import connection
        from causacion.models import ConexionContable
        ConexionContable.objects.create(empresa=self.empresa, proveedor="alegra",
                                        usuario="e@x.co", token="secreto-123")
        with connection.cursor() as cursor:
            cursor.execute("SELECT token FROM causacion_conexioncontable")
            crudo = cursor.fetchone()[0]
        self.assertNotIn("secreto-123", crudo)
        self.assertTrue(crudo.startswith("gAAAA"))  # marca de Fernet
        self.assertEqual(ConexionContable.objects.de_empresa(self.empresa)
                         .get().token, "secreto-123")

    def test_un_valor_heredado_en_claro_sigue_siendo_legible(self):
        from django.db import connection
        from causacion.models import ConexionContable
        conexion = ConexionContable.objects.create(
            empresa=self.empresa, proveedor="alegra", usuario="e@x.co", token="x")
        with connection.cursor() as cursor:
            cursor.execute("UPDATE causacion_conexioncontable SET token = %s "
                           "WHERE id = %s", ["token-viejo-en-claro", conexion.pk.hex])
        conexion.refresh_from_db()
        self.assertEqual(conexion.token, "token-viejo-en-claro")


class PruebasCodigosDeRespaldo(CasoConEmpresa):
    """2FA: códigos de un solo uso por si se pierde el teléfono."""

    def activar_2fa(self):
        from django_otp.oath import totp
        from django_otp.plugins.otp_totp.models import TOTPDevice
        self.client.get("/seguridad/2fa/")
        dispositivo = TOTPDevice.objects.get(user=self.usuario)
        token = f"{totp(dispositivo.bin_key, step=dispositivo.step, digits=dispositivo.digits):06d}"
        return self.client.post("/seguridad/2fa/", {"token": token})

    def test_al_activar_se_entregan_ocho_codigos(self):
        from django_otp.plugins.otp_static.models import StaticToken
        respuesta = self.activar_2fa()
        self.assertContains(respuesta, "códigos de respaldo")
        self.assertEqual(StaticToken.objects.filter(
            device__user=self.usuario).count(), 8)

    def test_un_codigo_de_respaldo_entra_una_sola_vez(self):
        from django_otp.plugins.otp_static.models import StaticToken
        self.activar_2fa()
        codigo = StaticToken.objects.filter(device__user=self.usuario).first().token
        # Sesión nueva: el código de respaldo reemplaza al de la app
        self.client.logout()
        self.client.force_login(self.usuario)
        self.client.post("/verificar/", {"token": codigo})
        self.assertEqual(self.client.get("/").status_code, 200)
        self.assertEqual(StaticToken.objects.filter(
            device__user=self.usuario).count(), 7)  # se consumió
        # El mismo código ya no sirve en otra sesión
        self.client.logout()
        self.client.force_login(self.usuario)
        respuesta = self.client.post("/verificar/", {"token": codigo})
        self.assertContains(respuesta, "incorrecto")

    def test_regenerar_invalida_los_anteriores(self):
        from django_otp.plugins.otp_static.models import StaticToken
        self.activar_2fa()
        viejos = set(StaticToken.objects.filter(
            device__user=self.usuario).values_list("token", flat=True))
        respuesta = self.client.post("/seguridad/2fa/codigos/")
        self.assertEqual(respuesta.status_code, 200)
        nuevos = set(StaticToken.objects.filter(
            device__user=self.usuario).values_list("token", flat=True))
        self.assertEqual(len(nuevos), 8)
        self.assertFalse(viejos & nuevos)


class PruebasPanelConfiguracion(CasoConEmpresa):
    """Panel de configuración de la empresa (solo admin)."""

    def test_admin_edita_los_datos_fiscales(self):
        respuesta = self.client.post(reverse("core:configuracion"), {
            "razon_social": "LEARNWAY SAS", "digito_verificacion": "7",
            "ciudad": "Medellín", "responsable_iva": "on",
            "es_agente_retencion": "on", "exonerada_parafiscales": "on",
            "tarifa_ica_por_mil": "9.66", "dias_anticipacion_alertas": "5"},
            follow=True)
        self.assertContains(respuesta, "actualizada")
        self.empresa.refresh_from_db()
        self.assertEqual(self.empresa.ciudad, "Medellín")
        self.assertEqual(self.empresa.tarifa_ica_por_mil, Decimal("9.66"))

    def test_operador_no_entra_a_configuracion(self):
        operador = Usuario.objects.create_user(username="op3@x.co",
                                               password="clave-larga-123")
        Membresia.objects.create(usuario=operador, empresa=self.empresa, rol="operador")
        self.client.force_login(operador)
        respuesta = self.client.get(reverse("core:configuracion"), follow=True)
        self.assertContains(respuesta, "Solo el administrador")


class PruebasPanelUsuarios(CasoConEmpresa):
    """Panel de usuarios: membresías, roles e invitaciones (solo admin)."""

    def setUp(self):
        super().setUp()
        self.otro = Usuario.objects.create_user(username="colega@x.co",
                                                password="clave-larga-123")
        self.membresia_otro = Membresia.objects.create(
            usuario=self.otro, empresa=self.empresa, rol="operador")

    def test_lista_los_usuarios_de_la_empresa(self):
        respuesta = self.client.get(reverse("core:usuarios"))
        self.assertContains(respuesta, "colega@x.co")

    def test_cambiar_rol_de_otro(self):
        self.client.post(reverse("core:cambiar_rol", args=[self.membresia_otro.pk]),
                         {"rol": "admin"})
        self.membresia_otro.refresh_from_db()
        self.assertEqual(self.membresia_otro.rol, "admin")

    def test_no_puedo_cambiar_mi_propio_rol(self):
        mi_membresia = Membresia.objects.get(usuario=self.usuario, empresa=self.empresa)
        respuesta = self.client.post(
            reverse("core:cambiar_rol", args=[mi_membresia.pk]),
            {"rol": "operador"}, follow=True)
        self.assertContains(respuesta, "tu propio rol")
        mi_membresia.refresh_from_db()
        self.assertEqual(mi_membresia.rol, "admin")

    def test_quitar_acceso_a_otro(self):
        self.client.post(reverse("core:quitar_usuario", args=[self.membresia_otro.pk]))
        self.assertFalse(Membresia.objects.filter(pk=self.membresia_otro.pk).exists())

    def test_no_puedo_quitarme_a_mi_mismo(self):
        mi_membresia = Membresia.objects.get(usuario=self.usuario, empresa=self.empresa)
        respuesta = self.client.post(
            reverse("core:quitar_usuario", args=[mi_membresia.pk]), follow=True)
        self.assertContains(respuesta, "a ti mismo")
        self.assertTrue(Membresia.objects.filter(pk=mi_membresia.pk).exists())

    def test_no_toca_usuarios_de_otra_empresa(self):
        otra = Empresa.objects.create(nit="800111222", razon_social="OTRA SAS")
        ajeno = Usuario.objects.create_user(username="ajeno@x.co", password="clave-larga-123")
        membresia_ajena = Membresia.objects.create(usuario=ajeno, empresa=otra, rol="admin")
        respuesta = self.client.post(
            reverse("core:quitar_usuario", args=[membresia_ajena.pk]))
        self.assertEqual(respuesta.status_code, 404)  # no es de mi empresa
        self.assertTrue(Membresia.objects.filter(pk=membresia_ajena.pk).exists())


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


@override_settings(PERMITIR_CREAR_EMPRESAS=True)
class PruebasCrearEmpresa(CasoConEmpresa):
    """Autoservicio de alta de empresa (bandera DJANGO_PERMITIR_CREAR_EMPRESAS)."""

    def test_crea_la_empresa_y_queda_como_admin_activa(self):
        antes = Empresa.objects.count()
        self.client.post(reverse("core:crear_empresa"), {
            "razon_social": "NUEVA SAS", "nit": "900999888",
            "digito_verificacion": "1", "ciudad": "Cali"})
        self.assertEqual(Empresa.objects.count(), antes + 1)
        nueva = Empresa.objects.get(nit="900999888")
        membresia = Membresia.objects.get(usuario=self.usuario, empresa=nueva)
        self.assertEqual(membresia.rol, "admin")
        # queda como empresa activa en la sesión
        self.assertEqual(self.client.session["empresa_activa"], str(nueva.id))

    def test_nit_duplicado_no_crea(self):
        respuesta = self.client.post(reverse("core:crear_empresa"), {
            "razon_social": "OTRA SAS", "nit": self.empresa.nit,
            "digito_verificacion": "", "ciudad": ""})
        self.assertContains(respuesta, "Ya existe una empresa con ese NIT")
        self.assertFalse(Empresa.objects.filter(razon_social="OTRA SAS").exists())

    @override_settings(PERMITIR_CREAR_EMPRESAS=False)
    def test_apagado_no_permite_crear(self):
        antes = Empresa.objects.count()
        respuesta = self.client.post(reverse("core:crear_empresa"), {
            "razon_social": "NO DEBE", "nit": "111222333"}, follow=True)
        self.assertEqual(Empresa.objects.count(), antes)
        self.assertContains(respuesta, "no está habilitada")

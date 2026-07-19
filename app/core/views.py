from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django_otp import devices_for_user, login as otp_login, user_has_device
from django_otp.plugins.otp_totp.models import TOTPDevice

from .forms import (
    FormularioConfiguracionEmpresa,
    FormularioCrearEmpresa,
    FormularioInvitacion,
    FormularioRegistro,
    FormularioToken2FA,
)
from .models import ROLES, Invitacion, Membresia
from .tenancy import CLAVE_SESION, cambiar_empresa, rol_en_empresa


def inicio(request):
    """Panel del día: lo que el auxiliar revisa al sentarse a trabajar.
    (Requiere sesión: el middleware la protege.)"""
    from datetime import date
    from decimal import Decimal

    from calendario.logica import alertas_de
    from causacion.cartera import edades_de_cartera
    from causacion.models import FacturaCompra, FacturaVenta
    from cierre.logica import periodos_disponibles, resumen_cierre
    from conciliacion.models import MovimientoBancario

    empresa = request.empresa

    compras_pendientes = (FacturaCompra.objects.de_empresa(empresa)
                          .filter(estado="pendiente").count())
    ventas_pendientes = (FacturaVenta.objects.de_empresa(empresa)
                         .filter(estado="pendiente").count())

    partidas, totales = edades_de_cartera(empresa)
    total_cartera = sum(totales.values())
    cartera_vencida = total_cartera - totales["corriente"]

    movimientos = MovimientoBancario.objects.de_empresa(empresa)
    sin_conciliar = movimientos.filter(estado="pendiente").count()

    alertas = alertas_de(empresa)[:4]

    periodos = periodos_disponibles(empresa)
    cierre_mes = None
    if periodos:
        periodo = periodos[0]
        cierre_mes = {"periodo": periodo,
                      "resumen": resumen_cierre(empresa, periodo.year, periodo.month)}

    # §12: el 2FA es obligatorio para administradores — aviso hasta activarlo.
    # Si está desactivado por config (DJANGO_EXIGIR_2FA=0), no se avisa.
    aviso_2fa = (settings.EXIGIR_2FA
                 and rol_en_empresa(request, empresa) == "admin"
                 and not user_has_device(request.user, confirmed=True))

    return render(request, "core/inicio.html", {
        "aviso_2fa": aviso_2fa,
        "compras_pendientes": compras_pendientes,
        "ventas_pendientes": ventas_pendientes,
        "por_aprobar": compras_pendientes + ventas_pendientes,
        "total_cartera": total_cartera,
        "cartera_vencida": cartera_vencida,
        "sin_conciliar": sin_conciliar,
        "alertas": alertas,
        "cierre_mes": cierre_mes,
        "hoy": date.today(),
    })


def sin_empresa(request):
    """Usuario autenticado sin membresías: cuenta huérfana, no ve datos."""
    return render(request, "core/sin_empresa.html",
                  {"puede_crear_empresa": settings.PERMITIR_CREAR_EMPRESAS})


def crear_empresa(request):
    """Autoservicio de alta de empresa (§12): quien la crea queda como admin.
    Solo disponible si DJANGO_PERMITIR_CREAR_EMPRESAS=1."""
    if not settings.PERMITIR_CREAR_EMPRESAS:
        messages.error(request, "La creación de empresas no está habilitada.")
        return redirect("core:empresas")

    formulario = FormularioCrearEmpresa(request.POST or None)
    if request.method == "POST" and formulario.is_valid():
        empresa = formulario.save()
        Membresia.objects.create(usuario=request.user, empresa=empresa, rol="admin")
        request.session[CLAVE_SESION] = str(empresa.id)  # queda como activa
        # Como los software contables: la empresa nace con el PUC estándar del
        # sector real hasta subcuenta; el contador agrega sus auxiliares.
        from causacion.puc_estandar import sembrar_puc_estandar
        sembradas = sembrar_puc_estandar(empresa)
        messages.success(
            request, f"Empresa «{empresa.razon_social}» creada con el plan de "
            f"cuentas estándar ({sembradas} cuentas del PUC sector real). "
            "Completa sus datos fiscales para empezar a causar.")
        return redirect("core:configuracion")

    return render(request, "core/crear_empresa.html", {"formulario": formulario})


def registro(request, token):
    """Matrícula por token de un solo uso (PLAN.md §12).

    El mensaje de error nunca distingue entre token inexistente, vencido o ya
    usado — no dar pistas.
    """
    invitacion = Invitacion.buscar_valida(token)
    if invitacion is None:
        return render(request, "core/registro_invalido.html", status=410)

    formulario = FormularioRegistro(request.POST or None)
    if request.method == "POST" and formulario.is_valid():
        Usuario = get_user_model()
        usuario = Usuario.objects.filter(username=invitacion.correo).first()
        if usuario is None:
            usuario = Usuario.objects.create_user(
                username=invitacion.correo,
                email=invitacion.correo,
                first_name=formulario.cleaned_data["nombre"],
                password=formulario.cleaned_data["contrasena"],
            )
        Membresia.objects.get_or_create(
            usuario=usuario, empresa=invitacion.empresa,
            defaults={"rol": invitacion.rol})
        invitacion.marcar_usada()  # el token muere al usarse
        login(request, usuario,
              backend="django.contrib.auth.backends.ModelBackend")
        messages.success(request, f"Bienvenido. Quedaste vinculado a "
                                  f"{invitacion.empresa.razon_social}.")
        return redirect("core:inicio")

    return render(request, "core/registro.html", {
        "formulario": formulario,
        "correo": invitacion.correo,
        "empresa": invitacion.empresa,
    })


def _qr_svg(texto):
    """QR como SVG embebible (sin dependencia de imágenes)."""
    import qrcode
    import qrcode.image.svg
    imagen = qrcode.make(texto, image_factory=qrcode.image.svg.SvgPathImage,
                         box_size=12)
    return imagen.to_string().decode()


def _generar_codigos_respaldo(usuario):
    """8 códigos de un solo uso por si se pierde el teléfono. Regenerarlos
    invalida los anteriores."""
    from django_otp.plugins.otp_static.models import StaticDevice, StaticToken
    dispositivo, _ = StaticDevice.objects.get_or_create(
        user=usuario, name="Códigos de respaldo", defaults={"confirmed": True})
    dispositivo.confirmed = True
    dispositivo.save(update_fields=["confirmed"])
    dispositivo.token_set.all().delete()
    codigos = [StaticToken.random_token() for _ in range(8)]
    for codigo in codigos:
        dispositivo.token_set.create(token=codigo)
    return codigos


@require_POST
def regenerar_codigos(request):
    """Nuevos códigos de respaldo (solo con la sesión ya verificada)."""
    if not (request.user.is_verified() and user_has_device(request.user, confirmed=True)):
        return redirect("core:configurar_2fa")
    codigos = _generar_codigos_respaldo(request.user)
    messages.success(request, "Códigos de respaldo regenerados: los anteriores ya no sirven.")
    return render(request, "core/2fa_codigos.html", {"codigos": codigos})


def configurar_2fa(request):
    """Activar el segundo factor TOTP (§12): escanear el QR y confirmar."""
    if user_has_device(request.user, confirmed=True):
        return render(request, "core/2fa_activo.html")

    dispositivo = TOTPDevice.objects.filter(user=request.user,
                                            confirmed=False).first()
    if dispositivo is None:
        dispositivo = TOTPDevice.objects.create(
            user=request.user, name="Aplicación de autenticación", confirmed=False)

    formulario = FormularioToken2FA(request.POST or None)
    if request.method == "POST" and formulario.is_valid():
        if dispositivo.verify_token(formulario.cleaned_data["token"]):
            dispositivo.confirmed = True
            dispositivo.save(update_fields=["confirmed"])
            otp_login(request, dispositivo)
            messages.success(request, "Segundo factor activado: desde ahora el "
                                      "ingreso pedirá el código de tu aplicación.")
            return render(request, "core/2fa_codigos.html", {
                "codigos": _generar_codigos_respaldo(request.user),
            })
        formulario.add_error("token", "Código incorrecto: revisa la app y el reloj del teléfono.")

    import base64
    return render(request, "core/2fa_configurar.html", {
        "formulario": formulario,
        "qr": _qr_svg(dispositivo.config_url),
        "clave": base64.b32encode(dispositivo.bin_key).decode(),
    })


def verificar_2fa(request):
    """Validación del código en cada sesión de un usuario con 2FA activo."""
    if request.user.is_verified():
        return redirect("core:inicio")
    formulario = FormularioToken2FA(request.POST or None)
    if request.method == "POST" and formulario.is_valid():
        token = formulario.cleaned_data["token"]
        for dispositivo in devices_for_user(request.user, confirmed=True):
            if dispositivo.verify_token(token):
                otp_login(request, dispositivo)
                return redirect("core:inicio")
        formulario.add_error("token", "Código incorrecto o vencido.")
    return render(request, "core/2fa_verificar.html", {"formulario": formulario})


def empresas(request):
    """Selector de empresa activa: SOLO las membresías propias (PLAN.md §12:
    ningún endpoint lista empresas ajenas)."""
    membresias = request.user.membresias.select_related("empresa").order_by("creada")
    return render(request, "core/empresas.html", {
        "membresias": membresias,
        "es_admin": rol_en_empresa(request, request.empresa) == "admin",
        "puede_crear_empresa": settings.PERMITIR_CREAR_EMPRESAS,
    })


def _exige_admin(request):
    return rol_en_empresa(request, request.empresa) == "admin"


def configuracion(request):
    """Panel de configuración de la empresa activa (solo admin)."""
    if not _exige_admin(request):
        messages.error(request, "Solo el administrador de la empresa puede "
                                "cambiar la configuración.")
        return redirect("core:inicio")
    formulario = FormularioConfiguracionEmpresa(
        request.POST or None, instance=request.empresa)
    if request.method == "POST" and formulario.is_valid():
        formulario.save()
        messages.success(request, "Configuración de la empresa actualizada.")
        return redirect("core:configuracion")
    return render(request, "core/configuracion.html", {"formulario": formulario})


def usuarios(request):
    """Panel de usuarios de la empresa: membresías + invitaciones (solo admin)."""
    if not _exige_admin(request):
        messages.error(request, "Solo el administrador puede gestionar usuarios.")
        return redirect("core:inicio")
    empresa = request.empresa
    from django.utils import timezone
    return render(request, "core/usuarios.html", {
        "membresias": empresa.membresias.select_related("usuario").order_by("creada"),
        "invitaciones": empresa.invitaciones.filter(
            usada_en__isnull=True, expira__gt=timezone.now()).order_by("-creada"),
        "roles": ROLES,
        "yo": request.user.pk,
    })


@require_POST
def cambiar_rol(request, membresia_id):
    if not _exige_admin(request):
        return redirect("core:inicio")
    membresia = get_object_or_404(
        Membresia, pk=membresia_id, empresa=request.empresa)
    rol = request.POST.get("rol")
    if rol in dict(ROLES) and membresia.usuario_id != request.user.pk:
        membresia.rol = rol
        membresia.save(update_fields=["rol"])
        messages.success(request, f"Rol de {membresia.usuario} actualizado.")
    else:
        messages.error(request, "No puedes cambiar tu propio rol.")
    return redirect("core:usuarios")


@require_POST
def quitar_usuario(request, membresia_id):
    if not _exige_admin(request):
        return redirect("core:inicio")
    membresia = get_object_or_404(
        Membresia, pk=membresia_id, empresa=request.empresa)
    if membresia.usuario_id == request.user.pk:
        messages.error(request, "No puedes quitarte a ti mismo.")
    else:
        nombre = str(membresia.usuario)
        membresia.delete()
        messages.info(request, f"{nombre} ya no tiene acceso a la empresa.")
    return redirect("core:usuarios")


@require_POST
def revocar_invitacion(request, invitacion_id):
    if not _exige_admin(request):
        return redirect("core:inicio")
    invitacion = get_object_or_404(
        Invitacion, pk=invitacion_id, empresa=request.empresa)
    invitacion.delete()
    messages.info(request, "Invitación revocada.")
    return redirect("core:usuarios")


@require_POST
def cambiar(request):
    if cambiar_empresa(request, request.POST.get("empresa", "")):
        messages.success(request, "Empresa activa cambiada.")
    else:
        messages.error(request, "No perteneces a esa empresa.")
    return redirect("core:inicio")


def invitar(request):
    """Solo el admin de la empresa activa invita, y solo a SU empresa."""
    if rol_en_empresa(request, request.empresa) != "admin":
        messages.error(request, "Solo el administrador de la empresa puede invitar usuarios.")
        return redirect("core:empresas")

    formulario = FormularioInvitacion(request.POST or None)
    enlace = None
    if request.method == "POST" and formulario.is_valid():
        invitacion, token = Invitacion.crear(
            request.empresa,
            formulario.cleaned_data["correo"],
            formulario.cleaned_data["rol"],
        )
        enlace = request.build_absolute_uri(f"/registro/{token}/")
        send_mail(
            subject=f"Invitación a Auxiliar Contable — {request.empresa.razon_social}",
            message=(f"Te invitaron a la empresa {request.empresa.razon_social}.\n"
                     f"Completa tu registro aquí (el enlace vence en 72 horas):\n{enlace}"),
            from_email=None,
            recipient_list=[invitacion.correo],
        )
        messages.success(request, f"Invitación creada para {invitacion.correo} "
                                  "(vence en 72 horas).")
    return render(request, "core/invitar.html", {
        "formulario": FormularioInvitacion() if enlace else formulario,
        "enlace": enlace,
    })

from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.core.mail import send_mail
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST
from django_otp import devices_for_user, login as otp_login, user_has_device
from django_otp.plugins.otp_totp.models import TOTPDevice

from .forms import FormularioInvitacion, FormularioRegistro, FormularioToken2FA
from .models import Invitacion, Membresia
from .tenancy import cambiar_empresa, rol_en_empresa


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

    # §12: el 2FA es obligatorio para administradores — aviso hasta activarlo
    aviso_2fa = (rol_en_empresa(request, empresa) == "admin"
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
    return render(request, "core/sin_empresa.html")


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
            return redirect("core:inicio")
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
    })


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

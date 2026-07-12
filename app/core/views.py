from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.core.mail import send_mail
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from .forms import FormularioInvitacion, FormularioRegistro
from .models import Invitacion, Membresia
from .tenancy import cambiar_empresa, rol_en_empresa


def inicio(request):
    """Página de inicio (requiere sesión: el middleware la protege)."""
    return render(request, "core/inicio.html")


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

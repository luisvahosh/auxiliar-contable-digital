from django.contrib.auth import views as vistas_auth
from django.urls import path, reverse_lazy

from . import views
from .forms import FormularioLogin

app_name = "core"

urlpatterns = [
    path("", views.inicio, name="inicio"),
    # Recuperación de contraseña (§12: enlace de un solo uso, sin revelar
    # si el correo existe — Django responde igual en ambos casos)
    path("recuperar/", vistas_auth.PasswordResetView.as_view(
        template_name="core/recuperar.html",
        email_template_name="core/correo_recuperacion.txt",
        subject_template_name="core/correo_recuperacion_asunto.txt",
        success_url=reverse_lazy("core:password_reset_done"),
    ), name="password_reset"),
    path("recuperar/enviado/", vistas_auth.PasswordResetDoneView.as_view(
        template_name="core/recuperar_enviado.html"), name="password_reset_done"),
    path("recuperar/listo/", vistas_auth.PasswordResetCompleteView.as_view(
        template_name="core/recuperar_listo.html"), name="password_reset_complete"),
    path("recuperar/<uidb64>/<token>/", vistas_auth.PasswordResetConfirmView.as_view(
        template_name="core/recuperar_confirmar.html",
        success_url=reverse_lazy("core:password_reset_complete"),
    ), name="password_reset_confirm"),
    path("login/", vistas_auth.LoginView.as_view(
        template_name="core/login.html",
        authentication_form=FormularioLogin,
        redirect_authenticated_user=True,
    ), name="login"),
    path("salir/", vistas_auth.LogoutView.as_view(), name="logout"),
    path("registro/<str:token>/", views.registro, name="registro"),
    path("seguridad/2fa/", views.configurar_2fa, name="configurar_2fa"),
    path("seguridad/2fa/codigos/", views.regenerar_codigos, name="regenerar_codigos"),
    path("verificar/", views.verificar_2fa, name="verificar_2fa"),
    path("empresas/", views.empresas, name="empresas"),
    path("empresas/crear/", views.crear_empresa, name="crear_empresa"),
    path("empresas/cambiar/", views.cambiar, name="cambiar_empresa"),
    path("empresas/invitar/", views.invitar, name="invitar"),
    path("configuracion/", views.configuracion, name="configuracion"),
    path("usuarios/", views.usuarios, name="usuarios"),
    path("usuarios/<uuid:membresia_id>/rol/", views.cambiar_rol, name="cambiar_rol"),
    path("usuarios/<uuid:membresia_id>/quitar/", views.quitar_usuario, name="quitar_usuario"),
    path("invitaciones/<uuid:invitacion_id>/revocar/", views.revocar_invitacion,
         name="revocar_invitacion"),
    path("sin-empresa/", views.sin_empresa, name="sin_empresa"),
]
